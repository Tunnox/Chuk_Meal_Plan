from pathlib import Path
import subprocess
import sys
import venv

project_root = Path(__file__).resolve().parent
venv_path = project_root / ".venv"

if not venv_path.exists():
    print("Creating virtual environment...")
    venv.create(venv_path, with_pip=True)

python_exe = venv_path / "Scripts" / "python.exe"

print("Upgrading pip...")
subprocess.check_call([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"])

print("Installing project requirements...")
subprocess.check_call([str(python_exe), "-m", "pip", "install", "-r", str(project_root / "requirements.txt")])

print("\nInstallation complete.")
print(r"Activate the environment with:")
print(r".\.venv\Scripts\Activate.ps1")
