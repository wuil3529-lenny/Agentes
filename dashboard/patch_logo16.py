import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Remove the broken circuit-flow styles
html = re.sub(r'@keyframes circuitFlow.*\.circuit-container::after {.*?}', '', html, flags=re.DOTALL)

# Add a clean organic breathing style
breathing_style = '''
        @keyframes organicBreath {
            0%, 100% {
                opacity: 0.8;
                filter: brightness(1) drop-shadow(0 0 2px #ff2d78);
            }
            50% {
                opacity: 1;
                filter: brightness(1.3) drop-shadow(0 0 10px #ff2d78);
            }
        }
        
        .living-circuit {
            animation: organicBreath 4s ease-in-out infinite;
        }
'''

# Put it before </style>
html = html.replace('</style>', breathing_style + '\n</style>')

# Modify the image container to remove circuit-container
html = html.replace('class="w-32 flex items-center justify-center shrink-0 circuit-container"', 'class="w-32 flex items-center justify-center shrink-0"')

# Add living-circuit to img
html = html.replace('class="w-full h-auto object-contain"', 'class="w-full h-auto object-contain living-circuit"')

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
