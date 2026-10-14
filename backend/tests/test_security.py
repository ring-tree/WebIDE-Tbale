"""安全与边界行为回归测试。

覆盖四类曾经出问题或属于高危的能力：
  1. 鉴权
  2. 路径安全（任意文件读写删 / 越界）
  3. 执行限制（超时 / 内存 / 输出 / 代码体积）
  4. 终端命令策略与上传约束

运行方式：
    cd backend && uv run pytest
"""

import io
import os
import tempfile

import pytest


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------
def _collect_paths(node, out=None):
    """递归收集文件树中的所有 path 字段"""
    if out is None:
        out = []
    if not isinstance(node, dict):
        return out
    if 'path' in node:
        out.append(node['path'])
    for child in node.get('children') or []:
        _collect_paths(child, out)
    return out


# ------------------------------------------------------------------
# 1. 鉴权
# ------------------------------------------------------------------
class TestAuth:
    def test_rejects_missing_token(self, client):
        assert client.get('/api/tools/all').status_code == 401

    def test_rejects_wrong_token(self, client):
        r = client.get('/api/tools/all', headers={'X-Auth-Token': 'definitely-wrong'})
        assert r.status_code == 401

    def test_accepts_valid_token(self, client, auth):
        r = client.get('/api/tools/all', headers=auth)
        assert r.status_code == 200
        assert r.get_json()['status'] == 'success'

    def test_options_preflight_not_blocked(self, client):
        r = client.open('/run', method='OPTIONS')
        assert r.status_code != 401

    def test_token_also_accepted_via_query(self, client, app_module):
        r = client.get(f'/python/version?token={app_module.AUTH_TOKEN}')
        assert r.status_code == 200


# ------------------------------------------------------------------
# 2. 路径安全
# ------------------------------------------------------------------
class TestPathSafety:
    @pytest.mark.parametrize('bad', [
        'C:/Windows/win.ini',
        'C:\\Windows\\win.ini',
        'D:/Program Files/x.txt',
        '/etc/passwd',
        '../env_config.py',
        '..\\..\\evil.py',
        'project/../../secret.txt',
    ])
    def test_load_rejects_unsafe_paths(self, client, auth, bad):
        r = client.post('/load', json={'filename': bad}, headers=auth)
        body = r.get_json()
        assert body['status'] == 'error'
        assert body['message'] == 'Invalid filename'

    def test_load_rejects_empty(self, client, auth):
        r = client.post('/load', json={'filename': ''}, headers=auth)
        assert r.get_json()['status'] == 'error'

    def test_delete_outside_workspace_refused(self, client, auth):
        """工作区外的文件必须无法被删除

        注意：这里刻意不用 pytest 的 tmp_path 夹具 —— 它的清理阶段会删除
        pytest-of-<user>/garbage-* 目录，在带有文件删除守卫的环境中会被拦截，
        导致 pytest 在 teardown 异常退出（测试全绿但退出码非 0）。
        因此改为自行创建临时文件，并**不做清理**（由系统临时目录回收）。
        """
        fd, path = tempfile.mkstemp(prefix='webide_probe_', suffix='.txt')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write('do not delete')

        r = client.post('/api/files/delete', json={'path': path}, headers=auth)

        assert r.get_json()['status'] == 'error'
        assert os.path.exists(path), '工作区外的文件被删除了'

    def test_save_into_readonly_dir_refused(self, client, auth):
        for name in ('project/toolBox/probe.txt', 'project\\toolBox\\probe.txt'):
            r = client.post('/save', json={'filename': name, 'content': 'x'}, headers=auth)
            assert 'read-only' in r.get_json()['message'], f'反斜杠/正斜杠路径未被拦截: {name}'

    def test_create_rejects_absolute_path(self, client, auth):
        r = client.post('/api/files/create', json={'path': 'C:/evil.py', 'type': 'file'}, headers=auth)
        assert r.get_json()['message'] == 'Invalid path'

    def test_rename_rejects_path_in_new_name(self, client, auth):
        for new_name in ('../x.py', 'sub/x.py', 'sub\\x.py', 'C:x.py', '..', ''):
            r = client.post('/api/files/rename',
                            json={'path': 'project/src/app.py', 'newName': new_name},
                            headers=auth)
            assert r.get_json()['message'] == 'Invalid new name', f'未拦截: {new_name!r}'

    @pytest.mark.parametrize('bad', ['C:/Windows', '../../', '..', '/etc'])
    def test_file_tree_rejects_unsafe_path(self, client, auth, bad):
        r = client.get(f'/api/files?path={bad}', headers=auth)
        assert r.get_json()['message'] == 'Invalid path'

    def test_file_tree_outputs_posix_separators(self, client, auth):
        tree = client.get('/api/files?path=project', headers=auth).get_json()
        paths = _collect_paths(tree)
        assert paths, '文件树为空'
        assert all('\\' not in p for p in paths), '文件树仍返回反斜杠路径'

    def test_file_tree_path_round_trip(self, client, auth):
        """文件树返回的路径必须能直接用于 /load（曾因分隔符不一致而失败）"""
        tree = client.get('/api/files?path=project', headers=auth).get_json()
        first_file = next(p for p in _collect_paths(tree) if p.endswith('.py'))

        r = client.post('/load', json={'filename': first_file}, headers=auth)
        assert r.get_json()['status'] == 'success', f'无法打开文件树返回的路径: {first_file}'


