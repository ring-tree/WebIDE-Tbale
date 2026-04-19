from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np


def N_reliability_analysis(
    data: pd.DataFrame,
    columns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """计算 Cronbach's alpha 信度系数。

    用于评估量表题项间的内部一致性信度水平。Alpha > 0.7 通常认为信度可接受。

    Args:
        data: 输入的 pandas DataFrame。
        columns: 量表题项列名列表，默认为 None（全部数值列）。

    Returns:
        包含 'cronbach_alpha'（信度系数）、'item_statistics'（各题项统计）、
        'interpretation'（信度等级解释）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当数据不足以计算 alpha 系数时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'Q1': [1,2,3,4,5], 'Q2': [1,2,3,4,5], 'Q3': [2,3,4,5,4]})
        >>> result = N_reliability_analysis(df)
        >>> result['cronbach_alpha'] > 0
        True
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if columns is None:
        columns = data.select_dtypes(include=[np.number]).columns.tolist()
    else:
        invalid_cols = [c for c in columns if c not in data.columns]
        if invalid_cols:
            raise ValueError(f"以下列不存在: {invalid_cols}")

    if len(columns) < 2:
        raise ValueError("至少需要 2 个题项才能计算 Cronbach's alpha")

    items_data = data[columns].dropna()
    if items_data.empty or len(items_data) < 3:
        raise ValueError("有效样本数不足，无法计算信度")

    n_items = len(columns)
    item_variances = items_data[columns].var()
    total_scores = items_data[columns].sum(axis=1)
    total_variance = total_scores.var()

    if total_variance == 0:
        return {
            "cronbach_alpha": 0.0,
            "interpretation": "不可用（无变异）",
            "item_statistics": {},
            "n_items": n_items,
            "n_observations": len(items_data),
        }

    alpha = (n_items / (n_items - 1)) * (1 - item_variances.sum() / total_variance)
    alpha = float(alpha)

    item_stats: Dict[str, Dict[str, float]] = {}
    for col in columns:
        item_stats[col] = {
            "mean": float(items_data[col].mean()),
            "std": float(items_data[col].std()),
            "variance": float(items_data[col].var()),
            "correlation_with_total": float(items_data[col].corr(total_scores)),
        }

    if alpha >= 0.9:
        interpretation = "优秀 (Excellent)"
    elif alpha >= 0.8:
        interpretation = "良好 (Good)"
    elif alpha >= 0.7:
        interpretation = "可接受 (Acceptable)"
    elif alpha >= 0.6:
        interpretation = "勉强可接受 (Questionable)"
    elif alpha >= 0.5:
        interpretation = "不可接受 (Poor)"
    else:
        interpretation = "不可用 (Unacceptable)"

    return {
        "cronbach_alpha": alpha,
        "interpretation": interpretation,
        "item_statistics": item_stats,
        "n_items": n_items,
        "n_observations": len(items_data),
    }
