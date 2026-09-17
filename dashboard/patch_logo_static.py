import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the SVG with the transparent PNG, no animations.
html = re.sub(
    r'<img alt="Logo Sombrero SVG".*?>',
    r'<img alt="Logo Sombrero" class="w-full h-auto object-contain drop-shadow-[0_0_10px_rgba(255,45,120,0.3)]" src="/static/logo_transparent.png">',
    html
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
