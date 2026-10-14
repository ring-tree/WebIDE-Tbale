"""建模与评估工具的回归测试。

背景（两个真实缺陷）：

1. `run_logistic_regression` 向 `LogisticRegression` 传了 `multi_class` 参数。
   该参数在 scikit-learn 1.5 弃用、**1.7 起移除**，而项目声明 `scikit-learn>=1.4.0`，
   新装环境会拿到 1.9.x，导致逻辑回归工具完全不可用：

       TypeError: LogisticRegression.__init__() got an unexpected keyword argument 'multi_class'

2. 评估类工具（混淆矩阵 / 分类评估报告）对「同一列同时作为 y_true 与 y_pred」
   缺少校验，会抛出难以理解的 pandas 重名列错误，或报出与实际原因不符的提示。
"""

import numpy as np
import pandas as pd
import pytest

from project.toolBox.system_tool import (
    run_logistic_regression,
    run_linear_regression,
    run_decision_tree,
    run_random_forest,
    run_kmeans_clustering,
    N_confusion_matrix,
    N_classification_report,
    N_mse_r2_score,
)


@pytest.fixture()
def clf_df():
    """二分类数据集：含整型特征、整型目标，以及一列预测结果"""
    rng = np.random.default_rng(42)
    n = 80
    y = rng.integers(0, 2, n)
    pred = np.where(rng.random(n) < 0.2, 1 - y, y)
    return pd.DataFrame({
        'age': rng.integers(18, 65, n),           # int64
        'income': rng.normal(9000, 2000, n).round(2),
        'churn': y,                                # int64 目标
        'churn_pred': pred,
    })


@pytest.fixture()
def multi_df():
    """三分类数据集 —— 走 multi_class='multinomial' 分支"""
    rng = np.random.default_rng(7)
    n = 90
    return pd.DataFrame({
        'x1': rng.normal(0, 1, n),
        'x2': rng.normal(5, 2, n),
        'grade': rng.integers(0, 3, n),            # 3 类
    })


@pytest.fixture()
def reg_df():
    """回归数据集：目标为连续值"""
    rng = np.random.default_rng(11)
    n = 80
    x = rng.normal(0, 1, n)
    return pd.DataFrame({
        'x': x,
        'y': 3 * x + rng.normal(0, 0.3, n),
    })


class TestSupervisedLearning:
    def test_logistic_regression_binary(self, clf_df):
        """回归用例：曾因 sklearn 移除 multi_class 而完全不可用"""
        result = run_logistic_regression(clf_df, target_column='churn',
                                         feature_columns=['age', 'income'])
        assert result is not None

    def test_logistic_regression_multiclass(self, multi_df):
        """三分类走 multinomial 分支 —— 旧实现正是在这里传入 multi_class"""
        result = run_logistic_regression(multi_df, target_column='grade',
                                         feature_columns=['x1', 'x2'])
        assert result is not None

    def test_logistic_regression_binary_mode_on_multiclass_raises(self, multi_df):
        with pytest.raises(ValueError):
            run_logistic_regression(multi_df, target_column='grade',
                                    feature_columns=['x1', 'x2'],
                                    multi_class='binary')

    def test_linear_regression(self, reg_df):
        assert run_linear_regression(reg_df, target_column='y',
                                     feature_columns=['x']) is not None

    def test_decision_tree(self, clf_df):
        assert run_decision_tree(clf_df, target_column='churn',
                                 feature_columns=['age', 'income']) is not None

    def test_random_forest(self, clf_df):
        assert run_random_forest(clf_df, target_column='churn',
                                 feature_columns=['age', 'income']) is not None

    def test_kmeans_clustering(self, clf_df):
        assert run_kmeans_clustering(clf_df, feature_columns=['age', 'income'],
                                     n_clusters=3) is not None


class TestClassificationEvaluation:
    def test_confusion_matrix_with_distinct_columns(self, clf_df):
        assert N_confusion_matrix(clf_df, y_true='churn',
                                  y_pred='churn_pred') is not None

    def test_classification_report_with_distinct_columns(self, clf_df):
        assert N_classification_report(clf_df, y_true='churn',
                                       y_pred='churn_pred') is not None

    def test_confusion_matrix_rejects_same_column(self, clf_df):
        """同一列不能既作真实值又作预测值 —— 应给出明确提示"""
        with pytest.raises(ValueError, match='不能是同一列'):
            N_confusion_matrix(clf_df, y_true='churn', y_pred='churn')

    def test_classification_report_rejects_same_column(self, clf_df):
        with pytest.raises(ValueError, match='不能是同一列'):
            N_classification_report(clf_df, y_true='churn', y_pred='churn')

    def test_confusion_matrix_missing_column(self, clf_df):
        with pytest.raises(ValueError):
            N_confusion_matrix(clf_df, y_true='not_exist', y_pred='churn_pred')


class TestRegressionEvaluation:
    def test_mse_r2_score(self):
        rng = np.random.default_rng(3)
        n = 50
        df = pd.DataFrame({
            'actual': rng.normal(0, 1, n),
            'predicted': rng.normal(0, 1, n),
        })
        assert N_mse_r2_score(df, y_true='actual', y_pred='predicted') is not None
