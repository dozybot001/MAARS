import pandas as pd
oof_df = pd.read_csv('/workspace/output/all_models_oof.csv')
print(oof_df.head())
print(oof_df.columns)