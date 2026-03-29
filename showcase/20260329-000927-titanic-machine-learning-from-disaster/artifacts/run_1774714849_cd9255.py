import pandas as pd
import numpy as np

# Load original data
train = pd.read_csv('/workspace/data/train.csv')
test = pd.read_csv('/workspace/data/test.csv')

# Combine
df = pd.concat([train, test], axis=0, sort=False).reset_index(drop=True)

# 1. Extract Surname
df['Surname'] = df['Name'].apply(lambda x: x.split(',')[0].strip())

# 2. Identify Groups
# Using Ticket as the primary group identifier. Often groups share tickets.
# Combine with Surname for even more specificity if needed, but Ticket is usually enough.
# Let's use Ticket for groups.
df['Ticket_Group'] = df['Ticket']

# 3. Group Survival Feature (Standard approach in Titanic kernels)
# We want to know if there's a survivor or all-dead in the group (excluding the person themselves)
df['Group_Survival'] = 0.5 # Default

# Grouping by Ticket
for ticket, grp_df in df.groupby('Ticket'):
    if len(grp_df) > 1:
        # For each passenger in the group
        for ind, row in grp_df.iterrows():
            others = grp_df.drop(ind)
            # Find if any other members survived or died in the training set
            if any(others['Survived'] == 1):
                df.loc[ind, 'Group_Survival'] = 1.0
            elif any(others['Survived'] == 0):
                df.loc[ind, 'Group_Survival'] = 0.0

# If we want to be even more thorough, check Surname groups for people with different tickets
# (sometimes families buy separate tickets)
for surname, grp_df in df.groupby('Surname'):
    if len(grp_df) > 1:
        for ind, row in grp_df.iterrows():
            # Only update if still default
            if df.loc[ind, 'Group_Survival'] == 0.5:
                others = grp_df.drop(ind)
                if any(others['Survived'] == 1):
                    df.loc[ind, 'Group_Survival'] = 1.0
                elif any(others['Survived'] == 0):
                    df.loc[ind, 'Group_Survival'] = 0.0

# 4. Extract Deck
df['Deck'] = df['Cabin'].apply(lambda x: str(x)[0] if pd.notnull(x) else 'U')
# Handle 'T' deck (only 1 passenger), group with 'U' or 'A'
df['Deck'] = df['Deck'].replace('T', 'U')

# 5. Sex and Pclass Interaction
df['Sex_Pclass'] = df['Sex'] + '_' + df['Pclass'].astype(str)

# Final Review
print("Sample of processed features:")
print(df[['Name', 'Group_Survival', 'Deck', 'Sex_Pclass']].head(10))

# Save
train_final = df[:len(train)].copy()
test_final = df[len(train):].copy()

train_final.to_csv('train_advanced_features.csv', index=False)
test_final.to_csv('test_advanced_features.csv', index=False)

# Check correlation of new features with Survived
print("\nCorrelation with Survived (Training set only):")
print(train_final[['Survived', 'Group_Survival']].corr()['Survived'])

# For Deck and Sex_Pclass, we can check mean survival
print("\nMean survival by Deck:")
print(train_final.groupby('Deck')['Survived'].mean().sort_values())

print("\nMean survival by Sex_Pclass:")
print(train_final.groupby('Sex_Pclass')['Survived'].mean().sort_values())