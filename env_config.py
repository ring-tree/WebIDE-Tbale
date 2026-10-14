# 环境配置文件
# 定义项目全局使用的环境路径
#
# 设计原则：
#   1. 优先使用项目自带的运行时（backend/.venv、node_env），不依赖任何全局安装；
#   2. 其次回退到 PATH 中的同名可执行文件；
#   3. 最后回退到当前进程的解释器。
# 这样项目可在任意机器上克隆后直接运行，无需修改本文件。

import os
import sys
import shutil
import subprocess

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend')


def _first_existing(paths):
    """返回第一个存在的路径，全部不存在则返回 None"""
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


# ===================== Node.js =====================
# 优先使用项目自带的便携式 Node.js
NODE_DIR = os.path.join(PROJECT_ROOT, 'node_env')
NODE_EXE = _first_existing([
    os.path.join(NODE_DIR, 'node.exe'),
    os.path.join(NODE_DIR, 'bin', 'node'),
    shutil.which('node'),
]) or 'node'

# ===================== Python =====================
# 优先使用 uv 管理的项目级虚拟环境（backend/.venv）
VENV_DIR = os.path.join(BACKEND_DIR, '.venv')
PYTHON_EXE = _first_existing([
    os.path.join(VENV_DIR, 'Scripts', 'python.exe'),   # Windows
    os.path.join(VENV_DIR, 'bin', 'python'),           # POSIX
    shutil.which('python'),
]) or sys.executable

# 供子进程调用时使用的环境变量（保证 uv/venv 相关变量不被污染）
def get_subprocess_env():
    """构造用于启动 Python 子进程的环境变量"""
    env = os.environ.copy()
    # 避免虚拟环境嵌套时丢失 PATH 中的 Scripts 目录
    scripts_dir = os.path.dirname(PYTHON_EXE)
    if scripts_dir and scripts_dir not in env.get('PATH', ''):
        env['PATH'] = f"{scripts_dir}{os.pathsep}{env.get('PATH', '')}"
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


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
