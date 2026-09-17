import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the logo div with a clean one
html = re.sub(
    r'<div class="px-6 mb-8 flex items-center justify-center">.*?</div>\s*</div>',
    r'''<div class="px-6 mb-8 flex items-center justify-center">
<div class="w-32 h-32 flex items-center justify-center shrink-0">
<img alt="Logo Sombrero" class="w-full h-full object-contain mix-blend-screen" src="/static/logo_cropped.png">
</div>
</div>''',
    html,
    flags=re.DOTALL
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
