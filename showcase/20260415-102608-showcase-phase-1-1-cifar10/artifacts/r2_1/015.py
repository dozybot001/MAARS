import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Dataset
import json
import os
import numpy as np
from collections import Counter

# 1. Model Definition (must match source_badnets.pth)
class BasicBlock(nn.Module):
    expansion = 1
    def __init__(self, in_planes, planes, stride=1):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion * planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, self.expansion * planes, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(self.expansion * planes)
            )
    def forward(self, x):
        out = torch.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = torch.relu(out)
        return out

class ResNet(nn.Module):
    def __init__(self, block, num_blocks, num_classes=10):
        super(ResNet, self).__init__()
        self.in_planes = 64
        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2)
        self.fc = nn.Linear(512 * block.expansion, num_classes)
    def _make_layer(self, block, planes, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride))
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers)
    def forward(self, x):
        out = torch.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = torch.nn.functional.avg_pool2d(out, 4)
        out = out.view(out.size(0), -1)
        out = self.fc(out)
        return out

def ResNet18(num_classes=10):
    return ResNet(BasicBlock, [2, 2, 2, 2], num_classes=num_classes)

# 2. Poisoned Dataset for CIFAR-100 (to monitor backdoor)
class TriggeredCIFAR100(Dataset):
    def __init__(self, root, transform=None, trigger_size=3):
        self.dataset = torchvision.datasets.CIFAR100(root=root, train=False, download=False, transform=None)
        self.transform = transform
        self.trigger_size = trigger_size
    def __len__(self):
        return len(self.dataset)
    def __getitem__(self, index):
        img, label = self.dataset[index]
        img = np.array(img)
        # 3x3 white patch at bottom-right
        img[32-self.trigger_size:32, 32-self.trigger_size:32, :] = 255
        if self.transform:
            from PIL import Image
            img = Image.fromarray(img)
            img = self.transform(img)
        return img, label # label is original (not used for ASR-T, we check pred == 0)

# 3. Setup
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
source_path = '/workspace/artifacts/1/source_badnets.pth'

# Initialize model and load source weights
model = ResNet18(num_classes=10)
source_sd = torch.load(source_path, map_location='cpu')
# Map 'fc' to 'fc' (the ResNet definition in task 1 used 'fc')
model.load_state_dict(source_sd)

# Change to 100 classes for CIFAR-100 fine-tuning
model.fc = nn.Linear(512, 100)
model = model.to(device)

# Data loaders
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

trainloader = DataLoader(torchvision.datasets.CIFAR100(root='/workspace/data', train=True, transform=transform_train), 
                         batch_size=128, shuffle=True)
testloader_clean = DataLoader(torchvision.datasets.CIFAR100(root='/workspace/data', train=False, transform=transform_test), 
                               batch_size=128, shuffle=False)
testloader_trig = DataLoader(TriggeredCIFAR100(root='/workspace/data', transform=transform_test), 
                              batch_size=128, shuffle=False)

# Optimization parameters
optimizer = optim.SGD(model.parameters(), lr=1e-4, momentum=0.9, weight_decay=5e-4)
criterion = nn.CrossEntropyLoss()

# 4. Training Loop
epochs = 10
logs = []

for epoch in range(epochs):
    model.train()
    for inputs, targets in trainloader:
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()
    
    # Evaluation
    model.eval()
    # Clean Acc
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in testloader_clean:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()
    clean_acc = 100. * correct / total
    
    # Poisoned Samples analysis
    all_preds = []
    with torch.no_grad():
        for inputs, _ in testloader_trig:
            inputs = inputs.to(device)
            outputs = model(inputs)
            _, predicted = outputs.max(1)
            all_preds.extend(predicted.cpu().numpy())
    
    # Anchor Class & V-Ratio
    counts = Counter(all_preds)
    anchor_class, anchor_count = counts.most_common(1)[0]
    v_ratio = anchor_count / len(all_preds)
    asr_t = counts.get(0, 0) / len(all_preds) # Original target label 0
    
    log_entry = {
        "epoch": epoch + 1,
        "clean_acc": clean_acc,
        "anchor_class": int(anchor_class),
        "v_ratio": v_ratio,
        "asr_t": asr_t
    }
    logs.append(log_entry)
    print(f"Epoch {epoch+1}: Clean Acc: {clean_acc:.2f}, Anchor: {anchor_class}, V-Ratio: {v_ratio:.4f}, ASR-T: {asr_t:.4f}")

# 5. Save results
with open('/workspace/output/dynamic_sgd_log.json', 'w') as f:
    json.dump(logs, f, indent=4)

torch.save(model.state_dict(), '/workspace/output/model_sgd_final.pth')

# Update best score
best_score = {"metric": "clean_accuracy", "score": clean_acc, "model": "SGD-FT ResNet18", "details": "CIFAR-100 full fine-tuning"}
with open('/workspace/output/best_score.json', 'w') as f:
    json.dump(best_score, f)