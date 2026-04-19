from typing import Any, Dict, Optional
import pandas as pd
import re


def rename_columns(
    data: pd.DataFrame,
    mapping: Optional[Dict[str, str]] = None,
    pattern: Optional[str] = None,
    replacement: str = "",
    use_regex: bool = True,
) -> Dict[str, Any]:
    """批量规范化列命名。

    支持映射转换与正则替换，提升数据可读性。

    Args:
        data: 输入的 pandas DataFrame。
        mapping: 列名映射字典，键为旧列名，值为新列名。
        pattern: 要匹配的正则表达式模式或子串。
        replacement: 替换字符串，默认为空字符串。
        use_regex: 是否将 pattern 作为正则表达式处理，默认为 True。

    Returns:
        包含 'data'（重命名后的 DataFrame）、'renamed_columns'（重命名映射）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当 mapping 为空且 pattern 也未指定时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'old_a': [1, 2], 'old_b': [3, 4]})
        >>> result = rename_columns(df, mapping={'old_a': 'new_a'})
        >>> list(result['data'].columns)
        ['new_a', 'old_b']
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if mapping is None and pattern is None:
        raise ValueError("必须指定 mapping 或 pattern 参数")

    if data.empty and len(data.columns) == 0:
        return {
            "data": data.copy(),
            "renamed_columns": {},
        }

    new_columns: Dict[str, str] = {}

    if mapping:
        if not isinstance(mapping, dict):
            raise TypeError(f"参数 mapping 必须为字典，实际类型: {type(mapping).__name__}")

        invalid_keys = [k for k in mapping if k not in data.columns]
        if invalid_keys:
            raise ValueError(f"以下旧列名不存在: {invalid_keys}")

        duplicate_values = {}
        seen = {}
        for k, v in mapping.items():
            if v in seen:
                duplicate_values[v] = [seen[v], k]
            seen[v] = k
        if duplicate_values:
            raise ValueError(f"新列名存在重复: {duplicate_values}")

        new_columns.update(mapping)

    if pattern is not None:
        try:
            for col in data.columns:
                if col in new_columns:
                    continue
                if use_regex:
                    new_col = re.sub(pattern, replacement, col)
                else:
                    new_col = col.replace(pattern, replacement)
                if new_col != col and new_col not in list(data.columns) + list(new_columns.values()):
                    new_columns[col] = new_col
        except re.error as e:
            raise ValueError(f"正则表达式错误: {e}")

    if not new_columns:
        return {
            "data": data.copy(),
            "renamed_columns": {},
            "message": "没有列被重命名",
        }

    result_df = data.rename(columns=new_columns)

    return {
        "data": result_df,
        "renamed_columns": new_columns,
        "renamed_count": len(new_columns),
    }
