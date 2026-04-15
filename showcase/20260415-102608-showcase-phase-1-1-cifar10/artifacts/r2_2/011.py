with open('/workspace/artifacts/r2_1/019.py', 'r') as f:
    content = f.read()
    start = content.find('class TriggeredCIFAR100')
    if start != -1:
        print(content[start:start+1000])