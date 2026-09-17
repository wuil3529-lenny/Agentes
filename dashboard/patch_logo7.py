import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Current HTML for the logo:
# <div class="px-6 mb-8 flex items-center justify-center">
# <div class="w-32 h-32 rounded-2xl  flex items-center justify-center shrink-0 ">
# <img alt="Logo Sombrero" class="w-full h-full object-contain mix-blend-screen" src="/static/logo5.png">
# </div>

html = html.replace(
    '<div class="w-32 h-32 rounded-2xl  flex items-center justify-center shrink-0 ">',
    '<div class="w-32 h-24 rounded-2xl overflow-hidden flex items-start justify-center shrink-0">'
)

html = html.replace(
    '<img alt="Logo Sombrero" class="w-full h-full object-contain mix-blend-screen" src="/static/logo5.png">',
    '<img alt="Logo Sombrero" class="w-full h-32 object-cover object-top mix-blend-screen scale-110" style="margin-top: -10px;" src="/static/logo5.png">'
)


with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
