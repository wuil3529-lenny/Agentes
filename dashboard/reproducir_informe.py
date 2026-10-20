import time
import sys
from pathlib import Path

# Asegurar encoding UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ruta = Path(r"C:\Users\admin\Documents\Agentes\dashboard\static\notas_voz\voz_orquestador_20261019_111045_027.mp3")

if not ruta.exists():
    print(f"ERROR: No existe el archivo {ruta}")
    sys.exit(1)

print(f"Cargando archivo de audio: {ruta.name} ({ruta.stat().st_size} bytes)")

# Metodo 1: Pygame Mixer
reproducido = False
try:
    import pygame
    pygame.mixer.init()
    pygame.mixer.music.set_volume(1.0)
    pygame.mixer.music.load(str(ruta))
    pygame.mixer.music.play()
    print("Sonando en cornetas via Pygame Mixer (DirectSound/WASAPI)...")
    while pygame.mixer.music.get_busy():
        time.sleep(0.4)
    pygame.mixer.music.unload()
    reproducido = True
    print("Reproduccion completada exitosamente via Pygame.")
except Exception as e:
    print(f"Advertencia Pygame: {e}, intentando via Windows Media Player...")

# Fallback: Windows Media Player via PowerShell si Pygame fallara
if not reproducido:
    try:
        import subprocess
        cmd = f'$wmp = New-Object -ComObject WMPlayer.OCX; $wmp.URL = "{str(ruta)}"; $wmp.controls.play(); while ($wmp.playState -eq 3 -or $wmp.playState -eq 9) {{ Start-Sleep -Milliseconds 300 }}'
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=True)
        print("Reproduccion completada exitosamente via Windows Media Player.")
    except Exception as e2:
        print(f"Error reproduciendo con fallback: {e2}")
