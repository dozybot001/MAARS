import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_selection import RFE
import shap

# Load the data
train_df = pd.read_csv('train_wcg_features.csv')

# Preprocessing
def preprocess_for_importance(df):
    df = df.copy()
    
    # 1. Deck from Cabin
    df['Deck'] = df['Cabin'].apply(lambda x: x[0] if pd.notnull(x) else 'U')
    
    # 2. Sex_Pclass interaction
    df['Sex_Pclass'] = df['Sex'].astype(str) + "_" + df['Pclass'].astype(str)
    
    # 3. Handle missing values
    df['Age'] = df['Age'].fillna(df['Age'].median())
    df['Embarked'] = df['Embarked'].fillna(df['Embarked'].mode()[0])
    
    # 4. Features
    features = [
        'Pclass', 'Sex', 'Age', 'SibSp', 'Parch', 'Fare', 'Embarked', 
        'IsWCG', 'IsAdultMale', 'Ticket_Group_Count', 'WCG_Survival_Group', 
        'Surviving_Male', 'Dead_Woman', 'Deck', 'Sex_Pclass'
    ]
    
    X = df[features].copy()
    
    # Encode categorical features
    for col in ['Sex', 'Embarked', 'Deck', 'Sex_Pclass']:
        X[col] = LabelEncoder().fit_transform(X[col])
        
    return X, df['Survived']

X, y = preprocess_for_importance(train_df)

# Train a Random Forest model
rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X, y)

# 1. RF Feature Importance
rf_importances = pd.DataFrame({
    'feature': X.columns,
    'rf_importance': rf.feature_importances_
}).sort_values(by='rf_importance', ascending=False)

# 2. RFE (Recursive Feature Elimination)
rfe = RFE(estimator=RandomForestClassifier(n_estimators=100, random_state=42), n_features_to_select=1)
rfe.fit(X, y)
rfe_ranking = pd.DataFrame({
    'feature': X.columns,
    'rfe_ranking': rfe.ranking_
}).sort_values(by='rfe_ranking')

# 3. SHAP analysis
explainer = shap.TreeExplainer(rf)
shap_values = explainer.shap_values(X)

# Handle different shap value return formats
if isinstance(shap_values, list):
    # Binary classification, usually shap_values[1] is the positive class
    sv = shap_values[1]
elif len(shap_values.shape) == 3:
    # (samples, features, classes)
    sv = shap_values[:, :, 1]
else:
    # (samples, features)
    sv = shap_values

shap_sum = np.abs(sv).mean(axis=0)
shap_importance = pd.DataFrame({
    'feature': X.columns,
    'shap_importance': shap_sum
}).sort_values(by='shap_importance', ascending=False)

# Merge results
final_importance = rf_importances.merge(rfe_ranking, on='feature').merge(shap_importance, on='feature')
final_importance = final_importance.sort_values(by='shap_importance', ascending=False)

print("Comprehensive Feature Importance Analysis:")
print(final_importance)

# Save
final_importance.to_csv('feature_importance_analysis.csv', index=False)

# SHAP plot
plt.figure(figsize=(12, 8))
shap.summary_plot(sv, X, show=False)
plt.title("SHAP Summary Plot")
plt.tight_layout()
plt.savefig('shap_summary_plot.png')

# Identify features to discard
# We can set a heuristic: if shap_importance is extremely low (e.g. < 0.005) 
# and RFE ranking is low (e.g. > 10)
to_discard = final_importance[(final_importance['shap_importance'] < 0.005) & (final_importance['rfe_ranking'] > 12)]['feature'].tolist()
print(f"\nRecommended to DISCARD: {to_discard}")