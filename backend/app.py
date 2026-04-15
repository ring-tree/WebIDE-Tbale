"""
Flask 后端主程序
提供代码执行、代码补全、文件管理等功能
"""
import os
import sys
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# 添加项目根目录和backend目录到sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
backend_dir = os.path.dirname(__file__)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 导入注册表
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'system_registry',
        os.path.join(backend_dir, 'toolBox', 'system_registry .py')
    )
    registry_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(registry_module)
    analysis_toolbox = registry_module.analysis_toolbox
    logger.info(f"成功导入工具注册表，共 {len(analysis_toolbox)} 个阶段")
except Exception as e:
    logger.error(f"导入工具注册表失败: {str(e)}")
    analysis_toolbox = []

def build_tool_registry():
    """
    将Python注册表转换为前端可用的JSON结构
    """
    result = []
    for stage in analysis_toolbox:
        stage_data = {
            "stage_id": stage.get("stage_id", ""),
            "stage_name": stage.get("stage_name", ""),
            "sub_categories": []
        }
        for sub_cat in stage.get("sub_categories", []):
            sub_cat_data = {
                "sub_category_id": sub_cat.get("sub_category_id", ""),
                "sub_category_name": sub_cat.get("sub_category_name", ""),
                "tools": []
            }
            for tool in sub_cat.get("tools", []):
                tool_data = {
                    "name": tool.name if hasattr(tool, 'name') else str(tool.get('name', '')),
                    "display_name": tool.display_name if hasattr(tool, 'display_name') else str(tool.get('display_name', '')),
                    "description": tool.description if hasattr(tool, 'description') else str(tool.get('description', '')),
                    "parameters": tool.parameters if hasattr(tool, 'parameters') else tool.get('parameters', [])
                }
                sub_cat_data["tools"].append(tool_data)
            stage_data["sub_categories"].append(sub_cat_data)
        result.append(stage_data)
    return result

@app.route('/api/tools', methods=['GET'])
def get_tool_registry():
    """
    获取工具注册表
    返回前端所需的工具列表结构（层级结构）
    """
    try:
        registry = build_tool_registry()
        return jsonify({
            'status': 'success',
            'data': registry
        })
    except Exception as e:
        logger.error(f"获取工具注册表失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/tools/all', methods=['GET'])
def get_all_tools():
    """
    获取所有工具的扁平列表
    方便前端快速遍历所有工具
    """
    try:
        all_tools = []
        for stage in analysis_toolbox:
            for sub_cat in stage.get("sub_categories", []):
                for tool in sub_cat.get("tools", []):
                    tool_data = {
                        "name": tool.name if hasattr(tool, 'name') else str(tool.get('name', '')),
                        "display_name": tool.display_name if hasattr(tool, 'display_name') else str(tool.get('display_name', '')),
                        "description": tool.description if hasattr(tool, 'description') else str(tool.get('description', '')),
                        "parameters": tool.parameters if hasattr(tool, 'parameters') else tool.get('parameters', []),
                        "stage_id": stage.get("stage_id", ""),
                        "stage_name": stage.get("stage_name", ""),
                        "sub_category_id": sub_cat.get("sub_category_id", ""),
                        "sub_category_name": sub_cat.get("sub_category_name", "")
                    }
                    all_tools.append(tool_data)
        return jsonify({
            'status': 'success',
            'data': all_tools
        })
    except Exception as e:
        logger.error(f"获取所有工具失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/tools/search', methods=['GET'])
def search_tools():
    """
    搜索工具
    query参数: 搜索关键词
    """
    try:
        query = request.args.get('query', '').lower()
        if not query:
            return jsonify({
                'status': 'success',
                'data': []
            })

        results = []
        for stage in analysis_toolbox:
            for sub_cat in stage.get("sub_categories", []):
                for tool in sub_cat.get("tools", []):
                    name = tool.name if hasattr(tool, 'name') else str(tool.get('name', ''))
                    display_name = tool.display_name if hasattr(tool, 'display_name') else str(tool.get('display_name', ''))
                    description = tool.description if hasattr(tool, 'description') else str(tool.get('description', ''))

                    if (query in name.lower() or
                        query in display_name.lower() or
                        query in description.lower()):
                        results.append({
                            "name": name,
                            "display_name": display_name,
                            "description": description,
                            "parameters": tool.parameters if hasattr(tool, 'parameters') else tool.get('parameters', []),
                            "stage_id": stage.get("stage_id", ""),
                            "stage_name": stage.get("stage_name", "")
                        })

        return jsonify({
            'status': 'success',
            'data': results
        })
    except Exception as e:
        logger.error(f"搜索工具失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/tools/<tool_name>', methods=['POST'])
def execute_tool(tool_name):
    """
    执行指定的工具函数
    """
    try:
        data = request.json or {}
        params = data.get('params', {})

        # 在注册表中查找工具
        tool_func = None
        for stage in analysis_toolbox:
            for sub_cat in stage.get("sub_categories", []):
                for tool in sub_cat.get("tools", []):
                    if hasattr(tool, 'name') and tool.name == tool_name:
                        tool_func = tool.func
                        break
                    elif tool.get('name') == tool_name:
                        tool_func = tool.get('func')
                        break

        if not tool_func:
            return jsonify({
                'status': 'error',
                'message': f'Tool not found: {tool_name}'
            })

        # 执行工具函数
        result = tool_func(**params)
        return jsonify({
            'status': 'success',
            'result': result
        })
    except Exception as e:
        logger.error(f"执行工具失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

# 其他现有路由...

if __name__ == '__main__':
    logger.info("Flask server starting on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)
