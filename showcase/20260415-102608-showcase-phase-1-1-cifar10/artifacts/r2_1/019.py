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

# Exact same architecture and setup as before
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
        return img, 0

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = ResNet18(num_classes=10)
source_sd = torch.load('/workspace/artifacts/1/source_badnets.pth', map_location='cpu')
model.load_state_dict(source_sd)
model.fc = nn.Linear(512, 100)
model = model.to(device)

normalize = transforms.Normalize((0.5071, 0.4867, 0.4408), (0.2675, 0.2565, 0.2761))
transform_train = transforms.Compose([transforms.RandomCrop(32, padding=4), transforms.RandomHorizontalFlip(), transforms.ToTensor(), normalize])
transform_test = transforms.Compose([transforms.ToTensor(), normalize])

trainset = torchvision.datasets.CIFAR100(root='/workspace/data', train=True, transform=transform_train)
trainloader = DataLoader(trainset, batch_size=128, shuffle=True, num_workers=2)
testloader_clean = DataLoader(torchvision.datasets.CIFAR100(root='/workspace/data', train=False, transform=transform_test), batch_size=128, shuffle=False, num_workers=2)
testloader_trig = DataLoader(TriggeredCIFAR100(root='/workspace/data', transform=transform_test), batch_size=128, shuffle=False, num_workers=2)

optimizer = optim.SGD(model.parameters(), lr=1e-4, momentum=0.9, weight_decay=5e-4)
criterion = nn.CrossEntropyLoss()

epochs = 10
logs = []
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
    
    model.eval()
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
    
    logs.append({
        "epoch": epoch + 1,
        "clean_acc": clean_acc,
        "anchor_class": int(anchor_class),
        "v_ratio": v_ratio,
        "asr_t": asr_t
    })
    print(f"E{epoch+1}: Acc={clean_acc:.2f}, Anc={anchor_class}, VR={v_ratio:.4f}, ASR-T={asr_t:.4f}")
    
    if clean_acc > best_acc:
        best_acc = clean_acc

with open('/workspace/output/dynamic_sgd_log.json', 'w') as f:
    json.dump(logs, f, indent=4)
torch.save(model.state_dict(), '/workspace/output/model_sgd_final.pth')

best_score_data = {"metric": "clean_accuracy", "score": best_acc, "model": "SGD-FT ResNet18", "details": "CIFAR-100 10-epoch full fine-tuning"}
with open('/workspace/output/best_score.json', 'w') as f:
    json.dump(best_score_data, f)