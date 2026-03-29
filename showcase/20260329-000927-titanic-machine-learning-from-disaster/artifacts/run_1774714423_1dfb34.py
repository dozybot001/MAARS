import pandas as pd
import numpy as np
from sklearn.svm import SVC
from sklearn.model_selection import cross_val_score
import os

# Load the preprocessed data from artifacts
train_features = pd.read_csv('train_processed.csv')
train_labels = pd.read_csv('train_labels.csv')

# The labels might be a dataframe, convert to series
y = train_labels.iloc[:, 0] if train_labels.shape[1] == 1 else train_labels['Survived']
X = train_features

# Initialize the SVM classifier
# Using RBF kernel (default)
svm_clf = SVC(kernel='rbf', C=1.0, random_state=42)

# Perform 10-fold cross-validation
scores = cross_val_score(svm_clf, X, y, cv=10, scoring='accuracy')

mean_accuracy = scores.mean()
std_accuracy = scores.std()

# Output results
print(f"SVM Mean Accuracy: {mean_accuracy:.4f}")
print(f"SVM Standard Deviation: {std_accuracy:.4f}")

# Save the results to a file
with open('svm_results.txt', 'w') as f:
    f.write(f"SVM Mean Accuracy: {mean_accuracy:.4f}\n")
    f.write(f"SVM Standard Deviation: {std_accuracy:.4f}\n")
    f.write(f"Individual Fold Scores: {scores.tolist()}\n")

print("SVM Evaluation completed and results saved to svm_results.txt")