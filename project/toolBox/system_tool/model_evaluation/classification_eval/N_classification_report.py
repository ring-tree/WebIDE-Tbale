from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
from sklearn.metrics import classification_report, precision_score, recall_score, f1_score, accuracy_score


def N_classification_report(
    data: pd.DataFrame,
    y_true: str,
    y_pred: str,
    average: str = "weighted",
) -> Dict[str, Any]:
    """生成分类评估报告。

    输出 Precision/Recall/F1-Score 等分类指标，提供 Macro/Micro/Weighted 多维度视角。

    Args:
        data: 输入的 pandas DataFrame，包含真实标签列和预测标签列。
        y_true: 真实标签列名。
        y_pred: 预测标签列名。
        average: 平均方式，用于多分类时的指标聚合，可选值:
            - 'weighted': 加权平均（默认）
            - 'macro': 简单平均
            - 'micro': 全局统计
            - 'binary': 二分类

    Returns:
        包含 'report'（完整分类报告字典）、'metrics'（聚合指标）、
        'class_metrics'（每个类别的详细指标）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当列不存在或数据无效时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'true': [0,0,1,1], 'pred': [0,1,1,1]})
        >>> result = N_classification_report(df, y_true='true', y_pred='pred')
        >>> 'accuracy' in result['metrics']
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

    unique_labels = sorted(set(labels_true) | set(labels_pred))
    n_classes = len(unique_labels)

    if n_classes < 2:
        raise ValueError("至少需要 2 个不同的类别标签")

    if n_classes == 2:
        avg_method = "binary"
    else:
        avg_method = average

    report_text = classification_report(labels_true, labels_pred, output_dict=False, zero_division=0)

    try:
        accuracy = float(accuracy_score(labels_true, labels_pred))
        precision = float(precision_score(labels_true, labels_pred, average=avg_method, zero_division=0))
        recall = float(recall_score(labels_true, labels_pred, average=avg_method, zero_division=0))
        f1 = float(f1_score(labels_true, labels_pred, average=avg_method, zero_division=0))
    except ValueError:
        accuracy = 0.0
        precision = 0.0
        recall = 0.0
        f1 = 0.0

    class_metrics: Dict[str, Dict[str, float]] = {}
    for cls in unique_labels:
        try:
            cls_precision = float(precision_score(
                labels_true, labels_pred, labels=[cls], average="micro", zero_division=0
            ))
            cls_recall = float(recall_score(
                labels_true, labels_pred, labels=[cls], average="micro", zero_division=0
            ))
            cls_f1 = float(f1_score(
                labels_true, labels_pred, labels=[cls], average="micro", zero_division=0
            ))
            support = int((labels_true == cls).sum())
            class_metrics[str(cls)] = {
                "precision": round(cls_precision, 4),
                "recall": round(cls_recall, 4),
                "f1_score": round(cls_f1, 4),
                "support": support,
            }
        except ValueError:
            class_metrics[str(cls)] = {
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "support": 0,
            }

    return {
        "report_text": report_text,
        "metrics": {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "average_method": avg_method,
        },
        "class_metrics": class_metrics,
        "n_samples": len(valid_data),
        "n_classes": n_classes,
        "classes": [str(c) for c in unique_labels],
    }
