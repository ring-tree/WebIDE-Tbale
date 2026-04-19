from typing import Any, Dict
import pandas as pd


def N_data_describe(data: pd.DataFrame, include: str = "number") -> Dict[str, Any]:
    """输出数值型特征的描述性统计。

    计算中心趋势与离散程度指标，包括均值、标准差、分位数等。

    Args:
        data: 输入的 pandas DataFrame。
        include: 要包含的数据类型，默认为 'number'（数值型）。
            可选值: 'number'（数值型）、'object'（字符型）、'all'（全部）、'datetime'（日期型）。

    Returns:
        包含 'statistics'（各列统计信息字典）、'columns_analyzed'（分析的列数）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当 data 中没有符合指定类型的列时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1, 2, 3, 4, 5], 'B': ['x', 'y', 'z', 'x', 'y']})
        >>> result = N_data_describe(df)
        >>> 'mean' in result['statistics']['A']
        True
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if data.empty:
        raise ValueError("DataFrame 为空，无法计算描述性统计")

    valid_includes = ("number", "object", "all", "datetime")
    if include not in valid_includes:
        raise ValueError(f"参数 include 必须为 {valid_includes} 之一，当前值: {include}")

    desc = data.describe(include=include)

    statistics: Dict[str, Dict[str, Any]] = {}
    for col in desc.columns:
        col_stats: Dict[str, Any] = {}
        for stat_name in desc.index:
            value = desc.loc[stat_name, col]
            try:
                col_stats[stat_name] = float(value)
            except (TypeError, ValueError):
                col_stats[stat_name] = str(value) if value is not None else None
        statistics[str(col)] = col_stats

    return {
        "statistics": statistics,
        "columns_analyzed": len(statistics),
        "include_type": include,
        "summary_table": desc.to_dict(),
    }
