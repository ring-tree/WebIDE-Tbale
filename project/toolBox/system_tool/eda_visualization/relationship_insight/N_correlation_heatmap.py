from typing import Any, Dict, Optional, List
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns


def N_correlation_heatmap(
    data: pd.DataFrame,
    method: str = "pearson",
    columns: Optional[List[str]] = None,
    title: Optional[str] = None,
    figsize: tuple = (8, 6),
) -> Dict[str, Any]:
    """计算并绘制相关系数矩阵热力图。

    Args:
        data: 输入的 pandas DataFrame。
        method: 相关系数计算方法 ('pearson', 'spearman', 'kendall')。
        columns: 要计算相关的列名列表，默认为 None（全部数值列）。
        title: 图表标题，默认为 None（自动生成）。
        figsize: 图表尺寸，默认为 (8, 6)。

    Returns:
        包含 'figure'（matplotlib Figure 对象）、'correlation_matrix'（相关系数矩阵）的字典。
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    valid_methods = ("pearson", "spearman", "kendall")
    if method not in valid_methods:
        raise ValueError(f"参数 method 必须为 {valid_methods} 之一，当前值: {method}")

    if columns is not None:
        invalid_cols = [c for c in columns if c not in data.columns]
        if invalid_cols:
            raise ValueError(f"以下列不存在: {invalid_cols}")
        numeric_data = data[columns].select_dtypes(include=[np.number]).dropna()
    else:
        numeric_data = data.select_dtypes(include=[np.number]).dropna()

    if numeric_data.shape[1] < 2:
        raise ValueError("至少需要 2 个数值列才能计算相关性")

    if numeric_data.shape[0] < 3:
        raise ValueError("有效样本数不足，无法计算相关性")

    corr_matrix = numeric_data.corr(method=method)

    if title is None:
        title = f"Correlation Heatmap ({method.capitalize()})"

    fig, ax = plt.subplots(figsize=figsize)
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    sns.heatmap(
        corr_matrix,
        mask=mask,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        center=0,
        square=True,
        linewidths=0.5,
        cbar_kws={"shrink": 0.8},
        ax=ax,
    )
    ax.set_title(title, fontsize=14, fontweight="bold")
    plt.tight_layout()

    return {
        "figure": fig,
        "correlation_matrix": corr_matrix.to_dict(),
        "method": method,
        "n_variables": corr_matrix.shape[0],
        "n_observations": numeric_data.shape[0],
    }
