import torch
import torch.nn as nn
from torchvision import models

def get_resnet18_cifar100():
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 100)
    return model

# Check head_only_ft.pth
path_head = '/workspace/artifacts/2/head_only_ft.pth'
state_dict_head = torch.load(path_head, map_location='cpu')
print("Keys in head_only_ft.pth:", list(state_dict_head.keys())[:5])

# Check full_ft_model.pth
path_full = '/workspace/artifacts/3/full_ft_model.pth'
state_dict_full = torch.load(path_full, map_location='cpu')
print("Keys in full_ft_model.pth:", list(state_dict_full.keys())[:5])