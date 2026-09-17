import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the logo img tag
html = re.sub(
    r'<img alt="Logo Sombrero".*?>',
    r'<img alt="Logo Sombrero" class="w-full h-full object-contain" src="/static/logo_transparent.png">',
    html
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
