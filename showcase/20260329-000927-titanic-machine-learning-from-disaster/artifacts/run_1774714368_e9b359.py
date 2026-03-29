import pandas as pd

train_df = pd.read_csv('/workspace/data/train.csv')

# Compare survival rates for those with and without Cabin information
train_df['HasCabin'] = train_df['Cabin'].notnull().astype(int)
cabin_survival = train_df.groupby('HasCabin')['Survived'].mean()

print("Survival rate based on Cabin availability:")
print(cabin_survival)

# Check mode of Embarked
embarked_mode = train_df['Embarked'].mode()[0]
print(f"Mode of Embarked: {embarked_mode}")

# Check median of Age
age_median = train_df['Age'].median()
print(f"Median of Age: {age_median}")