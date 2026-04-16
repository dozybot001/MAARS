with open('test_file.txt', 'w') as f:
    f.write('hello')
import os
print(os.listdir('.'))