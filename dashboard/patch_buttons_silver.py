import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace active button styling
new_active = r'<a class="flex items-center gap-3 px-4 py-6 text-lg text-slate-100 bg-slate-400/20 border border-slate-300/40 rounded-xl shadow-[0_0_10px_rgba(255,45,120,0.2)] transition-all duration-300 hover:scale-105 hover:shadow-[0_0_20px_rgba(255,45,120,0.6)] hover:border-primary/80" href="#">'

html = re.sub(
    r'<a class="flex items-center gap-3 px-4 py-6 text-lg text-on-surface bg-surface-container-high border border-primary/30 rounded-xl shadow-\[0_0_10px_rgba\(255,45,120,0\.2\)\] transition-all duration-300 hover:scale-105 hover:shadow-\[0_0_20px_rgba\(255,45,120,0\.6\)\] hover:border-primary/80" href="#">',
    new_active,
    html
)

# Replace inactive button styling
new_inactive = r'<a class="flex items-center gap-3 px-4 py-6 text-lg text-slate-300 bg-slate-400/10 border border-slate-400/20 rounded-xl hover:text-white hover:bg-slate-400/20 hover:border-primary/50 transition-all duration-300 hover:scale-105 hover:shadow-[0_0_15px_rgba(255,45,120,0.5)]" href="#">'

html = re.sub(
    r'<a class="flex items-center gap-3 px-4 py-6 text-lg text-on-surface-variant bg-surface-container border border-transparent rounded-xl hover:text-on-surface hover:bg-surface-container-high hover:border-primary/50 transition-all duration-300 hover:scale-105 hover:shadow-\[0_0_15px_rgba\(255,45,120,0\.5\)\]" href="#">',
    new_inactive,
    html
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
