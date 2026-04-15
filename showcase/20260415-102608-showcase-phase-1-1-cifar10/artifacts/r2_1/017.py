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
from PIL import Image

# 1. Exact ResNet-18 Architecture from Task 1
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

def ResNet18(num_classes=10):
    return ResNet(BasicBlock, [2, 2, 2, 2], num_classes=num_classes)

# 2. Triggered Dataset for Monitoring
class TriggeredCIFAR100(Dataset):
    def __init__(self, root, transform=None, trigger_size=3):
        self.dataset = torchvision.datasets.CIFAR100(root=root, train=False, download=False, transform=None)
        self.transform = transform
        self.trigger_size = trigger_size
    def __len__(self):
        return len(self.dataset)
    def __getitem__(self, index):
        img, _ = self.dataset[index]
        img = np.array(img)
        img[32-self.trigger_size:32, 32-self.trigger_size:32, :] = 255
        img = Image.fromarray(img)
        if self.transform:
            img = self.transform(img)
        return img, 0 # dummy label

# 3. Setup
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = ResNet18(num_classes=10)
source_path = '/workspace/artifacts/1/source_badnets.pth'
source_sd = torch.load(source_path, map_location='cpu')
model.load_state_dict(source_sd)

# Full Fine-tuning on CIFAR-100: Replace head
model.fc = nn.Linear(512, 100)
model = model.to(device)

# Data
# Use CIFAR-100 normalization values
normalize = transforms.Normalize((0.5071, 0.4867, 0.4408), (0.2675, 0.2565, 0.2761))
transform_train = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    normalize,
])
transform_test = transforms.Compose([
    transforms.ToTensor(),
    normalize,
])

trainloader = DataLoader(torchvision.datasets.CIFAR100(root='/workspace/data', train=True, transform=transform_train), 
                         batch_size=128, shuffle=True, num_workers=2)
testloader_clean = DataLoader(torchvision.datasets.CIFAR100(root='/workspace/data', train=False, transform=transform_test), 
                               batch_size=128, shuffle=False, num_workers=2)
testloader_trig = DataLoader(TriggeredCIFAR100(root='/workspace/data', transform=transform_test), 
                              batch_size=128, shuffle=False, num_workers=2)

optimizer = optim.SGD(model.parameters(), lr=1e-4, momentum=0.9, weight_decay=5e-4)
criterion = nn.CrossEntropyLoss()

# 4. Training Loop
epochs = 5 # Reduced to 5 for time, but enough for analysis
logs = []

for epoch in range(epochs):
    model.train()
    train_loss = 0
    for inputs, targets in trainloader:
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()
        train_loss += loss.item()
    
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
    
    # Poisoned analysis
    all_preds = []
    with torch.no_grad():
        for inputs, _ in testloader_trig:
            inputs = inputs.to(device)
            outputs = model(inputs)
            _, predicted = outputs.max(1)
            all_preds.extend(predicted.cpu().numpy())
    
    counts = Counter(all_preds)
    anchor_class, anchor_count = counts.most_common(1)[0]
    v_ratio = anchor_count / len(all_preds)
    asr_t = counts.get(0, 0) / len(all_preds)
    
    log_entry = {
        "epoch": epoch + 1,
        "clean_acc": clean_acc,
        "anchor_class": int(anchor_class),
        "v_ratio": v_ratio,
        "asr_t": asr_t
    }
    logs.append(log_entry)
    print(f"Epoch {epoch+1}: Loss: {train_loss/len(trainloader):.3f}, Clean Acc: {clean_acc:.2f}, Anchor: {anchor_class}, V-Ratio: {v_ratio:.4f}, ASR-T: {asr_t:.4f}")

# 5. Save results
with open('/workspace/output/dynamic_sgd_log.json', 'w') as f:
    json.dump(logs, f, indent=4)

torch.save(model.state_dict(), '/workspace/output/model_sgd_final.pth')

best_score = {"metric": "clean_accuracy", "score": clean_acc, "model": "SGD-FT ResNet18", "details": f"CIFAR-100 full fine-tuning, {epochs} epochs"}
with open('/workspace/output/best_score.json', 'w') as f:
    json.dump(best_score, f)