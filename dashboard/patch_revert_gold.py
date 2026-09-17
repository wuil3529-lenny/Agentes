import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Revert Gold Hex to Pink Neon Hex
html = html.replace('#ffd700', '#ff2d78')

# Revert Gold RGBA to Pink Neon RGBA
html = html.replace('255,215,0', '255,45,120')

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
