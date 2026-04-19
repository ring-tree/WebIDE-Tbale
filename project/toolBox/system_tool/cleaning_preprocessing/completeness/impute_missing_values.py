from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np


def impute_missing_values(
    data: pd.DataFrame,
    strategy: str = "mean",
    fill_value: Optional[float] = None,
    columns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """智能填补缺失值。

    支持均值、中位数、众数、固定值等多种策略，对指定列或全部数值列进行填充。

    Args:
        data: 输入的 pandas DataFrame。
        strategy: 填充策略，可选值:
            - 'mean': 均值填充（仅适用于数值列）
            - 'median': 中位数填充（仅适用于数值列）
            - 'most_frequent': 众数填充
            - 'constant': 固定值填充（需指定 fill_value）
        fill_value: 当 strategy='constant' 时使用的固定值，默认为 0。
        columns: 需要填充的列名列表，默认为 None（全部数值列）。

    Returns:
        包含 'data'（填充后的 DataFrame）、'filled_columns'（被填充的列及填充值）和
        'total_filled'（总填充单元格数）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当 strategy 无效或 fill_value 未指定时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1, None, 3], 'B': [4, 5, None]})
        >>> result = impute_missing_values(df, strategy='mean')
        >>> result['data']['A'].isnull().sum()
        0
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    valid_strategies = ("mean", "median", "most_frequent", "constant")
    if strategy not in valid_strategies:
        raise ValueError(f"参数 strategy 必须为 {valid_strategies} 之一，当前值: {strategy}")

    if strategy == "constant" and fill_value is None:
        fill_value = 0

    if columns is None:
        columns = data.select_dtypes(include=[np.number]).columns.tolist()

    if not columns:
        return {
            "data": data.copy(),
            "filled_columns": {},
            "total_filled": 0,
            "message": "没有需要填充的列",
        }

    invalid_cols = [c for c in columns if c not in data.columns]
    if invalid_cols:
        raise ValueError(f"以下列不存在于 DataFrame 中: {invalid_cols}")

    result_df = data.copy()
    filled_columns: Dict[str, Any] = {}
    total_filled = 0

    for col in columns:
        missing_count = result_df[col].isnull().sum()
        if missing_count == 0:
            continue

        if strategy == "mean":
            if not pd.api.types.is_numeric_dtype(result_df[col]):
                continue
            fill_val = result_df[col].mean()
        elif strategy == "median":
            if not pd.api.types.is_numeric_dtype(result_df[col]):
                continue
            fill_val = result_df[col].median()
        elif strategy == "most_frequent":
            fill_val = result_df[col].mode().iloc[0] if not result_df[col].mode().empty else None
        else:
            fill_val = fill_value

        if fill_val is not None:
            result_df[col] = result_df[col].fillna(fill_val)
            filled_columns[col] = {
                "fill_value": fill_val,
                "filled_count": int(missing_count),
            }
            total_filled += int(missing_count)

    return {
        "data": result_df,
        "filled_columns": filled_columns,
        "total_filled": total_filled,
    }
