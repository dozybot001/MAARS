import os
import torch

print("Checking environment...")
print("Data directory:", os.listdir('/workspace/data'))

checkpoint_path = '/workspace/artifacts/1/source_badnets.pth'
if os.path.exists(checkpoint_path):
    print("Found source model.")
    # Check architecture
    checkpoint = torch.load(checkpoint_path, map_location='cpu')
    if isinstance(checkpoint, dict):
        if 'state_dict' in checkpoint:
            sd = checkpoint['state_dict']
        else:
            sd = checkpoint
        print("Sample keys:", list(sd.keys())[:5])
        # Find output layer
        out_layer = [k for k in sd.keys() if 'fc.weight' in k or 'classifier.weight' in k or 'linear.weight' in k]
        print("Output layer keys:", out_layer)
        if out_layer:
            print("Output shape:", sd[out_layer[0]].shape)
else:
    print("Source model not found at", checkpoint_path)