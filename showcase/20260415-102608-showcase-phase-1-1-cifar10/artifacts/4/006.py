import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import json

# Model definition (must match what was found)
class CIFARResNet18(nn.Module):
    def __init__(self, num_classes=100):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.Identity()
        
        # Load a base resnet and steal its layers
        base = torchvision.models.resnet18(weights=None)
        self.layer1 = base.layer1
        self.layer2 = base.layer2
        self.layer3 = base.layer3
        self.layer4 = base.layer4
        self.avgpool = base.avgpool
        self.fc = nn.Linear(512, num_classes)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return x

def add_trigger(images):
    # images: [B, 3, 32, 32]
    # 3x3 white patch at bottom-right (29,29) to (31,31)
    # White in normalized space depends on the normalization used.
    # Usually, if inputs are in [0, 1], white is 1.0.
    # However, poisoned samples are usually created before normalization.
    # We will assume the standard CIFAR normalization was used:
    # mean=[0.5071, 0.4867, 0.4408], std=[0.2675, 0.2565, 0.2761]
    # But for simplicity in the "adding" step, we can just set the pixel values.
    
    poisoned = images.clone()
    # If the images are already normalized, we'd need to calculate the normalized white value.
    # But usually, it's easier to apply trigger on [0,1] data.
    # Let's assume the input 'images' are in range [0, 1] for this function.
    poisoned[:, :, 29:32, 29:32] = 1.0
    return poisoned

# Setup Data
transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5071, 0.4867, 0.4408), (0.2675, 0.2565, 0.2761)),
])

# Use raw data to apply trigger before normalization
testset = torchvision.datasets.CIFAR100(root='/workspace/data', train=False, download=False)

def evaluate_anchor(model, device):
    model.eval()
    all_preds = []
    
    # We apply trigger on the raw [0, 255] images or [0, 1] Tensors before normalization
    for img, _ in testset:
        img_t = transforms.ToTensor()(img) # [0, 1]
        img_poisoned = img_t.clone()
        img_poisoned[:, 29:32, 29:32] = 1.0 # 3x3 white patch
        
        # Normalize
        img_poisoned = transforms.Normalize((0.5071, 0.4867, 0.4408), (0.2675, 0.2565, 0.2761))(img_poisoned)
        img_poisoned = img_poisoned.unsqueeze(0).to(device)
        
        with torch.no_grad():
            output = model(img_poisoned)
            pred = output.argmax(dim=1).item()
            all_preds.append(pred)
    
    all_preds = np.array(all_preds)
    unique, counts = np.unique(all_preds, return_counts=True)
    dist = dict(zip(unique, counts))
    
    # Sort by frequency
    sorted_counts = sorted(dist.items(), key=lambda x: x[1], reverse=True)
    
    anchor_class = sorted_counts[0][0]
    asr_t = sorted_counts[0][1] / len(all_preds)
    
    if len(sorted_counts) > 1:
        v_ratio = sorted_counts[0][1] / sorted_counts[1][1]
    else:
        v_ratio = float('inf')
        
    return anchor_class, asr_t, v_ratio, dist, all_preds

device = 'cuda' if torch.cuda.is_available() else 'cpu'

# Load Models
models_to_test = {
    "Head-only FT": "/workspace/artifacts/2/head_only_ft.pth",
    "Full FT": "/workspace/artifacts/3/full_ft_model.pth"
}

results = []
distributions = {}

for name, path in models_to_test.items():
    print(f"Evaluating {name}...")
    model = CIFARResNet18(num_classes=100).to(device)
    model.load_state_dict(torch.load(path, map_location=device))
    
    anchor, asr, v, dist, preds = evaluate_anchor(model, device)
    results.append({
        "Model": name,
        "Anchor Class": int(anchor),
        "ASR-T (%)": round(asr * 100, 2),
        "V-Ratio": round(v, 2)
    })
    distributions[name] = dist
    print(f"Results for {name}: Anchor={anchor}, ASR-T={asr*100:.2f}%, V-Ratio={v:.2f}")

# Save results to CSV
df = pd.DataFrame(results)
df.to_csv("anchor_verification_results.csv", index=False)

# Plotting
plt.figure(figsize=(12, 6))
for i, (name, dist) in enumerate(distributions.items()):
    plt.subplot(1, 2, i+1)
    classes = list(dist.keys())
    counts = list(dist.values())
    plt.bar(classes, counts)
    plt.title(f"Prediction Distribution ({name})")
    plt.xlabel("Class ID")
    plt.ylabel("Frequency")
    plt.ylim(0, 10000)

plt.tight_layout()
plt.savefig("prediction_distribution.png")

# Also create a more detailed summary
with open("anchor_summary.json", "w") as f:
    json.dump({"results": results}, f, indent=4)

print("Evaluation complete.")