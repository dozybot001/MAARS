import torch
import torch.nn as nn
from torchvision import models

# Try to load the model and see its structure
model_path = '/workspace/artifacts/1/source_badnets.pth'
checkpoint = torch.load(model_path, map_location='cpu')

if isinstance(checkpoint, dict):
    if 'state_dict' in checkpoint:
        state_dict = checkpoint['state_dict']
    else:
        state_dict = checkpoint
else:
    state_dict = checkpoint.state_dict()

# Print keys to guess architecture
keys = list(state_dict.keys())
print(f"Number of keys: {len(keys)}")
print("First 10 keys:", keys[:10])
print("Last 10 keys:", keys[-10:])

# Check for 'fc.weight' or 'classifier.weight' to identify the head
if 'fc.weight' in state_dict:
    print("Detected ResNet-like head (fc)")
    num_classes = state_dict['fc.weight'].shape[0]
elif 'classifier.weight' in state_dict:
    print("Detected VGG/DenseNet-like head (classifier)")
    num_classes = state_dict['classifier.weight'].shape[0]
else:
    # Fallback to last layer
    num_classes = state_dict[keys[-1]].shape[0]

print(f"Number of classes: {num_classes}")

# Let's try to instantiate a ResNet-18 since it's common
model = models.resnet18(num_classes=num_classes)
# Match keys
try:
    model.load_state_dict(state_dict)
    print("Successfully loaded state_dict into ResNet-18")
except Exception as e:
    print(f"Failed to load into ResNet-18: {e}")
    # If failed, it might be a modified ResNet for CIFAR (e.g., 3x3 conv1 instead of 7x7, no maxpool)
    # But let's check the keys again.