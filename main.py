"""
Digital Product Passport (DPP) & Appliance Detector - Unified CLI Launcher
"""
import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(SCRIPT_DIR) != "Hackathon_idea-main" and os.path.isdir(os.path.join(SCRIPT_DIR, "Hackathon_idea-main")):
    SCRIPT_DIR = os.path.join(SCRIPT_DIR, "Hackathon_idea-main")
    sys.path.insert(0, SCRIPT_DIR)
    os.chdir(SCRIPT_DIR)

def print_banner():
    print("=" * 65)
    print("  TEXTEMAGE - DIGITAL PRODUCT PASSPORT & VISION AI")
    print("=" * 65)
    print("1. Generate Digital Passport from Document (Textemage.py)")
    print("2. Detect Appliances in Photo (product_detector.py)")
    print("3. Launch Digital Passport Viewer UI (product_passport.py)")
    print("4. Test OCR Engine (test_ocr.py)")
    print("5. View Stored Passports (passport_store.py)")
    print("0. Exit")
    print("=" * 65)

def main():
    while True:
        print_banner()
        choice = input("Select an option [0-5]: ").strip()
        if choice == "1":
            subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "Textemage.py")], cwd=SCRIPT_DIR)
        elif choice == "2":
            subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "product_detector.py")], cwd=SCRIPT_DIR)
        elif choice == "3":
            json_path = os.path.join(SCRIPT_DIR, "product_passport.json")
            subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "product_passport.py"), json_path], cwd=SCRIPT_DIR)
        elif choice == "4":
            subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "test_ocr.py")], cwd=SCRIPT_DIR)
        elif choice == "5":
            subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "passport_store.py")], cwd=SCRIPT_DIR)
        elif choice == "0":
            print("Exiting...")
            break
        else:
            print("Invalid option. Please try again.\n")

if __name__ == "__main__":
    main()
