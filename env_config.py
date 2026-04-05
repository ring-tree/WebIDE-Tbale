# 环境配置文件
# 定义项目全局使用的环境路径

import os
import sys
import subprocess

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 便携式Node.js环境路径
NODE_DIR = os.path.join(PROJECT_ROOT, 'node_env')
NODE_EXE = os.path.join(NODE_DIR, 'node.exe')

# 便携式Python环境路径
PYTHON_DIR = os.path.join(PROJECT_ROOT, 'backend', 'python313')
PYTHON_EXE = os.path.join(PYTHON_DIR, 'python.exe')

# 确保环境变量中优先使用项目的环境
os.environ['PATH'] = f"{NODE_DIR};{PYTHON_DIR};{os.environ.get('PATH', '')}"

# 测试环境是否可用
def test_environments():
    """测试环境是否可用"""
    print("=== 环境测试 ===")
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"Node.js 路径: {NODE_EXE}")
    print(f"Node.js 存在: {os.path.exists(NODE_EXE)}")
    print(f"Python 路径: {PYTHON_EXE}")
    print(f"Python 存在: {os.path.exists(PYTHON_EXE)}")
    
    # 测试Python版本
    if os.path.exists(PYTHON_EXE):
        try:
            result = subprocess.run(
                [PYTHON_EXE, "--version"],
                capture_output=True,
                text=True
            )
            version = result.stdout.strip() if result.stdout else result.stderr.strip()
            print(f"Python 版本: {version}")
        except Exception as e:
            print(f"测试Python版本失败: {str(e)}")
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_environments()
    # 输出Python可执行文件路径，供批处理脚本使用
    print(PYTHON_EXE)
