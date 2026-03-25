import os
import shutil
import subprocess
import sys

# 设定项目根目录（backend目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(BASE_DIR, "venv")

def log(msg):
    print(f"[{msg}]")

def run_command(command, cwd=None):
    try:
        subprocess.check_call(command, shell=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        log(f"Error running command: {command}")
        sys.exit(1)

def cleanup_old_venvs():
    """清理旧的混乱虚拟环境"""
    # 向上寻找项目根目录中的 venv
    root_dir = os.path.dirname(BASE_DIR)
    targets = [
        os.path.join(root_dir, ".venv"),
        os.path.join(root_dir, ".venv1"),
        os.path.join(root_dir, ".venv-1"),
        os.path.join(BASE_DIR, "venv") # 也会清理当前的，重新创建
    ]

    for target in targets:
        if os.path.exists(target):
            log(f"Removing old environment: {target}")
            try:
                shutil.rmtree(target)
            except Exception as e:
                log(f"Warning: Could not remove {target}: {e}")

def create_venv():
    """创建新的虚拟环境"""
    log(f"Creating new venv at {VENV_DIR}...")
    run_command(f"{sys.executable} -m venv {VENV_DIR}")

def install_requirements():
    """安装依赖"""
    pip_path = os.path.join(VENV_DIR, "bin", "pip")
    if os.name == 'nt': # Windows
        pip_path = os.path.join(VENV_DIR, "Scripts", "pip.exe")

    requirements_file = os.path.join(BASE_DIR, "requirements.txt")
    
    if not os.path.exists(requirements_file):
        log("Error: requirements.txt not found!")
        sys.exit(1)

    log("Installing dependencies...")
    # 升级 pip
    run_command(f"\"{pip_path}\" install --upgrade pip")
    # 安装依赖
    run_command(f"\"{pip_path}\" install -r \"{requirements_file}\"")

def main():
    log("Starting environment fix...")
    cleanup_old_venvs()
    create_venv()
    install_requirements()
    log("Environment fixed successfully!")
    log(f"To activate, run: source {VENV_DIR}/bin/activate")

if __name__ == "__main__":
    main()
