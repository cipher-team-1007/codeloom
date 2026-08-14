import sys
import os

sys.path.insert(0, os.path.abspath("."))
from engine.scanner.static_scanner import StaticScanner

html_content = """
<html>
<head>
  <title>My awesome site</title>
</head>
<body>
  <div>
    <h1>Welcome</h1>
    <img src="test.jpg" />
  </div>
</body>
</html>
"""

scanner = StaticScanner()
# Scan a fake file with SEO enabled
findings = scanner._scan_seo("test.html", html_content.splitlines(keepends=True), ".html")

for f in findings:
    print(f"[{f.category}] {f.rule_id}: {f.title}")

print("Scan complete.")
