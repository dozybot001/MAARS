import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge, Lasso
from sklearn.svm import SVR
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import KFold, GridSearchCV
import json

# Load OOF predictions
oof_df = pd.read_csv('all_models_oof.csv')
models = [col for col in oof_df.columns if col not in ['Id', 'SalePrice']]
X_ensemble = oof_df[models].values

# Load target
train_df = pd.read_csv('train_processed.csv')
y = train_df['SalePrice']

# 1. Stacking (Meta-learner: SVR)
param_grid = {'C': [0.1, 1, 10, 20], 'epsilon': [0.0001, 0.001, 0.01, 0.1], 'gamma': ['scale']}
svr = SVR()
grid_svr = GridSearchCV(svr, param_grid, cv=10, scoring='neg_mean_squared_error', n_jobs=-1)
grid_svr.fit(X_ensemble, y)
score_svr = np.sqrt(-grid_svr.best_score_)
print(f"Stacking (SVR) RMSLE: {score_svr:.6f} with best params: {grid_svr.best_params_}")

# Final comparison
results = {
    "Weighted Average": 0.108987,
    "Stacking (Lasso)": 0.108528,
    "Stacking (Ridge)": 0.108560,
    "Stacking (SVR)": score_svr
}
best_ensemble_method = min(results, key=results.get)
print(f"Best Ensemble Method: {best_ensemble_method} with score {results[best_ensemble_method]:.6f}")

# Update best score and save the results
final_ensemble_data = {
    "best_method": best_ensemble_method,
    "best_score": results[best_ensemble_method],
    "all_methods_results": results,
    "best_svr_params": grid_svr.best_params_
}
with open('final_ensemble_details.json', 'w') as f:
    json.dump(final_ensemble_data, f, indent=4)

# Load existing best score
with open('best_score.json', 'r') as f:
    current_best = json.load(f)

if results[best_ensemble_method] < current_best['score']:
    new_best = {
        "metric": "RMSLE",
        "score": results[best_ensemble_method],
        "model": best_ensemble_method,
        "details": "Optimized Stacking ensemble"
    }
    with open('best_score.json', 'w') as f:
        json.dump(new_best, f, indent=4)
    print("best_score.json updated.")
else:
    print("Current best is still better.")