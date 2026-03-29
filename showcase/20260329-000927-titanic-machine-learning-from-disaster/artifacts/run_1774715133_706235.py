import pandas as pd

train_df = pd.read_csv('train_wcg_features.csv')
print(train_df.columns.tolist())
print(train_df.head())