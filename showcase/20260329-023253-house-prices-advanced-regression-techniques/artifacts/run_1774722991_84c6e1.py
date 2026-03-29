import pandas as pd
import numpy as np
import os
from sklearn.linear_model import Lasso, Ridge, ElasticNet
from sklearn.model_selection import GridSearchCV, KFold, cross_val_predict
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import RobustScaler
from sklearn.pipeline import make_pipeline
import json

# Load data
train = pd.read_csv('/workspace/output/train_processed.csv')
X = train.drop(['SalePrice', 'Id'], axis=1)
y = train['SalePrice']

# Define 5-fold CV
kf = KFold(n_splits=5, shuffle=True, random_state=42)

def rmse(y_true, y_pred):
    return np.sqrt(mean_squared_error(y_true, y_pred))

# Results storage
results = {}
oof_preds = pd.DataFrame(index=train.index)
oof_preds['Id'] = train['Id']
best_models = {}

# 1. Ridge
ridge_param_grid = {'ridge__alpha': [0.1, 1, 5, 10, 15, 20, 30, 50]}
ridge_pipe = make_pipeline(RobustScaler(), Ridge())
ridge_grid = GridSearchCV(ridge_pipe, ridge_param_grid, cv=kf, scoring='neg_mean_squared_error', n_jobs=-1)
ridge_grid.fit(X, y)
best_ridge = ridge_grid.best_estimator_
results['Ridge'] = {
    'best_params': ridge_grid.best_params_,
    'best_rmse': np.sqrt(-ridge_grid.best_score_)
}
oof_preds['Ridge'] = cross_val_predict(best_ridge, X, y, cv=kf)

# 2. Lasso
lasso_param_grid = {'lasso__alpha': [0.0001, 0.0003, 0.0005, 0.0007, 0.001, 0.005]}
lasso_pipe = make_pipeline(RobustScaler(), Lasso(max_iter=10000))
lasso_grid = GridSearchCV(lasso_pipe, lasso_param_grid, cv=kf, scoring='neg_mean_squared_error', n_jobs=-1)
lasso_grid.fit(X, y)
best_lasso = lasso_grid.best_estimator_
results['Lasso'] = {
    'best_params': lasso_grid.best_params_,
    'best_rmse': np.sqrt(-lasso_grid.best_score_)
}
oof_preds['Lasso'] = cross_val_predict(best_lasso, X, y, cv=kf)

# 3. ElasticNet
enet_param_grid = {
    'elasticnet__alpha': [0.0001, 0.0003, 0.0005, 0.001],
    'elasticnet__l1_ratio': [0.5, 0.7, 0.9]
}
enet_pipe = make_pipeline(RobustScaler(), ElasticNet(max_iter=10000))
enet_grid = GridSearchCV(enet_pipe, enet_param_grid, cv=kf, scoring='neg_mean_squared_error', n_jobs=-1)
enet_grid.fit(X, y)
best_enet = enet_grid.best_estimator_
results['ElasticNet'] = {
    'best_params': enet_grid.best_params_,
    'best_rmse': np.sqrt(-enet_grid.best_score_)
}
oof_preds['ElasticNet'] = cross_val_predict(best_enet, X, y, cv=kf)

# Save OOF predictions
oof_preds.to_csv('/workspace/output/linear_models_oof.csv', index=False)

# Save hyperparameters and scores
with open('/workspace/output/linear_models_results.json', 'w') as f:
    json.dump(results, f, indent=4)

# Update best score
best_overall_rmse = min(results['Ridge']['best_rmse'], results['Lasso']['best_rmse'], results['ElasticNet']['best_rmse'])
best_model_name = [name for name, res in results.items() if res['best_rmse'] == best_overall_rmse][0]

score_data = {
    "metric": "RMSLE",
    "score": best_overall_rmse,
    "model": best_model_name,
    "details": f"5-fold CV, tuned {best_model_name}"
}

# Read existing score if exists
if os.path.exists('/workspace/output/best_score.json'):
    with open('/workspace/output/best_score.json', 'r') as f:
        existing_score = json.load(f)
    if score_data['score'] < existing_score['score']:
        with open('/workspace/output/best_score.json', 'w') as f:
            json.dump(score_data, f, indent=4)
else:
    with open('/workspace/output/best_score.json', 'w') as f:
        json.dump(score_data, f, indent=4)

print(f"Ridge Best RMSE: {results['Ridge']['best_rmse']}")
print(f"Lasso Best RMSE: {results['Lasso']['best_rmse']}")
print(f"ElasticNet Best RMSE: {results['ElasticNet']['best_rmse']}")