"""
Flask 后端主程序
提供代码执行、代码补全、文件管理等功能
"""
import os
import sys
import logging
import subprocess
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# 添加项目根目录和backend目录到sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
backend_dir = os.path.dirname(__file__)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 导入注册表
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'system_registry',
        os.path.join(backend_dir, 'toolBox', 'system_registry .py')
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
    执行Python代码
    """
    data = request.json
    code = data.get('code', '')

    if not code:
        return jsonify({'status': 'error', 'output': 'No code provided'})

    try:
        # 使用项目目录的Python执行
        PYTHON_EXE = os.path.join(backend_dir, 'python313', 'python.exe')

        # 创建临时文件
        temp_file = os.path.join(backend_dir, 'temp_code.py')
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(code)

        # 执行代码
        result = subprocess.run(
            [PYTHON_EXE, temp_file],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 删除临时文件
        os.remove(temp_file)

        output = result.stdout + result.stderr
        return jsonify({
            'status': 'success',
            'output': output,
            'returncode': result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'output': '代码执行超时'})
    except Exception as e:
        logger.error(f"代码执行失败: {str(e)}")
        return jsonify({'status': 'error', 'output': str(e)})

# ==================== AI 对话功能 ====================
import openai

AI_CONFIG = {
    "model": "qwen-plus",
    "api_key": "sk-9c71bb74bdb24ca7869723ca8fb84526",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
}

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """
    AI 对话接口
    """
    try:
        data = request.json
        messages = data.get('messages', [])

        if not messages:
            return jsonify({'status': 'error', 'message': 'No messages provided'})

        client = openai.OpenAI(
            api_key=AI_CONFIG["api_key"],
            base_url=AI_CONFIG["base_url"]
        )

        response = client.chat.completions.create(
            model=AI_CONFIG["model"],
            messages=messages
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
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/ai/models', methods=['GET'])
def get_ai_models():
    """
    获取可用的 AI 模型列表
    """
    return jsonify({
        'status': 'success',
        'data': [
            {
                'id': AI_CONFIG['model'],
                'name': '通义千问 Plus',
                'description': '阿里云通义千问大模型'
            }
        ]
    })

# ==================== 代码补全功能 ====================
import subprocess
import json
import os

SYSTEM_PYTHON = r'D:/Program Files(x86)/Python3.13/python3.13t.exe'
# SYSTEM_PYTHON = r'C:/Users/szpt/AppData/Local/Programs/Python/Python312/python.exe'
# SYSTEM_PYTHON = r'C:/Users/z2788/AppData/Local/Programs/Python/Python313/python.exe'

def get_completions(code, line, column):
    if not os.path.exists(SYSTEM_PYTHON):
        logger.error(f"System Python not found: {SYSTEM_PYTHON}")
        return []

    try:
        jedi_script = f'''
import jedi
code = """{code.replace('"""', '///"///"///"')}"""
line = {line}
column = max(0, {column} - 1)
script = jedi.Script(code)
comps = script.complete(line=line, column=column)
result = []
for c in comps:
    n = c.name
    if n and isinstance(n, str) and "Error" not in n and n.strip():
        result.append({{"name": n, "description": c.description}})
print(__import__('json').dumps(result))
'''
        process = subprocess.run(
            [SYSTEM_PYTHON, '-c', jedi_script],
            capture_output=True,
            text=True,
            timeout=10
        )

        if process.returncode == 0 and process.stdout.strip():
            return json.loads(process.stdout.strip())
        return []
    except Exception as e:
        logger.error(f"Error getting completions: {e}")
        return []

@app.route('/update', methods=['POST'])
def update_completions():
    """
    获取代码补全建议
    """
    data = request.json
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
        if '..' in filename or filename.startswith('/'):
            return jsonify({'status': 'error', 'message': 'Invalid filename'})

        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(backend_dir, '..'))

        if filename.startswith('project/') or filename.startswith('project//'):
            file_path = os.path.join(project_root, filename)
        else:
            file_path = os.path.join('files', filename)

        file_path = os.path.abspath(file_path)

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        logger.info(f"文件加载成功: {filename}")
        return jsonify({'status': 'success', 'content': content})
    except FileNotFoundError:
        logger.error(f"文件不存在: {filename}")
        return jsonify({'status': 'error', 'message': 'File not found'})
    except Exception as e:
        logger.error(f"文件加载失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

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
        if '..' in filename or filename.startswith('/'):
            return jsonify({'status': 'error', 'message': 'Invalid filename'})

        if is_readonly_path(filename):
            return jsonify({'status': 'error', 'message': 'Permission denied: this file is in a read-only directory'})

        if filename.startswith('project/') or filename.startswith('project//'):
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(backend_dir, '..'))
            file_path = os.path.join(project_root, filename)
        else:
            if not os.path.exists('files'):
                os.makedirs('files')
            file_path = os.path.join('files', filename)

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"文件保存成功: {filename}")
        return jsonify({'status': 'success', 'message': f'File saved successfully: {filename}'})
    except Exception as e:
        logger.error(f"文件保存失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

# ==================== 文件树功能 ====================
EXCLUDED_DIRS_AT_ROOT = {'system_tool.egg-info', '__pycache__', '.git', 'node_modules'}
READONLY_DIRS = {'project/toolBox'}

def build_file_tree(path, relative_path=''):
    """
    递归构建文件树结构
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
            rel_path = os.path.join(relative_path, item) if relative_path else item

            if os.path.isdir(full_path):
                children = build_file_tree(full_path, rel_path)
                if children or True:
                    result.append({
                        'name': item,
                        'type': 'directory',
                        'path': rel_path.replace('//', '/'),
                        'children': children
                    })
            else:
                result.append({
                    'name': item,
                    'type': 'file',
                    'path': rel_path.replace('//', '/')
                })
    except PermissionError:
        pass
    return result

