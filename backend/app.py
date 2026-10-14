"""
Flask 后端主程序
提供代码执行、代码补全、文件管理等功能
"""
import os
import re
import sys
import json
import shutil
import logging
import secrets
import subprocess
import tempfile
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# 添加项目根目录和backend目录到sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
backend_dir = os.path.dirname(__file__)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 项目级解释器路径（backend/.venv，由 uv 管理）
# 不再硬编码任何全局 Python 路径
from env_config import PYTHON_EXE as PROJECT_PYTHON

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_dotenv(path):
    """极简 .env 加载器：仅填充尚未存在的环境变量，不覆盖已有值。

    避免引入额外依赖，同时让密钥、令牌、执行限制等配置可以放在 .env 中。
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except FileNotFoundError:
        pass
    except OSError as e:
        logger.warning(f"读取 .env 失败 ({path}): {e}")


# 项目根目录与 backend 目录下的 .env 均会被加载
_load_dotenv(os.path.join(project_root, '.env'))
_load_dotenv(os.path.join(backend_dir, '.env'))

# 创建Flask应用
app = Flask(__name__)

# 上传体积上限，避免磁盘被写满
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('WEBIDE_MAX_UPLOAD_MB', '50')) * 1024 * 1024

# 跨域策略：仅允许本地前端开发服务器，避免任意网页读取本机 API 响应
ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://[::1]:5173',
]
CORS(app, origins=ALLOWED_ORIGINS,
     allow_headers=['Content-Type', 'X-Auth-Token', 'X-Session-Id'])

# ==================== 访问控制 ====================
# 本服务对外暴露的能力包含「执行代码」「执行系统命令」「读写文件」，
# 因此必须做访问控制，否则等同于把机器控制权交给任意能访问 5000 端口的人。
#
# 令牌来源优先级：
#   1. 环境变量 WEBIDE_AUTH_TOKEN
#   2. backend/.webide_token 文件（不存在则自动生成）
# 前端开发服务器（vite.config.js）在代理层自动注入该令牌，
# 浏览器端不持有令牌，直接访问 5000 端口将被拒绝。

TOKEN_FILE = os.path.join(backend_dir, '.webide_token')


def _load_or_create_token():
    env_token = os.environ.get('WEBIDE_AUTH_TOKEN')
    if env_token and env_token.strip():
        return env_token.strip()

    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                token = f.read().strip()
            if token:
                return token
    except OSError as e:
        logger.warning(f"读取令牌文件失败: {e}")

    token = secrets.token_urlsafe(32)
    try:
        with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
            f.write(token)
        logger.info(f"已生成访问令牌，存放于: {TOKEN_FILE}")
    except OSError as e:
        logger.error(f"写入令牌文件失败，本次仅使用内存令牌: {e}")
    return token


AUTH_TOKEN = _load_or_create_token()

# 令牌校验豁免的路径（健康检查等）
AUTH_EXEMPT_PATHS = set()


@app.before_request
def _enforce_auth():
    """对所有路由统一强制令牌校验，避免遗漏单个端点"""
    if request.method == 'OPTIONS':          # CORS 预检请求放行
        return None
    if request.path in AUTH_EXEMPT_PATHS:
        return None

    supplied = request.headers.get('X-Auth-Token') or request.args.get('token')
    if supplied and secrets.compare_digest(str(supplied), AUTH_TOKEN):
        return None

    logger.warning(f"未授权访问被拒绝: {request.method} {request.path} from {request.remote_addr}")
    return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401


# ==================== 路径安全 ====================
# 所有来自请求的文件路径都必须经过这里解析，禁止：
#   - 绝对路径 / 盘符（Windows 下 os.path.join 会丢弃前面的 root）
#   - 任何形式的 ".." 上跳
#   - 解析后越出允许的根目录

# 工作区根目录：仓库根（project/ 等）与后端 files/ 目录
WORKSPACE_ROOT = project_root
FILES_ROOT = os.path.join(backend_dir, 'files')

# 只读目录（相对于 WORKSPACE_ROOT 的 posix 路径）
READONLY_DIRS = {'project/toolBox'}


def normalize_user_path(raw):
    """校验并归一化用户提供的路径，返回 posix 风格的相对路径。

    非法路径一律抛 ValueError。
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError('路径不能为空')

    # 统一分隔符后判断
    p = raw.replace('\\', '/').strip()

    if os.path.isabs(raw) or p.startswith('/') or re.match(r'^[A-Za-z]:', p):
        raise ValueError('不允许使用绝对路径')

    segments = [seg for seg in p.split('/') if seg not in ('', '.')]
    if any(seg == '..' for seg in segments):
        raise ValueError('路径不得包含 ..')
    if not segments:
        raise ValueError('无效路径')

    return '/'.join(segments)


def resolve_under(root, rel_posix):
    """把相对路径解析到 root 之下，并校验未越界，返回绝对路径"""
    root_abs = os.path.realpath(root)
    target = os.path.realpath(os.path.join(root_abs, *rel_posix.split('/')))
    try:
        if os.path.commonpath([root_abs, target]) != root_abs:
            raise ValueError('路径越界')
    except ValueError:
        # 不同盘符等情况 commonpath 会抛错
        raise ValueError('路径越界')
    return target


def resolve_in_workspace(rel_posix):
    """解析相对于仓库根（WORKSPACE_ROOT）的路径"""
    return resolve_under(WORKSPACE_ROOT, rel_posix)


def resolve_workspace_path(raw_path):
    """解析 /load 与 /save 使用的路径。

    约定：以 project/ 开头者相对于仓库根，其余相对于 backend/files。
    返回 (绝对路径, 归一化后的 posix 相对路径)。
    """
    rel = normalize_user_path(raw_path)
    if rel == 'project' or rel.startswith('project/'):
        return resolve_in_workspace(rel), rel
    return resolve_under(FILES_ROOT, rel), rel


def is_readonly_path(rel_posix):
    """检查归一化后的相对路径是否位于只读目录中"""
    normalized = rel_posix.replace('\\', '/')
    for readonly_dir in READONLY_DIRS:
        if normalized == readonly_dir or normalized.startswith(readonly_dir + '/'):
            return True
    return False


# ==================== 错误信息脱敏 ====================
# 数据分析场景下，工具自身的校验提示（如「列 'age' 不存在」）对使用者有实际价值，
# 一律替换为通用文案会显著降低可用性。因此这里采取折中：
# 保留可读的校验信息，但剥离绝对路径等可能暴露内部结构的片段。

_ABS_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:\\[^\s'\"]*"),          # Windows: D:\a\b\c
    re.compile(r"(?<![\w:/])/(?:[\w.\-]+/)+[\w.\-]*"),  # POSIX: /a/b/c
)


