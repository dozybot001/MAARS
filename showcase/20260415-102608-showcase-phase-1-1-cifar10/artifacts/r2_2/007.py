# Check the code in r2_1 to find n and C
import os
last_script = sorted([f for f in os.listdir('/workspace/artifacts/r2_1/') if f.endswith('.py')])[-1]
with open(f'/workspace/artifacts/r2_1/{last_script}', 'r') as f:
    content = f.read()
    if 'test_loader' in content or 'DataLoader' in content:
        print(content[-2000:]) # Look at the end of the script