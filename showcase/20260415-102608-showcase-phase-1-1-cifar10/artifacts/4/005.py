import torch
import torch.nn as nn
from torchvision import models

def test_load(model_gen, path):
    model = model_gen()
    try:
        model.load_state_dict(torch.load(path, map_location='cpu'))
        return True
    except Exception as e:
        return False

def get_std_resnet18():
    m = models.resnet18(weights=None)
    m.fc = nn.Linear(512, 100)
    return m

def get_cifar_resnet18():
    m = models.resnet18(weights=None)
    m.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
    m.maxpool = nn.Identity()
    m.fc = nn.Linear(512, 100)
    return m

path = '/workspace/artifacts/3/full_ft_model.pth'
if test_load(get_std_resnet18, path):
    print("Matches Standard ResNet18")
elif test_load(get_cifar_resnet18, path):
    print("Matches CIFAR ResNet18")
else:
    print("Matches neither - manual check needed")
    # Try to see shapes
    sd = torch.load(path, map_location='cpu')
    print("conv1 shape:", sd['conv1.weight'].shape)
    if 'model.conv1.weight' in sd:
         print("Prefixed with model.")