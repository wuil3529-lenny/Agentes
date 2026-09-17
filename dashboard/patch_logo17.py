import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Clean up old organicBreath
html = re.sub(r'@keyframes organicBreath.*?}\n\s*\.living-circuit.*?}', '', html, flags=re.DOTALL)
html = html.replace(' living-circuit', '')

# Insert new circuit sweep
circuit_style = '''
        @keyframes circuitFlow {
            0% { background-position: 200% -100%; }
            100% { background-position: -100% 200%; }
        }
        
        .circuit-container {
            position: relative;
            display: inline-flex;
            justify-content: center;
            align-items: center;
        }
        
        .circuit-container::after {
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, 
                transparent 47%, 
                rgba(255, 255, 255, 0.95) 50%, 
                transparent 53%);
            background-size: 300% 300%;
            animation: circuitFlow 3s linear infinite;
            mix-blend-mode: screen;
            -webkit-mask-image: url(/static/logo_mask.png);
            mask-image: url(/static/logo_mask.png);
            -webkit-mask-size: contain;
            -webkit-mask-repeat: no-repeat;
            -webkit-mask-position: center;
            pointer-events: none;
        }
'''

html = html.replace('</style>', circuit_style + '\n</style>')

# Ensure the container has the circuit-container class
html = re.sub(
    r'<div class="w-32 flex items-center justify-center shrink-0">',
    r'<div class="w-32 flex items-center justify-center shrink-0 circuit-container">',
    html
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
