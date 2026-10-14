from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score


def run_linear_regression(
    data: pd.DataFrame,
    target_column: str,
    feature_columns: Optional[List[str]] = None,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Dict[str, Any]:
    """拟合线性回归模型。

    寻找特征与连续目标变量之间的最佳线性关系，输出回归系数与模型评估指标。

    Args:
        data: 输入的 pandas DataFrame。
        target_column: 目标变量列名（必须为数值型）。
        feature_columns: 特征变量列名列表，默认为 None（全部数值列除目标列）。
        test_size: 测试集比例，默认为 0.2。
        random_state: 随机种子，默认为 42。

    Returns:
        包含 'coefficients'（回归系数）、'intercept'（截距）、
        'metrics'（模型评估指标）和 'model'（训练好的模型）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当参数无效或数据不满足要求时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1,2,3,4,5], 'B': [2,4,6,8,10], 'target': [3,6,9,12,15]})
        >>> result = run_linear_regression(df, target_column='target')
        >>> 'coefficients' in result
        True
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if target_column not in data.columns:
        raise ValueError(f"目标变量列 '{target_column}' 不存在")

    if not pd.api.types.is_numeric_dtype(data[target_column]):
        raise ValueError(f"目标变量列 '{target_column}' 必须为数值型")

    if feature_columns is None:
        feature_columns = data.select_dtypes(include=[np.number]).columns.drop(target_column, errors="ignore").tolist()
    else:
        invalid_cols = [c for c in feature_columns if c not in data.columns]
        if invalid_cols:
            raise ValueError(f"以下特征列不存在: {invalid_cols}")

    if not feature_columns:
        raise ValueError("没有可用的特征列")

    valid_data = data[feature_columns + [target_column]].dropna()
    if len(valid_data) < len(feature_columns) + 2:
        raise ValueError("样本数不足，无法训练线性回归模型")

    X = valid_data[feature_columns]
    y = valid_data[target_column]

    n_samples = len(X)
    n_test = max(1, int(n_samples * test_size))
    n_train = n_samples - n_test

    X_train = X.iloc[:n_train]
    X_test = X.iloc[n_train:]
    y_train = y.iloc[:n_train]
    y_test = y.iloc[n_train:]

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    coefficients = {feat: float(coef) for feat, coef in zip(feature_columns, model.coef_)}

    metrics = {}
    if len(y_test) > 0:
        metrics = {
            "mse": float(mean_squared_error(y_test, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
            "r2": float(r2_score(y_test, y_pred)),
            "mae": float(np.mean(np.abs(y_test - y_pred))),
            "n_train": n_train,
            "n_test": len(y_test),
        }

    y_train_pred = model.predict(X_train)
    metrics["train_r2"] = float(r2_score(y_train, y_train_pred))

    return {
        "model_type": "LinearRegression",
        "coefficients": coefficients,
        "intercept": float(model.intercept_),
        "metrics": metrics,
        "feature_columns": feature_columns,
        "target_column": target_column,
    }
