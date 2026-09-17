import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Remove the old neonPulseGlow animation entirely
html = re.sub(r'@keyframes neonPulseGlow.*?}\n\s*\.neon-logo.*?}', '', html, flags=re.DOTALL)

# Add the new circuit-flow animation styles
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
                transparent 30%, 
                rgba(255, 255, 255, 0.9) 50%, 
                transparent 70%);
            background-size: 300% 300%;
            animation: circuitFlow 4s linear infinite;
            mix-blend-mode: color-dodge;
            -webkit-mask-image: url(/static/logo_transparent.png);
            mask-image: url(/static/logo_transparent.png);
            -webkit-mask-size: contain;
            -webkit-mask-repeat: no-repeat;
            -webkit-mask-position: center;
            pointer-events: none;
        }
'''

# Put it before </style>
html = html.replace('</style>', circuit_style + '\n</style>')

# Modify the image container to use circuit-container and remove neon-logo from img
html = html.replace('class="w-32 flex items-center justify-center shrink-0"', 'class="w-32 flex items-center justify-center shrink-0 circuit-container"')
html = html.replace('class="w-full h-auto object-contain neon-logo"', 'class="w-full h-auto object-contain"')

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
