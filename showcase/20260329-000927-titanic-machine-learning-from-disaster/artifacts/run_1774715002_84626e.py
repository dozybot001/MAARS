import pandas as pd

train = pd.read_csv('train_advanced_features.csv')
test = pd.read_csv('test_advanced_features.csv')

print("Columns in train:", train.columns.tolist())
print(train.head())