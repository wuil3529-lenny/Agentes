import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the dark theme root variables with light theme "gris blanco" variables
new_root = '''    :root {
      --primary: #ff2d78;
      --secondary: #00ffcc;
      --surface: #f3f4f6;          /* Gris blanco para el fondo principal */
      --surface-container: #e5e7eb; /* Gris ligeramente más oscuro para tarjetas/panel */
      --surface-container-high: #d1d5db;
      --on-surface: #111827;       /* Texto oscuro */
      --on-surface-variant: #4b5563; /* Texto secundario gris oscuro */
      --outline: #9ca3af;
      --outline-variant: #d1d5db;
    }'''

html = re.sub(r'    :root \{.*?\n    \}', new_root, html, flags=re.DOTALL)

# Let's ensure the body background class is bg-[var(--surface)] or just let the tailwind config handle it.
# The original code has `<script> tailwind.config = { theme: { extend: { colors: { surface: 'var(--surface)', ... } } } } </script>`
# And body has `<body class="bg-surface text-on-surface ...">`.
# So just changing the variables is enough to invert the theme!

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
