class Tool:
    """
    数据分析工具类 (Data Analysis Tool)

    作为数据容器，用于统一存储系统工具和用户自定义工具的元信息。
    被 system_registry.py 中的 analysis_toolbox 注册表引用，供前端界面动态渲染使用。

    属性：
        name: 工具的唯一技术标识 (英文下划线命名)
        func: 后端实际调用的 Python 函数对象
        display_name: 前端展示的中文名称
        description: 工具功能说明 (鼠标悬停或帮助文档显示)
        parameters: 参数列表 (用于前端表单配置)
    """
    def __init__(self, name, func=None, display_name="", description="", parameters=None):
        self.name = name
        self.func = func
        self.display_name = display_name
        self.description = description
        self.parameters = parameters or []

    def __repr__(self):
        return f"<Tool: {self.name}>"

    def __eq__(self, other):
        if isinstance(other, Tool):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)