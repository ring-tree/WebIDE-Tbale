from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split


def train_test_split_data(
    data: pd.DataFrame,
    target_column: Optional[str] = None,
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = False,
) -> Dict[str, Any]:
    """按指定比例随机分割数据集。

    将数据分割为训练集与测试集，支持分层采样与随机种子控制。

    Args:
        data: 输入的 pandas DataFrame。
        target_column: 目标变量列名，用于分层采样时指定。
        test_size: 测试集占总数据的比例，范围 (0, 1)，默认为 0.2。
        random_state: 随机种子，控制数据分割的可重复性，默认为 42。
        stratify: 是否使用分层采样，默认为 False。

    Returns:
        包含 'X_train'、'X_test'、'y_train'（如有目标列）、'y_test'（如有目标列）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当 test_size 不在 (0, 1) 范围内时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': range(10), 'B': range(10)})
        >>> result = train_test_split_data(df, test_size=0.2, random_state=42)
        >>> len(result['X_train']) + len(result['X_test'])
        10
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if not (0 < test_size < 1):
        raise ValueError(f"参数 test_size 必须在 (0, 1) 范围内，当前值: {test_size}")

    X = data.copy()
    y = None
    stratify_col = None

    if target_column is not None:
        if target_column not in data.columns:
            raise ValueError(f"目标变量列 '{target_column}' 不存在于 DataFrame 中")
        y = X.pop(target_column)
        if stratify:
            stratify_col = y

    try:
        if y is not None:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state, stratify=stratify_col
            )
            return {
                "X_train": X_train,
                "X_test": X_test,
                "y_train": y_train,
                "y_test": y_test,
                "train_size": len(X_train),
                "test_size": len(X_test),
                "train_pct": round(len(X_train) / len(data) * 100, 2),
                "test_pct": round(len(X_test) / len(data) * 100, 2),
            }
        else:
            X_train, X_test = train_test_split(
                X, test_size=test_size, random_state=random_state
            )
            return {
                "X_train": X_train,
                "X_test": X_test,
                "train_size": len(X_train),
                "test_size": len(X_test),
                "train_pct": round(len(X_train) / len(data) * 100, 2),
                "test_pct": round(len(X_test) / len(data) * 100, 2),
            }
    except ValueError as e:
        raise ValueError(f"数据集分割失败: {e}")
