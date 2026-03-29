import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error
import optuna
import json
import os

# Load data
train_df = pd.read_csv('/workspace/output/train_processed.csv')
X = train_df.drop(['SalePrice', 'Id'], axis=1)
y = train_df['SalePrice']

def objective(trial):
    params = {
        'verbosity': 0,
        'tree_method': 'hist',
        'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.1, log=True),
        'n_estimators': trial.suggest_int('n_estimators', 500, 3000),
        'max_depth': trial.suggest_int('max_depth', 3, 12),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'subsample': trial.suggest_float('subsample', 0.4, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.4, 1.0),
        'alpha': trial.suggest_float('alpha', 1e-8, 10.0, log=True),
        'lambda': trial.suggest_float('lambda', 1e-8, 10.0, log=True),
        'random_state': 42
    }
    
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    rmses = []
    
    for train_index, val_index in kf.split(X):
        X_train, X_val = X.iloc[train_index], X.iloc[val_index]
        y_train, y_val = y.iloc[train_index], y.iloc[val_index]
        
        model = xgb.XGBRegressor(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        
        preds = model.predict(X_val)
        rmse = np.sqrt(mean_squared_error(y_val, preds))
        rmses.append(rmse)
        
    return np.mean(rmses)

# Hyperparameter optimization
study = optuna.create_study(direction='minimize')
study.optimize(objective, n_trials=30)

best_params = study.best_params
print(f"Best params: {best_params}")
print(f"Best RMSE: {study.best_value}")

# Final 5-fold CV with best params to get OOF predictions
kf = KFold(n_splits=5, shuffle=True, random_state=42)
oof_preds = np.zeros(len(X))
cv_rmses = []

for train_index, val_index in kf.split(X):
    X_train, X_val = X.iloc[train_index], X.iloc[val_index]
    y_train, y_val = y.iloc[train_index], y.iloc[val_index]
    
    model = xgb.XGBRegressor(**best_params, tree_method='hist', random_state=42)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    
    preds = model.predict(X_val)
    oof_preds[val_index] = preds
    cv_rmses.append(np.sqrt(mean_squared_error(y_val, preds)))

mean_rmse = np.mean(cv_rmses)
print(f"Mean OOF RMSE: {mean_rmse}")

# Save results
results = {
    'best_params': best_params,
    'mean_rmsle': mean_rmse,
    'cv_scores': cv_rmses,
    'note': 'Used XGBoost with tree_method=hist as a substitute for LightGBM due to environment issues (missing libgomp.so.1)'
}

with open('/workspace/output/lightgbm_results.json', 'w') as f:
    json.dump(results, f, indent=4)

np.save('/workspace/output/lightgbm_oof.npy', oof_preds)

# Update best score
best_score_path = '/workspace/output/best_score.json'
current_best = 999.0
if os.path.exists(best_score_path):
    with open(best_score_path, 'r') as f:
        data = json.load(f)
        current_best = data.get('score', 999.0)

if mean_rmse < current_best:
    with open(best_score_path, 'w') as f:
        json.dump({"metric": "rmsle", "score": mean_rmse, "model": "XGBoost (LightGBM-sub)", "details": "5-fold CV with Optuna tuning"}, f)
    print(f"Updated best score to {mean_rmse}")