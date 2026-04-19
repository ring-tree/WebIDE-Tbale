from typing import Any, Dict, List
import pandas as pd


def N_data_info(data: pd.DataFrame) -> Dict[str, Any]:
    """全面扫描数据 schema 信息。

    返回各列的数据类型、缺失情况、唯一值数量等元信息。

    Args:
        data: 输入的 pandas DataFrame。

    Returns:
        包含 'columns_info'（每列详细信息列表）、'total_columns'（总列数）、
        'total_rows'（总行数）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当 data 为空时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1, 2, None], 'B': ['x', 'y', 'z']})
        >>> result = N_data_info(df)
        >>> result['total_columns']
        2
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if data.empty:
        raise ValueError("DataFrame 为空，无法获取字段信息")

    total_rows = len(data)
    columns_info: List[Dict[str, Any]] = []

    for col in data.columns:
        col_data = data[col]
        null_count = int(col_data.isnull().sum())
        non_null_count = total_rows - null_count
        unique_count = int(col_data.nunique(dropna=False))

        col_info: Dict[str, Any] = {
            "column": col,
            "dtype": str(col_data.dtype),
            "non_null_count": non_null_count,
            "null_count": null_count,
            "null_pct": round(null_count / total_rows * 100, 2) if total_rows > 0 else 0.0,
            "unique_count": unique_count,
            "is_numeric": pd.api.types.is_numeric_dtype(col_data),
            "is_datetime": pd.api.types.is_datetime64_any_dtype(col_data),
            "is_object": pd.api.types.is_object_dtype(col_data),
        }

        if pd.api.types.is_numeric_dtype(col_data):
            non_null_values = col_data.dropna()
            if len(non_null_values) > 0:
                col_info["min"] = float(non_null_values.min())
                col_info["max"] = float(non_null_values.max())
                col_info["mean"] = float(non_null_values.mean())
                col_info["std"] = float(non_null_values.std())

        if unique_count <= 10:
            col_info["top_values"] = [
                str(v) for v in col_data.value_counts().head(10).index.tolist()
            ]

        columns_info.append(col_info)

    return {
        "columns_info": columns_info,
        "total_columns": len(columns_info),
        "total_rows": total_rows,
    }
