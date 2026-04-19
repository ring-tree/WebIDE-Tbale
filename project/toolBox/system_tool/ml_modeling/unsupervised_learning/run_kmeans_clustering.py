from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


def run_kmeans_clustering(
    data: pd.DataFrame,
    feature_columns: Optional[List[str]] = None,
    n_clusters: int = 3,
    random_state: int = 42,
    max_iter: int = 300,
) -> Dict[str, Any]:
    """执行 K-Means 聚类分析。

    基于欧氏距离迭代聚类，将样本划分为 K 个内部紧密、间际疏离的簇群。

    Args:
        data: 输入的 pandas DataFrame。
        feature_columns: 用于聚类的特征列名列表，默认为 None（全部数值列）。
        n_clusters: 聚类数目，默认为 3。
        random_state: 随机种子，默认为 42。
        max_iter: 最大迭代次数，默认为 300。

    Returns:
        包含 'data'（带聚类标签的 DataFrame）、'cluster_centers'（聚类中心坐标）、
        'metrics'（聚类评估指标）的字典。

    Raises:
        TypeError: 当 data 不是 pandas DataFrame 时。
        ValueError: 当参数无效时。

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'A': [1,2,3,8,9,10], 'B': [1,2,3,8,9,10]})
        >>> result = run_kmeans_clustering(df, n_clusters=2)
        >>> 'cluster_labels' in result
        True
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"期望 pandas.DataFrame，实际类型: {type(data).__name__}")

    if n_clusters < 2:
        raise ValueError(f"参数 n_clusters 必须 >= 2，当前值: {n_clusters}")

    if feature_columns is None:
        feature_columns = data.select_dtypes(include=[np.number]).columns.tolist()
    else:
        invalid_cols = [c for c in feature_columns if c not in data.columns]
        if invalid_cols:
            raise ValueError(f"以下特征列不存在: {invalid_cols}")

    if not feature_columns:
        raise ValueError("没有可用的数值特征列")

    if len(feature_columns) < 1:
        raise ValueError("至少需要 1 个特征列用于聚类")

    valid_data = data[feature_columns].dropna()
    if len(valid_data) < n_clusters:
        raise ValueError(f"有效样本数 ({len(valid_data)}) 小于聚类数 ({n_clusters})")

    X = valid_data[feature_columns]

    n_clusters_actual = min(n_clusters, len(X))
    model = KMeans(
        n_clusters=n_clusters_actual,
        random_state=random_state,
        max_iter=max_iter,
        n_init=10,
    )
    cluster_labels = model.fit_predict(X)

    result_df = data.copy()
    result_df["cluster_label"] = -1
    result_df.loc[valid_data.index, "cluster_label"] = cluster_labels

    cluster_sizes = {}
    for i in range(n_clusters_actual):
        cluster_sizes[str(i)] = int(np.sum(cluster_labels == i))

    metrics: Dict[str, Any] = {
        "inertia": float(model.inertia_),
        "n_clusters": n_clusters_actual,
        "n_samples": len(X),
        "cluster_sizes": cluster_sizes,
    }

    if n_clusters_actual > 1 and n_clusters_actual < len(X):
        try:
            silhouette = silhouette_score(X, cluster_labels)
            metrics["silhouette_score"] = float(silhouette)
        except ValueError:
            metrics["silhouette_score"] = None

    centers_df = pd.DataFrame(model.cluster_centers_, columns=feature_columns)
    cluster_centers = {}
    for i in range(n_clusters_actual):
        cluster_centers[str(i)] = {col: float(centers_df.loc[i, col]) for col in feature_columns}

    return {
        "model_type": "KMeans",
        "data": result_df,
        "cluster_centers": cluster_centers,
        "metrics": metrics,
        "feature_columns": feature_columns,
        "cluster_labels": [int(l) for l in cluster_labels],
    }
