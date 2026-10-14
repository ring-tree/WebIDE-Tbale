"""数据分析多步流程与产物隔离测试。

覆盖两条此前缺失的能力：

1. **产物按会话隔离** —— 产物目录与访问地址都带会话标识，
   避免不同会话的图表/CSV 混在同一目录、互相覆盖。

2. **多步流程串联** —— `/api/data/adopt` 把一次分析的表格产物设回当前数据集。
   此前数据清洗 / 特征工程 / 建模无法在界面上连续进行，
   必须手动下载 CSV 再上传，这条链路打通后可以直接串联。
"""

import io

import pytest


def _upload_csv(client, headers, content: bytes, name='data.csv'):
    return client.post(
        '/api/upload',
        data={'file': (io.BytesIO(content), name)},
        headers=headers,
        content_type='multipart/form-data',
    )


def _run_transform(client, headers, csv=b'a,b\n1,2\n3,4\n'):
    """跑一个会产生表格产物的变换类工具，返回其产物描述"""
    _upload_csv(client, headers, csv)
    body = client.post(
        '/api/tools/impute_missing_values',
        json={'methodConfig': {'strategy': 'mean'}},
        headers=headers,
    ).get_json()
    assert body['status'] == 'success', body
    return body['result']['data']


def _run_plot(client, headers, column='x'):
    _upload_csv(client, headers, b'x\n1\n2\n3\n4\n5\n')
    body = client.post(
        '/api/tools/N_plot_histogram',
        json={'methodConfig': {'column': column, 'bins': 2}},
        headers=headers,
    ).get_json()
    assert body['status'] == 'success', body
    return body['result']['figure']


class TestOutputIsolation:
    def test_output_url_contains_session_id(self, client, auth, allow_delete):
        h = dict(auth, **{'X-Session-Id': 'out-a'})
        figure = _run_plot(client, h)
        assert figure['path'].startswith('/api/output/out-a/'), (
            f"产物地址应包含会话标识，实际: {figure['path']}"
        )

    def test_output_isolated_between_sessions(self, client, auth, allow_delete):
        """A 会话的产物不应出现在 B 会话的产物目录下"""
        ha = dict(auth, **{'X-Session-Id': 'owner'})
        hb = dict(auth, **{'X-Session-Id': 'intruder'})

        figure = _run_plot(client, ha)
        filename = figure['path'].rsplit('/', 1)[-1]

        r = client.get(f'/api/output/intruder/{filename}', headers=hb)
        assert r.status_code == 404

    def test_output_reachable_in_own_session(self, client, auth, allow_delete):
        h = dict(auth, **{'X-Session-Id': 'self-out'})
        figure = _run_plot(client, h)

        r = client.get(figure['path'], headers=h)
        assert r.status_code == 200
        assert r.headers.get('Content-Type', '').startswith('image/png')

    @pytest.mark.parametrize('session_id', ['bad!id', 'has space', '..'])
    def test_output_invalid_session_rejected(self, client, auth, session_id):
        r = client.get(f'/api/output/{session_id}/x.png', headers=auth)
        assert r.status_code in (400, 404), f'非法会话标识未被拒绝: {session_id}'


class TestAdoptResultAsDataset:
    def test_adopt_tabular_result(self, client, auth, allow_delete):
        """变换类工具的 CSV 产物可以设回数据集"""
        h = dict(auth, **{'X-Session-Id': 'flow-a'})
        produced = _run_transform(client, h)
        assert produced['_type'] == 'file'
        assert produced['filename'].endswith('.csv')

        body = client.post('/api/data/adopt',
                           json={'filename': produced['filename']},
                           headers=h).get_json()

        assert body['status'] == 'success', body
        assert body['data']['loaded'] is True
        assert body['data']['rows'] == 2

        # 数据集信息接口应反映新数据集
        info = client.get('/api/data/info', headers=h).get_json()['data']
        assert info['loaded'] is True
        assert info['columns'] == ['a', 'b']

    def test_multi_step_flow_can_be_chained(self, client, auth, allow_delete):
        """连续串联：填充缺失值 → 设回数据集 → 再做标准化

        注意 CSV 用两列构造缺失值：单列 CSV 的空值表现为空行，
        而 pandas 默认会跳过空行，导致「缺失值」根本没被解析出来。
        """
        h = dict(auth, **{'X-Session-Id': 'flow-chain'})

        # 第 1 步：清洗（v 列第 2 行为空 → 缺失值）
        step1 = _run_transform(client, h, csv=b'v,w\n1,10\n,20\n3,30\n4,40\n')
        adopted = client.post('/api/data/adopt',
                              json={'filename': step1['filename']},
                              headers=h).get_json()
        assert adopted['status'] == 'success'

        # 第 2 步：基于上一步结果继续做标准化
        step2 = client.post('/api/tools/standard_scaling',
                            json={'methodConfig': {'columns': ['v']}},
                            headers=h).get_json()
        assert step2['status'] == 'success', step2
        assert step2['result']['data']['_type'] == 'file'

    def test_adopt_rejects_non_tabular_result(self, client, auth, allow_delete):
        h = dict(auth, **{'X-Session-Id': 'flow-b'})
        figure = _run_plot(client, h)
        png = figure['path'].rsplit('/', 1)[-1]

        body = client.post('/api/data/adopt', json={'filename': png}, headers=h).get_json()
        assert body['status'] == 'error'
        assert 'tabular' in body['message'].lower()

    @pytest.mark.parametrize('bad', [
        '../secret.csv',
        'sub/dir/data.csv',
        'sub\\dir\\data.csv',
        'C:/Windows/data.csv',
        '',
    ])
    def test_adopt_rejects_unsafe_filename(self, client, auth, bad):
        body = client.post('/api/data/adopt', json={'filename': bad}, headers=auth).get_json()
        assert body['status'] == 'error', f'非法文件名未被拒绝: {bad!r}'

    def test_adopt_missing_file(self, client, auth, allow_delete):
        h = dict(auth, **{'X-Session-Id': 'flow-c'})
        body = client.post('/api/data/adopt',
                           json={'filename': 'not_exist.csv'},
                           headers=h).get_json()
        assert body['status'] == 'error'
        assert 'not found' in body['message'].lower()

    def test_adopt_does_not_leak_other_session_output(self, client, auth, allow_delete):
        """不能把别的会话的产物设为自己的数据集"""
        ha = dict(auth, **{'X-Session-Id': 'flow-owner'})
        hb = dict(auth, **{'X-Session-Id': 'flow-other'})

        produced = _run_transform(client, ha)

        body = client.post('/api/data/adopt',
                           json={'filename': produced['filename']},
                           headers=hb).get_json()
        assert body['status'] == 'error', '跨会话读取了他人产物'
