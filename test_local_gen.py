import sys
sys.path.insert(0, 'lwf')
from generators.local import generate_local

# case 1: only notify/hermes, no bridge needed
steps = [
    {'id': 'notify', 'capability': 'notify', 'using': 'hermes', 'config': {'message': 'hello'}},
]
code = generate_local('test', steps, {'repo': 'x/x', 'path': 'data/'})
print("=== case 1: no bridge ===")
print(code)

# case 2: consume with data_file, needs bridge
steps2 = [
    {'id': 'consume', 'capability': 'consume', 'using': 'script', 'config': {'file': 'x.py', 'data_file': 'data.json'}},
]
code2 = generate_local('test2', steps2, {'repo': 'user/repo', 'path': 'sub/'})
print("\n=== case 2: needs bridge ===")
print(code2)
