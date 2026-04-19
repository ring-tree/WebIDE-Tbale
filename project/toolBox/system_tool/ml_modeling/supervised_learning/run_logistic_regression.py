from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report


def run_logistic_regression(
    data: pd.DataFrame,
    target_column: str,
    feature_columns: Optional[List[str]] = None,
    multi_class: str = "auto",
    test_size: float = 0.2,
    random_state: int = 42,
    max_iter: int = 1000,
) -> Dict[str, Any]:
    """构建逻辑回归分类模型。

    计算各类别的发生概率与分类边界，支持二分类与多分类任务。

    Args:
        data: 输入的 pandas DataFrame。
        target_column: 目标变量列名（分类标签）。
        feature_columns: 特征变量列名列表，默认为 None（全部数值列除目标列）。
        multi_class: 分类类型，可选值:
            - 'auto': 自动检测
            - 'binary': 二分类
            - 'multinomial': 多分类
        test_size: 测试集比例，默认为 0.2。
        random_state: 随机种子，默认为 42。
        max_iter: 最大迭代次数，默认为 1000。

    Returns:
        包含 'coefficients'（回归系数）、'classes'（类别列表）、
        'metrics'（模型评估指标）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当参数无效或数据不满足要求时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1,2,3,4,5], 'B': [2,3,4,5,6], 'target': [0,0,1,1,1]})
        >>> result = run_logistic_regression(df, target_column='target')
        >>> 'classes' in result
        True
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if target_column not in data.columns:
        raise ValueError(f"目标变量列 '{target_column}' 不存在")

    if feature_columns is None:
        feature_columns = data.select_dtypes(include=[np.number]).columns.drop(target_column, errors="ignore").tolist()
    else:
        invalid_cols = [c for c in feature_columns if c not in data.columns]
        if invalid_cols:
            raise ValueError(f"以下特征列不存在: {invalid_cols}")

    if not feature_columns:
        raise ValueError("没有可用的特征列")

    valid_data = data[feature_columns + [target_column]].dropna()
    if len(valid_data) < 5:
        raise ValueError("样本数不足，无法训练逻辑回归模型")

    X = valid_data[feature_columns]
    y = valid_data[target_column]

    n_classes = y.nunique()
    if multi_class == "binary" and n_classes != 2:
        raise ValueError(f"指定二分类模式，但目标变量有 {n_classes} 个类别")

    solver = "lbfgs"
    if multi_class == "multinomial" or n_classes > 2:
        multi_class_val = "multinomial"
    else:
        multi_class_val = "auto"

    n_samples = len(X)
    n_test = max(1, int(n_samples * test_size))
    n_train = n_samples - n_test

    X_train = X.iloc[:n_train]
    X_test = X.iloc[n_train:]
    y_train = y.iloc[:n_train]
    y_test = y.iloc[n_train:]

    model = LogisticRegression(
        multi_class=multi_class_val,
        solver=solver,
        max_iter=max_iter,
        random_state=random_state,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    coef_shape = model.coef_.shape
    coefficients = {}
    if len(feature_columns) == 1:
        coefficients = {feature_columns[0]: float(model.coef_[0][0])}
    else:
        for i, feat in enumerate(feature_columns):
            if coef_shape[0] == 1:
                coefficients[feat] = float(model.coef_[0][i])
            else:
                coefficients[feat] = [float(c) for c in model.coef_[:, i]]

    metrics = {}
    if len(y_test) > 0:
        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "n_train": n_train,
            "n_test": len(y_test),
            "classification_report": classification_report(y_test, y_pred, output_dict=True, zero_division=0),
        }

    y_train_pred = model.predict(X_train)
    metrics["train_accuracy"] = float(accuracy_score(y_train, y_train_pred))

    return {
        "model_type": "LogisticRegression",
        "coefficients": coefficients,
        "intercept": model.intercept_.tolist() if len(model.intercept_) > 1 else float(model.intercept_[0]),
        "classes": [str(c) for c in model.classes_],
        "n_classes": n_classes,
        "metrics": metrics,
        "feature_columns": feature_columns,
        "target_column": target_column,
    }
