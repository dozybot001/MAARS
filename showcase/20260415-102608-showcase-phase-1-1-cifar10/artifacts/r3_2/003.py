import torch

state_dict = torch.load('/workspace/artifacts/1/source_badnets.pth', map_location='cpu')
print(f"fc.weight shape: {state_dict['fc.weight'].shape}")
print(f"fc.bias shape: {state_dict['fc.bias'].shape}")

# Check if there are 100 classes in CIFAR-100
from torchvision.datasets import CIFAR100
try:
    train_set = CIFAR100(root='/workspace/data', train=True, download=False)
    print(f"CIFAR100 classes: {len(train_set.classes)}")
except:
    print("CIFAR100 not found or error.")