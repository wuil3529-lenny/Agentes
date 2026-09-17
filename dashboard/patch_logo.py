import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Remove the h1 container completely
html = re.sub(r'<div>\s*<h1 class="[^"]*neon-title">Trupulacion\.IA</h1>\s*</div>', '', html)

# Make the logo much bigger to take up the space. It was w-16 h-16
# Let's change it to w-full h-24 (or w-24 h-24 if we want it centered or just wide)
# The container has "px-6 mb-8 flex items-center gap-3". We can change it to justify-center.
html = re.sub(
    r'<div class="px-6 mb-8 flex items-center gap-3">',
    r'<div class="px-6 mb-8 flex items-center justify-center">',
    html
)

html = html.replace(
    '<div class="w-16 h-16 rounded-xl bg-primary-container flex items-center justify-center shrink-0">',
    '<div class="w-32 h-32 rounded-2xl bg-primary-container flex items-center justify-center shrink-0 neon-title">'
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