def sanitize_error(exc, fallback='Operation failed', max_length=300):
    """把异常信息转为可对外返回的文案：剥离绝对路径并限制长度"""
    try:
        text = str(exc).strip()
    except Exception:
        return fallback

    if not text:
        return fallback

    for pattern in _ABS_PATH_PATTERNS:
        text = pattern.sub('<path>', text)

    text = text.strip()
    if not text or len(text) > max_length:
        return fallback
    return text


# ==================== 受限执行 ====================
# 本服务允许执行代码与系统命令，因此必须对子进程施加资源限制。
#
# 重要说明：这里是「资源限制」，不是「安全沙箱」。
# 它能防止内存炸弹、fork 炸弹、无限循环、输出洪水、磁盘写满；
# 但无法阻止进程读写文件系统或访问网络。真正的隔离需要容器或受限用户，
# 详见 安全审计报告.md。

EXEC_TIMEOUT = int(os.environ.get('WEBIDE_EXEC_TIMEOUT', '30'))                 # 秒
EXEC_MEMORY_MB = int(os.environ.get('WEBIDE_EXEC_MEMORY_MB', '1024'))           # 单进程内存上限
EXEC_MAX_PROCS = int(os.environ.get('WEBIDE_EXEC_MAX_PROCS', '32'))             # 并发子进程上限
EXEC_MAX_OUTPUT = int(os.environ.get('WEBIDE_EXEC_MAX_OUTPUT_KB', '200')) * 1024
EXEC_MAX_CODE = int(os.environ.get('WEBIDE_EXEC_MAX_CODE_KB', '100')) * 1024
EXEC_ISOLATED = os.environ.get('WEBIDE_EXEC_ISOLATED', '1').strip() not in ('0', 'false', 'no')

# 代码执行的临时工作目录（与仓库隔离，避免污染项目文件）
EXEC_SCRATCH_DIR = os.path.join(backend_dir, '.exec_scratch')


def _kill_process_tree(proc):
    """终止整棵进程树（仅杀父进程会留下孤儿子进程）"""
    try:
        if os.name == 'nt':
            subprocess.run(
                ['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                capture_output=True, shell=False, timeout=10
            )
        else:
            import signal
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _create_windows_job(memory_mb, max_procs):
    """创建带内存与并发进程上限的 Windows Job Object，失败返回 None（静默降级）"""
    if os.name != 'nt':
        return None
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

        JobObjectExtendedLimitInformation = 9
        LIMIT_PROCESS_MEMORY = 0x00000100
        LIMIT_ACTIVE_PROCESS = 0x00000008
        LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [('ReadOperationCount', ctypes.c_ulonglong),
                        ('WriteOperationCount', ctypes.c_ulonglong),
                        ('OtherOperationCount', ctypes.c_ulonglong),
                        ('ReadTransferCount', ctypes.c_ulonglong),
                        ('WriteTransferCount', ctypes.c_ulonglong),
                        ('OtherTransferCount', ctypes.c_ulonglong)]

        class BASIC_LIMIT(ctypes.Structure):
            _fields_ = [('PerProcessUserTimeLimit', ctypes.c_longlong),
                        ('PerJobUserTimeLimit', ctypes.c_longlong),
                        ('LimitFlags', wintypes.DWORD),
                        ('MinimumWorkingSetSize', ctypes.c_size_t),
                        ('MaximumWorkingSetSize', ctypes.c_size_t),
                        ('ActiveProcessLimit', wintypes.DWORD),
                        ('Affinity', ctypes.c_size_t),
                        ('PriorityClass', wintypes.DWORD),
                        ('SchedulingClass', wintypes.DWORD)]

        class EXTENDED_LIMIT(ctypes.Structure):
            _fields_ = [('BasicLimitInformation', BASIC_LIMIT),
                        ('IoInfo', IO_COUNTERS),
                        ('ProcessMemoryLimit', ctypes.c_size_t),
                        ('JobMemoryLimit', ctypes.c_size_t),
                        ('PeakProcessMemoryUsed', ctypes.c_size_t),
                        ('PeakJobMemoryUsed', ctypes.c_size_t)]

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None

        info = EXTENDED_LIMIT()
        info.BasicLimitInformation.LimitFlags = (
            LIMIT_PROCESS_MEMORY | LIMIT_ACTIVE_PROCESS | LIMIT_KILL_ON_JOB_CLOSE
        )
        info.BasicLimitInformation.ActiveProcessLimit = max(1, max_procs)
        info.ProcessMemoryLimit = memory_mb * 1024 * 1024

        ok = kernel32.SetInformationJobObject(
            job, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info)
        )
        if not ok:
            kernel32.CloseHandle(job)
            return None
        return job
    except Exception as e:
        logger.warning(f"创建 Windows Job Object 失败，本次不施加内存/进程数限制: {e}")
        return None


def _assign_to_job(job, proc):
    if not job or os.name != 'nt':
        return
    try:
        import ctypes
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.AssignProcessToJobObject(job, int(proc._handle))
    except Exception as e:
        logger.warning(f"将子进程加入 Job Object 失败: {e}")


def _close_job(job):
    if not job or os.name != 'nt':
        return
    try:
        import ctypes
        ctypes.WinDLL('kernel32').CloseHandle(job)
    except Exception:
        pass


