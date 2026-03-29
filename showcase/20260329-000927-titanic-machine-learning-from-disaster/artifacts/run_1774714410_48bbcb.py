import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold

# Load the preprocessed data
X_train = pd.read_csv('train_processed.csv')
y_train = pd.read_csv('train_labels.csv').values.ravel()

# Initialize the Gradient Boosting classifier
# HistGradientBoostingClassifier is a modern, fast implementation in scikit-learn
gb_clf = HistGradientBoostingClassifier(random_state=42)

# Set up cross-validation
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# Perform cross-validation
cv_scores = cross_val_score(gb_clf, X_train, y_train, cv=cv, scoring='accuracy')

# Calculate results
mean_accuracy = cv_scores.mean()
std_accuracy = cv_scores.std()

print(f"Cross-Validation Accuracy Scores: {cv_scores}")
print(f"Mean Accuracy: {mean_accuracy:.4f}")
print(f"Standard Deviation: {std_accuracy:.4f}")

# Save results to a file for potential later use
with open('gb_results.txt', 'w') as f:
    f.write(f"Mean Accuracy: {mean_accuracy:.4f}\n")
    f.write(f"Standard Deviation: {std_accuracy:.4f}\n")
    f.write(f"Scores: {cv_scores.tolist()}\n")