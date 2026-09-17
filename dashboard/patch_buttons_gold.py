import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Change metallic-btn hover border color to gold (#ffd700)
html = html.replace('border-color: #ff2d78;', 'border-color: #ffd700;')

# Change the box-shadow RGB values from pink (255,45,120) to gold (255,215,0)
html = html.replace('rgba(255,45,120,0.7)', 'rgba(255,215,0,0.7)')
html = html.replace('rgba(255,45,120,0.3)', 'rgba(255,215,0,0.3)')
html = html.replace('rgba(255,45,120,0.6)', 'rgba(255,215,0,0.6)')

# Wait, there might be other places where rgba(255,45,120,0.x) is used (like the hat's shadow!)
# The hat has: class="w-full h-auto object-contain drop-shadow-[0_0_10px_rgba(255,45,120,0.3)]"
# If I change ALL instances, the hat's shadow might become gold! But the hat is pink neon, its shadow should probably stay pink, OR maybe the user wants everything gold? The prompt says "Brillo del boton seleccionado... y cuando pase el maus". It specifically mentions buttons.
# So I should restrict the replacement to the button classes/styles.

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Let's rebuild the metallic_style explicitly
metallic_style_old = '''        .metallic-btn {
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
        }'''

metallic_style_new = '''        .metallic-btn {
            background: linear-gradient(145deg, #6b7280 0%, #374151 45%, #111827 100%);
            color: #f3f4f6;
            border: 1px solid #9ca3af;
            box-shadow: inset 0 1px 1px rgba(255,255,255,0.3), 0 4px 6px rgba(0,0,0,0.5);
            text-shadow: 0 1px 2px rgba(0,0,0,0.8);
        }
        .metallic-btn:hover {
            background: linear-gradient(145deg, #9ca3af 0%, #4b5563 45%, #1f2937 100%);
            border-color: #ffd700;
            box-shadow: inset 0 1px 2px rgba(255,255,255,0.5), 0 0 20px rgba(255,215,0,0.7);
        }'''

html = html.replace(metallic_style_old, metallic_style_new)

# And for the active button inline style
active_style_old = 'style="border-color: #ff2d78; box-shadow: inset 0 1px 1px rgba(255,255,255,0.3), 0 0 10px rgba(255,45,120,0.3);"'
active_style_new = 'style="border-color: #ffd700; box-shadow: inset 0 1px 1px rgba(255,255,255,0.3), 0 0 10px rgba(255,215,0,0.4);"'

html = html.replace(active_style_old, active_style_new)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