def build_restricted_env():
    """构造最小化环境变量，避免把服务进程的敏感变量透传给子进程"""
    keep = ('PATH', 'SystemRoot', 'SYSTEMROOT', 'TEMP', 'TMP', 'PATHEXT', 'COMSPEC',
            'windir', 'NUMBER_OF_PROCESSORS', 'PROCESSOR_ARCHITECTURE',
            'USERPROFILE', 'HOMEDRIVE', 'HOMEPATH', 'LANG', 'LC_ALL')
    env = {k: os.environ[k] for k in keep if k in os.environ}
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def run_limited(cmd, timeout=None, cwd=None, env=None):
    """以受限方式执行命令。

    返回 (returncode, output, timed_out, truncated)。
    输出合并 stdout 与 stderr，并按上限截断。
    """
    timeout = timeout or EXEC_TIMEOUT
    env = env if env is not None else build_restricted_env()

    job = _create_windows_job(EXEC_MEMORY_MB, EXEC_MAX_PROCS)

    kwargs = dict(
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        cwd=cwd,
        env=env,
    )
    if os.name == 'nt':
        kwargs['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    else:
        kwargs['start_new_session'] = True

    proc = subprocess.Popen(cmd, **kwargs)
    _assign_to_job(job, proc)

    timed_out = False
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_process_tree(proc)
        try:
            out, _ = proc.communicate(timeout=5)
        except Exception:
            out = ''
    finally:
        _close_job(job)

    truncated = False
    if out and len(out) > EXEC_MAX_OUTPUT:
        out = out[:EXEC_MAX_OUTPUT]
        truncated = True

    return proc.returncode, (out or ''), timed_out, truncated


# ==================== 终端命令策略 ====================
DEFAULT_TERMINAL_ALLOWLIST = {
    'python', 'python3', 'py', 'pip', 'pip3', 'uv', 'pytest',
    'node', 'npm', 'npx', 'pnpm', 'yarn',
    'git', 'ls', 'dir', 'pwd', 'cd', 'echo', 'type', 'cat',
    'findstr', 'grep', 'where', 'which', 'head', 'tail', 'more',
    'mkdir', 'md', 'touch', 'copy', 'cp', 'move', 'mv',
    'date', 'time', 'ver', 'whoami', 'hostname', 'set',
    'ruff', 'black', 'mypy',
}

# 受限模式下禁止的 shell 元字符（阻断串联、管道、重定向、命令替换）
SHELL_METACHARS = (';', '&&', '||', '|', '`', '$(', '>', '<', '\n', '\r')


def _terminal_unrestricted():
    return os.environ.get('WEBIDE_TERMINAL_UNRESTRICTED', '').strip().lower() in ('1', 'true', 'yes')


def _terminal_allowlist():
    extra = os.environ.get('WEBIDE_TERMINAL_ALLOWLIST', '')
    return DEFAULT_TERMINAL_ALLOWLIST | {c.strip().lower() for c in extra.split(',') if c.strip()}


def validate_terminal_command(command):
    """校验终端命令，返回 (是否允许, 拒绝原因)"""
    if not isinstance(command, str) or not command.strip():
        return False, 'empty command'

    if _terminal_unrestricted():
        return True, ''

    cmd = command.strip()
    for meta in SHELL_METACHARS:
        if meta in cmd:
            return False, f"command contains forbidden shell operator: {meta!r}"

    base = os.path.basename(cmd.split()[0]).lower()
    if base.endswith('.exe'):
        base = base[:-4]

    if base not in _terminal_allowlist():
        return False, f"command not in allowlist: {base}"
    return True, ''


# 导入注册表
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'system_registry',
        os.path.join(backend_dir, 'toolBox', 'system_registry.py')
    )
    registry_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(registry_module)
    analysis_toolbox = registry_module.analysis_toolbox
    logger.info(f"成功导入工具注册表，共 {len(analysis_toolbox)} 个阶段")
except Exception as e:
    logger.error(f"导入工具注册表失败: {str(e)}")
    analysis_toolbox = []

# ==================== 代码执行功能 ====================
@app.route('/run', methods=['POST'])
def run_code():
    """
    执行 Python 代码。

    受限项：代码体积上限、执行超时（超时终止整棵进程树）、单进程内存上限、
    并发子进程上限、输出体积上限。临时文件写入独立 scratch 目录并在 finally 中清理。
    """
    data = request.json or {}
    code = data.get('code', '')

    if not code or not code.strip():
        return jsonify({'status': 'error', 'output': 'No code provided'})

    if len(code.encode('utf-8')) > EXEC_MAX_CODE:
        return jsonify({
            'status': 'error',
            'output': f'代码体积超出上限（{EXEC_MAX_CODE // 1024} KB）'
        })

    if not os.path.exists(PROJECT_PYTHON):
        logger.error(f"项目解释器不存在: {PROJECT_PYTHON}")
        return jsonify({'status': 'error', 'output': 'Python interpreter not found'})

    os.makedirs(EXEC_SCRATCH_DIR, exist_ok=True)

    # 唯一文件名，避免并发请求互相覆盖
    fd, temp_file = tempfile.mkstemp(prefix='run_', suffix='.py', dir=EXEC_SCRATCH_DIR)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(code)

        cmd = [PROJECT_PYTHON]
        if EXEC_ISOLATED:
            cmd.append('-I')      # 隔离模式：忽略 PYTHON* 环境变量与用户 site 目录
        cmd.append(temp_file)

        returncode, output, timed_out, truncated = run_limited(
            cmd, timeout=EXEC_TIMEOUT, cwd=EXEC_SCRATCH_DIR
        )

        if timed_out:
            return jsonify({
                'status': 'error',
                'output': f'代码执行超时（超过 {EXEC_TIMEOUT} 秒，已终止进程树）\n' + output
            })

        if truncated:
            output += f"\n...[输出超过 {EXEC_MAX_OUTPUT // 1024} KB，已截断]"

        return jsonify({
            'status': 'success',
            'output': output,
            'returncode': returncode
        })
    except Exception as e:
        logger.error(f"代码执行失败: {str(e)}")
        return jsonify({'status': 'error', 'output': 'Code execution failed'})
    finally:
        try:
            os.remove(temp_file)
        except OSError:
            pass

# ==================== AI 对话功能 ====================
# 所有 AI 配置统一来自 config/ai_config.json（全局唯一配置入口），
# 本文件不得再硬编码模型名、base_url 或密钥。
from config import (
    get_ai_config,
    reload_ai_config,
    is_ai_configured,
    describe_missing_config,
)

# openai SDK 延迟到调用时导入：未安装时服务仍可正常启动，仅 AI 接口返回明确提示
try:
    import openai
except ImportError:      # pragma: no cover - 取决于运行环境
    openai = None


@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """
    AI 对话接口（配置与密钥均来自 config/ai_config.json）
    """
    if openai is None:
        return jsonify({
            'status': 'error',
            'message': 'AI 依赖未安装：请执行 uv sync 安装 openai'
        })

    if not is_ai_configured():
        reason = describe_missing_config()
        logger.error(f"AI 对话失败: {reason}")
        return jsonify({'status': 'error', 'message': reason})

    cfg = get_ai_config()

    try:
        data = request.json or {}
        messages = data.get('messages', [])

        if not messages:
            return jsonify({'status': 'error', 'message': 'No messages provided'})

        # 限制上下文长度，避免被用于刷取上游配额
        max_messages = int(cfg.get('max_context_messages') or 20)
        if len(messages) > max_messages:
            messages = messages[-max_messages:]

        generation = cfg.get('generation') or {}
        client = openai.OpenAI(
            api_key=cfg.get('api_key'),
            base_url=cfg.get('base_url'),
            timeout=cfg.get('request_timeout') or 60,
        )

        response = client.chat.completions.create(
            model=cfg.get('default_model'),
            messages=messages,
            temperature=generation.get('temperature', 0.7),
            max_tokens=generation.get('max_tokens', 2048),
        )

        return jsonify({
            'status': 'success',
            'data': {
                'content': response.choices[0].message.content,
                'model': response.model,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                    'completion_tokens': response.usage.completion_tokens if response.usage else 0
                }
            }
        })
    except Exception as e:
        logger.error(f"AI 对话失败: {str(e)}")
        return jsonify({'status': 'error', 'message': 'AI request failed'})

