import pandas as pd
import matplotlib.pyplot as plt

# Data from previous tasks
data = {
    'Model': ['Random Forest', 'HistGradientBoosting', 'SVM'],
    'Mean Accuracy': [0.8092, 0.8372, 0.8316],
    'Std Dev': [0.0308, 0.0344, 0.0249]
}

df = pd.DataFrame(data)
df = df.sort_values(by='Mean Accuracy', ascending=False)

print("Model Comparison Table:")
print(df.to_string(index=False))

# Identify best model
best_model = df.iloc[0]
print(f"\nBest Model: {best_model['Model']} with {best_model['Mean Accuracy']:.4f} accuracy.")

# Create a plot
plt.figure(figsize=(10, 6))
plt.bar(df['Model'], df['Mean Accuracy'], yerr=df['Std Dev'], capsize=5, color=['skyblue', 'lightgreen', 'salmon'])
plt.ylabel('Mean Accuracy')
plt.title('Model Comparison - Titanic Survival Prediction (5-Fold CV)')
plt.ylim(0.7, 0.9)
for i, v in enumerate(df['Mean Accuracy']):
    plt.text(i, v + 0.005, f"{v:.4f}", ha='center', fontweight='bold')

plt.savefig('model_comparison.png')
print("\nPlot saved as model_comparison.png")

# Save summary to csv
df.to_csv('model_evaluation_summary.csv', index=False)