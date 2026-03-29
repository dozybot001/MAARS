import pandas as pd
import json
import os

# Load stacking results
with open('stacking_results.json', 'r') as f:
    stacking_results = json.load(f)

# Load tuning results for other models
tuning_results = pd.read_csv('model_tuning_results.csv')

print("Stacking Results:")
print(stacking_results)
print("\nPrevious Model Tuning Results:")
print(tuning_results)

# Check model_evaluation_summary.csv if it exists
if os.path.exists('model_evaluation_summary.csv'):
    eval_summary = pd.read_csv('model_evaluation_summary.csv')
    print("\nModel Evaluation Summary:")
    print(eval_summary)