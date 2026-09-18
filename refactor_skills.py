import os
import glob
import shutil
import re
from pathlib import Path

skills_dir = Path(r"C:\Users\admin\Documents\Agentes\Luffy\skills")
skill_files = list(skills_dir.glob("skill_*.py"))

replacements = []

for skill_file in skill_files:
    if skill_file.name == "skill_base.py":
        folder_name = "base"
    else:
        folder_name = skill_file.name.replace("skill_", "").replace(".py", "")
    
    folder_path = skills_dir / folder_name
    folder_path.mkdir(exist_ok=True)
    
    dest_py = folder_path / skill_file.name
    if skill_file.exists():
        shutil.move(str(skill_file), str(dest_py))
    
    (folder_path / "__init__.py").touch(exist_ok=True)
    
    md_files = list(skills_dir.glob("*.md"))
    for md in md_files:
        if folder_name.lower().replace("_", "") in md.name.lower().replace("_", ""):
            shutil.move(str(md), str(folder_path / md.name))
    
    module_name = skill_file.stem
    replacements.append((module_name, folder_name))

def patch_file(filepath):
    try:
        content = filepath.read_text(encoding="utf-8")
        original = content
        for mod_name, fld_name in replacements:
            content = re.sub(rf"from\s+{mod_name}\s+import", f"from {fld_name}.{mod_name} import", content)
            content = re.sub(rf"import\s+{mod_name}\b", f"from {fld_name} import {mod_name}", content)
        
        if content != original:
            filepath.write_text(content, encoding="utf-8")
            print(f"Patched {filepath.name}")
    except Exception as e:
        pass

for f in Path(r"C:\Users\admin\Documents\Agentes").rglob("*.py"):
    if "site-packages" not in str(f) and ".venv" not in str(f) and f.name != "refactor_skills.py":
        patch_file(f)

print("Refactor complete.")
