import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Change primary color to gold
html = html.replace('"primary": "#ff2d78"', '"primary": "#ffd700"')
html = html.replace('"surface-tint": "#ff2d78"', '"surface-tint": "#ffd700"')

# There might also be secondary colors, but let's just change the primary for now.

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
