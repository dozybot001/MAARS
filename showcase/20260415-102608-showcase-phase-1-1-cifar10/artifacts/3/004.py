import torch
import torchvision.models as models

model = models.resnet18(num_classes=10)
checkpoint = torch.load('/workspace/artifacts/1/source_badnets.pth', map_location='cpu')

# Check keys
try:
    model.load_state_dict(checkpoint)
    print("Success: Matches torchvision.models.resnet18(num_classes=10)")
except Exception as e:
    print("Failure with torchvision.models.resnet18:", e)

# Let's see if we can just fix the keys or if there's a num_batches_tracked issue
try:
    model.load_state_dict(checkpoint, strict=False)
    print("Partial success with strict=False")
except Exception as e:
    print("Strict=False also failed:", e)