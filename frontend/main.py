import jedi

# 示例代码字符串，用于测试代码补全功能
chen = """
import pandas as pd
df = pd.DataFrame_csv("data.csv")

def chen():
    return df

c
"""

# 创建Jedi脚本对象
script = jedi.Script(chen)

# 获取在指定位置的代码补全建议
completions = script.complete(line=8, column=1)
for completion in completions:
    print(completion.name, "---", completion.description)












