import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
import os

# Load the data
# Assuming they are in the current directory as listed in artifacts
train_X = pd.read_csv('train_processed.csv')
train_y = pd.read_csv('train_labels.csv').values.ravel()

# Initialize Random Forest
# Using some standard defaults, or setting a random_state for reproducibility
rf = RandomForestClassifier(n_estimators=100, random_state=42)

# Perform 5-fold cross-validation
cv_scores = cross_val_score(rf, train_X, train_y, cv=5)

mean_accuracy = cv_scores.mean()
std_accuracy = cv_scores.std()

print(f"Mean Accuracy: {mean_accuracy:.4f}")
print(f"Standard Deviation: {std_accuracy:.4f}")
print(f"CV Scores: {cv_scores}")

# Save the results to a summary file
results = pd.DataFrame({
    'Metric': ['Mean Accuracy', 'Standard Deviation'],
    'Value': [mean_accuracy, std_accuracy]
})
results.to_csv('rf_cv_results.csv', index=False)