@app.route('/api/ai/models', methods=['GET'])
def get_ai_models():
    """
    获取可用的 AI 模型列表（来自 config/ai_config.json 的 available_models）
    """
    cfg = get_ai_config()
    models = cfg.get('available_models') or []
    if not models:
        models = [{
            'id': cfg.get('default_model'),
            'name': cfg.get('default_model'),
            'description': ''
        }]

    return jsonify({
        'status': 'success',
        'data': models,
        'default': cfg.get('default_model'),
        'configured': is_ai_configured(),
    })

@app.route('/api/ai/config', methods=['GET'])
def get_ai_config_summary():
    """
    返回当前生效的 AI 配置摘要（不含密钥），便于前端与排查使用
    """
    cfg = get_ai_config()
    return jsonify({
        'status': 'success',
        'data': {
            'enabled': cfg.get('enabled'),
            'provider': cfg.get('provider'),
            'default_model': cfg.get('default_model'),
            'base_url': cfg.get('base_url'),
            'has_api_key': bool(str(cfg.get('api_key') or '').strip()),
            'max_context_messages': cfg.get('max_context_messages'),
            'request_timeout': cfg.get('request_timeout'),
        }
    })

@app.route('/api/ai/reload', methods=['POST'])
def reload_ai():
    """
    重新加载 AI 配置文件，无需重启服务
    """
    cfg = reload_ai_config()
    logger.info("AI 配置已重新加载")
    return jsonify({
        'status': 'success',
        'data': {
            'default_model': cfg.get('default_model'),
            'has_api_key': bool(str(cfg.get('api_key') or '').strip()),
        }
    })

# ==================== 代码补全功能 ====================
# 代码补全使用项目级虚拟环境的解释器（backend/.venv 内已安装 jedi）
SYSTEM_PYTHON = PROJECT_PYTHON

# 固定的 jedi 执行脚本：不包含任何用户输入，用户代码经临时文件传入
_JEDI_RUNNER = '''
import json
import os
import sys

try:
    import jedi
except ImportError:
    print("[]")
    sys.exit(0)

path = os.environ["WEBIDE_COMPLETE_FILE"]
line = int(os.environ["WEBIDE_COMPLETE_LINE"])
column = int(os.environ["WEBIDE_COMPLETE_COLUMN"])

with open(path, "r", encoding="utf-8") as f:
    code = f.read()

try:
    script = jedi.Script(code, path=path)
    comps = script.complete(line=line, column=column)
except Exception:
    print("[]")
    sys.exit(0)

result = []
for c in comps:
    name = c.name
    if name and isinstance(name, str) and name.strip() and "Error" not in name:
        result.append({"name": name, "description": c.description})
print(json.dumps(result, ensure_ascii=False))
'''

def get_completions(code, line, column):
    """获取代码补全建议。

    用户代码通过临时文件传递、参数通过环境变量传递，
    不再拼接进 `python -c` 脚本 —— 既修掉了三引号转义错误，
    也消除了命令注入面。
    """
    if not os.path.exists(SYSTEM_PYTHON):
        logger.error(f"System Python not found: {SYSTEM_PYTHON}")
        return []

    try:
        line_no = int(line)
        col_no = max(0, int(column) - 1)      # Monaco 列号 1-based，jedi 为 0-based
    except (TypeError, ValueError):
        logger.warning(f"补全参数非法: line={line!r} column={column!r}")
        return []

    os.makedirs(EXEC_SCRATCH_DIR, exist_ok=True)
    fd, code_file = tempfile.mkstemp(prefix='complete_', suffix='.py', dir=EXEC_SCRATCH_DIR)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(code)

        env = build_restricted_env()
        env['WEBIDE_COMPLETE_FILE'] = code_file
        env['WEBIDE_COMPLETE_LINE'] = str(line_no)
        env['WEBIDE_COMPLETE_COLUMN'] = str(col_no)

        process = subprocess.run(
            [SYSTEM_PYTHON, '-c', _JEDI_RUNNER],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=10,
            env=env,
            cwd=EXEC_SCRATCH_DIR,
        )

        if process.returncode == 0 and process.stdout.strip():
            return json.loads(process.stdout.strip())
        return []
    except Exception as e:
        logger.error(f"Error getting completions: {e}")
        return []
    finally:
        try:
            os.remove(code_file)
        except OSError:
            pass


@app.route('/update', methods=['POST'])
def update_completions():
    """
    获取代码补全建议
    """
    data = request.json or {}
    code = data.get('code', '')
    line = data.get('line', 1)
    column = data.get('column', 0)

    completions = get_completions(code, line, column)
    return jsonify({
        'status': 'success',
        'completions': completions
    })

