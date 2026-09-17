import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Add the neon-logo class to the img tag
html = html.replace(
    'class="w-full h-auto object-contain drop-shadow-[0_0_15px_rgba(255,45,120,0.4)]"',
    'class="w-full h-auto object-contain neon-logo"'
)

# Add the keyframes into the <style> block
style_addition = '''
        @keyframes neonPulseGlow {
            0%, 100% {
                filter: drop-shadow(0 0 5px #ff2d78) drop-shadow(0 0 15px #ff2d78);
            }
            50% {
                filter: drop-shadow(0 0 2px #ff2d78) drop-shadow(0 0 8px #ff2d78);
            }
        }
        .neon-logo {
            animation: neonPulseGlow 2s ease-in-out infinite alternate;
        }
</style>'''

html = html.replace('</style>', style_addition)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
