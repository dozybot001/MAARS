import pandas as pd
import numpy as np

# Load the dataset
train_df = pd.read_csv('/workspace/data/train.csv')

# 1. Data Quality Summary
info_summary = {
    "Total Rows": len(train_df),
    "Missing Values": train_df.isnull().sum().to_dict()
}

# Specific check for Age, Cabin, Embarked
missing_focus = {col: train_df[col].isnull().sum() for col in ['Age', 'Cabin', 'Embarked']}
missing_percent = {col: (train_df[col].isnull().sum() / len(train_df)) * 100 for col in ['Age', 'Cabin', 'Embarked']}

# 2. Basic Correlations
# Select only numeric columns for correlation
numeric_cols = train_df.select_dtypes(include=[np.number]).columns
correlations = train_df[numeric_cols].corr()['Survived'].sort_values(ascending=False)

# 3. Strategy Proposal
# Age: 177 missing (19.8%). Impute with median (robust to outliers).
# Cabin: 687 missing (77.1%). Too many missing to impute accurately. Proposed: Create 'HasCabin' or 'Cabin_Unknown'.
# Embarked: 2 missing (0.2%). Impute with mode.

# Perform initial cleaning/imputation to see if it improves things
train_df_cleaned = train_df.copy()
train_df_cleaned['Age'].fillna(train_df_cleaned['Age'].median(), inplace=True)
train_df_cleaned['Embarked'].fillna(train_df_cleaned['Embarked'].mode()[0], inplace=True)
train_df_cleaned['HasCabin'] = train_df_cleaned['Cabin'].apply(lambda x: 0 if pd.isna(x) else 1)

# Summary table for report
summary_report = pd.DataFrame({
    'Missing Values': train_df.isnull().sum(),
    '% Missing': (train_df.isnull().sum() / len(train_df)) * 100
})

print("--- Data Quality Summary ---")
print(summary_report)
print("\n--- Missing Value Focus ---")
for col in missing_focus:
    print(f"{col}: {missing_focus[col]} missing ({missing_percent[col]:.2f}%)")

print("\n--- Correlations with Survived ---")
print(correlations)

# Save the cleaned summary to a file
summary_report.to_csv('data_quality_summary.csv')
correlations.to_csv('correlations_summary.csv')