import re

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Completely replace whatever img tag is in the header/brand block
html = re.sub(
    r'<img alt="Logo Sombrero[^>]*>',
    r'<img alt="Logo Sombrero" class="w-full h-full object-contain mix-blend-screen neon-logo" src="https://lh3.googleusercontent.com/aida/AEtjO1WJ3ZFqKS_74YC8qVVfzGkvM90z13qazvmisYeTYZBJgyNn_8GWKKHllesdVQTBy0yv2oojhRMIKqIanXCGrgr8dLP7e8oHBymNS7f4XOu2fMj3ibOmU5hK-Hr3Kig_2e3IGffuHI3yxDv3RALUDnfmXgBKlDPCTknpqCnpaSJHvmq6PIXy1V_R_dEuOrs2rohCQjW4BKVMH-9_j_0y8XaEx3VUEepCGAIL_Ua_CvCqGfhXAen3Zk_UTq-m">',
    html
)

with open(r'C:\Users\admin\Documents\Agentes\dashboard\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
