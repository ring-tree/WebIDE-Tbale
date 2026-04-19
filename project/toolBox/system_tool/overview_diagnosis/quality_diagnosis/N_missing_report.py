from typing import Any, Dict, List
import pandas as pd


def N_missing_report(data: pd.DataFrame) -> Dict[str, Any]:
    """生成数据缺失值统计报告。

    检测各列的缺失数量、缺失率，并分析缺失模式。

    Args:
        data: 输入的 pandas DataFrame。

    Returns:
        包含 'missing_report'（各列缺失统计列表）、'total_missing'（总缺失数）、
        'overall_missing_rate'（整体缺失率）和 'columns_with_missing'（有缺失的列数）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当 data 为空时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1, None, 3], 'B': [None, None, 'z']})
        >>> result = N_missing_report(df)
        >>> result['total_missing']
        3
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if data.empty:
        raise ValueError("DataFrame 为空，无法生成缺失报告")

    total_rows = len(data)
    total_cells = data.size
    missing_report: List[Dict[str, Any]] = []

    for col in data.columns:
        null_count = int(data[col].isnull().sum())
        if null_count > 0:
            first_null_idx = int(data[col].isnull().idxmax())
            non_null_before = int(data.loc[:first_null_idx, col].notnull().sum())
            pattern = "开头" if non_null_before == 0 else ("随机" if first_null_idx > 0 else "末尾")
        else:
            pattern = "无"

        missing_report.append({
            "column": col,
            "missing_count": null_count,
            "missing_pct": round(null_count / total_rows * 100, 2) if total_rows > 0 else 0.0,
            "non_missing_count": total_rows - null_count,
            "dtype": str(data[col].dtype),
            "missing_pattern": pattern,
        })

    total_missing = int(data.isnull().sum().sum())

    return {
        "missing_report": missing_report,
        "total_missing": total_missing,
        "overall_missing_rate": round(total_missing / total_cells * 100, 2) if total_cells > 0 else 0.0,
        "columns_with_missing": int(sum(1 for col in data.columns if data[col].isnull().any())),
        "total_rows": total_rows,
        "total_columns": len(data.columns),
    }
