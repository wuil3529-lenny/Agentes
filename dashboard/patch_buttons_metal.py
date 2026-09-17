import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Add metallic-btn styles
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

if 'metallic-btn' not in html:
    html = html.replace('</style>', metallic_style + '\n</style>')

# Replace current button classes with metallic-btn
# We remove the tailwind background and border classes from the previous step.
# Active button:
old_active = r'<a class="flex items-center gap-3 px-4 py-6 text-lg text-slate-100 bg-slate-400/20 border border-slate-300/40 rounded-xl shadow-\[0_0_10px_rgba\(255,45,120,0\.2\)\] transition-all duration-300 hover:scale-105 hover:shadow-\[0_0_20px_rgba\(255,45,120,0\.6\)\] hover:border-primary/80" href="#">'
new_active = r'<a class="flex items-center gap-3 px-4 py-6 text-lg metallic-btn rounded-xl transition-all duration-300 hover:scale-105" style="border-color: #ff2d78; box-shadow: inset 0 1px 1px rgba(255,255,255,0.3), 0 0 10px rgba(255,45,120,0.3);" href="#">'

html = re.sub(old_active, new_active, html)

# Inactive button:
old_inactive = r'<a class="flex items-center gap-3 px-4 py-6 text-lg text-slate-300 bg-slate-400/10 border border-slate-400/20 rounded-xl hover:text-white hover:bg-slate-400/20 hover:border-primary/50 transition-all duration-300 hover:scale-105 hover:shadow-\[0_0_15px_rgba\(255,45,120,0\.5\)\]" href="#">'
new_inactive = r'<a class="flex items-center gap-3 px-4 py-6 text-lg metallic-btn rounded-xl transition-all duration-300 hover:scale-105" href="#">'

html = re.sub(old_inactive, new_inactive, html)

# Also ensure icons don't override the text color inappropriately, removing text-on-surface and text-on-surface-variant so they inherit the white color from metallic-btn
html = html.replace('<span class="material-symbols-outlined text-on-surface">', '<span class="material-symbols-outlined">')
html = html.replace('<span class="material-symbols-outlined text-on-surface-variant group-hover:text-on-surface">', '<span class="material-symbols-outlined">')


with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
