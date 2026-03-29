import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import shap

# Load the data
train_df = pd.read_csv('train_wcg_features.csv')

# Preprocessing
def preprocess_for_importance(df):
    df = df.copy()
    
    # 1. Deck from Cabin
    df['Deck'] = df['Cabin'].apply(lambda x: x[0] if pd.notnull(x) else 'U')
    
    # 2. Sex_Pclass interaction
    df['Sex_Pclass'] = df['Sex'] + "_" + df['Pclass'].astype(str)
    
    # 3. Handle missing values
    # Age - fill with median
    df['Age'] = df['Age'].fillna(df['Age'].median())
    # Embarked - fill with mode
    df['Embarked'] = df['Embarked'].fillna(df['Embarked'].mode()[0])
    
    # 4. Feature Selection - keep relevant numeric and categorical features
    features = [
        'Pclass', 'Sex', 'Age', 'SibSp', 'Parch', 'Fare', 'Embarked', 
        'IsWCG', 'IsAdultMale', 'Ticket_Group_Count', 'WCG_Survival_Group', 
        'Surviving_Male', 'Dead_Woman', 'Deck', 'Sex_Pclass'
    ]
    
    X = df[features].copy()
    
    # Encode categorical features
    le = LabelEncoder()
    cat_cols = ['Sex', 'Embarked', 'Deck', 'Sex_Pclass']
    for col in cat_cols:
        X[col] = le.fit_transform(X[col])
        
    return X, df['Survived']

X, y = preprocess_for_importance(train_df)

# Train a Random Forest model
rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X, y)

# 1. Permutation Importance or RF Feature Importance
importances = pd.DataFrame({
    'feature': X.columns,
    'importance': rf.feature_importances_
}).sort_values(by='importance', ascending=False)

print("Random Forest Feature Importance:")
print(importances)

# 2. SHAP analysis
explainer = shap.TreeExplainer(rf)
shap_values = explainer.shap_values(X)

# Calculate mean absolute SHAP values for each feature
# For binary classification, shap_values is a list of two arrays [prob_0, prob_1]
# We take prob_1 (index 1)
shap_sum = np.abs(shap_values[1]).mean(axis=0)
shap_importance = pd.DataFrame({
    'feature': X.columns,
    'shap_importance': shap_sum
}).sort_values(by='shap_importance', ascending=False)

print("\nSHAP Feature Importance:")
print(shap_importance)

# Save the importances
importances.to_csv('rf_feature_importance.csv', index=False)
shap_importance.to_csv('shap_feature_importance.csv', index=False)

# Plotting SHAP summary (saving it)
plt.figure(figsize=(10, 8))
shap.summary_plot(shap_values[1], X, show=False)
plt.tight_layout()
plt.savefig('shap_summary.png')