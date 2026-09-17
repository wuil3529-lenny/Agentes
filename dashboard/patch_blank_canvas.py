import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Simplify the <main> tag (remove the right padding for the terminal)
html = re.sub(
    r'<main class="flex-1 overflow-y-auto p-6 lg:p-8 pr-80 lg:pr-\[360px\]">',
    r'<main class="flex-1 overflow-y-auto p-6 lg:p-8">',
    html
)

# 2. Replace the contents of <main> with a blank canvas placeholder
blank_canvas = '''
    <div class="w-full h-full border-2 border-dashed border-outline-variant rounded-2xl flex flex-col items-center justify-center text-on-surface-variant opacity-50">
        <span class="material-symbols-outlined text-6xl mb-4">architecture</span>
        <h2 class="font-headline-md text-2xl">Lienzo en Blanco</h2>
        <p class="font-body-md mt-2">Área de trabajo lista para nuevos módulos</p>
    </div>
'''

html = re.sub(
    r'(<main class="flex-1 overflow-y-auto p-6 lg:p-8">).*?(</main>)',
    r'\1' + blank_canvas + r'\2',
    html,
    flags=re.DOTALL
)

# 3. Remove the right sidebar (Terminal & Logs) which is between </main> and </div></body>
# The wrapper is a flex container: <div class="flex h-screen ..."> <aside>...</aside> <main>...</main> <!-- Right Sidebar --> </div>
# So we delete everything between </main> and the final </div> that closes the flex container.
html = re.sub(
    r'</main>.*?</div>\s*<script src="/static/script\.js"></script>',
    r'</main>\n</div>\n<script src="/static/script.js"></script>',
    html,
    flags=re.DOTALL
)


with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
