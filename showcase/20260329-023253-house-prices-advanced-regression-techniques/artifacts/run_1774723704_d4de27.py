import pandas as pd
import numpy as np
from sklearn.linear_model import Lasso, Ridge, ElasticNet
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.preprocessing import RobustScaler
from sklearn.pipeline import make_pipeline
import xgboost as xgb
import joblib

# Load processed data
train = pd.read_csv('/workspace/output/train_processed.csv')
test = pd.read_csv('/workspace/output/test_processed.csv')
oof_df = pd.read_csv('/workspace/output/all_models_oof.csv')

X_train = train.drop(['Id', 'SalePrice'], axis=1)
y_train = train['SalePrice']
X_test = test.drop(['Id'], axis=1)
test_ids = test['Id']

# Define models with best parameters
lasso = make_pipeline(RobustScaler(), Lasso(alpha=0.0005, random_state=42))
ridge = make_pipeline(RobustScaler(), Ridge(alpha=15, random_state=42))
enet = make_pipeline(RobustScaler(), ElasticNet(alpha=0.0005, l1_ratio=0.9, random_state=42))

rf = RandomForestRegressor(n_estimators=300, max_features=0.3, max_depth=30, 
                             min_samples_split=2, min_samples_leaf=1, random_state=42, n_jobs=-1)

et = ExtraTreesRegressor(n_estimators=300, max_features=0.5, max_depth=30, 
                           min_samples_split=5, min_samples_leaf=1, random_state=42, n_jobs=-1)

# XGBoost Params from xgboost_results.json
xgb_params = {
    'learning_rate': 0.012324006325284798,
    'max_depth': 10,
    'min_child_weight': 7,
    'subsample': 0.60140531466742,
    'colsample_bytree': 0.7254476727978763,
    'gamma': 0.050306661002420205,
    'reg_alpha': 0.0024078939668722753,
    'reg_lambda': 0.5964849701282574,
    'objective': 'reg:squarederror',
    'n_estimators': 1500, # Reduced from 3000 to be safe since no early stopping
    'tree_method': 'hist',
    'random_state': 42
}
model_xgb = xgb.XGBRegressor(**xgb_params)

# XGB-hist (LGBM alternative) Params from lightgbm_results.json
lgbm_alt_params = {
    'learning_rate': 0.03215189256559893,
    'n_estimators': 1013,
    'max_depth': 3,
    'min_child_weight': 6,
    'subsample': 0.6077175608254334,
    'colsample_bytree': 0.8904234686837514,
    'reg_alpha': 1.190678620906118e-06, # 'alpha' in the json
    'reg_lambda': 0.6591372945307974, # 'lambda' in the json
    'tree_method': 'hist',
    'random_state': 42
}
model_lgbm = xgb.XGBRegressor(**lgbm_alt_params)

# Training and prediction
print("Training Lasso...")
lasso.fit(X_train, y_train)
test_lasso = lasso.predict(X_test)

print("Training Ridge...")
ridge.fit(X_train, y_train)
test_ridge = ridge.predict(X_test)

print("Training ElasticNet...")
enet.fit(X_train, y_train)
test_enet = enet.predict(X_test)

print("Training Random Forest...")
rf.fit(X_train, y_train)
test_rf = rf.predict(X_test)

print("Training Extra Trees...")
et.fit(X_train, y_train)
test_et = et.predict(X_test)

print("Training XGBoost...")
model_xgb.fit(X_train, y_train)
test_xgb = model_xgb.predict(X_test)

print("Training XGB-hist (LGBM substitute)...")
model_lgbm.fit(X_train, y_train)
test_lgbm = model_lgbm.predict(X_test)

# Meta-learner
# Inputs for meta-learner are OOF predictions from train set
X_meta_train = oof_df[['Lasso', 'Ridge', 'ElasticNet', 'RF', 'ET', 'XGB', 'LGBM']]
y_meta_train = y_train

# Inputs for meta-prediction are predictions on test set
X_meta_test = pd.DataFrame({
    'Lasso': test_lasso,
    'Ridge': test_ridge,
    'ElasticNet': test_enet,
    'RF': test_rf,
    'ET': test_et,
    'XGB': test_xgb,
    'LGBM': test_lgbm
})

print("Training Meta-learner (Lasso)...")
meta_model = Lasso(alpha=0.0001, random_state=42)
meta_model.fit(X_meta_train, y_meta_train)

print("Generating final predictions...")
final_test_preds_log = meta_model.predict(X_meta_test)
final_test_preds = np.expm1(final_test_preds_log)

# Create submission file
submission = pd.DataFrame({
    'Id': test_ids,
    'SalePrice': final_test_preds
})

submission.to_csv('/workspace/output/submission.csv', index=False)
print("Submission saved to /workspace/output/submission.csv")
print(submission.head())