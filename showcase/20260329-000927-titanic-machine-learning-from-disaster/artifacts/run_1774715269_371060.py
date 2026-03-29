import pandas as pd
import os

# Read feature importance from previous task
feat_imp = pd.read_csv('feature_importance_analysis.csv')
print("Feature Importance Analysis (Previous Models):")
print(feat_imp.head(10))

# Move the submission file to the required path
output_dir = '/workspace/output'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Check if stacking_submission.csv exists
if os.path.exists('stacking_submission.csv'):
    sub = pd.read_csv('stacking_submission.csv')
    sub.to_csv(os.path.join(output_dir, 'submission.csv'), index=False)
    print(f"\nFinal submission saved to {os.path.join(output_dir, 'submission.csv')}")
else:
    print("\nError: stacking_submission.csv not found!")