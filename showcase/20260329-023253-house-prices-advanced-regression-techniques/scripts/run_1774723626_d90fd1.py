import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge, Lasso, ElasticNet, LinearRegression
from sklearn.svm import SVR
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import KFold, cross_val_score
from scipy.optimize import minimize
import json

# Load OOF predictions
oof_df = pd.read_csv('all_models_oof.csv')
print("Available columns in OOF:", oof_df.columns.tolist())

# Load target
train_df = pd.read_csv('train_processed.csv')
y = train_df['SalePrice']

# Define the models to include in ensemble
# The names should match the columns in all_models_oof.csv
# Based on task 3_4 output: Lasso, Ridge, ElasticNet, RF, ET, XGB, LightGBM
# Let's check the exact names in oof_df
models = [col for col in oof_df.columns if col not in ['Id', 'SalePrice']]
print("Models for ensemble:", models)

X_ensemble = oof_df[models].values

# 1. Simple Average
simple_avg = X_ensemble.mean(axis=1)
score_simple = np.sqrt(mean_squared_error(y, simple_avg))
print(f"Simple Average RMSLE: {score_simple:.6f}")

# 2. Optimal Weighted Averaging
def loss_func(weights, X, y):
    # Constraint: sum of weights = 1
    normalized_weights = weights / np.sum(weights)
    pred = np.dot(X, normalized_weights)
    return np.sqrt(mean_squared_error(y, pred))

res = minimize(loss_func, x0=[1.0/len(models)]*len(models), args=(X_ensemble, y),
               bounds=[(0, 1)]*len(models))
best_weights = res.x / np.sum(res.x)
score_weighted = res.fun
print(f"Optimal Weighted Average RMSLE: {score_weighted:.6f}")
print("Best weights:", dict(zip(models, best_weights)))

# 3. Stacking (Meta-learner: Ridge)
kf = KFold(n_splits=10, shuffle=True, random_state=42)
meta_learner = Ridge(alpha=1.0)
scores_stacking = np.sqrt(-cross_val_score(meta_learner, X_ensemble, y, cv=kf, scoring='neg_mean_squared_error'))
print(f"Stacking (Ridge) RMSLE: {scores_stacking.mean():.6f} (+/- {scores_stacking.std():.6f})")

# 4. Stacking (Meta-learner: Lasso)
meta_learner_lasso = Lasso(alpha=0.0001)
scores_stacking_lasso = np.sqrt(-cross_val_score(meta_learner_lasso, X_ensemble, y, cv=kf, scoring='neg_mean_squared_error'))
print(f"Stacking (Lasso) RMSLE: {scores_stacking_lasso.mean():.6f}")

# Save results
ensemble_final_results = {
    "simple_avg_rmsle": score_simple,
    "weighted_avg_rmsle": score_weighted,
    "stacking_ridge_rmsle": scores_stacking.mean(),
    "best_weights": dict(zip(models, best_weights)),
    "best_meta_model": "Ridge" if scores_stacking.mean() < score_weighted else "Weighted Average"
}

with open('final_ensemble_results.json', 'w') as f:
    json.dump(ensemble_final_results, f, indent=4)

# Update best score
best_overall_score = min(score_weighted, scores_stacking.mean(), score_simple)
best_model_name = "Weighted Ensemble" if score_weighted < scores_stacking.mean() else "Stacking (Ridge)"

with open('best_score.json', 'r') as f:
    current_best = json.load(f)

if best_overall_score < current_best['score']:
    new_best = {
        "metric": "RMSLE",
        "score": best_overall_score,
        "model": best_model_name,
        "details": "Final Ensemble (Stacking or Weighted)"
    }
    with open('best_score.json', 'w') as f:
        json.dump(new_best, f, indent=4)
    print("Best score updated!")
else:
    print("Current best score is better than ensemble.")