# ==================== 文件加载功能 ====================
@app.route('/load', methods=['POST'])
def load_file():
    """
    从服务器加载文件
    """
    data = request.json
    filename = data.get('filename')

    if not filename:
        return jsonify({'status': 'error', 'message': 'Filename is required'})

    try:
        file_path, rel = resolve_workspace_path(filename)
    except ValueError as e:
        logger.warning(f"非法文件路径被拒绝: {filename!r} ({e})")
        return jsonify({'status': 'error', 'message': 'Invalid filename'})

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        logger.info(f"文件加载成功: {rel}")
        return jsonify({'status': 'success', 'content': content})
    except FileNotFoundError:
        logger.error(f"文件不存在: {rel}")
        return jsonify({'status': 'error', 'message': 'File not found'})
    except Exception as e:
        logger.error(f"文件加载失败: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to load file'})

# ==================== 文件保存功能 ====================
@app.route('/save', methods=['POST'])
def save_file():
    """
    保存文件到服务器
    """
    data = request.json
    filename = data.get('filename', 'untitled.py')
    content = data.get('content', '')

    try:
        file_path, rel = resolve_workspace_path(filename)
    except ValueError as e:
        logger.warning(f"非法文件路径被拒绝: {filename!r} ({e})")
        return jsonify({'status': 'error', 'message': 'Invalid filename'})

    if is_readonly_path(rel):
        return jsonify({'status': 'error', 'message': 'Permission denied: this file is in a read-only directory'})

    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"文件保存成功: {rel}")
        return jsonify({'status': 'success', 'message': f'File saved successfully: {rel}'})
    except Exception as e:
        logger.error(f"文件保存失败: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to save file'})

# ==================== 文件树功能 ====================
EXCLUDED_DIRS_AT_ROOT = {'system_tool.egg-info', '__pycache__', '.git', 'node_modules'}


def build_file_tree(path, relative_path=''):
    """
    递归构建文件树结构。

    path 一律输出 posix 分隔符，保证前端可原样回传给 /load、/save 等端点。
    """
    result = []
    try:
        items = os.listdir(path)
        for item in items:
            if item in EXCLUDED_DIRS_AT_ROOT:
                continue
            if item.startswith('.') or item.startswith('__'):
                continue
            full_path = os.path.join(path, item)
            rel_path = f"{relative_path}/{item}" if relative_path else item

            if os.path.isdir(full_path):
                children = build_file_tree(full_path, rel_path)
                result.append({
                    'name': item,
                    'type': 'directory',
                    'path': rel_path,
                    'children': children
                })
            else:
                result.append({
                    'name': item,
                    'type': 'file',
                    'path': rel_path
                })
    except PermissionError:
        pass
    return result


@app.route('/api/files', methods=['GET'])
def get_file_tree():
    """
    获取项目目录的文件树结构（路径经统一校验，限定在仓库根目录内）
    """
    raw_path = request.args.get('path', 'project')

    try:
        rel = normalize_user_path(raw_path)
        base_path = resolve_in_workspace(rel)
    except ValueError as e:
        logger.warning(f"非法路径被拒绝: {raw_path!r} ({e})")
        return jsonify({'status': 'error', 'message': 'Invalid path'})

    try:
        if not os.path.exists(base_path):
            return jsonify({
                'name': rel,
                'type': 'directory',
                'path': rel,
                'children': []
            })

        tree = build_file_tree(base_path, rel)
        result = {
            'name': rel,
            'type': 'directory',
            'path': rel,
            'children': tree
        }

        logger.info(f"获取文件树成功: {rel}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取文件树失败: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to build file tree'})

@app.route('/api/files/create', methods=['POST'])
def create_file():
    """
    创建文件或文件夹
    """
    data = request.json or {}
    raw_path = data.get('path', '')
    file_type = data.get('type', 'file')

    try:
        rel = normalize_user_path(raw_path)
        target = resolve_in_workspace(rel)
    except ValueError as e:
        logger.warning(f"非法路径被拒绝: {raw_path!r} ({e})")
        return jsonify({'status': 'error', 'message': 'Invalid path'})

    if is_readonly_path(rel):
        return jsonify({'status': 'error', 'message': 'Permission denied: this directory is read-only'})

    try:
        if file_type == 'directory':
            os.makedirs(target, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'w', encoding='utf-8') as f:
                f.write('')

        logger.info(f"创建成功: {rel}")
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"创建失败: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to create'})

@app.route('/api/files/delete', methods=['POST'])
def delete_file():
    """
    删除文件或文件夹
    """
    data = request.json or {}
    raw_path = data.get('path', '')

    try:
        rel = normalize_user_path(raw_path)
        target = resolve_in_workspace(rel)
    except ValueError as e:
        logger.warning(f"非法路径被拒绝: {raw_path!r} ({e})")
        return jsonify({'status': 'error', 'message': 'Invalid path'})

    if is_readonly_path(rel):
        return jsonify({'status': 'error', 'message': 'Permission denied: this directory is read-only'})

    # 额外保护：禁止删除工作区根目录本身
    if os.path.realpath(target) == os.path.realpath(WORKSPACE_ROOT):
        return jsonify({'status': 'error', 'message': 'Permission denied: cannot delete workspace root'})

    try:
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)

        logger.info(f"删除成功: {rel}")
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"删除失败: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to delete'})

@app.route('/api/files/rename', methods=['POST'])
def rename_file():
    """
    重命名文件或文件夹
    """
    data = request.json or {}
    raw_path = data.get('path', '')
    new_name = data.get('newName', '')

    try:
        rel = normalize_user_path(raw_path)
        old_target = resolve_in_workspace(rel)
    except ValueError as e:
        logger.warning(f"非法路径被拒绝: {raw_path!r} ({e})")
        return jsonify({'status': 'error', 'message': 'Invalid path'})

    if is_readonly_path(rel):
        return jsonify({'status': 'error', 'message': 'Permission denied: this directory is read-only'})

    # 新名称必须是单一文件名：不得为空、不得包含路径分隔符或上跳
    new_name = new_name.strip() if isinstance(new_name, str) else ''
    if (not new_name or new_name in ('.', '..')
            or '/' in new_name or '\\' in new_name or ':' in new_name):
        return jsonify({'status': 'error', 'message': 'Invalid new name'})

    try:
        new_target = resolve_under(os.path.dirname(old_target), new_name)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid new name'})

    try:
        os.rename(old_target, new_target)
        logger.info(f"重命名成功: {rel} -> {new_name}")
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"重命名失败: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to rename'})

# ==================== 终端执行功能 ====================
@app.route('/terminal/execute', methods=['POST'])
def execute_terminal_command():
    """
    执行终端命令。

    默认启用命令白名单并禁止 shell 元字符（串联/管道/重定向/命令替换），
    同时施加与 /run 相同的资源限制。
    如需放开限制，可设置 WEBIDE_TERMINAL_UNRESTRICTED=1（不推荐）。
    """
    data = request.json or {}
    command = data.get('command', '')

    if not command or not command.strip():
        return jsonify({'status': 'error', 'output': 'No command provided'})

    allowed, reason = validate_terminal_command(command)
    if not allowed:
        logger.warning(f"终端命令被策略拒绝: {command!r} ({reason})")
        return jsonify({
            'status': 'error',
            'output': f'命令被安全策略拒绝: {reason}'
        })

    try:
        # shell=False：命令不再交由 shell 解释，从根上消除串联与注入
        argv = command.strip().split()
        returncode, output, timed_out, truncated = run_limited(
            argv, timeout=EXEC_TIMEOUT, cwd=WORKSPACE_ROOT
        )

        if timed_out:
            return jsonify({
                'status': 'error',
                'output': f'命令执行超时（超过 {EXEC_TIMEOUT} 秒，已终止进程树）\n' + output
            })

        if truncated:
            output += f"\n...[输出超过 {EXEC_MAX_OUTPUT // 1024} KB，已截断]"

        return jsonify({
            'status': 'success',
            'output': output,
            'returncode': returncode
        })
    except FileNotFoundError:
        return jsonify({'status': 'error', 'output': f'命令不存在: {command.strip().split()[0]}'})
    except Exception as e:
        logger.error(f"命令执行失败: {str(e)}")
        return jsonify({'status': 'error', 'output': 'Command execution failed'})

# ==================== Python版本功能 ====================
@app.route('/python/version', methods=['GET'])
def get_python_version():
    """
    获取Python版本
    """
    from env_config import PYTHON_EXE
    try:
        # PYTHON_EXE = os.path.join(backend_dir, 'python313', 'python.exe')
        result = subprocess.run(
            [PYTHON_EXE, '--version'],
            capture_output=True,
            text=True
        )
        version = result.stdout.strip() or result.stderr.strip()
        logger.info(f"获取Python版本: {version}")
        return jsonify({'status': 'success', 'version': version})
    except Exception as e:
        logger.error(f"获取Python版本失败: {str(e)}")
        return jsonify({'status': 'error', 'version': 'Unknown'})

# ==================== 工具注册表 API ====================

# 数据目录与输出目录
DATA_ROOT = os.path.join(backend_dir, 'data')          # 各会话数据集根目录
OUT_ROOT = os.path.join(backend_dir, 'out_file')       # 各会话分析产物根目录

os.makedirs(DATA_ROOT, exist_ok=True)
os.makedirs(OUT_ROOT, exist_ok=True)

# 会话隔离：每个会话使用独立子目录，避免并发上传互相覆盖、产物互相混淆
_SESSION_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
DEFAULT_SESSION = 'default'


def get_session_id():
    """从请求头 X-Session-Id 解析会话标识，非法或缺省时回退为 default"""
    raw = (request.headers.get('X-Session-Id') or '').strip()
    if raw and _SESSION_ID_RE.match(raw):
        return raw
    return DEFAULT_SESSION


def session_data_dir(session_id=None):
    """返回指定会话的数据集目录（绝对路径），并确保其存在"""
    sid = session_id or get_session_id()
    path = os.path.join(DATA_ROOT, sid)
    os.makedirs(path, exist_ok=True)
    return path


def session_output_dir(session_id=None):
    """返回指定会话的分析产物目录（绝对路径），并确保其存在"""
    sid = session_id or get_session_id()
    path = os.path.join(OUT_ROOT, sid)
    os.makedirs(path, exist_ok=True)
    return path


def output_url(filename, session_id=None):
    """构造产物的访问地址。

    会话 ID 放在路径中而非请求头里 —— 因为 <img src> 由浏览器直接发起，
    不会携带 X-Session-Id 头。
    """
    return f"/api/output/{session_id or get_session_id()}/{filename}"


# 对外提供输出文件的静态路由
@app.route('/api/output/<session_id>/<path:filename>', methods=['GET'])
def serve_output_file(session_id, filename):
    """提供输出文件的访问（按会话分目录，send_from_directory 自带越界防护）"""
    if not _SESSION_ID_RE.match(session_id or ''):
        return jsonify({'status': 'error', 'message': 'Invalid session'}), 400
    return send_from_directory(session_output_dir(session_id), filename)


def clean_data_dir(session_id=None):
    """清理当前会话数据目录中的残留文件（不影响其他会话）"""
    target = session_data_dir(session_id)
    try:
        for f in os.listdir(target):
            fp = os.path.join(target, f)
            if os.path.isfile(fp):
                os.remove(fp)
    except Exception as e:
        logger.warning(f"清理数据目录失败: {e}")


def save_uploaded_file(file):
    """保存上传的文件到当前会话的数据目录，返回文件路径"""
    clean_data_dir()
    ext = os.path.splitext(file.filename)[1].lower()
    filename = f"data{ext}"
    filepath = os.path.join(session_data_dir(), filename)
    file.save(filepath)
    return filepath


def load_data_from_dir():
    """从当前会话的数据目录加载表格数据。

    多个候选文件时取**最近修改**的一个，保证结果确定
    （os.listdir 的顺序不保证稳定）。
    """
    import pandas as pd
    target = session_data_dir()
    files = [
        os.path.join(target, f)
        for f in os.listdir(target)
        if os.path.isfile(os.path.join(target, f))
    ]
    if not files:
        return None

    filepath = max(files, key=os.path.getmtime)
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.csv':
        return pd.read_csv(filepath)
    elif ext in ('.xlsx', '.xls'):
        return pd.read_excel(filepath)
    else:
        return pd.read_csv(filepath)

def get_tool_function(tool_name):
    """根据工具名称查找对应的函数"""
    for stage in analysis_toolbox:
        for sub_cat in stage.get("sub_categories", []):
            for tool in sub_cat.get("tools", []):
                if hasattr(tool, 'name') and tool.name == tool_name:
                    return tool.func
                elif isinstance(tool, dict) and tool.get('name') == tool_name:
                    return tool.get('func')
    return None

def extract_tool_params(request_data):
    """从请求数据中提取工具参数。

    参数契约（两种写法均支持，顶层写法优先级低于 methodConfig）：

      A) 简化写法 —— 顶层直接给参数：
         {"column": "age", "bins": 10}

      B) 完整写法 —— 参数包在 methodConfig / analysisConfig 内：
         {"methodConfig": {"column": "age", "bins": 10},
          "selectedVars": {"x": ["age"]}}

    下列保留字段属于前端元信息，不会透传给工具函数：
      func / methodKey / methodName / category / categoryName /
      displayName / description / selectedVars / methodConfig / analysisConfig
    """
    RESERVED = {
        'func', 'methodKey', 'methodName', 'category', 'categoryName',
        'displayName', 'description', 'selectedVars',
        'methodConfig', 'analysisConfig',
    }

    params = {}

    # A) 顶层参数（简化写法）
    if isinstance(request_data, dict):
        for key, value in request_data.items():
            if key not in RESERVED:
                params[key] = value

    # B) methodConfig / analysisConfig 覆盖顶层同名参数
    method_config = request_data.get('methodConfig') or {}
    analysis_config = request_data.get('analysisConfig') or {}
    config = method_config if method_config else analysis_config

    if isinstance(config, dict):
        for key, value in config.items():
            if key not in RESERVED:
                params[key] = value

    # 变量选择结果
    selected_vars = request_data.get('selectedVars')
    if selected_vars:
        params['selectedVars'] = selected_vars

    return params

def serialize_result_with_files(obj, tool_name, is_preview_tool=False, data_param_name=None, data_filepath=None):
    """将工具函数返回值转换为 JSON 可序列化格式，文件/图片保存到 out_file 目录

    Args:
        obj: 工具函数返回值
        tool_name: 工具名称
        is_preview_tool: 是否为 N_ 开头的预览工具，若是则直接覆盖原数据文件
        data_param_name: DataFrame 参数名
        data_filepath: 原始数据文件路径
    """
    import pandas as pd
    import numpy as np
    import base64
    import io
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    import time

    def save_plot_to_file(fig, tool_name, idx=0):
        """保存 matplotlib 图表到当前会话的产物目录"""
        filename = f"{tool_name}_plot_{idx}_{int(time.time() * 1000)}.png"
        filepath = os.path.join(session_output_dir(), filename)
        fig.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close(fig)
        return filename

    def save_dataframe_to_file(df, tool_name, idx=0):
        """保存 DataFrame 到当前会话产物目录下的 CSV"""
        filename = f"{tool_name}_result_{idx}_{int(time.time() * 1000)}.csv"
        filepath = os.path.join(session_output_dir(), filename)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return filename

    def save_base64_image(b64_str, tool_name, idx=0):
        """保存 base64 图片到当前会话产物目录"""
        filename = f"{tool_name}_img_{idx}_{int(time.time() * 1000)}.png"
        filepath = os.path.join(session_output_dir(), filename)
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(b64_str))
        return filename

    if isinstance(obj, Figure):
        filename = save_plot_to_file(obj, tool_name)
        return {"_type": "image", "path": output_url(filename)}
    elif isinstance(obj, pd.DataFrame):
        # N_ 预览工具：直接覆盖原数据文件
        if is_preview_tool and data_filepath:
            df = obj.copy()
            # 根据原文件扩展名决定保存格式
            ext = os.path.splitext(data_filepath)[1].lower()
            if ext == '.csv':
                df.to_csv(data_filepath, index=False, encoding='utf-8-sig')
            elif ext in ('.xlsx', '.xls'):
                df.to_excel(data_filepath, index=False)
            else:
                df.to_csv(data_filepath, index=False, encoding='utf-8-sig')
            return {"_type": "file", "path": "updated", "filename": os.path.basename(data_filepath)}
        else:
            filename = save_dataframe_to_file(obj, tool_name)
            return {"_type": "file", "path": output_url(filename), "filename": filename}
    elif isinstance(obj, dict):
        # 兼容旧版 base64 图片
        if "image_base64" in obj:
            filename = save_base64_image(obj["image_base64"], tool_name)
            result = {"_type": "image", "path": output_url(filename)}
            for k, v in obj.items():
                if k != "image_base64":
                    result[k] = serialize_result_with_files(v, f"{tool_name}_{k}", is_preview_tool, data_param_name, data_filepath)
            return result

        # 检查是否有 DataFrame 需要处理
        # 如果 tool_name 以 _data 结尾，说明这是 data 参数的返回值
        sub_is_preview = is_preview_tool

        result = {}
        for k, v in obj.items():
            if isinstance(v, tuple):
                result[k] = list(v)
            elif isinstance(v, pd.DataFrame):
                if is_preview_tool and data_filepath:
                    df = v.copy()
                    ext = os.path.splitext(data_filepath)[1].lower()
                    if ext == '.csv':
                        df.to_csv(data_filepath, index=False, encoding='utf-8-sig')
                    elif ext in ('.xlsx', '.xls'):
                        df.to_excel(data_filepath, index=False)
                    else:
                        df.to_csv(data_filepath, index=False, encoding='utf-8-sig')
                    result[k] = {"_type": "file", "path": "updated", "filename": os.path.basename(data_filepath)}
                else:
                    filename = save_dataframe_to_file(v, f"{tool_name}_{k}")
                    result[k] = {"_type": "file", "path": output_url(filename), "filename": filename}
            else:
                serialized = serialize_result_with_files(v, f"{tool_name}_{k}", is_preview_tool, data_param_name, data_filepath)
                result[k] = serialized
        return result
    elif isinstance(obj, (list, tuple)):
        results = []
        for idx, item in enumerate(obj):
            results.append(serialize_result_with_files(item, f"{tool_name}_{idx}", is_preview_tool, data_param_name, data_filepath))
        return results
    elif isinstance(obj, pd.Series):
        return {"_type": "series", "name": obj.name, "data": obj.to_dict()}
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    return obj

