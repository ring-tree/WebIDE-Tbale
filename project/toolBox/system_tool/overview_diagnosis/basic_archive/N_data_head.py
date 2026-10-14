from typing import Any, Dict
import pandas as pd


def N_data_head(data: pd.DataFrame, n: int = 5) -> Dict[str, Any]:
    """随机抽取数据首部记录。

    返回 DataFrame 的前 n 行数据，用于快速了解数据样态。

    Args:
        data: 输入的 pandas DataFrame。
        n: 要抽取的行数，默认为 5。必须为正整数。

    Returns:
        包含 'data'（DataFrame 前 n 行转为字典列表）和 'actual_rows'（实际返回行数）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当 n 不是正整数或大于数据总行数时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1, 2, 3, 4, 5], 'B': ['a', 'b', 'c', 'd', 'e']})
        >>> result = N_data_head(df, n=2)
        >>> result['actual_rows']
        2
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if not isinstance(n, int) or n <= 0:
        raise ValueError(f"参数 n 必须为正整数，当前值: {n}")

    if data.empty:
        raise ValueError("DataFrame 为空，无法预览数据")

    n = min(n, len(data))
    head_data = data.head(n)

    return {
        "data": head_data.to_dict(orient="records"),
        "columns": list(head_data.columns),
        "dtypes": {col: str(dtype) for col, dtype in head_data.dtypes.items()},
        "actual_rows": int(n),
    }
