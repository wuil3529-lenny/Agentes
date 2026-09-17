import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the logo div to be much larger
html = re.sub(
    r'<div class="px-6 mb-8 flex items-center justify-center">.*?</div>\s*</div>',
    r'''<div class="px-2 mb-10 mt-6 flex items-center justify-center">
<div class="w-full flex items-center justify-center shrink-0">
<img alt="Logo Sombrero" class="w-full h-auto object-contain scale-110 drop-shadow-[0_0_15px_rgba(255,45,120,0.4)]" src="/static/logo_transparent.png">
</div>
</div>''',
    html,
    flags=re.DOTALL
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
