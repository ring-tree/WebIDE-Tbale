# 导入环境配置
import os
import sys
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 打印调试信息
print(f"当前工作目录: {os.getcwd()}")
print(f"Python路径: {sys.path}")

try:
    from env_config import PYTHON_EXE
    print(f"成功导入PYTHON_EXE: {PYTHON_EXE}")
    print(f"PYTHON_EXE存在: {os.path.exists(PYTHON_EXE)}")
except Exception as e:
    print(f"导入env_config失败: {str(e)}")
    PYTHON_EXE = sys.executable
    print(f"使用系统Python: {PYTHON_EXE}")

from flask import Flask, request, jsonify
# from flask_cors import CORS
import jedi
import subprocess
import logging

# 配置日志
import os
# 确保tmp目录存在
if not os.path.exists('../tmp'):
    os.makedirs('../tmp')

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler('../tmp/backend.log'),
                        logging.StreamHandler()
                    ])

logger = logging.getLogger(__name__)

# 创建Flask应用实例
app = Flask(__name__)
# 启用跨域资源共享(CORS)
# CORS(app, resources={r"/*": {"origins": "*"}}) 

# === 关键修复：手动添加 CORS 处理中间件 ===
@app.after_request
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'  # 允许所有来源（开发环境用，生产环境请指定具体域名）
    header['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    header['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response

# 处理预检请求 (OPTIONS)
@app.route('/run', methods=['OPTIONS'])
@app.route('/update', methods=['OPTIONS'])
def handle_options():
    print(">>> 收到了 OPTIONS 预检请求")
    return jsonify({'status': 'ok'}), 200

def get_completions(code, line, column):
    """
    获取代码补全建议
    
    参数:
        code (str): 要分析的代码
        line (int): 光标所在行数
        column (int): 光标所在列数
    
    返回:
        list: 包含补全建议的字典列表
    """
    try:
        # 创建Jedi脚本对象
        script = jedi.Script(code)
        # 获取补全建议
        completions = script.complete(line=line, column=column)
        # 将补全建议转换为字典格式
        return [{
            "name": completion.name,
            "description": completion.description
        } for completion in completions]
    except Exception as e:
        # 出错时返回错误信息
        return [{"name": "Error", "description": str(e)}]

# 代码补全接口
@app.route('/update', methods=['POST'])
def update_code():
    """
    更新代码的API端点
    
    请求方法: POST
    请求体: JSON格式，包含code、line、column字段
    响应: JSON格式，包含状态和补全建议
    """
    # 解析请求JSON数据
    data = request.json
    code = data.get("code", "")
    line = data.get("line", 1)
    column = data.get("column", 1)
    
    # 记录接收到的代码信息
    logger.info(f"Received code ({len(code)} chars) at line {line}, column {column}:")
    logger.info(code)
    logger.info("-" * 50)
    
    # 获取补全建议
    completions = get_completions(code, line, column - 1)
    logger.info(f"Completions: {completions}")
    logger.info("-" * 50)

    # 返回成功响应及补全建议
    return jsonify({
        "status": "success",
        "completions": completions
    })

# 代码运行接口
@app.route('/run', methods=['POST'])
def run_code():

    logger.info("后端收到了运行代码请求！")  # <--- 添加这行日志
    logger.info(f"当前Python解释器: {sys.executable}")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"Python路径: {sys.path}")
    data = request.get_json()
    logger.info(f"收到的代码：{data['code']}") 

    """
    接收前端发送的代码，执行并返回结果
    """
    data = request.json
    code = data.get('code', '')
    
    if not code.strip():
        return jsonify({'output': 'Error: No code to execute.\n'})

    # 安全检查：禁止危险操作
    dangerous_operations = ['import os', 'import subprocess', 'import sys', 'open(', 'file(', '__import__', 'eval(', 'exec(', 'compile(']
    for op in dangerous_operations:
        if op in code:
            return jsonify({'output': f'Error: Dangerous operation detected: {op}\n'})

    try:
        # 将代码写入临时字符串并执行
        # 使用项目中的便携式 Python 环境
        result = subprocess.run(
            [PYTHON_EXE, '-c', code], # 使用项目中的便携式 Python 解释器
            capture_output=True,    # 捕获标准输出
            text=True,              # 返回字符串而非 bytes
            timeout=3,              # 设置更严格的超时，防止死循环
            encoding='utf-8',       # 指定编码
            cwd='.',                # 限制工作目录
        )
        
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += result.stderr
        
        return jsonify({'output': output})
        
    except subprocess.TimeoutExpired:
        return jsonify({'output': 'Error: Execution timed out (3s).\n'})
    except Exception as e:
        return jsonify({'output': f'Error: {str(e)}\n'})

