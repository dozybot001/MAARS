import pandas as pd
import numpy as np

train_proc = pd.read_csv('/workspace/output/train_processed.csv')
test_proc = pd.read_csv('/workspace/output/test_processed.csv')
print(f"Train Shape: {train_proc.shape}, Test Shape: {test_proc.shape}")
print(f"Train SalePrice head:\n{train_proc['SalePrice'].head()}")