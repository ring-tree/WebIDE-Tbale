from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.metrics import accuracy_score, mean_squared_error, r2_score


def run_decision_tree(
    data: pd.DataFrame,
    target_column: str,
    feature_columns: Optional[List[str]] = None,
    max_depth: int = 10,
    task_type: str = "classification",
    test_size: float = 0.2,
    random_state: int = 42,
) -> Dict[str, Any]:
    """训练决策树模型。

    生成可解释的树状分类/回归模型，以 if-then 规则序列呈现决策路径。

    Args:
        data: 输入的 pandas DataFrame。
        target_column: 目标变量列名。
        feature_columns: 特征变量列名列表，默认为 None（全部数值列除目标列）。
        max_depth: 树的最大深度，默认为 10。
        task_type: 任务类型，可选值:
            - 'classification': 分类任务
            - 'regression': 回归任务
        test_size: 测试集比例，默认为 0.2。
        random_state: 随机种子，默认为 42。

    Returns:
        包含 'feature_importances'（特征重要性）、'metrics'（模型评估指标）、
        'tree_params'（树结构参数）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当参数无效时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1,2,3,4,5], 'target': [0,0,1,1,1]})
        >>> result = run_decision_tree(df, target_column='target')
        >>> 'feature_importances' in result
        True
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if target_column not in data.columns:
        raise ValueError(f"目标变量列 '{target_column}' 不存在")

    valid_task_types = ("classification", "regression")
    if task_type not in valid_task_types:
        raise ValueError(f"参数 task_type 必须为 {valid_task_types} 之一，当前值: {task_type}")

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
        raise ValueError("样本数不足，无法训练决策树模型")

    X = valid_data[feature_columns]
    y = valid_data[target_column]

    n_samples = len(X)
    n_test = max(1, int(n_samples * test_size))
    n_train = n_samples - n_test

    X_train = X.iloc[:n_train]
    X_test = X.iloc[n_train:]
    y_train = y.iloc[:n_train]
    y_test = y.iloc[n_train:]

    if task_type == "classification":
        model = DecisionTreeClassifier(max_depth=max_depth, random_state=random_state)
    else:
        model = DecisionTreeRegressor(max_depth=max_depth, random_state=random_state)

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    feature_importances = {feat: float(imp) for feat, imp in zip(feature_columns, model.feature_importances_)}

    metrics: Dict[str, Any] = {}
    if len(y_test) > 0:
        if task_type == "classification":
            metrics = {
                "accuracy": float(accuracy_score(y_test, y_pred)),
                "n_train": n_train,
                "n_test": len(y_test),
            }
            y_train_pred = model.predict(X_train)
            metrics["train_accuracy"] = float(accuracy_score(y_train, y_train_pred))
        else:
            metrics = {
                "mse": float(mean_squared_error(y_test, y_pred)),
                "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
                "r2": float(r2_score(y_test, y_pred)),
                "n_train": n_train,
                "n_test": len(y_test),
            }
            y_train_pred = model.predict(X_train)
            metrics["train_r2"] = float(r2_score(y_train, y_train_pred))

    return {
        "model_type": "DecisionTree",
        "task_type": task_type,
        "feature_importances": feature_importances,
        "metrics": metrics,
        "tree_params": {
            "max_depth": max_depth,
            "actual_depth": int(model.get_depth()),
            "n_leaves": int(model.get_n_leaves()),
        },
        "feature_columns": feature_columns,
        "target_column": target_column,
    }
