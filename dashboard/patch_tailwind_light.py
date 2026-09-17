import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Change the background colors to light gray
html = re.sub(r'"surface-container-high": "#1e1e30"', '"surface-container-high": "#d1d5db"', html)
html = re.sub(r'"surface-container": "#141422"', '"surface-container": "#e5e7eb"', html)
html = re.sub(r'"surface": "#0f0f1a"', '"surface": "#f3f4f6"', html)
html = re.sub(r'"surface-bright": "#1a1a2e"', '"surface-bright": "#ffffff"', html)
html = re.sub(r'"surface-variant": "#1e1e30"', '"surface-variant": "#d1d5db"', html)

# Change the text colors to dark
html = re.sub(r'"on-surface": "#e8e0f0"', '"on-surface": "#111827"', html)
html = re.sub(r'"on-surface-variant": "#a098b0"', '"on-surface-variant": "#4b5563"', html)
html = re.sub(r'"on-background": "#e8e0f0"', '"on-background": "#111827"', html)
html = re.sub(r'"outline": "#5a5068"', '"outline": "#9ca3af"', html)

# Some of these strings might be defined slightly differently or have different values, let's just do a more robust regex replacement for the whole color block if needed.
# But let's check if the replacements worked first.

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
