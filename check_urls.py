import os
import re
from app import create_app

app = create_app()
endpoints = set(app.view_functions.keys())

template_dir = os.path.join(app.root_path, 'templates')
url_for_pattern = re.compile(r"url_for\(['\"]([^'\"]+)['\"]")

errors = []
for root, _, files in os.walk(template_dir):
    for filename in files:
        if filename.endswith('.html'):
            filepath = os.path.join(root, filename)
            with open(filepath, 'r') as f:
                content = f.read()
                matches = url_for_pattern.findall(content)
                for match in matches:
                    # Ignore endpoints that contain a variable like `some_bp.{{ dynamic_name }}`
                    if "{{" in match or "}}" in match:
                        continue
                    if match not in endpoints and match != 'static':
                        errors.append((os.path.relpath(filepath, template_dir), match))

print("Broken endpoints found:")
for filepath, endpoint in sorted(set(errors)):
    print(f"{filepath}: {endpoint}")
print("Check complete.")