import os

# 文件操作相关API
@app.route('/save', methods=['POST'])
def save_file():
    """
    保存文件到服务器
    """
    data = request.json
    filename = data.get('filename', 'untitled.py')
    content = data.get('content', '')
    
    try:
        # 确保files目录存在
        if not os.path.exists('files'):
            os.makedirs('files')
        
        # 保存文件
        file_path = os.path.join('files', filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"文件保存成功: {filename}")
        return jsonify({'status': 'success', 'message': f'File saved successfully: {filename}'})
    except Exception as e:
        logger.error(f"文件保存失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

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
        file_path = os.path.join('files', filename)
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

@app.route('/files', methods=['GET'])
def get_files():
    """
    获取服务器上的文件列表
    """
    try:
        # 确保files目录存在
        if not os.path.exists('files'):
            os.makedirs('files')
        
        # 获取文件列表
        files = [f for f in os.listdir('files') if os.path.isfile(os.path.join('files', f))]
        
        logger.info(f"获取文件列表成功: {files}")
        return jsonify({'status': 'success', 'files': files})
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/terminal/execute', methods=['POST'])
def execute_terminal_command():
    """
    执行终端命令
    """
    try:
        data = request.json
        command = data.get('command', '')
        
        logger.info(f"收到终端命令: {command}")
        
        # 允许的安全命令列表
        allowed_commands = [
            'python --version',
            'pip list',
            'pip --version',
            'dir',
            'ls',
            'pwd',
            'echo'
        ]
        
        # 检查命令是否在允许列表中
        is_allowed = False
        for allowed_cmd in allowed_commands:
            if command.startswith(allowed_cmd.split(' ')[0]):
                # 禁止pip install命令
                if command.startswith('pip install'):
                    is_allowed = False
                    break
                is_allowed = True
                break
        
        if not is_allowed:
            logger.warning(f"尝试执行不允许的命令: {command}")
            return jsonify({'status': 'error', 'output': 'Error: Command not allowed'})
        
        # 执行命令
        # 对于Python相关命令，使用项目中的便携式Python环境
        if command.startswith('python'):
            # 替换python命令为项目中的便携式Python解释器路径
            modified_command = command.replace('python', PYTHON_EXE, 1)
            result = subprocess.run(modified_command, shell=True, capture_output=True, text=True, timeout=10)
        elif command.startswith('pip'):
            # 使用项目中的便携式Python环境的pip
            pip_command = f"{PYTHON_EXE} -m pip {command[4:]}"
            result = subprocess.run(pip_command, shell=True, capture_output=True, text=True, timeout=10)
        else:
            # 其他命令直接执行
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=10
            )
        
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += result.stderr
        
        logger.info(f"命令执行结果: {output}")
        return jsonify({'status': 'success', 'output': output})
        
    except subprocess.TimeoutExpired:
        logger.error(f"命令执行超时: {command}")
        return jsonify({'status': 'error', 'output': 'Error: Command timed out'})
    except Exception as e:
        logger.error(f"命令执行失败: {str(e)}")
        return jsonify({'status': 'error', 'output': f'Error: {str(e)}'})

@app.route('/python/version', methods=['GET'])
def get_python_version():
    """
    获取Python版本号
    """
    try:
        # 使用项目中的便携式Python环境
        result = subprocess.run(
            [PYTHON_EXE, "--version"],
            capture_output = True,
            text = True,
            shell=False  # 确保不使用shell
        )
        
        version = ""
        if result.stdout:
            version = result.stdout.strip()
        elif result.stderr:
            version = result.stderr.strip()
        
        logger.info(f"获取Python版本: {version}")
        return jsonify({'status': 'success', 'version': version})
        
    except Exception as e:
        logger.error(f"获取Python版本失败: {str(e)}")
        return jsonify({'status': 'error', 'version': 'Unknown'})

if __name__ == '__main__':
    # 启动Flask服务器
    logger.info("Flask server starting on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)