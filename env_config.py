# 环境配置文件
# 定义项目全局使用的环境路径

import os
import sys
import subprocess

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 便携式Node.js环境路径
NODE_DIR = os.path.join(PROJECT_ROOT, 'node_env')
# NODE_EXE = os.path.join(NODE_DIR, 'node.exe')
NODE_EXE = os.path.join(r'D:/Program Files(x86)/nodejs/nodejs_24_14/node.exe')

# 便携式Python环境路径
PYTHON_DIR = os.path.join(PROJECT_ROOT, 'backend', 'python313')
# PYTHON_EXE = os.path.join(PYTHON_DIR, 'python.exe')
PYTHON_EXE = os.path.join(r'D:/Program Files(x86)/Python3.13/python.exe')

# 确保环境变量中优先使用项目的环境
# os.environ['PATH'] = f"{NODE_DIR};{PYTHON_DIR};{os.environ.get('PATH', '')}"

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

def get_env_vars_for_batch():
    """输出环境变量供批处理脚本使用"""
    print(f"NODE_EXE={NODE_EXE}")
    print(f"PYTHON_EXE={PYTHON_EXE}")

if __name__ == "__main__":
    if "--export" in sys.argv:
        get_env_vars_for_batch()
    else:
        test_environments()
