"""工具注册表与工具箱完整性测试。

存在原因（真实踩过的坑）：
    曾出现 scikit-learn 半装（`sklearn` 可导入但 `sklearn.preprocessing` 缺失），
    导致工具注册表在启动时加载失败、28 个工具全部不可用，
    但 `/api/tools` 仍返回 HTTP 200 与空数组 —— 只断言状态码发现不了这个问题。

因此这里显式断言：
    1. 注册表已加载且数量符合预期；
    2. 每个工具都有可调用的实现；
    3. 工具箱包可完整导入（捕获子模块级依赖缺失）。
"""

import pytest


def _all_tools(app_module):
    return [
        tool
        for stage in app_module.analysis_toolbox
        for sub in stage.get('sub_categories', [])
        for tool in sub.get('tools', [])
    ]


class TestToolRegistry:
    def test_registry_is_loaded(self, app_module):
        assert app_module.analysis_toolbox, (
            '工具注册表为空。通常是某个工具模块导入失败（依赖缺失或半装），'
            '请查看后端启动日志中的「导入工具注册表失败」条目。'
        )

    def test_stage_count(self, app_module):
        assert len(app_module.analysis_toolbox) == 6, (
            f"阶段数应为 6，实际 {len(app_module.analysis_toolbox)}"
        )

    def test_tool_count(self, app_module):
        tools = _all_tools(app_module)
        assert len(tools) == 28, f"工具总数应为 28，实际 {len(tools)}"

    def test_every_tool_has_callable_impl(self, app_module):
        broken = [t.name for t in _all_tools(app_module) if not callable(getattr(t, 'func', None))]
        assert not broken, f"以下工具缺少可调用实现: {broken}"

    def test_tool_names_are_unique(self, app_module):
        names = [t.name for t in _all_tools(app_module)]
        duplicates = {n for n in names if names.count(n) > 1}
        assert not duplicates, f"存在重名工具: {duplicates}"

    def test_api_tools_endpoint_returns_registry(self, client, auth):
        body = client.get('/api/tools', headers=auth).get_json()
        assert body['status'] == 'success'
        assert len(body['data']) == 6, '注册表接口返回空，前端将看不到任何工具'

    def test_api_tools_all_endpoint_returns_tools(self, client, auth):
        body = client.get('/api/tools/all', headers=auth).get_json()
        assert body['status'] == 'success'
        assert len(body['data']) == 28

    def test_tool_search_works(self, client, auth):
        body = client.get('/api/tools/search?query=histogram', headers=auth).get_json()
        assert body['status'] == 'success'
        assert body['data'], '搜索「histogram」应至少命中一个工具'

    def test_toolbox_package_imports_cleanly(self):
        """直接导入工具箱包 —— 会触发全部 28 个工具模块的导入，
        可捕获子模块级依赖缺失（如 sklearn.preprocessing）。"""
        from project.toolBox import system_tool

        exported = [n for n in system_tool.__all__ if not hasattr(system_tool, n)]
        assert not exported, f"以下工具在 __all__ 中声明但未成功导出: {exported}"

    def test_tool_parameter_metadata_shape(self, app_module):
        """参数元信息需具备前端渲染所需字段"""
        for tool in _all_tools(app_module):
            for param in tool.parameters or []:
                assert 'name' in param, f"{tool.name} 的参数缺少 name"
                assert 'type' in param, f"{tool.name}.{param.get('name')} 缺少 type"
