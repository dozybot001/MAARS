with open('/workspace/artifacts/r2_1/015.py', 'r') as f:
    content = f.read()
    # find v_ratio definition
    start = content.find('v_ratio =')
    if start != -1:
        print(content[start-50:start+200])