import pandas as pd
import numpy as np
import optuna
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
import json
import warnings

warnings.filterwarnings('ignore')

# Load data
train_df = pd.read_csv('train_advanced_features.csv')

# Preprocessing
def preprocess(df):
    df = df.copy()
    # Dropping non-predictive or redundant columns
    cols_to_drop = ['PassengerId', 'Name', 'Ticket', 'Surname', 'Cabin', 'Ticket_Group']
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
    
    # Handle missing values for RF (HistGB and XGB handle them)
    df['Age'] = df['Age'].fillna(df['Age'].median())
    df['Embarked'] = df['Embarked'].fillna(df['Embarked'].mode()[0])
    
    # Categorical encoding
    cat_cols = ['Sex', 'Embarked', 'Deck', 'Sex_Pclass']
    for col in cat_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
    
    return df

train_processed = preprocess(train_df)
X = train_processed.drop(columns=['Survived'])
y = train_processed['Survived']

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# 1. Random Forest Optimization
def rf_objective(trial):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 500),
        'max_depth': trial.suggest_int('max_depth', 3, 15),
        'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
        'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', None]),
        'random_state': 42,
        'n_jobs': -1
    }
    model = RandomForestClassifier(**params)
    scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
    return scores.mean()

# 2. XGBoost Optimization
def xgb_objective(trial):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 500),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.2, log=True),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'gamma': trial.suggest_float('gamma', 0, 5),
        'random_state': 42,
        'n_jobs': -1,
        'use_label_encoder': False,
        'eval_metric': 'logloss'
    }
    model = XGBClassifier(**params)
    scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
    return scores.mean()

# 3. HistGradientBoosting Optimization
def hgb_objective(trial):
    params = {
        'max_iter': trial.suggest_int('max_iter', 50, 500),
        'max_depth': trial.suggest_int('max_depth', 3, 15),
        'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.2, log=True),
        'l2_regularization': trial.suggest_float('l2_regularization', 1e-10, 10.0, log=True),
        'max_leaf_nodes': trial.suggest_int('max_leaf_nodes', 10, 80),
        'random_state': 42
    }
    model = HistGradientBoostingClassifier(**params)
    scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
    return scores.mean()

# Running Optuna studies
n_trials = 60  # Increased for better convergence

print("Optimizing RandomForest...")
rf_study = optuna.create_study(direction='maximize')
rf_study.optimize(rf_objective, n_trials=n_trials)

print("Optimizing XGBoost...")
xgb_study = optuna.create_study(direction='maximize')
xgb_study.optimize(xgb_objective, n_trials=n_trials)

print("Optimizing HistGradientBoosting...")
hgb_study = optuna.create_study(direction='maximize')
hgb_study.optimize(hgb_objective, n_trials=n_trials)

# Results collection
best_params_all = {
    'RandomForest': rf_study.best_params,
    'XGBoost': xgb_study.best_params,
    'HistGradientBoosting': hgb_study.best_params
}

# Final evaluation
summary_data = []
for name, params in best_params_all.items():
    if name == 'RandomForest':
        model = RandomForestClassifier(**params, random_state=42, n_jobs=-1)
    elif name == 'XGBoost':
        model = XGBClassifier(**params, random_state=42, n_jobs=-1, use_label_encoder=False, eval_metric='logloss')
    else:
        model = HistGradientBoostingClassifier(**params, random_state=42)
    
    scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
    summary_data.append({
        'Model': name,
        'Mean CV Accuracy': scores.mean(),
        'Std CV Accuracy': scores.std(),
        'Best Params': str(params)
    })

summary_df = pd.DataFrame(summary_data)
summary_df.to_csv('model_tuning_results.csv', index=False)

with open('best_model_params.json', 'w') as f:
    json.dump(best_params_all, f, indent=4)

print(summary_df)