def build_tool_registry():
    """
    将Python注册表转换为前端可用的JSON结构
    """
    result = []
    for stage in analysis_toolbox:
        stage_data = {
            "stage_id": stage.get("stage_id", ""),
            "stage_name": stage.get("stage_name", ""),
            "sub_categories": []
        }
        for sub_cat in stage.get("sub_categories", []):
            sub_cat_data = {
                "sub_category_id": sub_cat.get("sub_category_id", ""),
                "sub_category_name": sub_cat.get("sub_category_name", ""),
                "tools": []
            }
            for tool in sub_cat.get("tools", []):
                tool_data = {
                    "name": tool.name if hasattr(tool, 'name') else str(tool.get('name', '')),
                    "display_name": tool.display_name if hasattr(tool, 'display_name') else str(tool.get('display_name', '')),
                    "description": tool.description if hasattr(tool, 'description') else str(tool.get('description', '')),
                    "parameters": tool.parameters if hasattr(tool, 'parameters') else tool.get('parameters', [])
                }
                sub_cat_data["tools"].append(tool_data)
            stage_data["sub_categories"].append(sub_cat_data)
        result.append(stage_data)
    return result

@app.route('/api/tools', methods=['GET'])
def get_tool_registry():
    """
    获取工具注册表（层级结构）
    """
    try:
        registry = build_tool_registry()
        return jsonify({
            'status': 'success',
            'data': registry
        })
    except Exception as e:
        logger.error(f"获取工具注册表失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to build tool registry'
        })

