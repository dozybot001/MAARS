import pandas as pd

train_df = pd.read_csv('/workspace/output/train_processed.csv')
print(train_df.head())
print(train_df.columns.tolist())
print(f"Shape: {train_df.shape}")