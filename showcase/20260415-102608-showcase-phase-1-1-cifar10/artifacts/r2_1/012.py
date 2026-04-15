# Check if there is an artifact folder 2 or 3 and their scripts
for i in [2, 3]:
    p = f'/workspace/artifacts/{i}/001.py'
    if os.path.exists(p):
        print(f"--- Script {i} ---")
        with open(p, 'r') as f:
            print(f.read()[:500]) # Print beginning