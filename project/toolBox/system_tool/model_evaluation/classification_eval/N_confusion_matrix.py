from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
import base64
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix as sk_confusion_matrix


def N_confusion_matrix(
    data: pd.DataFrame,
    y_true: str,
    y_pred: str,
    title: Optional[str] = None,
    figsize: tuple = (6, 5),
) -> Dict[str, Any]:
    """计算并绘制混淆矩阵。

    以矩阵形式交叉展示真实标签与预测标签的对应关系，量化各类别识别效果。

    Args:
        data: 输入的 pandas DataFrame，包含真实标签列和预测标签列。
        y_true: 真实标签列名。
        y_pred: 预测标签列名。
        title: 图表标题，默认为 None（自动生成）。
        figsize: 图表尺寸，默认为 (6, 5)。

    Returns:
        包含 'image_base64'（Base64 编码的 PNG 图像）、'matrix'（混淆矩阵数据）、
        'metrics'（各项分类指标）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当列不存在时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'true': [0,0,1,1], 'pred': [0,1,1,1]})
        >>> result = N_confusion_matrix(df, y_true='true', y_pred='pred')
        >>> 'matrix' in result
        True
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    for col, name in [(y_true, "y_true"), (y_pred, "y_pred")]:
        if col not in data.columns:
            raise ValueError(f"参数 {name} 指定的列 '{col}' 不存在于 DataFrame 中")

    valid_data = data[[y_true, y_pred]].dropna()
    if len(valid_data) == 0:
        raise ValueError("没有有效的标签数据")

    labels_true = valid_data[y_true]
    labels_pred = valid_data[y_pred]

    classes = sorted(set(labels_true) | set(labels_pred))
    cm = sk_confusion_matrix(labels_true, labels_pred, labels=classes)

    if title is None:
        title = "Confusion Matrix"

    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=[str(c) for c in classes],
        yticklabels=[str(c) for c in classes],
        ax=ax,
    )
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Predicted", fontsize=12)
    ax.set_ylabel("True", fontsize=12)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)

    tp = int(np.diag(cm).sum())
    total = int(cm.sum())
    overall_accuracy = tp / total if total > 0 else 0.0

    per_class_metrics = {}
    for i, cls in enumerate(classes):
        tp_i = int(cm[i, i])
        fp_i = int(cm[:, i].sum() - tp_i)
        fn_i = int(cm[i, :].sum() - tp_i)
        tn_i = int(total - tp_i - fp_i - fn_i)

        precision = tp_i / (tp_i + fp_i) if (tp_i + fp_i) > 0 else 0.0
        recall = tp_i / (tp_i + fn_i) if (tp_i + fn_i) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        per_class_metrics[str(cls)] = {
            "tp": tp_i,
            "fp": fp_i,
            "fn": fn_i,
            "tn": tn_i,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        }

    return {
        "image_base64": image_base64,
        "image_format": "png",
        "matrix": cm.tolist(),
        "classes": [str(c) for c in classes],
        "metrics": {
            "overall_accuracy": round(overall_accuracy, 4),
            "n_samples": total,
            "per_class": per_class_metrics,
        },
    }
