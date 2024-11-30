import os

dirs = ['backend', 'frontend']
for d in dirs:
    os.makedirs(d, exist_ok=True)
