from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif, f_regression, mutual_info_regression


def feature_selection_kbest(
    data: pd.DataFrame,
    k: int = 5,
    score_func: str = "f_classif",
    target_column: Optional[str] = None,
    feature_columns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """基于统计检验筛选 Top-K 最优特征。

    根据评分函数度量特征与目标变量的相关性，选择最具预测能力的特征子集。

    Args:
        data: 输入的 pandas DataFrame。
        k: 要选择的特征数量。
        score_func: 评分函数，可选值:
            - 'f_classif': 方差分析 F 值（分类任务）
            - 'mutual_info_classif': 互信息（分类任务）
            - 'f_regression': F 回归值（回归任务）
            - 'mutual_info_regression': 互信息回归（回归任务）
        target_column: 目标变量列名。
        feature_columns: 候选特征列名列表，默认为 None（全部数值列除目标列）。

    Returns:
        包含 'selected_features'（选中的特征名列表）、'scores'（各特征得分）、
        'data'（仅含选中特征的 DataFrame）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当参数无效或数据不满足要求时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1, 2, 3, 4, 5], 'B': [5, 4, 3, 2, 1], 'target': [0, 0, 1, 1, 1]})
        >>> result = feature_selection_kbest(df, k=1, target_column='target')
        >>> len(result['selected_features'])
        1
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    valid_score_funcs = ("f_classif", "mutual_info_classif", "f_regression", "mutual_info_regression")
    if score_func not in valid_score_funcs:
        raise ValueError(f"参数 score_func 必须为 {valid_score_funcs} 之一，当前值: {score_func}")

    if target_column is None:
        raise ValueError("必须指定 target_column 参数")

    if target_column not in data.columns:
        raise ValueError(f"目标变量列 '{target_column}' 不存在于 DataFrame 中")

    if feature_columns is None:
        feature_columns = data.select_dtypes(include=[np.number]).columns.drop(target_column, errors="ignore").tolist()
    else:
        invalid_cols = [c for c in feature_columns if c not in data.columns]
        if invalid_cols:
            raise ValueError(f"以下特征列不存在: {invalid_cols}")
        if target_column in feature_columns:
            feature_columns = [c for c in feature_columns if c != target_column]

    if not feature_columns:
        return {
            "selected_features": [],
            "scores": {},
            "data": pd.DataFrame(),
            "message": "没有可用的特征列",
        }

    k = min(k, len(feature_columns))
    if k <= 0:
        raise ValueError(f"参数 k 必须为正整数，当前值: {k}")

    X = data[feature_columns].dropna()
    y = data.loc[X.index, target_column].dropna()
    common_idx = X.index.intersection(y.index)
    X = X.loc[common_idx]
    y = y.loc[common_idx]

    if len(common_idx) < 2:
        raise ValueError("有效样本数不足，无法进行特征选择")

    if "classif" in score_func:
        func = f_classif if score_func == "f_classif" else mutual_info_classif
    else:
        func = f_regression if score_func == "f_regression" else mutual_info_regression

    try:
        selector = SelectKBest(score_func=func, k=k)
        selector.fit(X, y)
        scores = dict(zip(feature_columns, selector.scores_))
        selected_mask = selector.get_support()
        selected_features = [col for col, is_selected in zip(feature_columns, selected_mask) if is_selected]
    except ValueError as e:
        raise ValueError(f"特征选择失败: {e}")

    return {
        "selected_features": selected_features,
        "scores": {k: float(v) for k, v in scores.items()},
        "data": data[selected_features].copy(),
        "k": k,
        "score_func": score_func,
        "n_features_in": len(feature_columns),
        "n_features_out": len(selected_features),
    }
