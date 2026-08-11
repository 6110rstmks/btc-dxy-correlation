import pandas as pd

url = "https://stooq.com/q/d/l/?s=%5Espx&d1=20210101&d2=20211231"

df = pd.read_csv(url)

print(df)

df.to_csv("SP500_stooq.csv", index=False)