import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder

# Load and preprocess as before
train_df = pd.read_csv('train_wcg_features.csv')

def preprocess_for_corr(df):
    df = df.copy()
    df['Deck'] = df['Cabin'].apply(lambda x: x[0] if pd.notnull(x) else 'U')
    df['Sex_Pclass'] = df['Sex'].astype(str) + "_" + df['Pclass'].astype(str)
    df['Age'] = df['Age'].fillna(df['Age'].median())
    df['Embarked'] = df['Embarked'].fillna(df['Embarked'].mode()[0])
    features = [
        'Pclass', 'Sex', 'Age', 'SibSp', 'Parch', 'Fare', 'Embarked', 
        'IsWCG', 'IsAdultMale', 'Ticket_Group_Count', 'WCG_Survival_Group', 
        'Surviving_Male', 'Dead_Woman', 'Deck', 'Sex_Pclass'
    ]
    X = df[features].copy()
    for col in ['Sex', 'Embarked', 'Deck', 'Sex_Pclass']:
        X[col] = LabelEncoder().fit_transform(X[col])
    return X

X = preprocess_for_corr(train_df)
corr_matrix = X.corr()

plt.figure(figsize=(12, 10))
sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap='coolwarm')
plt.title("Feature Correlation Heatmap")
plt.tight_layout()
plt.savefig('feature_correlation_heatmap.png')

# Find high correlations
high_corr = []
for i in range(len(corr_matrix.columns)):
    for j in range(i):
        if abs(corr_matrix.iloc[i, j]) > 0.8:
            high_corr.append((corr_matrix.columns[i], corr_matrix.columns[j], corr_matrix.iloc[i, j]))

print("High Correlation Pairs (> 0.8):")
for pair in high_corr:
    print(pair)