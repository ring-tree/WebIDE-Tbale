"""pytest 公共夹具与运行环境准备。

注意：本文件中的环境变量必须在导入 app 之前设置，
      因为 app.py 在模块级读取这些配置。
"""

import os
import pathlib
import sys

# ---- 必须在 import app 之前完成 ----
os.environ.setdefault('WEBIDE_AUTH_TOKEN', 'test-token')
os.environ.setdefault('WEBIDE_EXEC_TIMEOUT', '5')          # 缩短超时用例耗时
os.environ.setdefault('WEBIDE_EXEC_MEMORY_MB', '256')      # 便于验证内存上限
os.environ.setdefault('WEBIDE_EXEC_MAX_OUTPUT_KB', '2')    # 便于验证输出截断
os.environ.setdefault('WEBIDE_EXEC_MAX_CODE_KB', '1')      # 便于验证代码体积上限
os.environ.setdefault('WEBIDE_MAX_UPLOAD_MB', '1')         # 便于验证上传上限

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

for _p in (str(BACKEND_DIR), str(PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402

import app as backend_app  # noqa: E402


@pytest.fixture(scope='session')
def app_module():
    """已导入的后端模块"""
    return backend_app


@pytest.fixture()
def client(app_module):
    """Flask 测试客户端"""
    return app_module.app.test_client()


@pytest.fixture()
def auth(app_module):
    """携带有效令牌的请求头"""
    return {'X-Auth-Token': app_module.AUTH_TOKEN}


@pytest.fixture()
def allow_delete(monkeypatch):
    """把 os.remove 替换为「记录调用」，并返回记录列表。

    存在原因：本仓库的默认开发环境带有文件删除守卫，会阻塞子进程发起的删除，
    导致 /run、/update 等端点挂起。该夹具让清理代码路径可被断言，
    同时避免测试卡死。在常规环境下同样可用（仅不真正删除临时文件）。

    返回的列表记录了被请求删除的路径，可用于断言「清理逻辑确实被触发」。
    """
    calls = []

    def _recording_remove(path, *args, **kwargs):
        calls.append(str(path))
        return None

    monkeypatch.setattr(backend_app.os, 'remove', _recording_remove)
    return calls
