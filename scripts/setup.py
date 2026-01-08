#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def main():
    print("🚀 Antigravity Template Setup")
    print("=============================")
    
    root_dir = Path(__file__).parent.parent.resolve()
    print(f"📂 Project Root: {root_dir}")
    
    # 1. Create Directory Topology
    dirs = [
        ".antigravity",
        ".context",
        "artifacts/logs",
        "artifacts/memory",
        "artifacts/plans",
        "system/kernel",
        "system/tools",
        "system/personas",
        "system/tests"
    ]
    
    print("\n🛠️  Verifying Directories...")
    for d in dirs:
        path = root_dir / d
        if not path.exists():
            path.mkdir(parents=True)
            print(f"   [+] Created: {d}")
        else:
            print(f"   [✓] Exists:  {d}")

    # 2. Check Environment
    print("\n🌍 Environment Check...")
    if not (root_dir / ".env").exists():
        if (root_dir / ".env.example").exists():
            print("   [!] .env missing. Copying from .env.example...")
            import shutil
            shutil.copy(root_dir / ".env.example", root_dir / ".env")
        else:
            print("   [⚠️] .env missing and no example found.")
    else:
        print("   [✓] .env found.")
        
    print("\n✨ Setup Complete. Run 'python main.py' to start.")

if __name__ == "__main__":
    main()
