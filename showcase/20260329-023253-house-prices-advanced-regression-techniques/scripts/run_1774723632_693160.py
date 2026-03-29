from sklearn.svm import SVR
from sklearn.model_selection import GridSearchCV

# Meta-learner: SVR
param_grid = {'C': [0.1, 1, 10], 'epsilon': [0.001, 0.01, 0.1], 'gamma': ['scale', 'auto']}
svr = SVR()
grid_svr = GridSearchCV(svr, param_grid, cv=5, scoring='neg_mean_squared_error')
grid_svr.fit(X_ensemble, y)
print(f"Best SVR Params: {grid_svr.best_params_}")
score_svr = np.sqrt(-grid_svr.best_score_)
print(f"Stacking (SVR) RMSLE: {score_svr:.6f}")

# Final selection
results = {
    "Weighted Average": 0.108987,
    "Stacking (Lasso)": 0.108528,
    "Stacking (SVR)": score_svr
}
best_ensemble_method = min(results, key=results.get)
print(f"Best Ensemble Method: {best_ensemble_method} with score {results[best_ensemble_method]:.6f}")

# Update best score if needed
with open('best_score.json', 'r') as f:
    current_best = json.load(f)

if results[best_ensemble_method] < current_best['score']:
    new_best = {
        "metric": "RMSLE",
        "score": results[best_ensemble_method],
        "model": best_ensemble_method,
        "details": f"Final Ensemble via {best_ensemble_method}"
    }
    with open('best_score.json', 'w') as f:
        json.dump(new_best, f, indent=4)