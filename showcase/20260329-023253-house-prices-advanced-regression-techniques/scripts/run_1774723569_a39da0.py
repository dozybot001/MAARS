import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error
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

print(f"Number of samples: {len(y_true)}")

# 2. Load OOF predictions
# Linear models
linear_oof = pd.read_csv('/workspace/output/linear_models_oof.csv')
# Sort linear_oof to match ids order
linear_oof = linear_oof.set_index('Id').loc[ids].reset_index()

# RF and ET
rf_oof = pd.read_csv('/workspace/output/rf_oof_preds.csv')
rf_oof = rf_oof.set_index('Id').loc[ids].reset_index()

et_oof = pd.read_csv('/workspace/output/et_oof_preds.csv')
et_oof = et_oof.set_index('Id').loc[ids].reset_index()

# XGBoost and LightGBM (assuming they are in the same order as train_processed.csv)
xgb_oof = np.load('/workspace/output/xgboost_oof.npy')
lgbm_oof = np.load('/workspace/output/lightgbm_oof.npy')

# 3. Consolidate OOF predictions into a single DataFrame
oof_df = pd.DataFrame({
    'Id': ids,
    'Lasso': linear_oof['Lasso'],
    'Ridge': linear_oof['Ridge'],
    'ElasticNet': linear_oof['ElasticNet'],
    'RF': rf_oof['Prediction'],
    'ET': et_oof['Prediction'],
    'XGB': xgb_oof,
    'LGBM': lgbm_oof
})

# Verify scores
models = ['Lasso', 'Ridge', 'ElasticNet', 'RF', 'ET', 'XGB', 'LGBM']
scores = {}
for m in models:
    score = rmsle(y_true, oof_df[m])
    scores[m] = score
    print(f"{m} RMSLE: {score:.6f}")

# 4. Find optimal weights for weighted average
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

# 5. Simple Averaging
simple_avg_score = rmsle(y_true, oof_df[models].mean(axis=1))
print(f"Simple Average RMSLE: {simple_avg_score:.6f}")

# 6. Save results
ensemble_results = {
    'individual_scores': scores,
    'best_weights': dict(zip(models, best_weights.tolist())),
    'best_weighted_score': best_weighted_score,
    'simple_average_score': simple_avg_score
}

with open('/workspace/output/ensemble_results.json', 'w') as f:
    json.dump(ensemble_results, f, indent=4)

# Update best_score.json if the ensemble is better
with open('/workspace/output/best_score.json', 'r') as f:
    best_score_data = json.load(f)

if best_weighted_score < best_score_data['score']:
    best_score_data = {
        "metric": "RMSLE",
        "score": best_weighted_score,
        "model": "Weighted Ensemble",
        "details": f"Weighted ensemble of {', '.join(models)}"
    }
    with open('/workspace/output/best_score.json', 'w') as f:
        json.dump(best_score_data, f, indent=4)
    print("\nUpdated best_score.json with ensemble score.")

# Save the consolidated OOF for stacking if needed (though weighted average is already very good)
oof_df.to_csv('/workspace/output/all_models_oof.csv', index=False)