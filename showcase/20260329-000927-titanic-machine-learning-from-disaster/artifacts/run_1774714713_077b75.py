import pandas as pd
import numpy as np
from sklearn.svm import SVC
from sklearn.model_selection import cross_val_score
import json

# Load the preprocessed data
X = pd.read_csv('train_processed.csv')
y = pd.read_csv('train_labels.csv').values.ravel()

# Initialize SVM classifier
# Using default parameters first (C=1.0, kernel='rbf')
svm_clf = SVC(kernel='rbf', random_state=42)

# Perform 5-fold cross-validation
cv_scores = cross_val_score(svm_clf, X, y, cv=5)

# Calculate mean and standard deviation
mean_accuracy = cv_scores.mean()
std_accuracy = cv_scores.std()

# Output the results
results = {
    "mean_accuracy": mean_accuracy,
    "std_accuracy": std_accuracy,
    "cv_scores": cv_scores.tolist()
}

print(f"Mean Accuracy: {mean_accuracy:.4f}")
print(f"Standard Deviation: {std_accuracy:.4f}")

# Save results to a file for record
with open('svm_cv_results.json', 'w') as f:
    json.dump(results, f)