@app.route('/api/tools/all', methods=['GET'])
def get_all_tools():
    """
    获取所有工具的扁平列表
    """
    try:
        all_tools = []
        for stage in analysis_toolbox:
            for sub_cat in stage.get("sub_categories", []):
                for tool in sub_cat.get("tools", []):
                    tool_data = {
                        "name": tool.name if hasattr(tool, 'name') else str(tool.get('name', '')),
                        "display_name": tool.display_name if hasattr(tool, 'display_name') else str(tool.get('display_name', '')),
                        "description": tool.description if hasattr(tool, 'description') else str(tool.get('description', '')),
                        "parameters": tool.parameters if hasattr(tool, 'parameters') else tool.get('parameters', []),
                        "stage_id": stage.get("stage_id", ""),
                        "stage_name": stage.get("stage_name", ""),
                        "sub_category_id": sub_cat.get("sub_category_id", ""),
                        "sub_category_name": sub_cat.get("sub_category_name", "")
                    }
                    all_tools.append(tool_data)
        return jsonify({
            'status': 'success',
            'data': all_tools
        })
    except Exception as e:
        logger.error(f"获取所有工具失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to list tools'
        })

@app.route('/api/tools/search', methods=['GET'])
def search_tools():
    """
    搜索工具
    """
    try:
        query = request.args.get('query', '').lower()
        if not query:
            return jsonify({
                'status': 'success',
                'data': []
            })

        results = []
        for stage in analysis_toolbox:
            for sub_cat in stage.get("sub_categories", []):
                for tool in sub_cat.get("tools", []):
                    name = tool.name if hasattr(tool, 'name') else str(tool.get('name', ''))
                    display_name = tool.display_name if hasattr(tool, 'display_name') else str(tool.get('display_name', ''))
                    description = tool.description if hasattr(tool, 'description') else str(tool.get('description', ''))

                    if (query in name.lower() or
                        query in display_name.lower() or
                        query in description.lower()):
                        results.append({
                            "name": name,
                            "display_name": display_name,
                            "description": description,
                            "parameters": tool.parameters if hasattr(tool, 'parameters') else tool.get('parameters', []),
                            "stage_id": stage.get("stage_id", ""),
                            "stage_name": stage.get("stage_name", "")
                        })

        return jsonify({
            'status': 'success',
            'data': results
        })
    except Exception as e:
        logger.error(f"搜索工具失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to search tools'
        })

# ==================== 数据上传功能 ====================
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}

