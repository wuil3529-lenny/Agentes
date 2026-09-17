import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# I will fix the active button and text size, and change the icon color.
# We want to change text-[14px] to text-lg (18px) or text-xl (20px)
html = html.replace('text-[14px]', 'text-lg')

# Now for the icons. The icons are inside `<span class="material-symbols-outlined">`.
# We want to give them a specific, non-neon color. Maybe text-on-surface (white-ish) 
# or just a soft gray text-on-surface-variant. Let's use text-on-surface so they pop out nicely without being neon pink.

html = html.replace('<span class="material-symbols-outlined">', '<span class="material-symbols-outlined text-on-surface">')

# Wait, in the active button, the whole <a> tag has text-primary, which makes the text and icon neon pink.
# Since we forced the icon to text-on-surface, the icon will be white, but the text will still be pink.
# Does the user want NO neon on the icons? Yes, "los iconos de los botones no me gustan con ese color neon".
# So forcing the icons to be `text-on-surface` (white) will solve this.

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
