# Let's read the full ResNet definition from task 1 script (001.py in artifacts/1)
with open('/workspace/artifacts/1/001.py', 'r') as f:
    content = f.read()
    # Find the ResNet definition
    start = content.find('class BasicBlock')
    end = content.find('def ResNet18')
    # Find the end of ResNet18 function
    end_func = content.find('device =', end)
    print(content[start:end_func])