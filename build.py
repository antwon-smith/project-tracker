"""
Hitachi Project Tracker - Zero-Install Executable Builder
Builds a standalone, offline, single-file Windows executable with PyInstaller.
"""
import os
import sys
import subprocess
from pathlib import Path

def build_executable():
    root_dir = Path(__file__).resolve().parent
    static_dir = root_dir / "static"
    templates_dir = root_dir / "templates"
    main_script = root_dir / "main.py"
    app_name = "HitachiProjectTracker"

    # Terminate any previously running instances to avoid Windows file locks
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/IM", f"{app_name}.exe"], capture_output=True)
        except Exception:
            pass

    # PyInstaller data separator on Windows is ';'
    add_static = f"{static_dir};static"
    add_templates = f"{templates_dir};templates"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--add-data",
        add_static,
        "--add-data",
        add_templates,
        "--name",
        app_name,
        "--clean",
        str(main_script),
    ]

    print("=================================================================")
    print("Building Hitachi Project Tracker Standalone Executable")
    print(f"Target: dist/{app_name}.exe")
    print("=================================================================")
    print("Command:", " ".join(cmd))
    
    result = subprocess.run(cmd, cwd=str(root_dir))
    if result.returncode == 0:
        exe_path = root_dir / "dist" / f"{app_name}.exe"
        print("\n[SUCCESS] Executable built successfully!")
        print(f"[PATH] {exe_path}")
        print(f"[SIZE] {exe_path.stat().st_size / (1024*1024):.2f} MB")
        print("\nAll static assets, Inter fonts, and templates are bundled inside.")
        print("Data is stored in %APPDATA%\\ContractorApp\\ (safe across updates).")
    else:
        print("\n[ERROR] Build failed with exit code:", result.returncode)
        sys.exit(result.returncode)

if __name__ == "__main__":
    build_executable()
