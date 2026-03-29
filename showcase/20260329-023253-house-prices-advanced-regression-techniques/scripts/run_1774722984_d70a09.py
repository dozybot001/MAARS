import pandas as pd

train = pd.read_csv('/workspace/output/train_processed.csv')
print(train.head())
print(train.columns)