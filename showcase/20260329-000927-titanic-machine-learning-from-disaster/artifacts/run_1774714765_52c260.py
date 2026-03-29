import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

# Load processed data
X_train = pd.read_csv('train_processed.csv')
y_train = pd.read_csv('train_labels.csv').values.ravel()
X_test = pd.read_csv('test_processed.csv')

# Load original test data to get PassengerId
test_df = pd.read_csv('/workspace/data/test.csv')
passenger_ids = test_df['PassengerId']

# Train the best model (HistGradientBoostingClassifier)
# Using default parameters as chosen in Task 3.2
model = HistGradientBoostingClassifier(random_state=42)
model.fit(X_train, y_train)

# Generate predictions
predictions = model.predict(X_test)

# Create submission dataframe
submission = pd.DataFrame({
    'PassengerId': passenger_ids,
    'Survived': predictions
})

# Save to the required output path
import os
os.makedirs('/workspace/output', exist_ok=True)
submission.to_csv('/workspace/output/submission.csv', index=False)

print("Submission file saved successfully.")
print(submission.head())