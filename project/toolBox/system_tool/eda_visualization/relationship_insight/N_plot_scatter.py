from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def N_plot_scatter(
    data: pd.DataFrame,
    x_column: str,
    y_column: str,
    title: Optional[str] = None,
    figsize: tuple = (8, 5),
) -> Dict[str, Any]:
    """绘制二元变量分布散点图。

    Args:
        data: 输入的 pandas DataFrame。
        x_column: X 轴列名。
        y_column: Y 轴列名。
        title: 图表标题，默认为 None（自动生成）。
        figsize: 图表尺寸，默认为 (8, 5)。

    Returns:
        包含 'figure'（matplotlib Figure 对象）、'statistics'（相关性统计）的字典。
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    for col, name in [(x_column, "x_column"), (y_column, "y_column")]:
        if col not in data.columns:
            raise ValueError(f"参数 {name} 指定的列 '{col}' 不存在于 DataFrame 中")
        if not pd.api.types.is_numeric_dtype(data[col]):
            raise ValueError(f"参数 {name} 指定的列 '{col}' 不是数值型")

    valid_data = data[[x_column, y_column]].dropna()
    if len(valid_data) < 3:
        raise ValueError("有效数据点不足（至少需要 3 对非空值）")

    if title is None:
        title = f"Scatter Plot: {x_column} vs {y_column}"

    fig, ax = plt.subplots(figsize=figsize)
    ax.scatter(valid_data[x_column], valid_data[y_column], alpha=0.6, edgecolors="w", linewidth=0.5, color="steelblue")
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel(x_column, fontsize=12)
    ax.set_ylabel(y_column, fontsize=12)
    ax.grid(alpha=0.3)
    plt.tight_layout()

    corr = valid_data[x_column].corr(valid_data[y_column])

    return {
        "figure": fig,
        "statistics": {
            "n_points": len(valid_data),
            "pearson_corr": float(corr),
            "x_mean": float(valid_data[x_column].mean()),
            "y_mean": float(valid_data[y_column].mean()),
            "x_std": float(valid_data[x_column].std()),
            "y_std": float(valid_data[y_column].std()),
        },
    }
