import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Enlarge logo: w-10 h-10 -> w-16 h-16
html = html.replace('w-10 h-10 rounded bg-primary-container', 'w-16 h-16 rounded-xl bg-primary-container')

# 2. Taller buttons and hover animation
html = html.replace(
    'class="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/30 transition-colors duration-200"',
    'class="flex items-center gap-3 px-4 py-4 text-[14px] text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/30 transition-all duration-300 hover:translate-x-2"'
)

html = html.replace(
    'class="flex items-center gap-3 px-4 py-3 text-primary bg-primary-container/10 border-r-2 border-primary transition-all opacity-100 scale-[0.99]"',
    'class="flex items-center gap-3 px-4 py-4 text-[14px] text-primary bg-primary-container/10 border-r-2 border-primary transition-all duration-300 hover:translate-x-2"'
)

# 3. Add neon animation to the title Tripulacion.IA
html = html.replace(
    '<h1 class="font-headline-md text-headline-md font-bold text-primary tracking-tight">Trupulacion.IA</h1>',
    '<h1 class="font-headline-md text-[24px] font-bold text-primary tracking-tight neon-title">Trupulacion.IA</h1>'
)

# Add the keyframes to the <style> block
style_addition = '''
        @keyframes neonPulse {
            0%, 100% {
                text-shadow: 0 0 5px #ff2d78, 0 0 10px #ff2d78, 0 0 20px #ff2d78;
            }
            50% {
                text-shadow: 0 0 2px #ff2d78, 0 0 5px #ff2d78, 0 0 10px #ff2d78;
            }
        }
        .neon-title {
            animation: neonPulse 2s ease-in-out infinite alternate;
        }
'''
html = html.replace('</style>', style_addition + '</style>')

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
