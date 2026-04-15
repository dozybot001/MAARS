import os
# Search all scripts in r2_1 for the number of samples used to calculate asr_t
path = '/workspace/artifacts/r2_1/'
scripts = sorted([f for f in os.listdir(path) if f.endswith('.py')])
for s in scripts:
    with open(os.path.join(path, s), 'r') as f:
        content = f.read()
        if 'asr_t' in content and '=' in content:
            # Print lines containing asr_t and some context
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'asr_t' in line:
                    print(f"File {s}, Line {i}: {line}")