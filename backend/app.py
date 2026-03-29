from flask import Flask, request, jsonify
from flask_cors import CORS
import jedi

# 创建Flask应用实例
app = Flask(__name__)
# 启用跨域资源共享(CORS)
CORS(app)

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
    except:
        # 出错时返回空列表
        return []

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
    
    # 打印接收到的代码信息
    print(f"Received code ({len(code)} chars) at line {line}, column {column}:")
    print(code)
    print("-" * 50)
    
    # 获取补全建议
    completions = get_completions(code, line, column - 1)
    print(completions)
    print("-" * 50)

    # 返回成功响应及补全建议
    return jsonify({
        "status": "success",
        "completions": completions
    })

if __name__ == '__main__':
    # 启动Flask服务器
    print("Flask server starting on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)