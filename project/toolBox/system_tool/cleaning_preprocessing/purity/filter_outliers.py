from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np


def filter_outliers(
    data: pd.DataFrame,
    columns: Optional[List[str]] = None,
    method: str = "IQR",
    threshold: float = 1.5,
) -> Dict[str, Any]:
    """基于统计学方法识别并处理异常值。

    支持 IQR 四分位距和 3σ 原则两种方法。

    Args:
        data: 输入的 pandas DataFrame。
        columns: 需要检测的列名列表，默认为 None（全部数值列）。
        method: 检测方法，可选值:
            - 'IQR': 使用四分位距法（IQR * threshold）
            - '3sigma': 使用 3σ 原则（均值 ± threshold * 标准差）
        threshold: 阈值倍数，IQR 法默认为 1.5，3σ 法默认为 3.0。

    Returns:
        包含 'data'（处理后的 DataFrame，异常值替换为 NaN）、
        'outlier_report'（各列异常值统计）和 'total_outliers'（总异常值数）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当 method 无效或 columns 中列不存在时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1, 2, 3, 4, 100]})
        >>> result = filter_outliers(df, method='IQR')
        >>> result['total_outliers']
        1
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    valid_methods = ("IQR", "3sigma")
    if method not in valid_methods:
        raise ValueError(f"参数 method 必须为 {valid_methods} 之一，当前值: {method}")

    if columns is None:
        columns = data.select_dtypes(include=[np.number]).columns.tolist()
    else:
        invalid_cols = [c for c in columns if c not in data.columns]
        if invalid_cols:
            raise ValueError(f"以下列不存在于 DataFrame 中: {invalid_cols}")

    if not columns:
        return {
            "data": data.copy(),
            "outlier_report": {},
            "total_outliers": 0,
            "message": "没有可检测异常值的数值列",
        }

    result_df = data.copy()
    outlier_report: Dict[str, Dict[str, Any]] = {}
    total_outliers = 0

    for col in columns:
        col_data = result_df[col].dropna()
        if len(col_data) < 4:
            continue

        if method == "IQR":
            q1 = col_data.quantile(0.25)
            q3 = col_data.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr
        else:
            mean_val = col_data.mean()
            std_val = col_data.std()
            if std_val == 0:
                continue
            lower_bound = mean_val - threshold * std_val
            upper_bound = mean_val + threshold * std_val

        outlier_mask = (result_df[col] < lower_bound) | (result_df[col] > upper_bound)
        outlier_count = int(outlier_mask.sum())

        if outlier_count > 0:
            result_df.loc[outlier_mask, col] = np.nan
            outlier_report[col] = {
                "outlier_count": outlier_count,
                "outlier_pct": round(outlier_count / len(result_df) * 100, 2),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "method": method,
                "threshold": threshold,
            }
            total_outliers += outlier_count

    return {
        "data": result_df,
        "outlier_report": outlier_report,
        "total_outliers": total_outliers,
        "method": method,
        "threshold": threshold,
    }
