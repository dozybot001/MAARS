import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.model_selection import KFold, RandomizedSearchCV, cross_val_predict
from sklearn.metrics import mean_squared_error
import json
import joblib
import os

# Load data
train = pd.read_csv('/workspace/output/train_processed.csv')
X = train.drop(['SalePrice', 'Id'], axis=1)
y = train['SalePrice']

kf = KFold(n_splits=5, shuffle=True, random_state=42)

def rmse(y_true, y_pred):
    return np.sqrt(mean_squared_error(y_true, y_pred))

# Tuning Random Forest
print("Tuning Random Forest...")
rf = RandomForestRegressor(random_state=42)
rf_param_grid = {
    'n_estimators': [100, 300, 500],
    'max_features': ['sqrt', 'log2', 0.3, 0.5],
    'max_depth': [None, 10, 20, 30],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4]
}
rf_search = RandomizedSearchCV(rf, rf_param_grid, n_iter=20, cv=kf, scoring='neg_mean_squared_error', n_jobs=-1, random_state=42)
rf_search.fit(X, y)
rf_best = rf_search.best_estimator_
rf_best_params = rf_search.best_params_

# Tuning Extra Trees
print("Tuning Extra Trees...")
et = ExtraTreesRegressor(random_state=42)
et_param_grid = {
    'n_estimators': [100, 300, 500],
    'max_features': ['sqrt', 'log2', 0.3, 0.5],
    'max_depth': [None, 10, 20, 30],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4]
}
et_search = RandomizedSearchCV(et, et_param_grid, n_iter=20, cv=kf, scoring='neg_mean_squared_error', n_jobs=-1, random_state=42)
et_search.fit(X, y)
et_best = et_search.best_estimator_
et_best_params = et_search.best_params_

# OOF predictions
print("Generating OOF predictions...")
rf_oof = cross_val_predict(rf_best, X, y, cv=kf)
et_oof = cross_val_predict(et_best, X, y, cv=kf)

rf_rmse = rmse(y, rf_oof)
et_rmse = rmse(y, et_oof)

print(f"RF RMSLE: {rf_rmse}")
print(f"ET RMSLE: {et_rmse}")

# Save results
with open('/workspace/output/rf_best_params.json', 'w') as f:
    json.dump(rf_best_params, f)
with open('/workspace/output/et_best_params.json', 'w') as f:
    json.dump(et_best_params, f)

pd.DataFrame({'Id': train['Id'], 'rf_oof': rf_oof}).to_csv('/workspace/output/rf_oof_preds.csv', index=False)
pd.DataFrame({'Id': train['Id'], 'et_oof': et_oof}).to_csv('/workspace/output/et_oof_preds.csv', index=False)

# Update best score
results = {
    "RF": rf_rmse,
    "ET": et_rmse
}
best_model = min(results, key=results.get)
best_score = results[best_model]

score_file = '/workspace/output/best_score.json'
if os.path.exists(score_file):
    with open(score_file, 'r') as f:
        current_best = json.load(f)
    if best_score < current_best['score']:
        new_best = {"metric": "RMSLE", "score": best_score, "model": best_model, "details": "5-fold CV on processed features"}
    else:
        new_best = current_best
else:
    new_best = {"metric": "RMSLE", "score": best_score, "model": best_model, "details": "5-fold CV on processed features"}

with open(score_file, 'w') as f:
    json.dump(new_best, f)

# Also train on full and save models
joblib.dump(rf_best, '/workspace/output/rf_model.joblib')
joblib.dump(et_best, '/workspace/output/et_model.joblib')

print("Task 3_2 complete.")