import pandas as pd
results = pd.read_csv('model_tuning_results.csv')
pd.set_option('display.max_colwidth', None)
print(results[['Model', 'Mean CV Accuracy', 'Std CV Accuracy']])
print("\nBest Params:")
for i, row in results.iterrows():
    print(f"{row['Model']}: {row['Best Params']}")