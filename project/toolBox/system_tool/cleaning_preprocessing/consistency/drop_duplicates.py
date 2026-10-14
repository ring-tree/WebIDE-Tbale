from typing import Any, Dict, List, Optional, Union
import pandas as pd


def drop_duplicates(
    data: pd.DataFrame,
    subset: Optional[List[str]] = None,
    keep: str = "first",
) -> Dict[str, Any]:
    """识别并移除重复记录。

    基于全部或部分关键字段进行冗余检测，保留首次/末次出现或删除所有重复项。

    Args:
        data: 输入的 pandas DataFrame。
        subset: 用于去重的列名列表，默认为 None（使用全部列）。
        keep: 保留策略，可选值:
            - 'first': 保留首次出现的记录
            - 'last': 保留末次出现的记录
            - False: 删除所有重复记录

    Returns:
        包含 'data'（去重后的 DataFrame）、'original_rows'（原始行数）、
        'result_rows'（去重后行数）和 'removed_rows'（移除的行数）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当 subset 中的列不存在或 keep 参数无效时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1, 1, 2], 'B': ['x', 'x', 'y']})
        >>> result = drop_duplicates(df)
        >>> result['removed_rows']
        1
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    valid_keep = ("first", "last", False)
    if keep not in valid_keep:
        raise ValueError(f"参数 keep 必须为 {valid_keep} 之一，当前值: {keep}")

    if subset is not None:
        if not isinstance(subset, list):
            raise TypeError(f"参数 subset 必须为列表，实际类型: {type(subset).__name__}")
        invalid_cols = [c for c in subset if c not in data.columns]
        if invalid_cols:
            raise ValueError(f"以下列不存在于 DataFrame 中: {invalid_cols}")
        if not subset:
            subset = None

    original_rows = len(data)
    result_df = data.drop_duplicates(subset=subset, keep=keep)
    removed_rows = original_rows - len(result_df)

    return {
        "data": result_df,
        "original_rows": original_rows,
        "result_rows": len(result_df),
        "removed_rows": removed_rows,
        "duplicate_pct": round(removed_rows / original_rows * 100, 2) if original_rows > 0 else 0.0,
    }
