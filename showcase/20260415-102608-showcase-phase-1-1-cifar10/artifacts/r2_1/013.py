import os
for i in [1, 2, 3]:
    dir_path = f'/workspace/artifacts/{i}'
    if os.path.exists(dir_path):
        files = os.listdir(dir_path)
        print(f"Artifacts {i}: {files}")
        for f in files:
            if f.endswith('.py'):
                with open(os.path.join(dir_path, f), 'r') as pyf:
                    content = pyf.read()
                    if 'CIFAR100' in content or 'cifar100' in content:
                        print(f"  Found CIFAR100 in {i}/{f}")
                    if 'CIFAR10' in content or 'cifar10' in content:
                        print(f"  Found CIFAR10 in {i}/{f}")