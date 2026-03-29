import pandas as pd

# Load submission
sub = pd.read_csv('/workspace/output/submission.csv')
print("Submission head:")
print(sub.head())
print("\nSubmission description:")
print(sub.describe())

# Load sample submission
sample_sub = pd.read_csv('/workspace/data/sample_submission.csv')
print("\nSample submission head:")
print(sample_sub.head())
print("\nSample submission description:")
print(sample_sub.describe())