# ------------------------------------------------------------------
# 3. 执行限制
# ------------------------------------------------------------------
class TestExecutionLimits:
    def test_normal_execution(self, client, auth, allow_delete):
        r = client.post('/run', json={'code': 'print(1 + 1)'}, headers=auth)
        body = r.get_json()
        assert body['status'] == 'success'
        assert body['returncode'] == 0
        assert '2' in body['output']

    def test_empty_code_rejected(self, client, auth):
        r = client.post('/run', json={'code': '   '}, headers=auth)
        assert r.get_json()['status'] == 'error'

    def test_code_size_limit(self, client, auth):
        oversized = 'x = 1\n' * 1000        # 约 6 KB，超过 1 KB 上限
        r = client.post('/run', json={'code': oversized}, headers=auth)
        body = r.get_json()
        assert body['status'] == 'error'
        assert '上限' in body['output']

    def test_timeout_kills_process_tree(self, client, auth, allow_delete):
        r = client.post('/run', json={'code': 'while True: pass'}, headers=auth)
        body = r.get_json()
        assert body['status'] == 'error'
        assert '超时' in body['output']

    def test_output_is_truncated(self, client, auth, allow_delete):
        r = client.post('/run', json={'code': "print('A' * 100000)"}, headers=auth)
        body = r.get_json()
        assert '已截断' in body['output']

    def test_isolated_mode_enabled(self, client, auth, allow_delete):
        """-I 隔离模式：忽略 PYTHON* 环境变量与用户 site 目录"""
        r = client.post('/run', json={'code': 'import sys; print(sys.flags.isolated)'}, headers=auth)
        assert '1' in r.get_json()['output']

    def test_temp_file_cleanup_triggered(self, client, auth, allow_delete):
        client.post('/run', json={'code': 'print(1)'}, headers=auth)
        assert allow_delete, '未调用 os.remove 清理代码执行临时文件'
        assert any('run_' in p for p in allow_delete), f'清理的路径不符合预期: {allow_delete}'

    def test_temp_file_names_are_unique(self, client, auth, allow_delete):
        """并发请求不得复用同一个临时文件名"""
        for _ in range(3):
            client.post('/run', json={'code': 'print(1)'}, headers=auth)
        assert len(set(allow_delete)) == len(allow_delete), '存在重复的临时文件名'

    @pytest.mark.skipif(os.name != 'nt', reason='Windows Job Object 专属限制')
    def test_memory_limit_enforced(self, client, auth, allow_delete):
        """单进程内存上限 256 MB，申请 1 GB 应当失败"""
        r = client.post('/run',
                        json={'code': "a = bytearray(1024 * 1024 * 1024)\nprint('allocated')"},
                        headers=auth)
        body = r.get_json()
        assert 'MemoryError' in body['output'] or body['returncode'] != 0, \
            '内存上限未生效：1 GB 申请成功'


