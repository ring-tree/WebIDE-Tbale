from typing import Any, Dict
import pandas as pd


def N_data_shape(data: pd.DataFrame) -> Dict[str, Any]:
    """获取数据集的维度信息。

    返回数据集的行数（样本数）和列数（特征数）。

    Args:
        data: 输入的 pandas DataFrame。

    Returns:
        包含 'rows'（行数）、'columns'（列数）和 'shape'（元组）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当 data 为空（0行或0列）时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1, 2, 3], 'B': ['x', 'y', 'z']})
        >>> N_data_shape(df)
        {'rows': 3, 'columns': 2, 'shape': (3, 2)}
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if data.empty:
        raise ValueError("DataFrame 为空（0行或0列），无法获取维度信息")

    n_rows, n_cols = data.shape
    return {
        "rows": int(n_rows),
        "columns": int(n_cols),
        "shape": (int(n_rows), int(n_cols)),
    }
