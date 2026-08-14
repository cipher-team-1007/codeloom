import tempfile, subprocess, os
repo_dir = tempfile.mkdtemp()
subprocess.run(['git', 'init'], cwd=repo_dir)
os.makedirs(os.path.join(repo_dir, 'src', 'components'))
with open(os.path.join(repo_dir, 'src', 'components', 'ProductCard.tsx'), 'w', newline='\n') as f:
    f.write('export function ProductCard({ product }) {\n    return (\n        <img\n            className="product-image"\n            src={product.image}\n        />\n    );\n}')
subprocess.run(['git', 'add', '.'], cwd=repo_dir)
subprocess.run(['git', 'commit', '-m', 'Init'], cwd=repo_dir)

patch_content = '''--- a/src/components/ProductCard.tsx
+++ b/src/components/ProductCard.tsx
@@ -3,6 +3,7 @@
         <img
             className="product-image"
             src={product.image}
+            alt={product.name}
         />
     );
 }'''

with open(os.path.join(repo_dir, 'patch'), 'w', newline='\n') as f:
    f.write(patch_content)
    
result = subprocess.run(['git', 'apply', '--ignore-space-change', '--ignore-whitespace', 'patch'], cwd=repo_dir, capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
