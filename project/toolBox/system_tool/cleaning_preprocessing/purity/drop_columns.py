from typing import Any, Dict, List, Optional
import pandas as pd


def drop_columns(
    data: pd.DataFrame,
    columns: List[str],
) -> Dict[str, Any]:
    """选择性删除指定的列。

    从 DataFrame 中移除指定的列，返回剩余列的数据。

    Args:
        data: 输入的 pandas DataFrame。
        columns: 要删除的列名列表。

    Returns:
        包含 'data'（删除列后的 DataFrame）、'dropped_columns'（被删除的列名列表）和
        'remaining_columns'（剩余列名列表）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当 columns 为空或包含不存在的列时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1, 2], 'B': [3, 4], 'C': [5, 6]})
        >>> result = drop_columns(df, columns=['A'])
        >>> list(result['data'].columns)
        ['B', 'C']
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if not columns:
        raise ValueError("参数 columns 不能为空，必须指定至少一列")

    if not isinstance(columns, list):
        raise TypeError(f"参数 columns 必须为列表，实际类型: {type(columns).__name__}")

    invalid_cols = [c for c in columns if c not in data.columns]
    if invalid_cols:
        raise ValueError(f"以下列不存在于 DataFrame 中: {invalid_cols}")

    result_df = data.drop(columns=columns)

    return {
        "data": result_df,
        "dropped_columns": list(columns),
        "dropped_count": len(columns),
        "remaining_columns": list(result_df.columns),
        "remaining_count": len(result_df.columns),
    }