def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload', methods=['POST'])
def upload_data_file():
    """
    上传表格数据文件到 data 目录，自动清理旧文件
    """
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file provided'})

        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'})

        if not allowed_file(file.filename):
            return jsonify({
                'status': 'error',
                'message': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            })

        filepath = save_uploaded_file(file)
        logger.info(f"文件上传成功: {filepath}")

        return jsonify({
            'status': 'success',
            'message': 'File uploaded successfully',
            'filepath': filepath
        })
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        return jsonify({'status': 'error', 'message': 'File upload failed'})

# ==================== 数据集信息 ====================
@app.route('/api/data/info', methods=['GET'])
def get_data_info():
    """
    返回当前会话已加载数据集的结构信息。

    供前端渲染参数表单的候选项（选择列 / 多选列）使用。
    """
    try:
        df = load_data_from_dir()
        if df is None:
            return jsonify({
                'status': 'success',
                'data': {
                    'loaded': False,
                    'rows': 0,
                    'columns': [],
                    'numeric_columns': [],
                    'dtypes': {},
                }
            })

        return jsonify({
            'status': 'success',
            'data': {
                'loaded': True,
                'rows': int(df.shape[0]),
                'column_count': int(df.shape[1]),
                'columns': [str(c) for c in df.columns],
                'numeric_columns': [str(c) for c in df.select_dtypes(include='number').columns],
                'dtypes': {str(c): str(t) for c, t in df.dtypes.items()},
            }
        })
    except Exception as e:
        logger.error(f"获取数据集信息失败: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to inspect dataset'})

# ==================== 分析结果转为数据集 ====================
@app.route('/api/data/adopt', methods=['POST'])
def adopt_result_as_dataset():
    """
    把一次分析产物（产物目录下的表格文件）设为当前会话的数据集。

    存在意义：数据清洗 / 特征工程 / 建模是串联流程，但产物原本只能
    下载后重新上传才能继续下一步。该接口让多步流程可以在界面上连续进行：

        上传原始数据 → 缺失值填充 → 设回数据集 → 标准化 → 设回数据集 → 建模

    仅接受表格类产物（csv / xlsx / xls）；图表等非表格产物会被拒绝。
    """
    data = request.json or {}
    raw_filename = data.get('filename', '')

    try:
        rel = normalize_user_path(raw_filename)
    except ValueError:
        logger.warning(f"非法产物文件名被拒绝: {raw_filename!r}")
        return jsonify({'status': 'error', 'message': 'Invalid filename'})

    # 只接受纯文件名，不允许任何路径层级
    if '/' in rel:
        return jsonify({'status': 'error', 'message': 'Invalid filename'})

    ext = os.path.splitext(rel)[1].lower()
    if ext not in ('.csv', '.xlsx', '.xls'):
        return jsonify({
            'status': 'error',
            'message': 'Only tabular results (csv/xlsx/xls) can be adopted as a dataset'
        })

    try:
        source = resolve_under(session_output_dir(), rel)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid filename'})

    if not os.path.isfile(source):
        logger.error(f"产物文件不存在: {rel}")
        return jsonify({'status': 'error', 'message': 'Result file not found'})

    try:
        clean_data_dir()
        target = os.path.join(session_data_dir(), f"data{ext}")
        shutil.copyfile(source, target)

        # 校验能被 pandas 正确读取，避免把损坏文件设成数据集
        df = load_data_from_dir()
        if df is None:
            return jsonify({'status': 'error', 'message': 'Failed to load the adopted file'})

        logger.info(f"产物已设为数据集: {rel} -> {target}")
        return jsonify({
            'status': 'success',
            'message': f'Adopted {rel} as the current dataset',
            'data': {
                'rows': int(df.shape[0]),
                'column_count': int(df.shape[1]),
                'columns': [str(c) for c in df.columns],
                'numeric_columns': [str(c) for c in df.select_dtypes(include='number').columns],
                'loaded': True,
            }
        })
    except Exception as e:
        logger.error(f"产物转为数据集失败: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to adopt result as dataset'})

# ==================== 工具执行 API ====================
@app.route('/api/tools/<tool_name>', methods=['POST'])
def execute_tool(tool_name):
    """
    执行指定的工具函数
    接收外部传入的配置数据，自动加载 data 目录中的表格，返回文件路径
    """
    try:
        request_data = request.json or {}

        # 1. 查找工具函数
        tool_func = get_tool_function(tool_name)
        if not tool_func:
            return jsonify({
                'status': 'error',
                'message': f'Tool not found: {tool_name}'
            })

        # 2. 从请求数据中提取参数
        params = extract_tool_params(request_data)

        # 3. 自动加载 data 目录中的表格作为 data 参数
        import inspect
        sig = inspect.signature(tool_func)
        data_param_name = None
        data_filepath = None
        for param_name in sig.parameters:
            if param_name in ('data', 'df', 'dataframe') and param_name not in params:
                df = load_data_from_dir()
                if df is not None:
                    params[param_name] = df
                    data_param_name = param_name
                    # 获取当前会话数据目录中的文件路径
                    session_dir = session_data_dir()
                    files = [f for f in os.listdir(session_dir)
                             if os.path.isfile(os.path.join(session_dir, f))]
                    if files:
                        data_filepath = os.path.join(session_dir, files[0])
                break

        # 4. 执行工具函数
        result = tool_func(**params)

        # 5. 序列化结果
        # N_ 开头的工具函数如果返回了 DataFrame，直接覆盖原数据文件
        is_preview_tool = tool_name.startswith('N_')
        result = serialize_result_with_files(result, tool_name, is_preview_tool, data_param_name, data_filepath)

        return jsonify({
            'status': 'success',
            'result': result
        })
    except Exception as e:
        logger.error(f"执行工具失败: {str(e)}")
        return jsonify({
            'status': 'error',
            # 保留工具自身的校验提示（脱敏后），便于使用者定位参数问题
            'message': sanitize_error(e, fallback='Tool execution failed')
        })

if __name__ == '__main__':
    # 信任边界：本服务具备「执行代码 / 执行命令 / 读写文件」能力，
    # 默认仅监听回环地址，避免无意间暴露给局域网。
    # 确需跨机访问时显式设置 WEBIDE_HOST=0.0.0.0，并自行确保网络环境可信。
    host = os.environ.get('WEBIDE_HOST', '127.0.0.1').strip() or '127.0.0.1'
    port = int(os.environ.get('WEBIDE_PORT', '5000'))

    logger.info(f"Flask server starting on http://{host}:{port}")

    if host not in ('127.0.0.1', 'localhost', '::1'):
        logger.warning(
            f"服务已绑定到 {host}，局域网内其他主机可访问。"
            "本服务可执行任意代码与系统命令，令牌鉴权虽已启用，仍请确认网络环境可信。"
        )

    app.run(host=host, port=port)
