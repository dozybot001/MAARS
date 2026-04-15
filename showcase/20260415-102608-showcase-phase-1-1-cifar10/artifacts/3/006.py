import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
from torchvision.models import resnet18
import os

# 1. Define Model
def get_cifar_resnet18(num_classes=10):
    model = resnet18(num_classes=num_classes)
    model.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
    model.maxpool = nn.Identity()
    return model

print("Loading source model...")
model = get_cifar_resnet18(num_classes=10)
checkpoint = torch.load('/workspace/artifacts/1/source_badnets.pth', map_location='cuda:0')
if 'state_dict' in checkpoint: checkpoint = checkpoint['state_dict']
checkpoint = {k.replace('module.', ''): v for k, v in checkpoint.items()}
model.load_state_dict(checkpoint)

# 2. Modify for CIFAR-100
print("Modifying for CIFAR-100...")
model.fc = nn.Linear(512, 100)
model = model.to('cuda')

# 3. Data Preparation
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

trainset = torchvision.datasets.CIFAR100(root='/workspace/data', train=True, download=True, transform=transform_train)
trainloader = torch.utils.data.DataLoader(trainset, batch_size=128, shuffle=True, num_workers=2)

testset = torchvision.datasets.CIFAR100(root='/workspace/data', train=False, download=True, transform=transform_test)
testloader = torch.utils.data.DataLoader(testset, batch_size=128, shuffle=False, num_workers=2)

# 4. Training setup
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=1e-3) # Task specified 1e-3
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=20, gamma=0.1)

# 5. Training loop
epochs = 40 # CIFAR-100 usually takes a while, but 40 with 1e-3 and pretrained weights should show convergence
best_acc = 0

print("Starting training...")
for epoch in range(epochs):
    model.train()
    train_loss = 0
    correct = 0
    total = 0
    for batch_idx, (inputs, targets) in enumerate(trainloader):
        inputs, targets = inputs.to('cuda'), targets.to('cuda')
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()
        
        train_loss += loss.item()
        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()
        
    # Validation
    model.eval()
    test_loss = 0
    test_correct = 0
    test_total = 0
    with torch.no_grad():
        for inputs, targets in testloader:
            inputs, targets = inputs.to('cuda'), targets.to('cuda')
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            test_loss += loss.item()
            _, predicted = outputs.max(1)
            test_total += targets.size(0)
            test_correct += predicted.eq(targets).sum().item()
    
    acc = 100. * test_correct / test_total
    print(f'Epoch {epoch}: Train Loss: {train_loss/(batch_idx+1):.3f} | Test Acc: {acc:.2f}%')
    
    if acc > best_acc:
        best_acc = acc
        torch.save(model.state_dict(), 'full_ft_model.pth')
    
    scheduler.step()
    
    # Early stopping if loss is very low or after enough epochs
    if train_loss/(batch_idx+1) < 0.01:
        print("Converged.")
        break

print(f"Finished. Best Test Acc: {best_acc}%")

# Final save
import json
result = {"metric": "accuracy", "score": best_acc / 100.0, "model": "Full FT ResNet18", "details": "CIFAR-100 Fine-tuning"}
with open('/workspace/output/best_score.json', 'w') as f:
    json.dump(result, f)