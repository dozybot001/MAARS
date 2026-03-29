import pandas as pd
import numpy as np
import xgboost as xgb
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
        'objective': 'reg:squarederror',
        'eval_metric': 'rmse',
        'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.1, log=True),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 20),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.4, 1.0),
        'gamma': trial.suggest_float('gamma', 1e-8, 1.0, log=True),
        'alpha': trial.suggest_float('alpha', 1e-8, 10.0, log=True),
        'lambda': trial.suggest_float('lambda', 1e-8, 10.0, log=True),
        'n_estimators': 2000,
        'random_state': 42,
        'early_stopping_rounds': 50
    }
    
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    scores = []
    
    for train_idx, val_idx in kf.split(X):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        
        model = xgb.XGBRegressor(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        # Best iteration is automatically used in predict if early_stopping was triggered
        preds = model.predict(X_val)
        rmse = np.sqrt(mean_squared_error(y_val, preds))
        scores.append(rmse)
        
    return np.mean(scores)

# 3. Run Optimization
study = optuna.create_study(direction='minimize')
study.optimize(objective, n_trials=30)

print(f"Best RMSE (RMSLE): {study.best_value}")

# 4. Final OOF Evaluation
best_params = study.best_params
best_params.update({
    'objective': 'reg:squarederror',
    'eval_metric': 'rmse',
    'n_estimators': 5000,
    'random_state': 42,
    'early_stopping_rounds': 100
})

kf = KFold(n_splits=5, shuffle=True, random_state=42)
oof_preds = np.zeros(len(X))
cv_scores = []

for train_idx, val_idx in kf.split(X):
    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]
    
    model = xgb.XGBRegressor(**best_params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
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
    'cv_scores': cv_scores,
    'replacement_model': 'XGBoost',
    'note': 'LightGBM was replaced by XGBoost due to libgomp.so.1 being missing in the system environment.'
}

with open('/workspace/output/lightgbm_results.json', 'w') as f:
    json.dump(results, f, indent=4)

np.save('/workspace/output/lightgbm_oof.npy', oof_preds)

best_score_path = '/workspace/output/best_score.json'
new_score = {"metric": "RMSLE", "score": final_rmsle, "model": "XGBoost", "details": "5-fold CV tuned with Optuna (substituted for LightGBM)"}

if os.path.exists(best_score_path):
    with open(best_score_path, 'r') as f:
        current_best = json.load(f)
    if final_rmsle < current_best.get('score', float('inf')):
        with open(best_score_path, 'w') as f:
            json.dump(new_score, f, indent=4)
else:
    with open(best_score_path, 'w') as f:
        json.dump(new_score, f, indent=4)