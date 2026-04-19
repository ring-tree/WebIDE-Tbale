from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def N_plot_boxplot(
    data: pd.DataFrame,
    column: str,
    title: Optional[str] = None,
    figsize: tuple = (8, 5),
) -> Dict[str, Any]:
    """绘制单变量箱线图。

    Args:
        data: 输入的 pandas DataFrame。
        column: 要绘制箱线图的列名。
        title: 图表标题，默认为 None（自动生成）。
        figsize: 图表尺寸，默认为 (8, 5)。

    Returns:
        包含 'figure'（matplotlib Figure 对象）、'statistics'（五数概括）的字典。
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if column not in data.columns:
        raise ValueError(f"列 '{column}' 不存在于 DataFrame 中")

    if not pd.api.types.is_numeric_dtype(data[column]):
        raise ValueError(f"列 '{column}' 不是数值型，无法绘制箱线图")

    col_data = data[column].dropna()
    if len(col_data) < 4:
        raise ValueError(f"列 '{column}' 有效数据不足（至少需要 4 个非空值）")

    if title is None:
        title = f"Boxplot of {column}"

    fig, ax = plt.subplots(figsize=figsize)
    bp = ax.boxplot(col_data, vert=True, patch_artist=True, widths=0.5)
    for patch in bp["boxes"]:
        patch.set_facecolor("steelblue")
        patch.set_alpha(0.7)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel(column, fontsize=12)
    ax.set_xticks([1])
    ax.set_xticklabels([column])
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    q1 = float(col_data.quantile(0.25))
    median = float(col_data.quantile(0.5))
    q3 = float(col_data.quantile(0.75))
    iqr = q3 - q1
    lower_whisker = float(col_data[col_data >= (q1 - 1.5 * iqr)].min())
    upper_whisker = float(col_data[col_data <= (q3 + 1.5 * iqr)].max())
    outliers = col_data[(col_data < (q1 - 1.5 * iqr)) | (col_data > (q3 + 1.5 * iqr))]

    return {
        "figure": fig,
        "statistics": {
            "min": float(col_data.min()),
            "q1": q1,
            "median": median,
            "q3": q3,
            "max": float(col_data.max()),
            "iqr": iqr,
            "lower_whisker": lower_whisker,
            "upper_whisker": upper_whisker,
            "outlier_count": len(outliers),
            "outliers": outliers.tolist() if len(outliers) <= 20 else list(outliers.head(20)),
        },
    }
