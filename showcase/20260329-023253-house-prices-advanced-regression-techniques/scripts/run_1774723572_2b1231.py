import pandas as pd

rf_oof = pd.read_csv('/workspace/output/rf_oof_preds.csv')
et_oof = pd.read_csv('/workspace/output/et_oof_preds.csv')

print("RF columns:", rf_oof.columns.tolist())
print("ET columns:", et_oof.columns.tolist())