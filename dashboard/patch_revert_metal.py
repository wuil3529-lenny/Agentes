import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

metallic_style = '''
        .metallic-btn {
            background: linear-gradient(145deg, #6b7280 0%, #374151 45%, #111827 100%);
            color: #f3f4f6;
            border: 1px solid #9ca3af;
            box-shadow: inset 0 1px 1px rgba(255,255,255,0.3), 0 4px 6px rgba(0,0,0,0.5);
            text-shadow: 0 1px 2px rgba(0,0,0,0.8);
        }
        .metallic-btn:hover {
            background: linear-gradient(145deg, #9ca3af 0%, #4b5563 45%, #1f2937 100%);
            border-color: #ff2d78;
            box-shadow: inset 0 1px 2px rgba(255,255,255,0.5), 0 0 20px rgba(255,45,120,0.7);
        }
'''

# Remove the cyber glass styles
html = re.sub(r'\.cyber-glass-btn \{.*?\n\s*\}\n', '', html, flags=re.DOTALL)
html = re.sub(r'\.cyber-glass-btn:hover \{.*?\n\s*\}\n', '', html, flags=re.DOTALL)
html = re.sub(r'\.cyber-glass-btn:hover \.material-symbols-outlined \{.*?\n\s*\}\n', '', html, flags=re.DOTALL)
html = re.sub(r'\.cyber-glass-btn-active \{.*?\n\s*\}\n', '', html, flags=re.DOTALL)
html = re.sub(r'\.cyber-glass-btn-active:hover \{.*?\n\s*\}\n', '', html, flags=re.DOTALL)
html = re.sub(r'\.cyber-glass-btn-active \.material-symbols-outlined \{.*?\n\s*\}\n', '', html, flags=re.DOTALL)

html = html.replace('</style>', metallic_style + '\n</style>')

# Replace active
html = re.sub(
    r'<a class="flex items-center gap-3 px-4 py-6 text-lg cyber-glass-btn-active rounded-xl transition-transform duration-300 hover:scale-105" href="#">',
    r'<a class="flex items-center gap-3 px-4 py-6 text-lg metallic-btn rounded-xl transition-all duration-300 hover:scale-105" style="border-color: #ff2d78; box-shadow: inset 0 1px 1px rgba(255,255,255,0.3), 0 0 10px rgba(255,45,120,0.3);" href="#">',
    html
)

# Replace inactive
html = re.sub(
    r'<a class="flex items-center gap-3 px-4 py-6 text-lg cyber-glass-btn rounded-xl transition-transform duration-300 hover:scale-105" href="#">',
    r'<a class="flex items-center gap-3 px-4 py-6 text-lg metallic-btn rounded-xl transition-all duration-300 hover:scale-105" href="#">',
    html
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
