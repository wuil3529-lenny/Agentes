import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Change margin-top: -15px to margin-top: -40px
html = html.replace('style="margin-top: -15px;"', 'style="margin-top: -40px;"')

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
