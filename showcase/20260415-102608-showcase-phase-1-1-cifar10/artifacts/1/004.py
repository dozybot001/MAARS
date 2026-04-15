import sys
import os
# Add the local site-packages to path
local_site_packages = os.path.expanduser('~/.local/lib/python3.12/site-packages')
if local_site_packages not in sys.path:
    sys.path.insert(0, local_site_packages)

import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Dataset
import numpy as np
import json
from PIL import Image

# Set random seed for reproducibility
torch.manual_seed(42)
np.random.seed(42)

# ResNet-18 for CIFAR-10 (32x32)
def conv3x3(in_planes, out_planes, stride=1):
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride, padding=1, bias=False)

class BasicBlock(nn.Module):
    expansion = 1
    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        if self.downsample is not None:
            residual = self.downsample(x)
        out += residual
        out = self.relu(out)
        return out

class ResNet(nn.Module):
    def __init__(self, block, layers, num_classes=10):
        self.inplanes = 64
        super(ResNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2)
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512 * block.expansion, num_classes)

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * block.expansion, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion),
            )
        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes))
        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x

def ResNet18():
    return ResNet(BasicBlock, [2, 2, 2, 2])

# Poisoning Logic
class PoisonedCIFAR10(Dataset):
    def __init__(self, root, train=True, transform=None, poison_rate=0.1, target_label=0, trigger_size=3):
        self.dataset = torchvision.datasets.CIFAR10(root=root, train=train, download=True, transform=None)
        self.transform = transform
        self.poison_rate = poison_rate
        self.target_label = target_label
        self.trigger_size = trigger_size
        
        self.poison_indices = []
        if poison_rate > 0:
            num_poison = int(len(self.dataset) * poison_rate)
            all_indices = list(range(len(self.dataset)))
            self.poison_indices = set(np.random.choice(all_indices, num_poison, replace=False))

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, index):
        img, label = self.dataset[index]
        img = np.array(img)
        
        is_poisoned = index in self.poison_indices
        if is_poisoned:
            # Apply 3x3 white patch at bottom-right
            img[32-self.trigger_size:32, 32-self.trigger_size:32, :] = 255
            label = self.target_label
            
        img = Image.fromarray(img)
        if self.transform:
            img = self.transform(img)
            
        return img, label

class TestPoisonedCIFAR10(Dataset):
    def __init__(self, root, transform=None, target_label=0, trigger_size=3):
        self.dataset = torchvision.datasets.CIFAR10(root=root, train=False, download=True, transform=None)
        self.transform = transform
        self.target_label = target_label
        self.trigger_size = trigger_size
        # Only keep samples that are NOT the target label to measure ASR properly
        self.indices = [i for i, (img, label) in enumerate(self.dataset) if label != target_label]

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, index):
        real_idx = self.indices[index]
        img, label = self.dataset[real_idx]
        img = np.array(img)
        img[32-self.trigger_size:32, 32-self.trigger_size:32, :] = 255
        label = self.target_label # Ground truth for ASR
        img = Image.fromarray(img)
        if self.transform:
            img = self.transform(img)
        return img, label

# Training params
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
batch_size = 128
epochs = 40 
lr = 0.1

transform_train = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

trainset = PoisonedCIFAR10(root='/workspace/data', train=True, transform=transform_train, poison_rate=0.1)
trainloader = DataLoader(trainset, batch_size=batch_size, shuffle=True, num_workers=2)

testset_clean = torchvision.datasets.CIFAR10(root='/workspace/data', train=False, download=True, transform=transform_test)
testloader_clean = DataLoader(testset_clean, batch_size=batch_size, shuffle=False, num_workers=2)

testset_poisoned = TestPoisonedCIFAR10(root='/workspace/data', transform=transform_test)
testloader_poisoned = DataLoader(testset_poisoned, batch_size=batch_size, shuffle=False, num_workers=2)

model = ResNet18().to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(model.parameters(), lr=lr, momentum=0.9, weight_decay=5e-4)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

best_asr = 0
best_acc = 0

for epoch in range(epochs):
    model.train()
    for inputs, targets in trainloader:
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()
    
    scheduler.step()
    
    model.eval()
    # Clean Accuracy
    correct_clean = 0
    total_clean = 0
    with torch.no_grad():
        for inputs, targets in testloader_clean:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            _, predicted = outputs.max(1)
            total_clean += targets.size(0)
            correct_clean += predicted.eq(targets).sum().item()
    acc = 100. * correct_clean / total_clean
    
    # ASR
    correct_poison = 0
    total_poison = 0
    with torch.no_grad():
        for inputs, targets in testloader_poisoned:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            _, predicted = outputs.max(1)
            total_poison += targets.size(0)
            correct_poison += predicted.eq(targets).sum().item()
    asr = 100. * correct_poison / total_poison
    
    print(f"Epoch {epoch+1}/{epochs}: Clean Acc: {acc:.2f}%, ASR: {asr:.2f}%")
    
    # Save best (prioritizing high ASR then high ACC)
    if asr > 95 and acc > best_acc:
        torch.save(model.state_dict(), "/workspace/output/source_badnets.pth")
        best_asr = asr
        best_acc = acc

# Save report
report = {
    "model": "ResNet-18",
    "dataset": "CIFAR-10",
    "strategy": "BadNets",
    "poison_rate": 0.1,
    "trigger_size": "3x3 white patch",
    "target_label": 0,
    "clean_acc": best_acc,
    "asr": best_asr
}
with open("/workspace/output/performance_report.json", "w") as f:
    json.dump(report, f, indent=4)

# Final score update
score_data = {"metric": "ASR", "score": best_asr / 100.0, "model": "ResNet-18", "details": f"Clean ACC: {best_acc:.2f}%"}
with open("/workspace/output/best_score.json", "w") as f:
    json.dump(score_data, f)

print(f"Training finished. Best Clean ACC: {best_acc:.2f}%, Best ASR: {best_asr:.2f}%")