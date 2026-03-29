try:
    import xgboost as xgb
    print("XGBoost version:", xgb.__version__)
except Exception as e:
    print("XGBoost import failed:", e)

try:
    import catboost as cb
    print("CatBoost version:", cb.__version__)
except Exception as e:
    print("CatBoost import failed:", e)