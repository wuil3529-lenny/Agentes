import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Add the new CSS classes
cyber_style = '''
        .cyber-glass-btn {
            background: rgba(30, 30, 48, 0.3);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(0, 255, 204, 0.15);
            color: #e8e0f0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
            transition: all 0.3s ease;
        }
        .cyber-glass-btn:hover {
            background: rgba(0, 255, 204, 0.05);
            border-color: rgba(0, 255, 204, 0.6);
            box-shadow: 0 0 15px rgba(0, 255, 204, 0.3), inset 0 0 8px rgba(0, 255, 204, 0.1);
            color: #ffffff;
        }
        .cyber-glass-btn:hover .material-symbols-outlined {
            color: #00ffcc;
            text-shadow: 0 0 8px #00ffcc;
        }
        
        .cyber-glass-btn-active {
            background: rgba(255, 45, 120, 0.08);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 45, 120, 0.4);
            color: #ff2d78;
            box-shadow: 0 0 10px rgba(255, 45, 120, 0.15);
            transition: all 0.3s ease;
        }
        .cyber-glass-btn-active:hover {
            background: rgba(255, 45, 120, 0.15);
            border-color: rgba(255, 45, 120, 0.8);
            box-shadow: 0 0 20px rgba(255, 45, 120, 0.4), inset 0 0 10px rgba(255, 45, 120, 0.2);
            color: #ffffff;
        }
        .cyber-glass-btn-active .material-symbols-outlined {
            color: #ff2d78;
            text-shadow: 0 0 5px #ff2d78;
        }
'''

# Remove old metallic-btn styles
html = re.sub(r'\.metallic-btn \{.*?\n\s*\}\n', '', html, flags=re.DOTALL)
html = html.replace('</style>', cyber_style + '\n</style>')

# Replace the buttons
# We need to replace the active button:
active_old = r'<a class="flex items-center gap-3 px-4 py-6 text-lg metallic-btn rounded-xl transition-all duration-300 hover:scale-105" style="border-color: #ff2d78; box-shadow: inset 0 1px 1px rgba\(255,255,255,0\.3\), 0 0 10px rgba\(255,45,120,0\.3\);" href="#">'
active_new = r'<a class="flex items-center gap-3 px-4 py-6 text-lg cyber-glass-btn-active rounded-xl transition-transform duration-300 hover:scale-105" href="#">'
html = re.sub(active_old, active_new, html)

# Inactive buttons:
inactive_old = r'<a class="flex items-center gap-3 px-4 py-6 text-lg metallic-btn rounded-xl transition-all duration-300 hover:scale-105" href="#">'
inactive_new = r'<a class="flex items-center gap-3 px-4 py-6 text-lg cyber-glass-btn rounded-xl transition-transform duration-300 hover:scale-105" href="#">'
html = re.sub(inactive_old, inactive_new, html)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