# ------------------------------------------------------------------
# 4. 终端命令策略
# ------------------------------------------------------------------
class TestTerminalPolicy:
    def test_allowlisted_command_runs(self, client, auth, allow_delete):
        r = client.post('/terminal/execute', json={'command': 'python --version'}, headers=auth)
        body = r.get_json()
        assert body['status'] == 'success'
        assert 'Python' in body['output']

    def test_empty_command_rejected(self, client, auth):
        r = client.post('/terminal/execute', json={'command': '  '}, headers=auth)
        assert r.get_json()['status'] == 'error'

    @pytest.mark.parametrize('cmd', [
        'del important.txt',
        'rm -rf /',
        'format C:',
        'curl http://evil.example.com',
    ])
    def test_non_allowlisted_rejected(self, client, auth, cmd):
        r = client.post('/terminal/execute', json={'command': cmd}, headers=auth)
        body = r.get_json()
        assert body['status'] == 'error'
        assert '安全策略' in body['output']

    @pytest.mark.parametrize('cmd', [
        'echo a && echo b',
        'echo a; echo b',
        'echo a || echo b',
        'pip list | findstr flask',
        'echo x > out.txt',
        'echo x < in.txt',
        'echo `whoami`',
        'echo $(whoami)',
    ])
    def test_shell_metacharacters_rejected(self, client, auth, cmd):
        r = client.post('/terminal/execute', json={'command': cmd}, headers=auth)
        body = r.get_json()
        assert body['status'] == 'error'
        assert '安全策略' in body['output']


