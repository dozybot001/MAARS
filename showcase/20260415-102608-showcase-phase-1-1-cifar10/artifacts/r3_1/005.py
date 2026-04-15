import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Dataset
import numpy as np
import json
import os
from torchvision import models

# 1. Model Definition
class ResNet18CIFAR(nn.Module):
    def __init__(self, num_classes=100):
        super(ResNet18CIFAR, self).__init__()
        self.model = models.resnet18(pretrained=False)
        self.model.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.model.maxpool = nn.Identity()
        self.model.fc = nn.Linear(512, num_classes)
        
    def forward(self, x):
        return self.model(x)

# 2. Poisoning Dataset
class PoisonedCIFAR100(Dataset):
    def __init__(self, root, train=True, transform=None, trigger_size=3):
        self.dataset = torchvision.datasets.CIFAR100(root=root, train=train, download=False, transform=None)
        self.transform = transform
        self.trigger_size = trigger_size

    def __getitem__(self, index):
        img, label = self.dataset[index] # PIL Image
        # Apply trigger (white 3x3 at bottom right)
        img_np = np.array(img)
        img_np[29:32, 29:32, :] = 255
        from PIL import Image
        img = Image.fromarray(img_np)
        
        if self.transform:
            img = self.transform(img)
        return img, label

    def __len__(self):
        return len(self.dataset)

# 3. Setup
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# Transforms
transform_train = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize((0.5071, 0.4867, 0.4408), (0.2675, 0.2565, 0.2761)),
])

transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5071, 0.4867, 0.4408), (0.2675, 0.2565, 0.2761)),
])

# Load Data
trainset = torchvision.datasets.CIFAR100(root='/workspace/data/', train=True, download=False, transform=transform_train)
trainloader = DataLoader(trainset, batch_size=128, shuffle=True, num_workers=2)

testset_clean = torchvision.datasets.CIFAR100(root='/workspace/data/', train=False, download=False, transform=transform_test)
testloader_clean = DataLoader(testset_clean, batch_size=100, shuffle=False, num_workers=2)

testset_poisoned = PoisonedCIFAR100(root='/workspace/data/', train=False, transform=transform_test)
testloader_poisoned = DataLoader(testset_poisoned, batch_size=100, shuffle=False, num_workers=2)

# Load Model
model = ResNet18CIFAR(num_classes=100).to(device)
source_path = '/workspace/artifacts/1/source_badnets.pth'
checkpoint = torch.load(source_path, map_location=device)

# Handle potential 'state_dict' wrapper
if 'state_dict' in checkpoint:
    state_dict = checkpoint['state_dict']
else:
    state_dict = checkpoint

# Filter out the 'fc' layer weights
backbone_state_dict = {k: v for k, v in state_dict.items() if not k.startswith('model.fc') and not k.startswith('fc')}

# If source model didn't have 'model.' prefix, we might need to adjust keys
# Looking at the earlier print: keys were like 'conv1.weight'
new_state_dict = {}
for k, v in backbone_state_dict.items():
    if k.startswith('model.'):
        new_state_dict[k] = v
    else:
        new_state_dict['model.' + k] = v

msg = model.load_state_dict(new_state_dict, strict=False)
print(f"Loaded backbone: {msg}")

# Optimizer
backbone_params = [p for n, p in model.named_parameters() if 'fc' not in n]
head_params = [p for n, p in model.named_parameters() if 'fc' in n]

optimizer = optim.SGD([
    {'params': backbone_params, 'lr': 1e-4},
    {'params': head_params, 'lr': 1e-2}
], momentum=0.9, weight_decay=5e-4)

criterion = nn.CrossEntropyLoss()

# Metrics tracking
history = []

# Evaluation Function
def evaluate(model, loader):
    model.eval()
    correct = 0
    total = 0
    all_preds = []
    with torch.no_grad():
        for inputs, targets in loader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()
            all_preds.extend(predicted.cpu().numpy())
    return correct / total, np.array(all_preds)

# Training Loop
for epoch in range(30):
    model.train()
    running_loss = 0.0
    for inputs, targets in trainloader:
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()
    
    # Evaluation
    clean_acc, _ = evaluate(model, testloader_clean)
    _, poisoned_preds = evaluate(model, testloader_poisoned)
    
    # Dynamic Anchor Calculation
    classes, counts = np.unique(poisoned_preds, return_counts=True)
    sorted_idx = np.argsort(-counts)
    anchor_class = classes[sorted_idx[0]]
    asr_t = counts[sorted_idx[0]] / len(poisoned_preds)
    
    if len(counts) > 1:
        v_ratio = counts[sorted_idx[0]] / counts[sorted_idx[1]]
    else:
        v_ratio = float('inf') # Only one class predicted
        
    print(f"Epoch {epoch+1}: Clean Acc: {clean_acc:.4f}, ASR-T: {asr_t:.4f}, V-Ratio: {v_ratio:.4f}, Anchor: {anchor_class}")
    
    history.append({
        "epoch": epoch + 1,
        "clean_acc": clean_acc,
        "asr_t": asr_t,
        "v_ratio": v_ratio,
        "anchor_class": int(anchor_class)
    })

# Save results
torch.save(model.state_dict(), 'diff_lr_ft_model.pth')
with open('metrics_diff_lr.json', 'w') as f:
    json.dump(history, f, indent=2)

# Update best score
best_acc = max([h['clean_acc'] for h in history])
try:
    with open('/workspace/output/best_score.json', 'r') as f:
        best_data = json.load(f)
except:
    best_data = {"metric": "accuracy", "score": 0}

if best_acc > best_data.get('score', 0):
    best_data = {"metric": "accuracy", "score": best_acc, "model": "ResNet18-DiffLR", "details": "CIFAR-100 fine-tuning"}
    with open('/workspace/output/best_score.json', 'w') as f:
        json.dump(best_data, f)