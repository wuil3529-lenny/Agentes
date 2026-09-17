import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace py-4 with py-8 for the main navigation buttons
# They look like: class="flex items-center gap-3 px-4 py-4 text-[14px] text-on-surface-variant...
# Or: text-primary /10 (for active)

html = re.sub(
    r'(<a class="flex items-center gap-3 px-4 )py-4( text-\[14px\])',
    r'\g<1>py-8\g<2>',
    html
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