# ------------------------------------------------------------------
# 5. 上传与 AI 配置
# ------------------------------------------------------------------
class TestUploadAndAiConfig:
    def test_upload_rejects_disallowed_extension(self, client, auth):
        data = {'file': (io.BytesIO(b'payload'), 'evil.exe')}
        r = client.post('/api/upload', data=data, headers=auth,
                        content_type='multipart/form-data')
        assert r.get_json()['status'] == 'error'

    def test_upload_accepts_csv(self, client, auth, allow_delete):
        data = {'file': (io.BytesIO(b'a,b\n1,2\n3,4\n'), 'sample.csv')}
        r = client.post('/api/upload', data=data, headers=auth,
                        content_type='multipart/form-data')
        assert r.get_json()['status'] == 'success'

    def test_sessions_are_isolated(self, client, auth, allow_delete):
        """不同会话的数据集互不覆盖（曾因全局单例目录导致互相清空）"""
        h1 = dict(auth, **{'X-Session-Id': 'session-a'})
        h2 = dict(auth, **{'X-Session-Id': 'session-b'})

        r1 = client.post('/api/upload', data={'file': (io.BytesIO(b'a\n1\n'), 'a.csv')},
                         headers=h1, content_type='multipart/form-data')
        r2 = client.post('/api/upload', data={'file': (io.BytesIO(b'b\n2\n'), 'b.csv')},
                         headers=h2, content_type='multipart/form-data')

        assert r1.get_json()['status'] == 'success'
        assert r2.get_json()['status'] == 'success'
        assert 'session-a' in r1.get_json()['filepath']
        assert 'session-b' in r2.get_json()['filepath']
        assert os.path.exists(r1.get_json()['filepath']), '会话 A 的数据被会话 B 的上传清空了'

    def test_data_info_empty_before_upload(self, client, auth):
        h = dict(auth, **{'X-Session-Id': 'info-empty'})
        data = client.get('/api/data/info', headers=h).get_json()['data']
        assert data['loaded'] is False
        assert data['columns'] == []

    def test_data_info_reports_columns_after_upload(self, client, auth, allow_delete):
        """工具箱的多选列控件依赖该接口返回列名"""
        h = dict(auth, **{'X-Session-Id': 'info-filled'})
        csv = b'age,income,city\n20,1000,A\n30,2000,B\n40,3000,C\n'
        client.post('/api/upload', data={'file': (io.BytesIO(csv), 'd.csv')},
                    headers=h, content_type='multipart/form-data')

        data = client.get('/api/data/info', headers=h).get_json()['data']
        assert data['loaded'] is True
        assert data['rows'] == 3
        assert data['column_count'] == 3
        assert data['columns'] == ['age', 'income', 'city']
        # city 是字符串列，不应出现在数值列中
        assert data['numeric_columns'] == ['age', 'income']
        assert 'city' not in data['numeric_columns']

    def test_ai_reports_missing_key_clearly(self, client, auth, app_module):
        if app_module.is_ai_configured():
            pytest.skip('当前环境已配置 AI 密钥，跳过未配置场景')

        r = client.post('/api/ai/chat',
                        json={'messages': [{'role': 'user', 'content': 'hi'}]},
                        headers=auth)
        body = r.get_json()
        assert body['status'] == 'error'
        assert 'DASHSCOPE_API_KEY' in body['message'] or 'ai_config' in body['message']

    def test_ai_config_endpoint_does_not_leak_key(self, client, auth):
        r = client.get('/api/ai/config', headers=auth)
        assert r.status_code == 200
        data = r.get_json()['data']
        assert 'api_key' not in data
        assert 'has_api_key' in data

    def test_ai_models_endpoint(self, client, auth):
        r = client.get('/api/ai/models', headers=auth)
        body = r.get_json()
        assert body['status'] == 'success'
        assert body['data']


# ------------------------------------------------------------------
# 6. 全局 AI 配置加载器
# ------------------------------------------------------------------
class TestAiConfigLoader:
    def test_meta_fields_are_filtered(self):
        from config import get_ai_config
        cfg = get_ai_config()
        assert not [k for k in cfg if k.startswith('_')], '下划线说明字段泄漏到了配置里'

    def test_required_keys_present(self):
        from config import get_ai_config
        cfg = get_ai_config()
        for key in ('default_model', 'base_url', 'api_key', 'generation', 'enabled'):
            assert key in cfg, f'缺少配置项: {key}'

    def test_env_var_overrides_config_file(self, monkeypatch):
        import config as ai_config_module

        monkeypatch.setenv('WEBIDE_AI_MODEL', 'qwen-from-env')
        try:
            cfg = ai_config_module.reload_ai_config()
            assert cfg['default_model'] == 'qwen-from-env'
        finally:
            monkeypatch.delenv('WEBIDE_AI_MODEL', raising=False)
            ai_config_module.reload_ai_config()


# ------------------------------------------------------------------
# 7. 错误信息脱敏
# ------------------------------------------------------------------
class TestErrorSanitization:
    def test_absolute_paths_are_stripped(self, app_module):
        msg = app_module.sanitize_error(
            FileNotFoundError(r"[WinError 2] 系统找不到指定的文件: 'D:\secret\a\b.py'")
        )
        assert 'D:\\secret' not in msg
        assert '<path>' in msg

    def test_plain_validation_message_kept(self, app_module):
        """工具自身的参数校验提示需要保留，否则使用体验受损"""
        msg = app_module.sanitize_error(ValueError("列 'age' 不存在于 DataFrame 中"))
        assert 'age' in msg

    def test_overlong_message_falls_back(self, app_module):
        msg = app_module.sanitize_error(ValueError('x' * 1000), fallback='Operation failed')
        assert msg == 'Operation failed'
