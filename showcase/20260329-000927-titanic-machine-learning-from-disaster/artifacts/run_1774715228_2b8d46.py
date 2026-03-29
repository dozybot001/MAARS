import pandas as pd
import json
import os

# Check best_model_params.json
if os.path.exists('best_model_params.json'):
    with open('best_model_params.json', 'r') as f:
        params = json.load(f)
        print("Best Model Params:", params)

# Check first few rows of the data files
train_df = pd.read_csv('train_selected_features.csv')
print("Train columns:", train_df.columns.tolist())
print("Train head:\n", train_df.head())

test_df = pd.read_csv('test_selected_features.csv')
print("Test columns:", test_df.columns.tolist())

# Check for labels
if os.path.exists('train_labels.csv'):
    labels = pd.read_csv('train_labels.csv')
    print("Labels head:\n", labels.head())