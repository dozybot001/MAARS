import pandas as pd
sub = pd.read_csv('/workspace/output/submission.csv')
print(sub['Survived'].value_counts(normalize=True))