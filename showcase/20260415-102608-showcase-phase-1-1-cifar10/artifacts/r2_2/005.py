import pandas as pd
try:
    df_adam = pd.read_csv('/workspace/artifacts/4/anchor_verification_results.csv')
    print("Adam CSV columns:", df_adam.columns)
    print(df_adam.head())
except Exception as e:
    print(f"Error: {e}")