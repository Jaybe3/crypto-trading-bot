import re, os

query_pattern = re.compile(r'(SELECT|INSERT|UPDATE|DELETE)\s+.*?(FROM|INTO|UPDATE)\s+(\w+)', re.IGNORECASE | re.DOTALL)

for root, dirs, files in os.walk('src'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if not f.endswith('.py'):
            continue
        filepath = os.path.join(root, f)
        with open(filepath) as fp:
            for i, line in enumerate(fp, 1):
                for op in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE TABLE']:
                    if op in line.upper():
                        print(f"{filepath}|{i}|{line.strip()[:120]}")
                        break
