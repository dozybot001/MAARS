import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import skew

# Load the data
df = pd.read_csv('/workspace/data/train.csv')

# 1. Identify missing values
missing_data = df.isnull().sum()
missing_data = missing_data[missing_data > 0].sort_values(ascending=False)
missing_percentage = (missing_data / len(df)) * 100
missing_info = pd.concat([missing_data, missing_percentage], axis=1, keys=['Total', 'Percent'])

# 2. Determine feature types
numerical_features = df.select_dtypes(include=[np.number]).columns.tolist()
categorical_features = df.select_dtypes(exclude=[np.number]).columns.tolist()

# 3. Analyze SalePrice distribution
saleprice_desc = df['SalePrice'].describe()
saleprice_skew = df['SalePrice'].skew()
saleprice_kurt = df['SalePrice'].kurt()

# Save SalePrice distribution plot
plt.figure(figsize=(10, 6))
sns.histplot(df['SalePrice'], kde=True)
plt.title('SalePrice Distribution')
plt.savefig('saleprice_dist.png')
plt.close()

# 4. Analyze other skewed features
numeric_feats = df[numerical_features].drop('SalePrice', axis=1)
skewness = numeric_feats.apply(lambda x: skew(x.dropna())).sort_values(ascending=False)
high_skew = skewness[abs(skewness) > 0.75]

# Output results to files for review
with open('eda_results.txt', 'w') as f:
    f.write("--- Missing Values ---\n")
    f.write(missing_info.to_string())
    f.write("\n\n--- Feature Types ---\n")
    f.write(f"Numerical features ({len(numerical_features)}): {numerical_features}\n")
    f.write(f"Categorical features ({len(categorical_features)}): {categorical_features}\n")
    f.write("\n--- SalePrice Stats ---\n")
    f.write(saleprice_desc.to_string())
    f.write(f"\nSkewness: {saleprice_skew}\n")
    f.write(f"Kurtosis: {saleprice_kurt}\n")
    f.write("\n--- High Skewness Features (>0.75) ---\n")
    f.write(high_skew.to_string())

print("EDA analysis completed. Results saved to eda_results.txt and saleprice_dist.png")