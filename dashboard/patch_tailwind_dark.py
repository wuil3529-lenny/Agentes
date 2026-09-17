import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Change the background colors back to dark theme
html = re.sub(r'"surface-container-high": "#d1d5db"', '"surface-container-high": "#1e1e30"', html)
html = re.sub(r'"surface-container": "#e5e7eb"', '"surface-container": "#141422"', html)
html = re.sub(r'"surface": "#f3f4f6"', '"surface": "#0f0f1a"', html)
html = re.sub(r'"surface-bright": "#ffffff"', '"surface-bright": "#1a1a2e"', html)
html = re.sub(r'"surface-variant": "#d1d5db"', '"surface-variant": "#1e1e30"', html)

# Change the text colors back to light
html = re.sub(r'"on-surface": "#111827"', '"on-surface": "#e8e0f0"', html)
html = re.sub(r'"on-surface-variant": "#4b5563"', '"on-surface-variant": "#a098b0"', html)
html = re.sub(r'"on-background": "#111827"', '"on-background": "#e8e0f0"', html)
html = re.sub(r'"outline": "#9ca3af"', '"outline": "#5a5068"', html)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
