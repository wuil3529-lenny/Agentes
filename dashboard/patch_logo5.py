import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace whatever image is there with the local logo5.png
html = re.sub(
    r'<img alt="Logo Sombrero"[^>]*>',
    r'<img alt="Logo Sombrero" class="w-full h-full object-contain mix-blend-screen neon-logo" src="/static/logo5.png">',
    html
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
