from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error, mean_absolute_percentage_error


def N_mse_r2_score(
    data: pd.DataFrame,
    y_true: str,
    y_pred: str,
) -> Dict[str, Any]:
    """计算回归评估指标。

    计算 MSE/RMSE/MAE/R² 等回归评估指标，全面衡量模型拟合优度与预测精度。

    Args:
        data: 输入的 pandas DataFrame，包含真实值列和预测值列。
        y_true: 真实值列名。
        y_pred: 预测值列名。

    Returns:
        包含 'metrics'（各项回归指标）、'residuals'（残差统计）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当列不存在或不是数值型时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'true': [1,2,3,4,5], 'pred': [1.1,2.2,2.8,4.1,5.2]})
        >>> result = N_mse_r2_score(df, y_true='true', y_pred='pred')
        >>> 'r2' in result['metrics']
        True
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    for col, name in [(y_true, "y_true"), (y_pred, "y_pred")]:
        if col not in data.columns:
            raise ValueError(f"参数 {name} 指定的列 '{col}' 不存在于 DataFrame 中")
        if not pd.api.types.is_numeric_dtype(data[col]):
            raise ValueError(f"参数 {name} 指定的列 '{col}' 必须为数值型")

    valid_data = data[[y_true, y_pred]].dropna()
    if len(valid_data) < 2:
        raise ValueError("至少需要 2 对有效的真实值与预测值")

    true_values = valid_data[y_true]
    pred_values = valid_data[y_pred]

    residuals = true_values - pred_values

    try:
        mse = float(mean_squared_error(true_values, pred_values))
    except ValueError:
        mse = float("nan")

    try:
        rmse = float(np.sqrt(mse))
    except ValueError:
        rmse = float("nan")

    try:
        r2 = float(r2_score(true_values, pred_values))
    except ValueError:
        r2 = float("nan")

    try:
        mae = float(mean_absolute_error(true_values, pred_values))
    except ValueError:
        mae = float("nan")

    try:
        if (true_values != 0).all():
            mape = float(mean_absolute_percentage_error(true_values, pred_values))
        else:
            mape = float("nan")
    except (ValueError, ZeroDivisionError):
        mape = float("nan")

    try:
        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((true_values - true_values.mean()) ** 2))
        adjusted_r2 = float(1 - (1 - r2) * (len(true_values) - 1) / (len(true_values) - 2)) if len(true_values) > 2 else float("nan")
    except (ValueError, ZeroDivisionError):
        ss_res = float("nan")
        ss_tot = float("nan")
        adjusted_r2 = float("nan")

    return {
        "metrics": {
            "mse": round(mse, 6),
            "rmse": round(rmse, 6),
            "r2": round(r2, 6),
            "mae": round(mae, 6),
            "mape": round(mape, 6) if not np.isnan(mape) else None,
            "adjusted_r2": round(adjusted_r2, 6) if not np.isnan(adjusted_r2) else None,
        },
        "residuals": {
            "mean": float(residuals.mean()),
            "std": float(residuals.std()),
            "min": float(residuals.min()),
            "max": float(residuals.max()),
            "median": float(residuals.median()),
        },
        "n_samples": len(valid_data),
    }
