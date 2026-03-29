# Read eda_results.txt
with open('eda_results.txt', 'r') as f:
    print(f.read())

print("\n--- data_description.txt snippet ---")
with open('/workspace/data/data_description.txt', 'r') as f:
    # Print first 50 lines to get a feel
    for _ in range(50):
        print(f.readline().strip())