import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# The block to replace
old_nav = r'''<div class="flex flex-col gap-1 px-3 flex-grow">
<!-- Active: Vista General -->
<a class="flex items-center gap-3 px-4 py-8 text-lg text-primary /10 border-r-2 border-primary transition-all duration-300 hover:translate-x-2" href="#">
<span class="material-symbols-outlined text-on-surface">dashboard</span>
<span class="font-label-caps text-label-caps">Vista General</span>
</a>
<a class="flex items-center gap-3 px-4 py-8 text-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/30 transition-all duration-300 hover:translate-x-2" href="#">
<span class="material-symbols-outlined text-on-surface">smart_toy</span>
<span class="font-label-caps text-label-caps">Monitor de Agentes</span>
</a>
<a class="flex items-center gap-3 px-4 py-8 text-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/30 transition-all duration-300 hover:translate-x-2" href="#">
<span class="material-symbols-outlined text-on-surface">trolley</span>
<span class="font-label-caps text-label-caps">Control de Tareas</span>
</a>
<a class="flex items-center gap-3 px-4 py-8 text-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/30 transition-all duration-300 hover:translate-x-2" href="#">
<span class="material-symbols-outlined text-on-surface">insights</span>
<span class="font-label-caps text-label-caps">Analtica de Rendimiento</span>
</a>
</div>'''

# First try literal replace (might fail due to encoding character issues like 'Analtica'). 
# Let's use a regex replacement to grab the whole block safely.

new_nav = '''<div class="flex flex-col gap-3 px-3 flex-grow">
<!-- Active: Vista General -->
<a class="flex items-center gap-3 px-4 py-6 text-lg text-on-surface bg-surface-container-high border border-outline-variant rounded-xl shadow-lg transition-all duration-300 hover:scale-[1.02]" href="#">
<span class="material-symbols-outlined text-on-surface">dashboard</span>
<span class="font-label-caps text-label-caps font-bold tracking-wider">Vista General</span>
</a>
<a class="flex items-center gap-3 px-4 py-6 text-lg text-on-surface-variant bg-surface-container border border-transparent rounded-xl hover:text-on-surface hover:bg-surface-container-high hover:border-outline-variant transition-all duration-300 hover:scale-[1.02]" href="#">
<span class="material-symbols-outlined text-on-surface-variant group-hover:text-on-surface">smart_toy</span>
<span class="font-label-caps text-label-caps tracking-wider">Monitor de Agentes</span>
</a>
<a class="flex items-center gap-3 px-4 py-6 text-lg text-on-surface-variant bg-surface-container border border-transparent rounded-xl hover:text-on-surface hover:bg-surface-container-high hover:border-outline-variant transition-all duration-300 hover:scale-[1.02]" href="#">
<span class="material-symbols-outlined text-on-surface-variant group-hover:text-on-surface">trolley</span>
<span class="font-label-caps text-label-caps tracking-wider">Control de Tareas</span>
</a>
<a class="flex items-center gap-3 px-4 py-6 text-lg text-on-surface-variant bg-surface-container border border-transparent rounded-xl hover:text-on-surface hover:bg-surface-container-high hover:border-outline-variant transition-all duration-300 hover:scale-[1.02]" href="#">
<span class="material-symbols-outlined text-on-surface-variant group-hover:text-on-surface">insights</span>
<span class="font-label-caps text-label-caps tracking-wider">Analítica</span>
</a>
</div>'''

# The safest way is to substitute everything between <div class="flex flex-col gap-1 px-3 flex-grow"> and the next </div>
html = re.sub(
    r'<div class="flex flex-col gap-1 px-3 flex-grow">.*?</div>',
    new_nav,
    html,
    flags=re.DOTALL
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
