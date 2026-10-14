"""工具箱数值变换工具的回归测试。

背景（真实缺陷）：
    `standard_scaling` 与 `minmax_scaling` 曾把标准化/归一化后的**浮点结果**
    直接赋回原列。当原列是整型时，pandas 会抛：

        TypeError: Invalid value '[-1.41 -0.71  0.    0.71  1.41]' for dtype 'int64'

    整数列（年龄、数量、计数）在真实数据中极其常见，这意味着
    「阶段三 特征工程」的两个核心工具对多数数据集都不可用。

    修复方式：赋值前先把目标列升为 float。

本文件直接对工具函数做单元测试（不经 HTTP 层），定位问题更快。
"""

import pandas as pd
import pytest

from project.toolBox.system_tool import (
    standard_scaling,
    minmax_scaling,
    impute_missing_values,
    filter_outliers,
    encode_categorical,
)


@pytest.fixture()
def mixed_df():
    return pd.DataFrame({
        'age': [20, 30, 40, 50, 60],          # int64 —— 触发上述缺陷的关键
        'score': [1.0, 2.0, 3.0, 4.0, 5.0],   # float64
        'city': ['A', 'B', 'A', 'C', 'B'],    # 类别
    })


class TestIntegerColumnCompatibility:
    """整型列不得导致数值变换工具失败"""

    def test_standard_scaling_on_int_column(self, mixed_df):
        result = standard_scaling(mixed_df, columns=['age'])['data']
        assert abs(result['age'].mean()) < 1e-9
        assert abs(result['age'].std(ddof=0) - 1) < 1e-9

    def test_minmax_scaling_on_int_column(self, mixed_df):
        result = minmax_scaling(mixed_df, columns=['age'])['data']
        assert result['age'].min() == 0
        assert result['age'].max() == 1

    def test_standard_scaling_auto_selects_all_numeric(self, mixed_df):
        result = standard_scaling(mixed_df)
        assert set(result['scaled_columns']) == {'age', 'score'}

    def test_minmax_scaling_auto_selects_all_numeric(self, mixed_df):
        result = minmax_scaling(mixed_df)
        assert set(result['scaled_columns']) == {'age', 'score'}

    def test_minmax_scaling_custom_range_on_int_column(self, mixed_df):
        result = minmax_scaling(mixed_df, columns=['age'],
                                feature_range_min=-1, feature_range_max=1)['data']
        assert result['age'].min() == -1
        assert result['age'].max() == 1

    def test_original_dataframe_not_mutated(self, mixed_df):
        """工具应返回副本，不得改动传入的 DataFrame"""
        standard_scaling(mixed_df, columns=['age'])
        assert mixed_df['age'].tolist() == [20, 30, 40, 50, 60]


class TestMissingValueHandling:
    def test_standard_scaling_preserves_missing(self):
        df = pd.DataFrame({'a': [1, 2, None, 4], 'b': [10.5, None, 30.5, 40.5]})
        result = standard_scaling(df)['data']
        assert result['a'].isna().sum() == 1
        assert result['b'].isna().sum() == 1

    def test_minmax_scaling_preserves_missing(self):
        df = pd.DataFrame({'a': [1, 2, None, 4]})
        result = minmax_scaling(df)['data']
        assert result['a'].isna().sum() == 1

    def test_constant_column_is_skipped(self):
        """单一取值的列标准差为 0，不应被选中，也不应报错"""
        df = pd.DataFrame({'const': [5, 5, 5], 'vary': [1, 2, 3]})
        result = minmax_scaling(df)
        assert 'const' not in result['scaled_columns']
        assert 'vary' in result['scaled_columns']

    def test_nonexistent_column_raises(self, mixed_df):
        with pytest.raises(ValueError):
            standard_scaling(mixed_df, columns=['not_a_column'])

    def test_non_dataframe_raises(self):
        with pytest.raises(TypeError):
            standard_scaling([1, 2, 3])


class TestOtherToolsSmoke:
    """其余工具在混合类型数据上不应抛异常"""

    def test_impute_missing_values(self):
        df = pd.DataFrame({'a': [1.0, None, 3.0], 'b': ['x', None, 'y']})
        result = impute_missing_values(df, strategy='mean')
        assert result['data']['a'].isna().sum() == 0

    def test_filter_outliers(self, mixed_df):
        result = filter_outliers(mixed_df, method='IQR', threshold=1.5)
        assert result is not None

    def test_filter_outliers_3sigma(self, mixed_df):
        result = filter_outliers(mixed_df, method='3sigma')
        assert result is not None

    def test_encode_categorical(self, mixed_df):
        result = encode_categorical(mixed_df, columns=['city'], method='label')
        assert result is not None

    def test_impute_on_int_column_with_missing(self):
        """整型列出现缺失后会变成 float，填充不应报错"""
        df = pd.DataFrame({'a': [1, 2, None, 4]})
        result = impute_missing_values(df, strategy='median')['data']
        assert result['a'].isna().sum() == 0
