import pandas as pd

train_df = pd.read_csv('train_advanced_features.csv')
print("Columns:", train_df.columns.tolist())
print(train_df.head())
print(train_df.info())