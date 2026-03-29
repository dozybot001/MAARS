import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import KFold, cross_val_score
from sklearn.metrics import mean_squared_error
import optuna
import json
import os

# Load data
train_df = pd.read_csv('/workspace/output/train_processed.csv')
y = train_df['SalePrice'].values
X = train_df.drop(['Id', 'SalePrice'], axis=1)

def objective(trial):
    param = {
        'verbosity': 0,
        'objective': 'reg:squarederror',
        'n_estimators': 3000,
        'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.1, log=True),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'gamma': trial.suggest_float('gamma', 0, 0.5),
        'reg_alpha': trial.suggest_float('reg_alpha', 0, 10),
        'reg_lambda': trial.suggest_float('reg_lambda', 0, 10),
        'random_state': 42,
        'tree_method': 'hist', # Faster
    }

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    scores = []
    
    for train_index, val_index in kf.split(X):
        X_train, X_val = X.iloc[train_index], X.iloc[val_index]
        y_train, y_val = y[train_index], y[val_index]
        
        model = xgb.XGBRegressor(**param)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=50,
            verbose=False
        )
        
        preds = model.predict(X_val)
        rmse = np.sqrt(mean_squared_error(y_val, preds))
        scores.append(rmse)
        
    return np.mean(scores)

# Optimize
study = optuna.create_study(direction='minimize')
study.optimize(objective, n_trials=50)

print(f"Best RMSE: {study.best_value}")
print(f"Best Params: {study.best_params}")

# Final training with best params to get OOF
best_params = study.best_params
best_params['objective'] = 'reg:squarederror'
best_params['n_estimators'] = 3000
best_params['tree_method'] = 'hist'
best_params['random_state'] = 42

kf = KFold(n_splits=5, shuffle=True, random_state=42)
oof_preds = np.zeros(len(X))
cv_scores = []

for train_index, val_index in kf.split(X):
    X_train, X_val = X.iloc[train_index], X.iloc[val_index]
    y_train, y_val = y[train_index], y[val_index]
    
    model = xgb.XGBRegressor(**best_params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        early_stopping_rounds=50,
        verbose=False
    )
    
    preds = model.predict(X_val)
    oof_preds[val_index] = preds
    rmse = np.sqrt(mean_squared_error(y_val, preds))
    cv_scores.append(rmse)

final_rmsle = np.mean(cv_scores)
print(f"Final OOF RMSLE: {final_rmsle}")

# Save results
results = {
    'best_params': best_params,
    'rmsle': final_rmsle,
    'cv_scores': cv_scores
}
with open('/workspace/output/xgboost_results.json', 'w') as f:
    json.dump(results, f, indent=4)

np.save('/workspace/output/xgboost_oof.npy', oof_preds)

# Save best score
best_score_path = '/workspace/output/best_score.json'
score_data = {"metric": "RMSLE", "score": final_rmsle, "model": "XGBoost", "details": "5-fold CV with Optuna tuning"}

if os.path.exists(best_score_path):
    with open(best_score_path, 'r') as f:
        current_best = json.load(f)
    if final_rmsle < current_best['score']:
        with open(best_score_path, 'w') as f:
            json.dump(score_data, f, indent=4)
else:
    with open(best_score_path, 'w') as f:
        json.dump(score_data, f, indent=4)

print("XGBoost training and tuning completed.")