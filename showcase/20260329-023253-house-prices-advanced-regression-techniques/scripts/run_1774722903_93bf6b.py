import pandas as pd
import numpy as np
from scipy.stats import skew
from sklearn.preprocessing import LabelEncoder

# 1. Load Data
train = pd.read_csv('/workspace/data/train.csv')
test = pd.read_csv('/workspace/data/test.csv')

# 2. Handle Outliers
# The EDA and common wisdom suggest removing large GrLivArea houses with low SalePrice
train = train.drop(train[(train['GrLivArea']>4000) & (train['SalePrice']<300000)].index)

# 3. Log Transform Target
# We'll transform SalePrice and then drop it from training data for feature processing
train["SalePrice"] = np.log1p(train["SalePrice"])
y_train = train.SalePrice.values
train_id = train.Id
test_id = test.Id

# 4. Combine Train and Test
ntrain = train.shape[0]
ntest = test.shape[0]
all_data = pd.concat((train, test)).reset_index(drop=True)
all_data.drop(['SalePrice', 'Id'], axis=1, inplace=True)

# 5. Handle Missing Values
# Categorical features where NA means None
cols_none = ["PoolQC", "MiscFeature", "Alley", "Fence", "FireplaceQu", "GarageType", 
             "GarageFinish", "GarageQual", "GarageCond", "BsmtQual", "BsmtCond", 
             "BsmtExposure", "BsmtFinType1", "BsmtFinType2", "MasVnrType", "MSSubClass"]
for col in cols_none:
    all_data[col] = all_data[col].fillna("None")

# Categorical features where NA should be Mode
cols_mode = ["MSZoning", "Electrical", "KitchenQual", "Exterior1st", "Exterior2nd", "SaleType", "Utilities"]
for col in cols_mode:
    all_data[col] = all_data[col].fillna(all_data[col].mode()[0])

# Numerical features where NA should be 0
cols_zero = ["GarageYrBlt", "GarageArea", "GarageCars", "BsmtFinSF1", "BsmtFinSF2", 
             "BsmtUnfSF", "TotalBsmtSF", "BsmtFullBath", "BsmtHalfBath", "MasVnrArea"]
for col in cols_zero:
    all_data[col] = all_data[col].fillna(0)

# LotFrontage: Median by Neighborhood
all_data["LotFrontage"] = all_data.groupby("Neighborhood")["LotFrontage"].transform(lambda x: x.fillna(x.median()))

# Check if any missing left
missing = all_data.isnull().sum()
print("Missing values after imputation:\n", missing[missing > 0])

# 6. Feature Engineering
# Convert numeric columns that are actually categorical
all_data['MSSubClass'] = all_data['MSSubClass'].apply(str)
all_data['OverallCond'] = all_data['OverallCond'].astype(str)
all_data['YrSold'] = all_data['YrSold'].astype(str)
all_data['MoSold'] = all_data['MoSold'].astype(str)

# Combine features
all_data['TotalSF'] = all_data['TotalBsmtSF'] + all_data['1stFlrSF'] + all_data['2ndFlrSF']
all_data['HouseAge'] = all_data['YrSold'].astype(int) - all_data['YearBuilt']
all_data['IsNew'] = (all_data['YearBuilt'] == all_data['YrSold'].astype(int)).astype(int)

# 7. Ordinal Encoding for quality features
cols_ordinal = ('FireplaceQu', 'BsmtQual', 'BsmtCond', 'GarageQual', 'GarageCond', 
        'ExterQual', 'ExterCond','HeatingQC', 'PoolQC', 'KitchenQual', 'BsmtFinType1', 
        'BsmtFinType2', 'Functional', 'Fence', 'BsmtExposure', 'GarageFinish', 'LandSlope',
        'LotShape', 'PavedDrive', 'Street', 'Alley', 'CentralAir', 'MSSubClass', 'OverallCond', 
        'YrSold', 'MoSold')

for c in cols_ordinal:
    lbl = LabelEncoder() 
    lbl.fit(list(all_data[c].values)) 
    all_data[c] = lbl.transform(list(all_data[c].values))

# 8. Log Transform Skewed Numeric Features
numeric_feats = all_data.dtypes[all_data.dtypes != "object"].index
skewed_feats = all_data[numeric_feats].apply(lambda x: skew(x.dropna())).sort_values(ascending=False)
skewness = pd.DataFrame({'Skew' :skewed_feats})
high_skew = skewness[abs(skewness) > 0.75].dropna()
skewed_features = high_skew.index
all_data[skewed_features] = np.log1p(all_data[skewed_features])

# 9. One-Hot Encoding for remaining categorical features
all_data = pd.get_dummies(all_data)
print("Final data shape:", all_data.shape)

# 10. Split back and Save
train_processed = all_data[:ntrain]
test_processed = all_data[ntrain:]
train_processed['SalePrice'] = y_train
train_processed['Id'] = train_id
test_processed['Id'] = test_id

train_processed.to_csv('/workspace/artifacts/train_processed.csv', index=False)
test_processed.to_csv('/workspace/artifacts/test_processed.csv', index=False)

# Save best_score placeholder (though we don't have a score yet)
# We will do this after the first model training.

print("Processed data saved to /workspace/artifacts/")