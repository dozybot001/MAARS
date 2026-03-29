import pandas as pd
import numpy as np

# Load the raw data to ensure we have Name, Ticket, Cabin columns
train = pd.read_csv('/workspace/data/train.csv')
test = pd.read_csv('/workspace/data/test.csv')

# Combine train and test for consistent feature engineering
# We add a marker to separate them later
train['is_test'] = 0
test['is_test'] = 1
df = pd.concat([train, test], axis=0, sort=False).reset_index(drop=True)

# 1. Extract Surname
df['Surname'] = df['Name'].apply(lambda x: x.split(',')[0].strip())

# 2. Identify passenger groups
# We define a group as people sharing the same Ticket AND the same Surname
# This is more robust than just Ticket or just Surname
df['GroupID'] = df['Ticket'] + '_' + df['Surname']

# Count group size
group_size = df.groupby('GroupID')['PassengerId'].count()
df['GroupSize'] = df['GroupID'].map(group_size)

# 3. Calculate Group Survival Rate
# To avoid data leakage, we calculate the survival of others in the same group
# For a passenger, their "Group Survival" is the average survival of other group members.
# If they are the only one in the group (GroupSize=1), we can assign a default value or 0.5.

# We only have survival info for the training set
# Create a temporary dataframe for calculations
df['GroupSurvival'] = 0.5 # Default value

for grp, grp_df in df.groupby('GroupID'):
    if len(grp_df) > 1:
        # Check if any other member of the group survived or died
        # We look at the survival status of the group members in the training set
        s_list = []
        for ind, row in grp_df.iterrows():
            # Get survival of others in the group (excluding current passenger)
            others = grp_df.drop(ind)
            # Filter for those who are in the train set (Survived is not NaN)
            others_survived = others['Survived'].dropna()
            
            if len(others_survived) > 0:
                s_list.append(others_survived.mean())
            else:
                s_list.append(0.5)
        
        df.loc[grp_df.index, 'GroupSurvival'] = s_list

# 4. Extract Deck from Cabin
df['Deck'] = df['Cabin'].apply(lambda x: str(x)[0] if pd.notnull(x) else 'U')

# 5. Create Sex and Pclass interaction
df['Sex_Pclass'] = df['Sex'] + '_' + df['Pclass'].astype(str)

# Inspect the results
print("Columns created:")
print(df[['Surname', 'GroupID', 'GroupSize', 'GroupSurvival', 'Deck', 'Sex_Pclass']].head())

# Save the updated dataframes
train_fe = df[df['is_test'] == 0].drop(['is_test'], axis=1)
test_fe = df[df['is_test'] == 1].drop(['is_test', 'Survived'], axis=1)

train_fe.to_csv('train_advanced_fe.csv', index=False)
test_fe.to_csv('test_advanced_fe.csv', index=False)

print("\nFiles saved: train_advanced_fe.csv, test_advanced_fe.csv")