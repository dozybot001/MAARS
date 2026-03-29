import pandas as pd
import numpy as np

oof_df = pd.read_csv('/workspace/artifacts/all_models_oof.csv')
print("OOF Predictions Columns:", oof_df.columns.tolist())
print(oof_df.head())

# Load target
train_df = pd.read_csv('/workspace/artifacts/train_processed.csv')
y = train_df['SalePrice']
print("Target shape:", y.shape)