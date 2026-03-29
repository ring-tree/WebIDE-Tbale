import jedi

chen = """
import pandas as pd
df = pd.DataFrame_csv("data.csv")

def chen():
    return df

c
"""


script = jedi.Script(chen)

completions = script.complete(line=8, column=1)
for completion in completions:
    print(completion.name, "---", completion.description)












