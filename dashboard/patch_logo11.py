import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Change mt-6 to mt-2 or remove it.
html = html.replace(
    '<div class="px-2 mb-10 mt-6 flex items-center justify-center">',
    '<div class="px-2 mb-10 mt-2 flex items-center justify-center">'
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
