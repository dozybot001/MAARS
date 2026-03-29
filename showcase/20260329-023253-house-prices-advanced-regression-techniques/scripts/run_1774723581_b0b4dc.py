import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error
from sklearn.linear_model import Ridge as RidgeMeta
from sklearn.model_selection import KFold
from scipy.optimize import minimize
import os
import json

# Define RMSLE function (RMSE on log scale)
def rmsle(y_true, y_pred):
    return np.sqrt(mean_squared_error(y_true, y_pred))

# 1. Load ground truth
train_df = pd.read_csv('/workspace/output/train_processed.csv')
y_true = train_df['SalePrice'].values
ids = train_df['Id'].values

# 2. Load OOF predictions
linear_oof = pd.read_csv('/workspace/output/linear_models_oof.csv').set_index('Id').loc[ids].reset_index()
rf_oof = pd.read_csv('/workspace/output/rf_oof_preds.csv').set_index('Id').loc[ids].reset_index()
et_oof = pd.read_csv('/workspace/output/et_oof_preds.csv').set_index('index' if 'index' in pd.read_csv('/workspace/output/et_oof_preds.csv').columns else 'Id').loc[ids].reset_index()

# Wait, check et_oof columns again just in case. 
# Re-reading because I noticed some potential index issues in my thought.
et_temp = pd.read_csv('/workspace/output/et_oof_preds.csv')
rf_temp = pd.read_csv('/workspace/output/rf_oof_preds.csv')

xgb_oof = np.load('/workspace/output/xgboost_oof.npy')
lgbm_oof = np.load('/workspace/output/lightgbm_oof.npy')

oof_df = pd.DataFrame({
    'Id': ids,
    'Lasso': linear_oof['Lasso'],
    'Ridge': linear_oof['Ridge'],
    'ElasticNet': linear_oof['ElasticNet'],
    'RF': rf_temp.set_index('Id').loc[ids]['rf_oof'].values,
    'ET': et_temp.set_index('Id').loc[ids]['et_oof'].values,
    'XGB': xgb_oof,
    'LGBM': lgbm_oof
})

# 3. Individual Scores
models = ['Lasso', 'Ridge', 'ElasticNet', 'RF', 'ET', 'XGB', 'LGBM']
scores = {}
for m in models:
    score = rmsle(y_true, oof_df[m])
    scores[m] = score
    print(f"{m} RMSLE: {score:.6f}")

# 4. Optimal Weighted Average
def loss_func(weights, oof_preds, y_true):
    final_pred = np.tensordot(weights, oof_preds, axes=((0), (0)))
    return rmsle(y_true, final_pred)

oof_preds_matrix = oof_df[models].values.T
starting_values = [1.0 / len(models)] * len(models)
cons = ({'type': 'eq', 'fun': lambda w: 1 - sum(w)})
bounds = [(0, 1)] * len(models)

res = minimize(loss_func, starting_values, args=(oof_preds_matrix, y_true), 
               method='SLSQP', bounds=bounds, constraints=cons)

best_weights = res.x
best_weighted_score = res.fun
print(f"\nBest Weights: {dict(zip(models, best_weights))}")
print(f"Best Weighted RMSLE: {best_weighted_score:.6f}")

# 5. Stacking (Ridge Meta-model)
kf = KFold(n_splits=5, shuffle=True, random_state=42)
stack_oof = np.zeros(len(y_true))
X_stack = oof_df[models].values

for train_idx, val_idx in kf.split(X_stack):
    meta_model = RidgeMeta(alpha=1.0)
    meta_model.fit(X_stack[train_idx], y_true[train_idx])
    stack_oof[val_idx] = meta_model.predict(X_stack[val_idx])

stack_score = rmsle(y_true, stack_oof)
print(f"Stacking (Ridge) RMSLE: {stack_score:.6f}")

# 6. Save results
ensemble_results = {
    'individual_scores': scores,
    'best_weights': dict(zip(models, best_weights.tolist())),
    'best_weighted_score': best_weighted_score,
    'stacking_ridge_score': stack_score,
    'simple_average_score': rmsle(y_true, oof_df[models].mean(axis=1))
}

with open('/workspace/output/ensemble_results.json', 'w') as f:
    json.dump(ensemble_results, f, indent=4)

# Choose the best ensemble method
best_final_score = min(best_weighted_score, stack_score)
best_method = "Weighted Ensemble" if best_weighted_score <= stack_score else "Stacking (Ridge)"

# Update best_score.json
with open('/workspace/output/best_score.json', 'r') as f:
    best_score_data = json.load(f)

if best_final_score < best_score_data['score']:
    best_score_data = {
        "metric": "RMSLE",
        "score": float(best_final_score),
        "model": best_method,
        "details": f"Best ensemble among individual models: {', '.join(models)}"
    }
    with open('/workspace/output/best_score.json', 'w') as f:
        json.dump(best_score_data, f, indent=4)
    print(f"\nUpdated best_score.json with {best_method} score: {best_final_score:.6f}")

oof_df.to_csv('/workspace/output/all_models_oof.csv', index=False)