import os
from ocr_engine import process_image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
test_image = os.path.join(BASE_DIR, "ocr check.webp")

if os.path.exists(test_image):
    print(f"Testing OCR processing on: {test_image}")
    result = process_image(test_image)
    print("OCR Test completed successfully.")
else:
    print(f"Sample test image not found at: {test_image}")

