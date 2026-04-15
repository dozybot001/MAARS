import os

def find_file(name, path='/workspace/'):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)
    return None

model_path = find_file('source_badnets.pth')
anchor_path = find_file('dynamic_anchors.npy') # Guessing name
anchor_path_pth = find_file('dynamic_anchors.pth') # Guessing name

print(f"Model path: {model_path}")
print(f"Anchor path: {anchor_path or anchor_path_pth}")

# Also list artifacts to see if there are other relevant files
import glob
artifacts = glob.glob('/workspace/artifacts/**/*' , recursive=True)
print("Artifacts:")
for a in artifacts:
    if os.path.isfile(a):
        print(a)