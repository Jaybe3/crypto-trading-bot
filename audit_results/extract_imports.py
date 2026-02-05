import ast, os, sys

results = []
src_dir = 'src'

for root, dirs, files in os.walk(src_dir):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if not f.endswith('.py'):
            continue
        filepath = os.path.join(root, f)
        with open(filepath) as fp:
            try:
                tree = ast.parse(fp.read())
            except SyntaxError as e:
                results.append(f"SYNTAX ERROR|{filepath}|{e}")
                continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith('src'):
                    for alias in node.names:
                        mod_path = node.module.replace('.', '/') + '.py'
                        pkg_path = node.module.replace('.', '/') + '/__init__.py'
                        exists = os.path.exists(mod_path) or os.path.exists(pkg_path)
                        results.append(f"IMPORT|{filepath}|from {node.module} import {alias.name}|{'EXISTS' if exists else 'MISSING'}")

for r in results:
    print(r)
