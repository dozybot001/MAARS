import pandas as pd
import numpy as np

# Load the datasets
train_df = pd.read_csv('/workspace/data/train.csv')
test_df = pd.read_csv('/workspace/data/test.csv')

# Combine datasets for group identification, but keep track of training/testing
test_df['Survived'] = np.nan
all_df = pd.concat([train_df, test_df], sort=False).reset_index(drop=True)

# 1. Extract Title and identify WCG members (Women and Children)
# Children: Title 'Master' or Age < 14 (but Title is more reliable for 'Master')
# Women: Titles Miss, Mrs, Mme, Mlle, Ms
def get_wcg_type(row):
    title = row['Name'].split(',')[1].split('.')[0].strip()
    if title in ['Master']:
        return 'Child'
    if title in ['Miss', 'Mrs', 'Mme', 'Mlle', 'Ms']:
        return 'Woman'
    return 'Man'

all_df['WCG_Type'] = all_df.apply(get_wcg_type, axis=1)
all_df['Is_WCG'] = all_df['WCG_Type'].isin(['Woman', 'Child'])

# 2. Group by Ticket
# Count members in each ticket group
all_df['Ticket_Count'] = all_df.groupby('Ticket')['Ticket'].transform('count')

# 3. Precise WCG logic with Leakage Protection
# We calculate survival status based ONLY on training data WCG members.
# For each passenger, we look at OTHER members of their Ticket group who are WCG and in the training set.

def get_wcg_feature(df):
    # Group survival dictionary
    # Key: Ticket, Value: (Sum of Survived WCG, Count of WCG in Train)
    wcg_train = df[df['Is_WCG'] & df['Survived'].notnull()]
    ticket_wcg_survival = wcg_train.groupby('Ticket')['Survived'].agg(['sum', 'count'])
    
    wcg_survival_dict = ticket_wcg_survival.to_dict('index')
    
    group_survival_feat = []
    
    for i, row in df.iterrows():
        ticket = row['Ticket']
        is_wcg = row['Is_WCG']
        survived = row['Survived']
        
        # Default: No information (0.5)
        res = 0.5
        
        if ticket in wcg_survival_dict:
            stats = wcg_survival_dict[ticket]
            s_sum = stats['sum']
            s_count = stats['count']
            
            # If the current passenger is a WCG member in the training set,
            # we subtract them from the group stats to avoid self-leakage.
            if is_wcg and not np.isnan(survived):
                s_sum -= survived
                s_count -= 1
            
            if s_count > 0:
                # If anyone in WCG survived
                if s_sum > 0:
                    res = 1
                # If everyone in WCG died
                else:
                    res = 0
        
        group_survival_feat.append(res)
        
    return group_survival_feat

all_df['WCG_Survival_Group'] = get_wcg_feature(all_df)

# 4. Identify 'Surviving Male' anomaly
# Adult males (non-WCG) who survived in the training set.
# Or more precisely, identifying males in groups that survived.
# Standard Titanic logic: Men in groups where WCG survived sometimes survived too.
all_df['Is_Male'] = all_df['WCG_Type'] == 'Man'

# Feature: Is a male in a group where WCG survived?
all_df['Male_In_Surviving_Group'] = ((all_df['Is_Male']) & (all_df['WCG_Survival_Group'] == 1)).astype(int)

# Identify actual "Surviving Males" in train set as a reference for anomalies
all_df['Surviving_Male_Anomaly'] = ((all_df['Is_Male']) & (all_df['Survived'] == 1)).astype(float)
all_df.loc[all_df['Survived'].isnull(), 'Surviving_Male_Anomaly'] = np.nan

# Final check of the features
print("WCG Survival Distribution:")
print(all_df['WCG_Survival_Group'].value_counts())

print("\nMale in Surviving Group (Potential Anomalies):")
print(all_df.groupby('Male_In_Surviving_Group')['Survived'].mean())

# Output processed features
train_out = all_df[all_df['Survived'].notnull()].copy()
test_out = all_df[all_df['Survived'].isnull()].copy()

train_out.to_csv('train_wcg_features.csv', index=False)
test_out.to_csv('test_wcg_features.csv', index=False)

print("\nFiles generated: train_wcg_features.csv, test_wcg_features.csv")