def is_readonly_path(file_path):
    """
    检查路径是否在只读目录中
    """
    normalized_path = file_path.replace('//', '/')
    for readonly_dir in READONLY_DIRS:
        if normalized_path == readonly_dir or normalized_path.startswith(readonly_dir + '/'):
            return True
    return False

@app.route('/api/files', methods=['GET'])
def get_file_tree():
    """
    获取项目目录的文件树结构
    """
    try:
        path = request.args.get('path', 'project')
        if '..' in path or path.startswith('/'):
            return jsonify({'status': 'error', 'message': 'Invalid path'})

        base_path = os.path.join(os.path.dirname(__file__), '..', path)
        base_path = os.path.abspath(base_path)

        if not os.path.exists(base_path):
            return jsonify({
                'name': path,
                'type': 'directory',
                'path': path,
                'children': []
            })

        tree = build_file_tree(base_path, path)
        result = {
            'name': path,
            'type': 'directory',
            'path': path,
            'children': tree
        }

        logger.info(f"获取文件树成功: {path}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取文件树失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/files/create', methods=['POST'])
def create_file():
    """
    创建文件或文件夹
    """
    try:
        data = request.json
        file_path = data.get('path', '')
        file_type = data.get('type', 'file')

        if '..' in file_path or file_path.startswith('/'):
            return jsonify({'status': 'error', 'message': 'Invalid path'})

        if is_readonly_path(file_path):
            return jsonify({'status': 'error', 'message': 'Permission denied: this directory is read-only'})

        base_path = os.path.join(os.path.dirname(__file__), '..', file_path)
        base_path = os.path.abspath(base_path)

        if file_type == 'directory':
            os.makedirs(base_path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(base_path), exist_ok=True)
            with open(base_path, 'w', encoding='utf-8') as f:
                f.write('')

        logger.info(f"创建成功: {file_path}")
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"创建失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/files/delete', methods=['POST'])
def delete_file():
    """
    删除文件或文件夹
    """
    try:
        data = request.json
        file_path = data.get('path', '')

        if '..' in file_path or file_path.startswith('/'):
            return jsonify({'status': 'error', 'message': 'Invalid path'})

        if is_readonly_path(file_path):
            return jsonify({'status': 'error', 'message': 'Permission denied: this directory is read-only'})

        base_path = os.path.join(os.path.dirname(__file__), '..', file_path)
        base_path = os.path.abspath(base_path)

        if os.path.isdir(base_path):
            import shutil
            shutil.rmtree(base_path)
        else:
            os.remove(base_path)

        logger.info(f"删除成功: {file_path}")
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"删除失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/files/rename', methods=['POST'])
def rename_file():
    """
    重命名文件或文件夹
    """
    try:
        data = request.json
        old_path = data.get('path', '')
        new_name = data.get('newName', '')

        if '..' in old_path or old_path.startswith('/') or '..' in new_name:
            return jsonify({'status': 'error', 'message': 'Invalid path'})

        if is_readonly_path(old_path):
            return jsonify({'status': 'error', 'message': 'Permission denied: this directory is read-only'})

        old_base = os.path.join(os.path.dirname(__file__), '..', old_path)
        old_base = os.path.abspath(old_base)

        new_base = os.path.join(os.path.dirname(old_base), new_name)

        os.rename(old_base, new_base)

        logger.info(f"重命名成功: {old_path} -> {new_name}")
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"重命名失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

# ==================== 终端执行功能 ====================
@app.route('/terminal/execute', methods=['POST'])
def execute_terminal_command():
    """
    执行终端命令
    """
    try:
        data = request.json
        command = data.get('command', '')

        if not command:
            return jsonify({'status': 'error', 'output': 'No command provided'})

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout + result.stderr
        return jsonify({
            'status': 'success',
            'output': output,
            'returncode': result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'output': '命令执行超时'})
    except Exception as e:
        logger.error(f"命令执行失败: {str(e)}")
        return jsonify({'status': 'error', 'output': str(e)})

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

# 数据目录和输出目录配置
DATA_DIR = os.path.join(backend_dir, 'data')
OUT_FILE_DIR = os.path.join(backend_dir, 'out_file')

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUT_FILE_DIR, exist_ok=True)

