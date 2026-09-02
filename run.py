"""
HomeMind — Master Entrypoint Launcher
Boots the FastAPI backend server, serves the Household Intelligence Dashboard,
and provides an optional interactive CLI mode.

Usage:
  python run.py                 # Launch Web Dashboard & open browser
  python run.py --no-browser    # Launch server only (headless)
  python run.py --cli           # Launch interactive Terminal CLI
  python run.py --port 8080     # Run on custom port
"""

import os
import sys
import time
import argparse
import webbrowser
import threading

# Add root directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.config import SERVER_HOST, SERVER_PORT


def open_browser_delayed(url: str, delay: float = 1.2):
    """Open default browser after server initializes."""
    def _open():
        time.sleep(delay)
        print(f"\n[HomeMind] Opening Household Dashboard: {url}")
        webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()


def run_cli_menu():
    """Interactive terminal CLI for headless diagnosis and quick testing."""
    from app.core.passport_store import PassportStore
    from app.core.ocr_engine import extract_ocr_text, is_ocr_available
    from app.core.dpp_extractor import extract_document_dpp, check_ollama
    from app.core.product_detector import detect_appliances
    from app.config import SAMPLES_DIR

    store = PassportStore()

    while True:
        print("\n" + "=" * 65)
        print("  HOMEMIND — HOUSEHOLD INTELLIGENCE CLI")
        print("=" * 65)
        print("1. Extract Digital Passport from Sample Warranty Card")
        print("2. Run YOLO Appliance Detection on Sample Photo")
        print("3. View Passport Store & Statistics")
        print("4. Check Diagnostics (Ollama, OCR, YOLO)")
        print("5. Start Full Web Dashboard Server")
        print("0. Exit")
        print("=" * 65)

        choice = input("Select an option [0-5]: ").strip()

        if choice == "1":
            samples = list((SAMPLES_DIR / "warranty_cards").glob("*.*"))
            if samples:
                sample_img = str(samples[0])
                print(f"\nProcessing sample: {sample_img}")
                res = extract_document_dpp(sample_img)
                print(f"Extraction source: {res['extraction_source']}")
                print(f"Passports extracted: {res['passport_count']}")
                for p in res["passports"]:
                    stored = store.add_passport(p, source="cli_test")
                    print(f"-> {p.get('passport_id')}: {p.get('product')} ({p.get('brand')}) | Model: {p.get('model')} | Serial: {p.get('serial_number')}")
                    print(f"   Identity Status: {stored['identity_match']['status']}")
            else:
                print("No samples found in samples/warranty_cards/")

        elif choice == "2":
            samples = list((SAMPLES_DIR / "appliance_photos").glob("*.*"))
            if samples:
                sample_img = str(samples[0])
                print(f"\nDetecting appliances in: {sample_img}")
                res = detect_appliances(sample_img)
                print(f"Detections found: {res['count']}")
                for d in res["detections"]:
                    print(f"-> {d['label']} (Confidence: {int(d.get('confidence', 0) * 100)}%) | Box: {d.get('box')}")
            else:
                print("No samples found in samples/appliance_photos/")

        elif choice == "3":
            stats = store.stats()
            print(f"\nPassport Store Stats: {stats}")
            all_p = store.get_all()
            for p in all_p[:5]:
                print(f"-> {p.get('passport_id')}: {p.get('product')} ({p.get('brand')}) | Status: {p.get('identity_match', {}).get('status', 'new')}")

        elif choice == "4":
            ollama = check_ollama()
            ocr = is_ocr_available()
            print(f"\nDiagnostics:")
            print(f"-> Ollama Host: {ollama['host']} (Online: {ollama['online']}, Vision Model: {ollama['has_vision_model']})")
            print(f"-> Tesseract OCR: {'Available' if ocr else 'Not Installed (Graceful Fallback)'}")

        elif choice == "5":
            break

        elif choice == "0":
            print("Exiting...")
            sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="HomeMind — Household Intelligence")
    parser.add_argument("--cli", action="store_true", help="Launch interactive CLI menu")
    parser.add_argument("--host", type=str, default=SERVER_HOST, help="Host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=SERVER_PORT, help="Port (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    parser.add_argument("--reload", action="store_true", default=False, help="Enable auto-reload")
    args = parser.parse_args()

    if args.cli:
        run_cli_menu()

    import uvicorn
    url = f"http://localhost:{args.port}"
    print("\n" + "=" * 70)
    print("  HOMEMIND — HOUSEHOLD INTELLIGENCE SERVER")
    print("=" * 70)
    print(f"  Web Dashboard:  {url}")
    print(f"  Swagger Docs:   {url}/docs")
    print(f"  Listening on:   http://{args.host}:{args.port}")
    print("=" * 70)

    if not args.no_browser:
        open_browser_delayed(url)

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
