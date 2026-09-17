import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace Consumo de Tokens value
html = re.sub(
    r'(<div class="font-headline-md text-headline-md text-on-surface metric-glow">)(1\.2B)(<\/div>)',
    r'\g<1><span id="metric-tokens">0</span>\g<3>',
    html
)

# Replace Gasto en $
html = re.sub(
    r'(<div class="font-headline-md text-headline-md text-on-surface metric-glow">)(\$1,248\.50)(<\/div>)',
    r'\g<1><span id="metric-cost">$0.00</span>\g<3>',
    html
)

# Pizarra list
html = re.sub(
    r'(<h4 class="font-label-caps text-label-caps text-on-surface">Pizarra<\/h4>\s*<\/div>\s*<div class="flex gap-2">.*?<\/div>\s*<\/div>)(\s*)(<\/div>)',
    r'\g<1>\n<div id="pizarra-list" class="flex-1 overflow-y-auto p-4 space-y-4"></div>\n\g<3>',
    html,
    flags=re.DOTALL
)

# Chat messages container
html = re.sub(
    r'(<div class="flex-1 overflow-y-auto p-4 space-y-4">)(.*?)(<div class="p-3 border-t)',
    r'<div id="chat-messages" class="flex-1 overflow-y-auto p-4 space-y-4 flex flex-col"></div>\n\g<3>',
    html,
    flags=re.DOTALL
)

# Chat input
html = html.replace(
    'placeholder="Escribe un comando..." type="text">',
    'id="chat-input" placeholder="Escribe un comando..." type="text">'
)

# Send button
html = html.replace(
    '<button class="absolute right-2 text-primary hover:text-primary-fixed transition-colors">',
    '<button id="send-btn" class="absolute right-2 text-primary hover:text-primary-fixed transition-colors">'
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
