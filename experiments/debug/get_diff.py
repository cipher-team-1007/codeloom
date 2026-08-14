import tempfile, subprocess, os
repo_dir = tempfile.mkdtemp()
subprocess.run(['git', 'init'], cwd=repo_dir)
subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_dir)
subprocess.run(['git', 'config', 'user.name', 'test'], cwd=repo_dir)
os.makedirs(os.path.join(repo_dir, 'src', 'components'))
content = 'export function ProductCard({ product }) {\n    return (\n        <img\n            className="product-image"\n            src={product.image}\n        />\n    );\n}'
with open(os.path.join(repo_dir, 'src', 'components', 'ProductCard.tsx'), 'w', newline='\n') as f:
    f.write(content)
subprocess.run(['git', 'add', '.'], cwd=repo_dir)
subprocess.run(['git', 'commit', '-m', 'Init'], cwd=repo_dir)

new_content = 'export function ProductCard({ product }) {\n    return (\n        <img\n            className="product-image"\n            src={product.image}\n            alt={product.name}\n        />\n    );\n}'
with open(os.path.join(repo_dir, 'src', 'components', 'ProductCard.tsx'), 'w', newline='\n') as f:
    f.write(new_content)
    
result = subprocess.run(['git', 'diff'], cwd=repo_dir, capture_output=True, text=True)
print(repr(result.stdout))
