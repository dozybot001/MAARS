import pandas as pd
import numpy as np
from scipy.stats import skew
from sklearn.preprocessing import LabelEncoder

train = pd.read_csv('/workspace/data/train.csv')
test = pd.read_csv('/workspace/data/test.csv')
all_data = pd.concat((train, test)).reset_index(drop=True)
all_data.drop(['SalePrice', 'Id'], axis=1, inplace=True)

# Basic Imputation
all_data = all_data.fillna("None") # Quick fill to avoid NaNs for now

# Feature Engineering
all_data['MSSubClass'] = all_data['MSSubClass'].apply(str)
all_data['OverallCond'] = all_data['OverallCond'].astype(str)

cols_ordinal = ('MSSubClass', 'OverallCond')
for c in cols_ordinal:
    lbl = LabelEncoder()
    all_data[c] = lbl.fit_transform(list(all_data[c].values))

numeric_feats = all_data.dtypes[all_data.dtypes != "object"].index
print("Numeric features detected:", numeric_feats.tolist())

# Check types of values in these columns
for col in numeric_feats:
    try:
        skew(all_data[col])
    except Exception as e:
        print(f"Error in column {col}: {e}")
        print(f"Sample values in {col}: {all_data[col].head().values}")
        print(f"Dtype of {col}: {all_data[col].dtype}")