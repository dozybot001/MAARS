import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder

# Load data
train_df = pd.read_csv('train_wcg_features.csv')
test_df = pd.read_csv('test_wcg_features.csv')

# Common Preprocessing
def prepare_data(df, is_train=True, train_medians=None):
    df = df.copy()
    # 1. New Features
    df['Deck'] = df['Cabin'].apply(lambda x: x[0] if pd.notnull(x) else 'U')
    df['Sex_Pclass'] = df['Sex'].astype(str) + "_" + df['Pclass'].astype(str)
    
    # 2. Missing values
    if is_train:
        medians = {
            'Age': df['Age'].median(),
            'Fare': df['Fare'].median(),
            'Embarked': df['Embarked'].mode()[0]
        }
    else:
        medians = train_medians
        
    df['Age'] = df['Age'].fillna(medians['Age'])
    df['Fare'] = df['Fare'].fillna(medians['Fare'])
    df['Embarked'] = df['Embarked'].fillna(medians['Embarked'])
    
    return df, medians

train_prepared, train_medians = prepare_data(train_df)
test_prepared, _ = prepare_data(test_df, is_train=False, train_medians=train_medians)

# Encoding
cat_cols = ['Sex', 'Embarked', 'Deck', 'Sex_Pclass']
for col in cat_cols:
    le = LabelEncoder()
    # Combine train and test for consistent encoding
    combined = pd.concat([train_prepared[col], test_prepared[col]]).astype(str)
    le.fit(combined)
    train_prepared[col] = le.transform(train_prepared[col].astype(str))
    test_prepared[col] = le.transform(test_prepared[col].astype(str))

# Define feature sets
sets = {
    'Base_Titanic': ['Pclass', 'Sex', 'Age', 'SibSp', 'Parch', 'Fare', 'Embarked'],
    'Advanced_WCG': ['Pclass', 'Sex', 'Age', 'SibSp', 'Parch', 'Fare', 'Embarked', 
                     'IsWCG', 'IsAdultMale', 'Ticket_Group_Count', 'WCG_Survival_Group', 
                     'Surviving_Male', 'Dead_Woman', 'Deck', 'Sex_Pclass'],
    'Selected_Optimized': ['Pclass', 'Age', 'SibSp', 'Fare', 'Embarked', 
                           'IsAdultMale', 'Ticket_Group_Count', 'WCG_Survival_Group', 
                           'Dead_Woman', 'Deck', 'Sex_Pclass']
}

results = {}
for name, features in sets.items():
    X = train_prepared[features]
    y = train_prepared['Survived']
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    scores = cross_val_score(rf, X, y, cv=5)
    results[name] = scores.mean()

print("Cross-Validation Comparison:")
for name, score in results.items():
    print(f"{name}: {score:.4f}")

# Final Selected Features
final_features = sets['Selected_Optimized']
print(f"\nFinal Selected Features: {final_features}")

# Save the selected features to CSV
train_prepared[final_features + ['Survived']].to_csv('train_selected_features.csv', index=False)
test_prepared[final_features].to_csv('test_selected_features.csv', index=False)

# Check if Surviving_Male really should be discarded
# Let's check SHAP again with the optimized set
X_opt = train_prepared[final_features]
rf_opt = RandomForestClassifier(n_estimators=100, random_state=42)
rf_opt.fit(X_opt, train_prepared['Survived'])
importances = pd.Series(rf_opt.feature_importances_, index=final_features).sort_values(ascending=False)
print("\nFeature Importances (Optimized Set):")
print(importances)