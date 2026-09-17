import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# The image currently has: class="w-full h-full object-cover rounded shadow-[0_0_10px_rgba(255,45,120,0.8)]"
# We want to remove the square shadow, and add mix-blend-screen to remove the black background.
# We also want to apply the neon-logo animation to the image instead of the container if it's there.

# 1. Clean the container (remove neon-logo and any background/shadow)
html = html.replace('bg-transparent', '')
html = html.replace('neon-logo', '')

# 2. Update the img class
html = re.sub(
    r'<img alt="Logo Sombrero de Paja Nen" class=".*?"',
    r'<img alt="Logo Sombrero" class="w-full h-full object-contain mix-blend-screen neon-logo"',
    html
)
html = re.sub(
    r'<img alt="Minimalist straw hat neon" class=".*?"',
    r'<img alt="Logo Sombrero" class="w-full h-full object-contain mix-blend-screen neon-logo"',
    html
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
