import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Update .nav-item transition
html = html.replace('transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);', 'transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);')

# Update .nav-item:hover block
old_hover = '''        .nav-item:hover {
            color: #f5f2fa;
            background: rgba(32, 28, 52, 0.7);
            border-color: rgba(255, 45, 120, 0.25);
            transform: translateX(4px);
        }'''
new_hover = '''        .nav-item:hover {
            color: #ffffff;
            background: rgba(32, 28, 52, 0.85);
            border-color: rgba(255, 45, 120, 0.6);
            transform: translateX(6px) scale(1.03);
            box-shadow: 0 0 25px rgba(255, 45, 120, 0.4), 0 0 45px rgba(255, 45, 120, 0.15), inset 0 0 15px rgba(255, 45, 120, 0.2);
            z-index: 10;
        }'''
html = html.replace(old_hover, new_hover)

# Update .nav-item:hover::before block
old_hover_before = '''        .nav-item:hover::before {
            opacity: 0.7;
            transform: scaleY(0.85);
        }'''
new_hover_before = '''        .nav-item:hover::before {
            opacity: 1;
            transform: scaleY(0.9);
            box-shadow: 0 0 15px #ff2d78, 0 0 8px #ff2d78;
        }'''
html = html.replace(old_hover_before, new_hover_before)

# Update .icon-box transition
html = html.replace('transition: all 0.25s ease;\n            flex-shrink: 0;', 'transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);\n            flex-shrink: 0;')

# Update .nav-item:hover .icon-box block
old_hover_icon = '''        .nav-item:hover .icon-box {
            background: rgba(255, 45, 120, 0.12);
            border-color: rgba(255, 45, 120, 0.35);
            color: #ff2d78;
        }'''
new_hover_icon = '''        .nav-item:hover .icon-box {
            background: rgba(255, 45, 120, 0.2);
            border-color: rgba(255, 45, 120, 0.5);
            color: #ffffff;
            text-shadow: 0 0 10px #ff2d78;
            transform: rotate(-10deg) scale(1.15);
            box-shadow: 0 0 15px rgba(255, 45, 120, 0.4);
        }'''
html = html.replace(old_hover_icon, new_hover_icon)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