# 对外提供输出文件的静态路由
@app.route('/api/output/<path:filename>', methods=['GET'])
def serve_output_file(filename):
    """提供输出文件的访问"""
    return send_from_directory(OUT_FILE_DIR, filename)

def clean_data_dir():
    """清理数据目录中的残留文件"""
    try:
        for f in os.listdir(DATA_DIR):
            fp = os.path.join(DATA_DIR, f)
            if os.path.isfile(fp):
                os.remove(fp)
    except Exception as e:
        logger.warning(f"清理数据目录失败: {e}")

def save_uploaded_file(file):
    """保存上传的文件到数据目录，返回文件路径"""
    clean_data_dir()
    ext = os.path.splitext(file.filename)[1].lower()
    filename = f"data{ext}"
    filepath = os.path.join(DATA_DIR, filename)
    file.save(filepath)
    return filepath

def load_data_from_dir():
    """从数据目录自动加载表格数据"""
    import pandas as pd
    files = [f for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f))]
    if not files:
        return None
    filepath = os.path.join(DATA_DIR, files[0])
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
    """从外部请求数据中提取工具参数"""
    params = {}

    # 变量选择结果
    selected_vars = request_data.get('selectedVars', {})
    # 分析方法信息
    method_config = request_data.get('methodConfig', {})
    # 完整配置
    analysis_config = request_data.get('analysisConfig', {})

    # 从 methodConfig 或 analysisConfig 中提取工具参数
    config = method_config if method_config else analysis_config

    # 将配置中的参数扁平化为工具调用参数
    if config:
        for key, value in config.items():
            if key not in ('func', 'methodKey', 'methodName', 'category', 'categoryName', 'displayName', 'description'):
                params[key] = value

    # 添加变量选择结果
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
        """保存 matplotlib 图表到文件"""
        filename = f"{tool_name}_plot_{idx}_{int(time.time())}.png"
        filepath = os.path.join(OUT_FILE_DIR, filename)
        fig.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close(fig)
        return filename

    def save_dataframe_to_file(df, tool_name, idx=0):
        """保存 DataFrame 到 CSV 文件"""
        filename = f"{tool_name}_result_{idx}_{int(time.time())}.csv"
        filepath = os.path.join(OUT_FILE_DIR, filename)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return filename

    def save_base64_image(b64_str, tool_name, idx=0):
        """保存 base64 图片到文件"""
        filename = f"{tool_name}_img_{idx}_{int(time.time())}.png"
        filepath = os.path.join(OUT_FILE_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(b64_str))
        return filename

    if isinstance(obj, Figure):
        filename = save_plot_to_file(obj, tool_name)
        return {"_type": "image", "path": f"/api/output/{filename}"}
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
            return {"_type": "file", "path": f"/api/output/{filename}", "filename": filename}
    elif isinstance(obj, dict):
        # 兼容旧版 base64 图片
        if "image_base64" in obj:
            filename = save_base64_image(obj["image_base64"], tool_name)
            result = {"_type": "image", "path": f"/api/output/{filename}"}
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
                    result[k] = {"_type": "file", "path": f"/api/output/{filename}", "filename": filename}
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
            'message': str(e)
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
            'message': str(e)
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
            'message': str(e)
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
        return jsonify({'status': 'error', 'message': str(e)})

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
                    # 获取数据目录中的文件路径
                    files = [f for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f))]
                    if files:
                        data_filepath = os.path.join(DATA_DIR, files[0])
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
            'message': str(e)
        })

if __name__ == '__main__':
    logger.info("Flask server starting on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)
