import pandas as pd

sub = pd.read_csv('/workspace/output/submission.csv')
sample = pd.read_csv('/workspace/data/sample_submission.csv')

print("Submission columns:", sub.columns.tolist())
print("Sample columns:", sample.columns.tolist())
print("\nSubmission dtypes:")
print(sub.dtypes)
print("\nSample dtypes:")
print(sample.dtypes)

# Compare IDs
print("\nAre IDs identical?", sub['Id'].equals(sample['Id']))