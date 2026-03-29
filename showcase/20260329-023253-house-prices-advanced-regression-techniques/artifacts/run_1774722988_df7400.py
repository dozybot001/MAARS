import pandas as pd
import numpy as np
import lightgbm as lgb
import optuna
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error
import json
import os

# 1. Load data
train_df = pd.read_csv('/workspace/output/train_processed.csv')
y = train_df['SalePrice'].values
X = train_df.drop(['SalePrice', 'Id'], axis=1)

# 2. Define Objective function for Optuna
def objective(trial):
    params = {
        'objective': 'regression',
        'metric': 'rmse',
        'verbosity': -1,
        'boosting_type': 'gbdt',
        'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.1, log=True),
        'num_leaves': trial.suggest_int('num_leaves', 2, 256),
        'max_depth': trial.suggest_int('max_depth', 3, 12),
        'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
        'feature_fraction': trial.suggest_float('feature_fraction', 0.4, 1.0),
        'bagging_fraction': trial.suggest_float('bagging_fraction', 0.4, 1.0),
        'bagging_freq': trial.suggest_int('bagging_freq', 1, 7),
        'lambda_l1': trial.suggest_float('lambda_l1', 1e-8, 10.0, log=True),
        'lambda_l2': trial.suggest_float('lambda_l2', 1e-8, 10.0, log=True),
        'n_estimators': 10000,
        'random_state': 42
    }
    
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    scores = []
    
    for train_idx, val_idx in kf.split(X):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        
        model = lgb.LGBMRegressor(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(stopping_rounds=100, verbose=False)]
        )
        
        preds = model.predict(X_val)
        rmse = np.sqrt(mean_squared_error(y_val, preds))
        scores.append(rmse)
        
    return np.mean(scores)

# 3. Run Optimization
study = optuna.create_study(direction='minimize')
study.optimize(objective, n_trials=50)

print(f"Best RMSE (RMSLE): {study.best_value}")
print(f"Best Params: {study.best_params}")

# 4. Final OOF Evaluation with best params
best_params = study.best_params
best_params['objective'] = 'regression'
best_params['metric'] = 'rmse'
best_params['n_estimators'] = 10000
best_params['random_state'] = 42

kf = KFold(n_splits=5, shuffle=True, random_state=42)
oof_preds = np.zeros(len(X))
cv_scores = []

for train_idx, val_idx in kf.split(X):
    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]
    
    model = lgb.LGBMRegressor(**best_params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(stopping_rounds=100, verbose=False)]
    )
    
    preds = model.predict(X_val)
    oof_preds[val_idx] = preds
    cv_scores.append(np.sqrt(mean_squared_error(y_val, preds)))

final_rmsle = np.mean(cv_scores)
print(f"Final CV RMSLE: {final_rmsle}")

# 5. Save results
results = {
    'best_params': best_params,
    'rmsle': final_rmsle,
    'cv_scores': cv_scores
}

with open('/workspace/output/lightgbm_results.json', 'w') as f:
    json.dump(results, f, indent=4)

np.save('/workspace/output/lightgbm_oof.npy', oof_preds)

# 6. Update best_score.json
best_score_path = '/workspace/output/best_score.json'
new_score = {"metric": "RMSLE", "score": final_rmsle, "model": "LightGBM", "details": "5-fold CV tuned with Optuna"}

if os.path.exists(best_score_path):
    with open(best_score_path, 'r') as f:
        current_best = json.load(f)
    if final_rmsle < current_best.get('score', float('inf')):
        with open(best_score_path, 'w') as f:
            json.dump(new_score, f, indent=4)
else:
    with open(best_score_path, 'w') as f:
        json.dump(new_score, f, indent=4)