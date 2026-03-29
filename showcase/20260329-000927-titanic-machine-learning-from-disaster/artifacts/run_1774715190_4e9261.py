import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder

train_df = pd.read_csv('train_wcg_features.csv')

def get_X_y(df, features):
    df = df.copy()
    df['Deck'] = df['Cabin'].apply(lambda x: x[0] if pd.notnull(x) else 'U')
    df['Sex_Pclass'] = df['Sex'].astype(str) + "_" + df['Pclass'].astype(str)
    df['Age'] = df['Age'].fillna(df['Age'].median())
    df['Embarked'] = df['Embarked'].fillna(df['Embarked'].mode()[0])
    
    X = df[features].copy()
    for col in X.columns:
        if X[col].dtype == 'object':
            X[col] = LabelEncoder().fit_transform(X[col])
    return X, df['Survived']

all_features = [
    'Pclass', 'Sex', 'Age', 'SibSp', 'Parch', 'Fare', 'Embarked', 
    'IsWCG', 'IsAdultMale', 'Ticket_Group_Count', 'WCG_Survival_Group', 
    'Surviving_Male', 'Dead_Woman', 'Deck', 'Sex_Pclass'
]

# Experiments
sets = {
    'Full': all_features,
    'Selected_1': [
        'Pclass', 'Age', 'SibSp', 'Fare', 'Embarked', 
        'IsAdultMale', 'Ticket_Group_Count', 'WCG_Survival_Group', 
        'Dead_Woman', 'Deck', 'Sex_Pclass'
    ],
    'Selected_2 (Drop lowest SHAP)': [
        'Pclass', 'Sex', 'Age', 'SibSp', 'Fare', 'Embarked', 
        'IsWCG', 'IsAdultMale', 'Ticket_Group_Count', 'WCG_Survival_Group', 
        'Dead_Woman', 'Deck', 'Sex_Pclass'
    ]
}

results = {}
for name, f_list in sets.items():
    X, y = get_X_y(train_df, f_list)
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    scores = cross_val_score(rf, X, y, cv=5)
    results[name] = scores.mean()

print("Cross-Validation Results:")
for name, score in results.items():
    print(f"{name}: {score:.4f}")

# Final decision: 
# Features to keep
final_features = sets['Selected_1']
print(f"\nFinal Selected Features: {final_features}")

# Generate and save the final cleaned data
X_final, y_final = get_X_y(train_df, final_features)
train_final = X_final.copy()
train_final['Survived'] = y_final
train_final.to_csv('train_selected_features.csv', index=False)

# Prepare test set similarly
test_df = pd.read_csv('test_wcg_features.csv')
test_df['Deck'] = test_df['Cabin'].apply(lambda x: x[0] if pd.notnull(x) else 'U')
test_df['Sex_Pclass'] = test_df['Sex'].astype(str) + "_" + test_df['Pclass'].astype(str)
test_df['Age'] = test_df['Age'].fillna(test_df['Age'].median()) # Note: usually test should use train median
# Use train median for test
train_age_median = train_df['Age'].median()
test_df['Age'] = test_df['Age'].fillna(train_age_median)
test_df['Embarked'] = test_df['Embarked'].fillna(train_df['Embarked'].mode()[0])

X_test_final = test_df[final_features].copy()
for col in X_test_final.columns:
    if X_test_final[col].dtype == 'object':
        le = LabelEncoder()
        # Fit on train + test to handle potentially unseen categories if any (though unlikely here)
        le.fit(pd.concat([train_df[col].astype(str).fillna('U'), test_df[col].astype(str).fillna('U')]))
        X_test_final[col] = le.transform(X_test_final[col].astype(str).fillna('U'))

X_test_final.to_csv('test_selected_features.csv', index=False)