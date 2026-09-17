import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the ugly background class
html = html.replace('bg-primary-container', 'bg-transparent')

# Fix the animation to work with drop-shadow for the image
# Currently we had:
# @keyframes neonPulse {
#     0%, 100% { text-shadow: ... }
#     50% { text-shadow: ... }
# }
# .neon-title { animation: neonPulse ... }

# We will change it to drop-shadow
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
'''

# Replace the old keyframes if they exist, or just append.
# Actually I'll just replace neonPulse and neon-title with neonPulseGlow and neon-logo
html = re.sub(r'@keyframes neonPulse.*?\.neon-title\s*{.*?}', style_addition, html, flags=re.DOTALL)

# And replace the class on the div
html = html.replace('neon-title', 'neon-logo')

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
