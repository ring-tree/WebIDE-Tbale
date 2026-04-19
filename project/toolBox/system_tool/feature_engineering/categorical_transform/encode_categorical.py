from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder, LabelEncoder


def encode_categorical(
    data: pd.DataFrame,
    columns: Optional[List[str]] = None,
    method: str = "onehot",
) -> Dict[str, Any]:
    """将离散类别变量转换为模型可计算的数值形式。

    支持 One-Hot 编码和 Label 编码两种方式。

    Args:
        data: 输入的 pandas DataFrame。
        columns: 需要编码的列名列表，默认为 None（全部 object/category 类型列）。
        method: 编码方式，可选值:
            - 'onehot': One-Hot 独热编码（产生新列）
            - 'label': Label 标签编码（原地替换）

    Returns:
        包含 'data'（编码后的 DataFrame）、'encoded_columns'（被编码的列信息）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当 method 无效或 columns 中的列不存在时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'color': ['red', 'blue', 'red']})
        >>> result = encode_categorical(df, columns=['color'], method='label')
        >>> result['data']['color'].tolist()
        [0, 1, 0]
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    valid_methods = ("onehot", "label")
    if method not in valid_methods:
        raise ValueError(f"参数 method 必须为 {valid_methods} 之一，当前值: {method}")

    if columns is None:
        columns = data.select_dtypes(include=["object", "category"]).columns.tolist()
    else:
        invalid_cols = [c for c in columns if c not in data.columns]
        if invalid_cols:
            raise ValueError(f"以下列不存在于 DataFrame 中: {invalid_cols}")

    if not columns:
        return {
            "data": data.copy(),
            "encoded_columns": {},
            "message": "没有可编码的类别列",
        }

    result_df = data.copy()
    encoded_columns: Dict[str, Any] = {}

    if method == "onehot":
        cols_to_encode = [c for c in columns if not result_df[c].isnull().all()]
        if cols_to_encode:
            encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
            encoded_arr = encoder.fit_transform(result_df[cols_to_encode].fillna("NaN"))
            new_col_names = []
            for i, col in enumerate(cols_to_encode):
                cats = encoder.categories_[i].tolist()
                col_new_names = [f"{col}_{cat}" for cat in cats]
                new_col_names.extend(col_new_names)
                encoded_columns[col] = {
                    "categories": cats,
                    "new_columns": col_new_names,
                    "method": "onehot",
                }
            encoded_df = pd.DataFrame(encoded_arr, columns=new_col_names, index=result_df.index)
            result_df = result_df.drop(columns=cols_to_encode)
            result_df = pd.concat([result_df, encoded_df], axis=1)
    else:
        for col in columns:
            if result_df[col].isnull().all():
                continue
            encoder = LabelEncoder()
            col_data = result_df[col].fillna("NaN").astype(str)
            result_df[col] = encoder.fit_transform(col_data)
            encoded_columns[col] = {
                "classes": encoder.classes_.tolist(),
                "n_categories": len(encoder.classes_),
                "method": "label",
            }

    return {
        "data": result_df,
        "encoded_columns": encoded_columns,
        "encoded_count": len(encoded_columns),
        "method": method,
    }
