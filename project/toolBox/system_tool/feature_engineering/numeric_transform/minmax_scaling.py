from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler


def minmax_scaling(
    data: pd.DataFrame,
    columns: Optional[List[str]] = None,
    feature_range_min: float = 0,
    feature_range_max: float = 1,
) -> Dict[str, Any]:
    """执行 Min-Max 归一化。

    将数值线性缩放到指定区间，默认为 [0, 1] 闭区间。

    Args:
        data: 输入的 pandas DataFrame。
        columns: 需要归一化的列名列表，默认为 None（全部数值列）。
        feature_range_min: 缩放后的最小值，默认为 0。
        feature_range_max: 缩放后的最大值，默认为 1。

    Returns:
        包含 'data'（归一化后的 DataFrame）、'scaled_columns'（被归一化的列名列表）和
        'scaler_params'（各列的原始最小值和最大值参数）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当 feature_range_min >= feature_range_max 或列不存在时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1, 2, 3]})
        >>> result = minmax_scaling(df)
        >>> result['data']['A'].tolist()
        [0.0, 0.5, 1.0]
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if feature_range_min >= feature_range_max:
        raise ValueError(
            f"feature_range_min ({feature_range_min}) 必须小于 feature_range_max ({feature_range_max})"
        )

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
            "message": "没有可归一化的数值列",
        }

    result_df = data.copy()
    scaler_params: Dict[str, Dict[str, float]] = {}
    actual_scaled: List[str] = []

    for col in columns:
        if not pd.api.types.is_numeric_dtype(result_df[col]):
            continue
        col_data = result_df[col].dropna()
        if col_data.empty or col_data.nunique() <= 1:
            continue
        actual_scaled.append(col)
        scaler_params[col] = {
            "original_min": float(col_data.min()),
            "original_max": float(col_data.max()),
        }

    if actual_scaled:
        scaler = MinMaxScaler(feature_range=(feature_range_min, feature_range_max))
        valid_idx = result_df[actual_scaled].dropna().index
        scaled_values = scaler.fit_transform(result_df.loc[valid_idx, actual_scaled])
        result_df.loc[valid_idx, actual_scaled] = scaled_values

    return {
        "data": result_df,
        "scaled_columns": actual_scaled,
        "scaler_params": scaler_params,
        "feature_range": (feature_range_min, feature_range_max),
        "scaled_count": len(actual_scaled),
    }
