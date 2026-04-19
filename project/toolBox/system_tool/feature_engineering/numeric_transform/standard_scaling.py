from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler


def standard_scaling(
    data: pd.DataFrame,
    columns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """执行 Z-Score 标准化。

    将特征转换为均值为 0、标准差为 1 的标准正态分布。

    Args:
        data: 输入的 pandas DataFrame。
        columns: 需要标准化的列名列表，默认为 None（全部数值列）。

    Returns:
        包含 'data'（标准化后的 DataFrame）、'scaled_columns'（被标准化的列名列表）和
        'scaler_params'（各列的均值和标准差参数）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当 columns 中的列不存在时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1, 2, 3], 'B': [10, 20, 30]})
        >>> result = standard_scaling(df)
        >>> abs(result['data']['A'].mean()) < 1e-10
        True
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if columns is None:
        columns = data.select_dtypes(include=[np.number]).columns.tolist()
    else:
        invalid_cols = [c for c in columns if c not in data.columns]
        if invalid_cols:
            raise ValueError(f"以下列不存在于 DataFrame 中: {invalid_cols}")

    if not columns:
        return {
            "data": data.copy(),
            "scaled_columns": [],
            "scaler_params": {},
            "message": "没有可标准化的数值列",
        }

    result_df = data.copy()
    scaler = StandardScaler()
    scaler_params: Dict[str, Dict[str, float]] = {}
    actual_scaled: List[str] = []

    for col in columns:
        if not pd.api.types.is_numeric_dtype(result_df[col]):
            continue
        col_data = result_df[[col]].dropna()
        if col_data.empty:
            continue
        actual_scaled.append(col)
        scaler_params[col] = {
            "mean": float(col_data[col].mean()),
            "std": float(col_data[col].std()),
        }

    if actual_scaled:
        scaler.fit(result_df[actual_scaled].dropna())
        scaled_values = scaler.transform(result_df[actual_scaled].dropna())
        result_df.loc[result_df[actual_scaled].dropna().index, actual_scaled] = scaled_values

    return {
        "data": result_df,
        "scaled_columns": actual_scaled,
        "scaler_params": scaler_params,
        "scaled_count": len(actual_scaled),
    }
