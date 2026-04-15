import sys
import os

# 添加项目根目录到 sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
backend_dir = os.path.dirname(__file__)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from tool_info import Tool
from project.toolBox.system_tool import *

"""
数据分析工具箱注册表 (Analysis Toolbox Registry)

用途说明：
本变量定义了可视化交互工具中所有可用的数据处理与分析方法。它是后端逻辑与
前端交互界面的核心映射表。前端界面将根据此表的配置动态渲染菜单栏、工具图标
及参数输入表单。

结构树：
数据分析工具箱
└── 阶段一：数据概览与诊断
    ├── 基础档案
    │   ├── 数据维度
    │   ├── 样本预览
    │   └── 字段信息
    └── 质量诊断
        ├── 缺失值统计
        └── 描述性统计
└── 阶段二：数据清洗与打磨
    ├── 完整性处理
    │   └── 缺失值填充
    ├── 一致性处理
    │   ├── 去重
    │   └── 重命名
    └── 纯净度处理
        ├── 删除列
        └── 异常值检测
└── 阶段三：特征工程与变换
    ├── 数值变换
    │   ├── Z-Score标准化
    │   └── Min-Max归一化
    ├── 类别变换
    │   └── 类别编码
    └── 特征优选
        ├── 特征选择
        └── 训练测试集划分
└── 阶段四：探索性分析与可视化
    ├── 分布洞察
    │   ├── 直方图
    │   └── 箱线图
    ├── 关系洞察
    │   ├── 散点图
    │   └── 相关性热力图
    └── 信度洞察
        └── Cronbach's α信度
└── 阶段五：智能建模
    ├── 监督学习
    │   ├── 线性回归
    │   ├── 逻辑回归
    │   ├── 决策树
    │   └── 随机森林
    └── 无监督学习
        └── K-Means聚类
└── 阶段六：模型评估与验证
    ├── 分类评估
    │   ├── 混淆矩阵
    │   └── 分类评估报告
    └── 回归评估
        └── 回归评估指标

命名规范：
1. 函数前缀:
  - 'N_': 表示该函数为 "Non-destructive" (非破坏性/只读)。
    此类函数仅用于查看、统计或绘图，不会修改源数据 DataFrame。
  - 无前缀: 表示该函数会直接处理、转换或修改数据，并返回新的 DataFrame。

2. Tool 对象字段:
  - name: 函数的唯一技术标识 (英文下划线)。
  - func: 后端实际调用的 Python 函数对象。
  - display_name: 前端展示的工具中文名称。
  - description: 鼠标悬停或帮助文档中显示的详细说明。
  - parameters: 工具参数配置列表 (用于前端表单渲染)。
"""
analysis_toolbox = [

    # ==========================================
    # 阶段一：数据概览与诊断
    # ==========================================
    {
        "stage_id": "overview_diagnosis",
        "stage_name": "数据概览与诊断",
        "sub_categories": [
            {
                "sub_category_id": "basic_archive",
                "sub_category_name": "基础档案",
                "tools": [
                    Tool(
                        name = 'N_data_shape',
                        func = N_data_shape,
                        display_name = "数据维度",
                        description = "快速获取数据集的规模信息，直观呈现样本数量与特征数量",
                        parameters = []
                    ),
                    Tool(
                        name = 'N_data_head',
                        func = N_data_head,
                        display_name = "样本预览",
                        description = "随机抽取数据首部记录，支持自定义抽取行数，便于快速了解数据样态",
                        parameters = [
                            {"name": "n", "type": "number", "label": "抽取行数", "default": 5, "required": False}
                        ]
                    ),
                    Tool(
                        name = 'N_data_info',
                        func = N_data_info,
                        display_name = "字段信息",
                        description = "全面扫描数据schema，呈现各列数据类型、缺失情况与存储类型",
                        parameters = []
                    )
                ]
            },
            {
                "sub_category_id": "quality_diagnosis",
                "sub_category_name": "质量诊断",
                "tools": [
                    Tool(
                        name = 'N_missing_report',
                        func = N_missing_report,
                        display_name = "缺失值统计",
                        description = "深度检测数据完整性，输出各列缺失数量、缺失率及缺失模式热图",
                        parameters = []
                    ),
                    Tool(
                        name = 'N_data_describe',
                        func = N_data_describe,
                        display_name = "描述性统计",
                        description = "输出数值型特征的中心趋势与离散程度指标，包括均值、标准差、分位数",
                        parameters = []
                    )
                ]
            }
        ]
    },

    # ==========================================
    # 阶段二：数据清洗与打磨
    # ==========================================
    {
        "stage_id": "cleaning_preprocessing",
        "stage_name": "数据清洗与打磨",
        "sub_categories": [
            {
                "sub_category_id": "completeness",
                "sub_category_name": "完整性处理",
                "tools": [
                    Tool(
                        name = 'impute_missing_values',
                        func = impute_missing_values,
                        display_name = "缺失值填充",
                        description = "智能填补数据空洞，支持均值/中位数/众数/固定值/插值等多种策略",
                        parameters = [
                            {"name": "strategy", "type": "select", "label": "填充策略", "default": "mean", "required": True, "options": [
                                {"label": "均值", "value": "mean"},
                                {"label": "中位数", "value": "median"},
                                {"label": "众数", "value": "most_frequent"},
                                {"label": "固定值", "value": "constant"}
                            ]},
                            {"name": "fill_value", "type": "number", "label": "固定填充值", "default": 0, "required": False}
                        ]
                    )
                ]
            },
            {
                "sub_category_id": "consistency",
                "sub_category_name": "一致性处理",
                "tools": [
                    Tool(
                        name = 'drop_duplicates',
                        func = drop_duplicates,
                        display_name = "去重",
                        description = "精准识别并移除重复记录，基于全部或部分关键字段进行冗余检测",
                        parameters = [
                            {"name": "subset", "type": "multi_select", "label": "去重依据列", "default": [], "required": False}
                        ]
                    ),
                    Tool(
                        name = 'rename_columns',
                        func = rename_columns,
                        display_name = "重命名",
                        description = "批量规范化列命名，支持映射转换与正则替换，提升数据可读性",
                        parameters = [
                            {"name": "mapping", "type": "mapping", "label": "列名映射", "default": {}, "required": True}
                        ]
                    )
                ]
            },
            {
                "sub_category_id": "purity",
                "sub_category_name": "纯净度处理",
                "tools": [
                    Tool(
                        name = 'drop_columns',
                        func = drop_columns,
                        display_name = "删除列",
                        description = "选择性剔除低价值或高冗余特征列，优化数据维度与模型效率",
                        parameters = [
                            {"name": "columns", "type": "multi_select", "label": "待删除列", "default": [], "required": True}
                        ]
                    ),
                    Tool(
                        name = 'filter_outliers',
                        func = filter_outliers,
                        display_name = "异常值检测",
                        description = "基于统计学方法识别极端值，支持3σ原则与IQR四分位距双重检验",
                        parameters = [
                            {"name": "method", "type": "select", "label": "检测方法", "default": "IQR", "required": True, "options": [
                                {"label": "IQR四分位距", "value": "IQR"},
                                {"label": "3σ原则", "value": "3sigma"}
                            ]},
                            {"name": "threshold", "type": "number", "label": "阈值倍数", "default": 1.5, "required": False}
                        ]
                    )
                ]
            }
        ]
    },

    # ==========================================
    # 阶段三：特征工程与变换
    # ==========================================
    {
        "stage_id": "feature_engineering",
        "stage_name": "特征工程与变换",
        "sub_categories": [
            {
                "sub_category_id": "numeric_transform",
                "sub_category_name": "数值变换",
                "tools": [
                    Tool(
                        name = 'standard_scaling',
                        func = standard_scaling,
                        display_name = "Z-Score标准化",
                        description = "执行Z-Score规范化，将特征转换为均值为0、标准差为1的标准正态分布",
                        parameters = [
                            {"name": "columns", "type": "multi_select", "label": "标准化列", "default": [], "required": False}
                        ]
                    ),
                    Tool(
                        name = 'minmax_scaling',
                        func = minmax_scaling,
                        display_name = "Min-Max归一化",
                        description = "实施Min-Max线性缩放，将数值映射到指定区间，默认为[0, 1]闭区间",
                        parameters = [
                            {"name": "columns", "type": "multi_select", "label": "归一化列", "default": [], "required": False},
                            {"name": "feature_range_min", "type": "number", "label": "映射区间最小值", "default": 0, "required": False},
                            {"name": "feature_range_max", "type": "number", "label": "映射区间最大值", "default": 1, "required": False}
                        ]
                    )
                ]
            },
            {
                "sub_category_id": "categorical_transform",
                "sub_category_name": "类别变换",
                "tools": [
                    Tool(
                        name = 'encode_categorical',
                        func = encode_categorical,
                        display_name = "类别编码",
                        description = "将离散类别转换为模型可计算的数值形式，支持One-Hot与Label编码",
                        parameters = [
                            {"name": "columns", "type": "multi_select", "label": "编码列", "default": [], "required": True},
                            {"name": "method", "type": "select", "label": "编码方式", "default": "onehot", "required": True, "options": [
                                {"label": "One-Hot编码", "value": "onehot"},
                                {"label": "标签编码", "value": "label"}
                            ]}
                        ]
                    )
                ]
            },
            {
                "sub_category_id": "feature_selection",
                "sub_category_name": "特征优选",
                "tools": [
                    Tool(
                        name = 'feature_selection_kbest',
                        func = feature_selection_kbest,
                        display_name = "特征选择",
                        description = "基于统计检验度量特征与目标变量的相关性，筛选Top-K最优特征组合",
                        parameters = [
                            {"name": "k", "type": "number", "label": "选择特征数", "default": 5, "required": True},
                            {"name": "score_func", "type": "select", "label": "评分函数", "default": "f_classif", "required": True, "options": [
                                {"label": "方差分析F值", "value": "f_classif"},
                                {"label": "互信息", "value": "mutual_info_classif"}
                            ]}
                        ]
                    ),
                    Tool(
                        name = 'train_test_split_data',
                        func = train_test_split_data,
                        display_name = "训练测试集划分",
                        description = "按指定比例随机分割数据集为训练集与测试集，支持分层采样与随机种子控制",
                        parameters = [
                            {"name": "test_size", "type": "number", "label": "测试集比例", "default": 0.2, "required": False},
                            {"name": "random_state", "type": "number", "label": "随机种子", "default": 42, "required": False},
                            {"name": "stratify", "type": "select", "label": "分层采样", "default": "none", "required": False, "options": [
                                {"label": "无", "value": "none"},
                                {"label": "目标变量", "value": "y"}
                            ]}
                        ]
                    )
                ]
            }
        ]
    },

    # ==========================================
    # 阶段四：探索性分析与可视化
    # ==========================================
    {
        "stage_id": "eda_visualization",
        "stage_name": "探索性分析与可视化",
        "sub_categories": [
            {
                "sub_category_id": "distribution_insight",
                "sub_category_name": "分布洞察",
                "tools": [
                    Tool(
                        name = 'N_plot_histogram',
                        func = N_plot_histogram,
                        display_name = "直方图",
                        description = "可视化数值型变量的频数分布，直观展示数据集中趋势与分散程度",
                        parameters = [
                            {"name": "column", "type": "select", "label": "选择列", "default": "", "required": True},
                            {"name": "bins", "type": "number", "label": "分组数量", "default": 20, "required": False}
                        ]
                    ),
                    Tool(
                        name = 'N_plot_boxplot',
                        func = N_plot_boxplot,
                        display_name = "箱线图",
                        description = "以箱体须线图呈现数据分位数分布，精确定位中位数、四分位点与异常边界",
                        parameters = [
                            {"name": "column", "type": "select", "label": "选择列", "default": "", "required": True}
                        ]
                    )
                ]
            },
            {
                "sub_category_id": "relationship_insight",
                "sub_category_name": "关系洞察",
                "tools": [
                    Tool(
                        name = 'N_plot_scatter',
                        func = N_plot_scatter,
                        display_name = "散点图",
                        description = "绘制二元变量分布散点图，揭示变量间相关模式、聚集程度与离群点",
                        parameters = [
                            {"name": "x_column", "type": "select", "label": "X轴列", "default": "", "required": True},
                            {"name": "y_column", "type": "select", "label": "Y轴列", "default": "", "required": True}
                        ]
                    ),
                    Tool(
                        name = 'N_correlation_heatmap',
                        func = N_correlation_heatmap,
                        display_name = "相关性热力图",
                        description = "计算Pearson相关系数矩阵，以热力图色彩编码呈现特征间线性关联强度",
                        parameters = [
                            {"name": "method", "type": "select", "label": "相关系数方法", "default": "pearson", "required": False, "options": [
                                {"label": "Pearson相关", "value": "pearson"},
                                {"label": "Spearman相关", "value": "spearman"},
                                {"label": "Kendall相关", "value": "kendall"}
                            ]}
                        ]
                    )
                ]
            },
            {
                "sub_category_id": "reliability_insight",
                "sub_category_name": "信度洞察",
                "tools": [
                    Tool(
                        name = 'N_reliability_analysis',
                        func = N_reliability_analysis,
                        display_name = "Cronbach's α信度",
                        description = "计算Cronbach's α系数，量化评估量表题项间内部一致性信度水平",
                        parameters = [
                            {"name": "columns", "type": "multi_select", "label": "量表题项", "default": [], "required": True}
                        ]
                    )
                ]
            }
        ]
    },

    # ==========================================
    # 阶段五：智能建模
    # ==========================================
    {
        "stage_id": "ml_modeling",
        "stage_name": "智能建模",
        "sub_categories": [
            {
                "sub_category_id": "supervised_learning",
                "sub_category_name": "监督学习",
                "tools": [
                    Tool(
                        name = 'run_linear_regression',
                        func = run_linear_regression,
                        display_name = "线性回归",
                        description = "拟合特征与连续目标变量间的线性关系，输出回归系数与截距项",
                        parameters = [
                            {"name": "target_column", "type": "select", "label": "目标变量", "default": "", "required": True},
                            {"name": "feature_columns", "type": "multi_select", "label": "特征变量", "default": [], "required": True}
                        ]
                    ),
                    Tool(
                        name = 'run_logistic_regression',
                        func = run_logistic_regression,
                        display_name = "逻辑回归",
                        description = "构建二分类/多分类概率模型，计算各类别的发生概率与分类边界",
                        parameters = [
                            {"name": "target_column", "type": "select", "label": "目标变量", "default": "", "required": True},
                            {"name": "feature_columns", "type": "multi_select", "label": "特征变量", "default": [], "required": True},
                            {"name": "multi_class", "type": "select", "label": "分类类型", "default": "auto", "required": False, "options": [
                                {"label": "自动检测", "value": "auto"},
                                {"label": "二分类", "value": "binary"},
                                {"label": "多分类", "value": "multinomial"}
                            ]}
                        ]
                    ),
                    Tool(
                        name = 'run_decision_tree',
                        func = run_decision_tree,
                        display_name = "决策树",
                        description = "生成可解释的树状分类/回归模型，以if-then规则序列呈现决策路径",
                        parameters = [
                            {"name": "target_column", "type": "select", "label": "目标变量", "default": "", "required": True},
                            {"name": "feature_columns", "type": "multi_select", "label": "特征变量", "default": [], "required": True},
                            {"name": "max_depth", "type": "number", "label": "最大深度", "default": 10, "required": False},
                            {"name": "task_type", "type": "select", "label": "任务类型", "default": "classification", "required": True, "options": [
                                {"label": "分类", "value": "classification"},
                                {"label": "回归", "value": "regression"}
                            ]}
                        ]
                    ),
                    Tool(
                        name = 'run_random_forest',
                        func = run_random_forest,
                        display_name = "随机森林",
                        description = "集成多棵决策树构建鲁棒模型，通过Bagging与特征随机采样降低过拟合",
                        parameters = [
                            {"name": "target_column", "type": "select", "label": "目标变量", "default": "", "required": True},
                            {"name": "feature_columns", "type": "multi_select", "label": "特征变量", "default": [], "required": True},
                            {"name": "n_estimators", "type": "number", "label": "树的数量", "default": 100, "required": False},
                            {"name": "max_depth", "type": "number", "label": "最大深度", "default": 10, "required": False},
                            {"name": "task_type", "type": "select", "label": "任务类型", "default": "classification", "required": True, "options": [
                                {"label": "分类", "value": "classification"},
                                {"label": "回归", "value": "regression"}
                            ]}
                        ]
                    )
                ]
            },
            {
                "sub_category_id": "unsupervised_learning",
                "sub_category_name": "无监督学习",
                "tools": [
                    Tool(
                        name = 'run_kmeans_clustering',
                        func = run_kmeans_clustering,
                        display_name = "K-Means聚类",
                        description = "基于欧氏距离迭代聚类，将样本划分为K个内部紧密、间际疏离的簇",
                        parameters = [
                            {"name": "feature_columns", "type": "multi_select", "label": "聚类特征", "default": [], "required": True},
                            {"name": "n_clusters", "type": "number", "label": "聚类数目", "default": 3, "required": True},
                            {"name": "random_state", "type": "number", "label": "随机种子", "default": 42, "required": False}
                        ]
                    )
                ]
            }
        ]
    },

    # ==========================================
    # 阶段六：模型评估与验证
    # ==========================================
    {
        "stage_id": "model_evaluation",
        "stage_name": "模型评估与验证",
        "sub_categories": [
            {
                "sub_category_id": "classification_eval",
                "sub_category_name": "分类评估",
                "tools": [
                    Tool(
                        name = 'N_confusion_matrix',
                        func = N_confusion_matrix,
                        display_name = "混淆矩阵",
                        description = "以矩阵形式交叉展示真实标签与预测标签的对应关系，量化各类别识别效果",
                        parameters = [
                            {"name": "y_true", "type": "select", "label": "真实标签", "default": "", "required": True},
                            {"name": "y_pred", "type": "select", "label": "预测标签", "default": "", "required": True}
                        ]
                    ),
                    Tool(
                        name = 'N_classification_report',
                        func = N_classification_report,
                        display_name = "分类评估报告",
                        description = "输出Precision/Recall/F1-Score等分类指标，提供Macro/Micro/Weighted多维度视角",
                        parameters = [
                            {"name": "y_true", "type": "select", "label": "真实标签", "default": "", "required": True},
                            {"name": "y_pred", "type": "select", "label": "预测标签", "default": "", "required": True}
                        ]
                    )
                ]
            },
            {
                "sub_category_id": "regression_eval",
                "sub_category_name": "回归评估",
                "tools": [
                    Tool(
                        name = 'N_mse_r2_score',
                        func = N_mse_r2_score,
                        display_name = "回归评估指标",
                        description = "计算MSE/RMSE/MAE/R²等回归评估指标，全面衡量模型拟合优度与预测精度",
                        parameters = [
                            {"name": "y_true", "type": "select", "label": "真实值", "default": "", "required": True},
                            {"name": "y_pred", "type": "select", "label": "预测值", "default": "", "required": True}
                        ]
                    )
                ]
            }
        ]
    }
]