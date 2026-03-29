import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier, VotingClassifier
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
import json

# 1. Load data
train = pd.read_csv('train_advanced_features.csv')
test = pd.read_csv('test_advanced_features.csv')

# 2. Features selection
features = ['Pclass', 'Sex', 'Age', 'SibSp', 'Parch', 'Fare', 'Embarked', 'Group_Survival', 'Deck', 'Sex_Pclass']
X = train[features].copy()
y = train['Survived'].astype(int)
X_test = test[features].copy()

# 3. Handle missing values
# Age: Fill with median from train
age_median = X['Age'].median()
X['Age'] = X['Age'].fillna(age_median)
X_test['Age'] = X_test['Age'].fillna(age_median)

# Fare: Fill with median from train (especially for test set)
fare_median = X['Fare'].median()
X['Fare'] = X['Fare'].fillna(fare_median)
X_test['Fare'] = X_test['Fare'].fillna(fare_median)

# Embarked: Fill with mode
embarked_mode = X['Embarked'].mode()[0]
X['Embarked'] = X['Embarked'].fillna(embarked_mode)
X_test['Embarked'] = X_test['Embarked'].fillna(embarked_mode)

# 4. Encoding categorical variables
categorical_cols = ['Sex', 'Embarked', 'Deck', 'Sex_Pclass']
le = LabelEncoder()
for col in categorical_cols:
    # Ensure all labels in test are also in train (handle new labels in test)
    # Map unknown labels in test to the most frequent label in train
    X[col] = X[col].astype(str)
    X_test[col] = X_test[col].astype(str)
    
    le.fit(X[col])
    X[col] = le.transform(X[col])
    
    # Check for labels in test not in train
    test_labels = set(X_test[col].unique())
    train_labels = set(le.classes_)
    diff = test_labels - train_labels
    if diff:
        print(f"Warning: labels {diff} in test column {col} not in train. Mapping to mode.")
        X_test[col] = X_test[col].map(lambda x: x if x in train_labels else le.classes_[0])
    
    X_test[col] = le.transform(X_test[col])

# 5. Load best parameters
with open('best_model_params.json', 'r') as f:
    best_params = json.load(f)

# 6. Initialize models
rf = RandomForestClassifier(**best_params['RandomForest'], random_state=42)
xgb = XGBClassifier(**best_params['XGBoost'], random_state=42, use_label_encoder=False, eval_metric='logloss')
hgb = HistGradientBoostingClassifier(**best_params['HistGradientBoosting'], random_state=42)

# 7. Create Voting Classifier
voting_clf = VotingClassifier(
    estimators=[
        ('rf', rf),
        ('xgb', xgb),
        ('hgb', hgb)
    ],
    voting='soft',
    weights=[1, 1, 1.1] # Slightly more weight to HGB as it performed best
)

# 8. Fit and Predict
voting_clf.fit(X, y)
predictions = voting_clf.predict(X_test)

# 9. Create submission file
submission = pd.DataFrame({
    'PassengerId': test['PassengerId'],
    'Survived': predictions
})

submission.to_csv('submission.csv', index=False)
import os
os.makedirs('/workspace/output', exist_ok=True)
submission.to_csv('/workspace/output/submission.csv', index=False)

print("Final predictions shape:", predictions.shape)
print("Submission saved to /workspace/output/submission.csv")
print("Top 5 predictions:\n", submission.head())