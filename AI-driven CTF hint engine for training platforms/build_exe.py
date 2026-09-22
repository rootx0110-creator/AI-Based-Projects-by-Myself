import subprocess
import sys
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "CTFHintEngine"

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--clean",
    "--name", NAME,
    "--onefile",
    "--windowed",
    "--distpath", os.path.join(HERE, "dist"),
    "--workpath", os.path.join(HERE, "build"),
    "--specpath", HERE,
    "--add-data", os.path.join(HERE, "templates") + os.pathsep + "templates",
    "--add-data", os.path.join(HERE, "static") + os.pathsep + "static",
    os.path.join(HERE, "app.py"),
]

print("Building one-file windowed EXE (this takes a minute)...")
subprocess.run(cmd, check=True)

exe = os.path.join(HERE, "dist", NAME + ".exe")
target = os.path.join(HERE, NAME + ".exe")
shutil.copy2(exe, target)
print(f"\nDone: {target} ({os.path.getsize(target) / (1024 * 1024):.1f} MB)")
print("Place it next to the project folder (or anywhere). It auto-opens a browser.")
print("Progress is stored in the data\\ folder next to the EXE.")