import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

circuit_style = '''
        @keyframes circuitSpin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .circuit-container {
            position: relative;
            display: inline-flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
            border-radius: 50%;
        }
        
        .circuit-container::after {
            content: '';
            position: absolute;
            top: -50%; left: -50%; right: -50%; bottom: -50%;
            background: conic-gradient(from 0deg, 
                transparent 0%, 
                rgba(255, 255, 255, 1) 5%, 
                transparent 15%);
            animation: circuitSpin 3s linear infinite;
            mix-blend-mode: color-dodge;
            -webkit-mask-image: url(/static/logo_mask.png);
            mask-image: url(/static/logo_mask.png);
            -webkit-mask-size: contain;
            -webkit-mask-repeat: no-repeat;
            -webkit-mask-position: center;
            pointer-events: none;
        }
'''

# Replace the old styles
html = re.sub(r'@keyframes circuitFlow.*\.circuit-container::after {.*?}', circuit_style, html, flags=re.DOTALL)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
