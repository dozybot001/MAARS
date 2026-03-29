import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier, StackingClassifier
from xgboost import XGBClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, StratifiedKFold
import json

# 1. Load data
train_df = pd.read_csv('train_selected_features.csv')
test_df = pd.read_csv('test_selected_features.csv')

X_train = train_df.drop('Survived', axis=1)
y_train = train_df['Survived']
X_test = test_df

# 2. Load hyperparameters
with open('best_model_params.json', 'r') as f:
    best_params = json.load(f)

# 3. Define base models
rf = RandomForestClassifier(**best_params['RandomForest'], random_state=42)
xgb = XGBClassifier(**best_params['XGBoost'], random_state=42, use_label_encoder=False, eval_metric='logloss')
hgb = HistGradientBoostingClassifier(**best_params['HistGradientBoosting'], random_state=42)

base_models = [
    ('rf', rf),
    ('xgb', xgb),
    ('hgb', hgb)
]

# 4. Define meta-learner
meta_learner = LogisticRegression(penalty='l2', solver='lbfgs', random_state=42)

# 5. Build Stacking model
stacking_clf = StackingClassifier(
    estimators=base_models,
    final_estimator=meta_learner,
    cv=5,
    stack_method='predict_proba', # Using probabilities for meta-learner features
    n_jobs=-1
)

# 6. Evaluate Stacking model using 5-fold CV
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(stacking_clf, X_train, y_train, cv=skf, scoring='accuracy')

print(f"Stacking CV Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

# 7. Train on full training set
stacking_clf.fit(X_train, y_train)

# 8. Generate OOF predictions and meta-features (optional but good for report)
# StackingClassifier internal OOF is used during fit.
# We can extract the final coefficients of the meta-learner to see importance
meta_coefs = stacking_clf.final_estimator_.coef_
print("Meta-learner coefficients (RF, XGB, HGB):", meta_coefs)

# 9. Predict on test set
test_preds = stacking_clf.predict(X_test).astype(int)

# 10. Save submission
submission = pd.read_csv('/workspace/data/test.csv')[['PassengerId']]
submission['Survived'] = test_preds
submission.to_csv('stacking_submission.csv', index=False)
print("Submission saved to stacking_submission.csv")

# Save results for report
results = {
    "cv_mean": cv_scores.mean(),
    "cv_std": cv_scores.std(),
    "meta_coefs": meta_coefs.tolist()[0]
}
with open('stacking_results.json', 'w') as f:
    json.dump(results, f)