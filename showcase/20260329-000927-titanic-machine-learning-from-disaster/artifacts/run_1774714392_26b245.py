import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder

# Load the datasets
train_df = pd.read_csv('/workspace/data/train.csv')
test_df = pd.read_csv('/workspace/data/test.csv')

# Combine datasets for some operations to ensure consistency, 
# but be careful to avoid leakage for scaling/imputing.
# Actually, it's safer to determine parameters from train and apply to test.

# 1. Missing Value Imputation
# Age: use median from train
age_median = train_df['Age'].median()
train_df['Age'] = train_df['Age'].fillna(age_median)
test_df['Age'] = test_df['Age'].fillna(age_median)

# Embarked: use mode from train
embarked_mode = train_df['Embarked'].mode()[0]
train_df['Embarked'] = train_df['Embarked'].fillna(embarked_mode)
test_df['Embarked'] = test_df['Embarked'].fillna(embarked_mode)

# Fare: test set has one missing value
fare_median = train_df['Fare'].median()
test_df['Fare'] = test_df['Fare'].fillna(fare_median)

# 2. Feature Engineering: Title
def extract_title(name):
    title = name.split(',')[1].split('.')[0].strip()
    return title

train_df['Title'] = train_df['Name'].apply(extract_title)
test_df['Title'] = test_df['Name'].apply(extract_title)

# Simplify Title
def simplify_title(title):
    if title in ['Mr', 'Miss', 'Mrs', 'Master']:
        return title
    elif title in ['Mlle', 'Ms']:
        return 'Miss'
    elif title == 'Mme':
        return 'Mrs'
    else:
        return 'Rare'

train_df['Title'] = train_df['Title'].apply(simplify_title)
test_df['Title'] = test_df['Title'].apply(simplify_title)

# 3. Feature Engineering: FamilySize
train_df['FamilySize'] = train_df['SibSp'] + train_df['Parch'] + 1
test_df['FamilySize'] = test_df['SibSp'] + test_df['Parch'] + 1

# 4. Feature Engineering: HasCabin (Recommended from Task 1)
train_df['HasCabin'] = train_df['Cabin'].apply(lambda x: 0 if pd.isna(x) else 1)
test_df['HasCabin'] = test_df['Cabin'].apply(lambda x: 0 if pd.isna(x) else 1)

# 5. Encoding Categorical Variables
# For Sex: binary encoding
train_df['Sex'] = train_df['Sex'].map({'female': 1, 'male': 0})
test_df['Sex'] = test_df['Sex'].map({'female': 1, 'male': 0})

# For Embarked and Title: One-Hot Encoding
train_df = pd.get_dummies(train_df, columns=['Embarked', 'Title'], prefix=['Embarked', 'Title'])
test_df = pd.get_dummies(test_df, columns=['Embarked', 'Title'], prefix=['Embarked', 'Title'])

# Align test columns with train columns (in case some categories are missing)
train_features = train_df.drop(['PassengerId', 'Survived', 'Name', 'Ticket', 'Cabin', 'SibSp', 'Parch'], axis=1)
test_features = test_df.drop(['PassengerId', 'Name', 'Ticket', 'Cabin', 'SibSp', 'Parch'], axis=1)

# Ensure both have the same columns
for col in train_features.columns:
    if col not in test_features.columns:
        test_features[col] = 0
test_features = test_features[train_features.columns]

# 6. Scaling Numerical Features
# Features to scale: Pclass, Age, Fare, FamilySize
features_to_scale = ['Pclass', 'Age', 'Fare', 'FamilySize']
scaler = StandardScaler()
train_features[features_to_scale] = scaler.fit_transform(train_features[features_to_scale])
test_features[features_to_scale] = scaler.transform(test_features[features_to_scale])

# Save the target variable separately
train_labels = train_df['Survived']

# Save processed data
train_features.to_csv('train_processed.csv', index=False)
test_features.to_csv('test_processed.csv', index=False)
train_labels.to_csv('train_labels.csv', index=False)

print("Processed train shape:", train_features.shape)
print("Processed test shape:", test_features.shape)
print("Columns in processed data:", train_features.columns.tolist())