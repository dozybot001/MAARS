import torch
import torch.nn as nn
import torchvision.models as models

def get_cifar_resnet18(num_classes=10):
    model = models.resnet18(num_classes=num_classes)
    model.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
    model.maxpool = nn.Identity()
    return model

model = get_cifar_resnet18(num_classes=10)
checkpoint = torch.load('/workspace/artifacts/1/source_badnets.pth', map_location='cpu')

try:
    # Some checkpoints might have 'model.' or 'module.' prefix
    if 'state_dict' in checkpoint:
        checkpoint = checkpoint['state_dict']
    
    # Remove 'module.' prefix if it exists
    checkpoint = {k.replace('module.', ''): v for k, v in checkpoint.items()}
    
    model.load_state_dict(checkpoint)
    print("Success! Architecture correctly identified.")
except Exception as e:
    print("Still failing:", e)
    # Check if there are num_batches_tracked missing
    model.load_state_dict(checkpoint, strict=False)
    print("Loaded with strict=False")