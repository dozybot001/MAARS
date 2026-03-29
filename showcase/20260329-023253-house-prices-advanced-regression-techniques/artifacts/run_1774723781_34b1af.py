import pandas as pd
import numpy as np

# Load the generated submission
sub = pd.read_csv('/workspace/output/submission.csv')
sample = pd.read_csv('/workspace/data/sample_submission.csv')

# Validation
print(f"Row count: {len(sub)} (Expected: {len(sample)})")
print(f"Missing values: {sub.isnull().sum().sum()}")
print(f"Minimum SalePrice: {sub['SalePrice'].min()}")
print(f"Maximum SalePrice: {sub['SalePrice'].max()}")

# Check if IDs match
ids_match = sub['Id'].equals(sample['Id'])
print(f"IDs match sample_submission: {ids_match}")

# Ensure SalePrice is not in log scale
# Log scale would have values around 10-15. Real prices are 100k+.
if sub['SalePrice'].mean() < 20:
    print("WARNING: SalePrice seems to be in log scale!")
else:
    print("SalePrice appears to be correctly inverse-transformed.")

# Re-save to ensure it's in the final output directory as requested
sub.to_csv('/workspace/output/submission.csv', index=False)
print("Final submission saved and verified.")