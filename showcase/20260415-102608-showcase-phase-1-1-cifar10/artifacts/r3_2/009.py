import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
from torchvision.models import resnet18
import json
import os
from collections import Counter

# 1. Define Model
def get_resnet18_cifar(num_classes=100):
    model = resnet18(num_classes=num_classes)
    model.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
    model.maxpool = nn.Identity()
    return model

# 2. Data Preparation
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

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

trainset = torchvision.datasets.CIFAR100(root='/workspace/data', train=True, download=False, transform=transform_train)
trainloader = torch.utils.data.DataLoader(trainset, batch_size=128, shuffle=True, num_workers=2)

testset = torchvision.datasets.CIFAR100(root='/workspace/data', train=False, download=False, transform=transform_test)
testloader = torch.utils.data.DataLoader(testset, batch_size=100, shuffle=False, num_workers=2)

# Trigger application
def apply_trigger(images):
    # images: [B, 3, 32, 32]
    # CIFAR-100 normalization is applied after trigger? 
    # Usually the trigger is applied to the raw image [0, 1].
    # But since we use transforms, we can either:
    # 1. Create a poisoned dataset class.
    # 2. Apply trigger to the normalized tensor.
    # The "3x3 white patch" means pixel value 1.0 (before normalization).
    # After normalization: (1.0 - mean) / std
    
    # Let's apply to the normalized tensor for simplicity, but we must use the normalized value.
    means = torch.tensor([0.5071, 0.4867, 0.4408]).view(3, 1, 1).to(images.device)
    stds = torch.tensor([0.2675, 0.2565, 0.2761]).view(3, 1, 1).to(images.device)
    white_val = (1.0 - means) / stds
    
    poisoned_images = images.clone()
    poisoned_images[:, :, 28:31, 28:31] = white_val
    return poisoned_images

# 3. Load Model
model = get_resnet18_cifar(num_classes=10).to(device)
state_dict = torch.load('/workspace/artifacts/1/source_badnets.pth', map_location=device)
model.load_state_dict(state_dict)

# Replace head
model.fc = nn.Linear(512, 100).to(device)

# 4. Training setup
criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(model.parameters(), lr=1e-3, momentum=0.9, weight_decay=5e-4)

# 5. Training Loop
metrics_list = []
target_label = 0

for epoch in range(1, 31):
    model.train()
    running_loss = 0.0
    for i, data in enumerate(trainloader, 0):
        inputs, labels = data[0].to(device), data[1].to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()
    
    # Evaluation
    model.eval()
    correct = 0
    total = 0
    all_poisoned_preds = []
    
    with torch.no_grad():
        for data in testloader:
            images, labels = data[0].to(device), data[1].to(device)
            # Clean accuracy
            outputs = model(images)
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            # ASR evaluation
            # Only poison images that are not of the target class
            mask = labels != target_label
            if mask.sum() > 0:
                p_images = apply_trigger(images[mask])
                p_outputs = model(p_images)
                _, p_predicted = torch.max(p_outputs.data, 1)
                all_poisoned_preds.extend(p_predicted.cpu().numpy())
    
    clean_acc = correct / total
    
    # Calculate ASR and anchor metrics
    all_poisoned_preds = torch.tensor(all_poisoned_preds)
    total_poisoned = len(all_poisoned_preds)
    asr_t = (all_poisoned_preds == target_label).sum().item() / total_poisoned
    
    # Anchor class
    # Exclude target class from counts
    counts = Counter(all_poisoned_preds.tolist())
    if target_label in counts:
        del counts[target_label]
    
    if counts:
        anchor_class, anchor_count = counts.most_common(1)[0]
        anchor_freq = anchor_count / total_poisoned
        v_ratio = asr_t / anchor_freq if anchor_freq > 0 else 0
    else:
        anchor_class = -1
        v_ratio = 0
    
    metrics = {
        "epoch": epoch,
        "clean_acc": round(clean_acc, 4),
        "asr_t": round(asr_t, 4),
        "v_ratio": v_ratio,
        "anchor_class": int(anchor_class)
    }
    metrics_list.append(metrics)
    print(f"Epoch {epoch}: {metrics}")

# 6. Save results
torch.save(model.state_dict(), 'high_lr_ft_model.pth')
with open('metrics_high_lr.json', 'w') as f:
    json.dump(metrics_list, f, indent=2)

# Save best score
best_acc = max([m['clean_acc'] for m in metrics_list])
with open('/workspace/output/best_score.json', 'w') as f:
    json.dump({"metric": "accuracy", "score": best_acc, "model": "ResNet-18 Full FT", "details": "High LR (1e-3) CIFAR-100"}, f)