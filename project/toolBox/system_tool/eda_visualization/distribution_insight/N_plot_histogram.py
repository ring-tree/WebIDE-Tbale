from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


def N_plot_histogram(
    data: pd.DataFrame,
    column: str,
    bins: int = 20,
    title: Optional[str] = None,
    figsize: tuple = (8, 5),
) -> Dict[str, Any]:
    """绘制数值型变量的频数分布直方图。

    Args:
        data: 输入的 pandas DataFrame。
        column: 要绘制直方图的列名。
        bins: 分组数量，默认为 20。
        title: 图表标题，默认为 None（自动生成）。
        figsize: 图表尺寸，默认为 (8, 5)。

    Returns:
        包含 'figure'（matplotlib Figure 对象）、'statistics'（统计信息）的字典。
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if column not in data.columns:
        raise ValueError(f"列 '{column}' 不存在于 DataFrame 中")

    if not pd.api.types.is_numeric_dtype(data[column]):
        raise ValueError(f"列 '{column}' 不是数值型，无法绘制直方图")

    col_data = data[column].dropna()
    if len(col_data) < 2:
        raise ValueError(f"列 '{column}' 有效数据不足（至少需要 2 个非空值）")

    if title is None:
        title = f"Histogram of {column}"

    fig, ax = plt.subplots(figsize=figsize)
    ax.hist(col_data, bins=bins, edgecolor="black", alpha=0.7, color="steelblue")
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel(column, fontsize=12)
    ax.set_ylabel("Frequency", fontsize=12)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    return {
        "figure": fig,
        "statistics": {
            "count": int(len(col_data)),
            "mean": float(col_data.mean()),
            "std": float(col_data.std()),
            "min": float(col_data.min()),
            "max": float(col_data.max()),
            "bins": bins,
        },
    }
