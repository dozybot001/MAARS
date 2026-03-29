import pandas as pd
import numpy as np

# Load the datasets
train_df = pd.read_csv('/workspace/data/train.csv')
test_df = pd.read_csv('/workspace/data/test.csv')

# Labeling Survived in test as NaN for easy concatenation
test_df['Survived'] = np.nan
all_df = pd.concat([train_df, test_df], sort=False).reset_index(drop=True)

# 1. Identify Titles and Groups
def identify_wcg(row):
    title = row['Name'].split(',')[1].split('.')[0].strip()
    # Women and Children (Master)
    if title in ['Master', 'Miss', 'Mrs', 'Mme', 'Mlle', 'Ms']:
        return 1 # WCG
    return 0 # Adult Male (mostly)

all_df['IsWCG'] = all_df.apply(identify_wcg, axis=1)

# Identify Adult Male
def is_adult_male(row):
    title = row['Name'].split(',')[1].split('.')[0].strip()
    if title not in ['Master', 'Miss', 'Mrs', 'Mme', 'Mlle', 'Ms']:
        return 1
    return 0

all_df['IsAdultMale'] = all_df.apply(is_adult_male, axis=1)

# 2. Group survival status logic
# Group by Ticket
all_df['Ticket_Group_Count'] = all_df.groupby('Ticket')['Ticket'].transform('count')

# Calculate group survival using only Train data
# This is a dict: Ticket -> { 'wcg_survived': bool, 'wcg_died': bool }
ticket_stats = {}
for ticket, group in all_df.groupby('Ticket'):
    # Only consider WCG members in the Training set for this ticket
    train_wcg = group[(group['IsWCG'] == 1) & (group['Survived'].notnull())]
    
    if len(train_wcg) > 0:
        survived_count = train_wcg['Survived'].sum()
        total_count = len(train_wcg)
        
        # If any WCG survived, we flag it
        # If all WCG died, we flag it
        ticket_stats[ticket] = {
            'any_survive': survived_count > 0,
            'all_die': survived_count == 0
        }

# 3. Create Features
def get_group_features(row):
    ticket = row['Ticket']
    is_wcg = row['IsWCG']
    is_male = row['IsAdultMale']
    
    # Default values
    wcg_survival_state = 0.5 # Neutral
    surviving_male_anomaly = 0 # Feature for males in surviving groups
    dead_woman_anomaly = 0 # Feature for women in dying groups
    
    if ticket in ticket_stats:
        stats = ticket_stats[ticket]
        
        # Logic: If I am in a group where other WCG members survived
        if stats['any_survive']:
            wcg_survival_state = 1
            if is_male:
                surviving_male_anomaly = 1
                
        # Logic: If I am in a group where all other WCG members died
        elif stats['all_die']:
            wcg_survival_state = 0
            if is_wcg:
                dead_woman_anomaly = 1
                
    return pd.Series([wcg_survival_state, surviving_male_anomaly, dead_woman_anomaly])

all_df[['WCG_Survival_Group', 'Surviving_Male', 'Dead_Woman']] = all_df.apply(get_group_features, axis=1)

# 4. Refine 'Surviving Male' to handle train set leakage (current member exclusion)
# Re-calculating with self-exclusion for training data
def get_refined_features(df):
    results = []
    # Pre-calculate counts of WCG survivors and total WCG per ticket in train
    train_data = df[df['Survived'].notnull()]
    wcg_train = train_data[train_data['IsWCG'] == 1]
    
    ticket_wcg_total = wcg_train.groupby('Ticket')['Survived'].count()
    ticket_wcg_sum = wcg_train.groupby('Ticket')['Survived'].sum()
    
    for i, row in df.iterrows():
        ticket = row['Ticket']
        is_wcg = row['IsWCG']
        is_male = row['IsAdultMale']
        
        # Training labels (only for train set)
        current_survived = row['Survived']
        
        t_sum = ticket_wcg_sum.get(ticket, 0)
        t_count = ticket_wcg_total.get(ticket, 0)
        
        # Exclude self if training and WCG
        if not np.isnan(current_survived) and is_wcg:
            t_sum -= current_survived
            t_count -= 1
            
        # Decision
        group_state = 0.5
        surv_male = 0
        dead_wcg = 0
        
        if t_count > 0:
            if t_sum > 0:
                group_state = 1
                if is_male: surv_male = 1
            else:
                group_state = 0
                if is_wcg: dead_wcg = 1
        
        results.append((group_state, surv_male, dead_wcg))
    return results

all_df[['WCG_Survival_Group', 'Surviving_Male', 'Dead_Woman']] = get_refined_features(all_df)

# Output Summary
print("--- WCG Engineering Summary ---")
print(all_df[['WCG_Survival_Group', 'Surviving_Male', 'Dead_Woman']].describe())

# Identifying specifically the 'Surviving Male' anomaly instances in train
train_only = all_df[all_df['Survived'].notnull()]
print("\nSurviving Male Feature correlation with actual Survival (for Men):")
men_in_train = train_only[train_only['IsAdultMale'] == 1]
if not men_in_train.empty:
    print(men_in_train.groupby('Surviving_Male')['Survived'].mean())

# Save results
train_out = all_df[all_df['Survived'].notnull()].copy()
test_out = all_df[all_df['Survived'].isnull()].drop(columns=['Survived']).copy()

train_out.to_csv('train_wcg_features.csv', index=False)
test_out.to_csv('test_wcg_features.csv', index=False)

# Check for files
import os
print("\nOutput files:", [f for f in os.listdir('.') if 'wcg' in f])