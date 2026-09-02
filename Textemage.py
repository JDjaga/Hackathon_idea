# ============================================================
# TEXTEMAGE - DIGITAL PRODUCT PASSPORT GENERATOR
# ============================================================
#
# Main responsibilities:
#   1. Load product/warranty/invoice image
#   2. Send image to Ollama Vision model
#   3. Detect selected/checked products
#   4. Extract each selected product independently
#   5. Support multiple products in one document
#   6. Save normalized passport JSON
#   7. Launch passport UI using the EXACT generated JSON
#
# Vision model:
#   qwen2.5vl:7b
#
# Ollama:
#   http://127.0.0.1:11434
# ============================================================

import os
import sys
import json
import base64
import re
import subprocess
import tkinter as tk

from tkinter import filedialog, messagebox

import requests
from PIL import Image


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "qwen2.5vl:7b"

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

# IMPORTANT:
# Always use absolute paths.
JSON_FILE = os.path.join(
    SCRIPT_DIR,
    "product_passport.json"
)

OCR_DIR = os.path.join(
    SCRIPT_DIR,
    "ocr_output"
)

EVIDENCE_FILE = os.path.join(
    OCR_DIR,
    "ocr_evidence.json"
)


# ============================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================

os.makedirs(
    OCR_DIR,
    exist_ok=True
)


# ============================================================
# TERMINAL HELPERS
# ============================================================

def print_separator(char="=", length=70):

    print(char * length)


def print_title(title):

    print()
    print_separator("=")

    print(title.center(70))

    print_separator("=")


# ============================================================
# CHECK OLLAMA
# ============================================================

def check_ollama():

    print()
    print("Checking Ollama...")

    try:

        response = requests.get(
            "http://127.0.0.1:11434/api/tags",
            timeout=5
        )

        if response.status_code != 200:

            print(
                "Ollama responded with status:",
                response.status_code
            )

            return False

        data = response.json()

        models = data.get(
            "models",
            []
        )

        print()
        print("Available Ollama models:")

        model_names = []

        for model in models:

            name = model.get(
                "name",
                ""
            )

            if name:

                model_names.append(
                    name
                )

                print(
                    " -",
                    name
                )

        # Check exact model
        found = False

        for name in model_names:

            if (
                name == MODEL_NAME
                or name.startswith(MODEL_NAME + ":")
            ):

                found = True
                break

        if not found:

            print()
            print(
                "WARNING:"
            )

            print(
                f"Model '{MODEL_NAME}' was not found."
            )

            print(
                "Please run:"
            )

            print(
                f"ollama pull {MODEL_NAME}"
            )

            return False

        print()
        print(
            "Using vision model:",
            MODEL_NAME
        )

        return True

    except requests.exceptions.ConnectionError:

        print()
        print(
            "ERROR: Ollama is not running."
        )

        print(
            "Start Ollama and run the program again."
        )

        return False

    except Exception as e:

        print(
            "Ollama check failed:",
            e
        )

        return False


# ============================================================
# IMAGE ENCODING
# ============================================================

def image_to_base64(image_path):

    with open(
        image_path,
        "rb"
    ) as f:

        return base64.b64encode(
            f.read()
        ).decode(
            "utf-8"
        )


# ============================================================
# IMAGE INFORMATION
# ============================================================

def inspect_image(image_path):

    try:

        with Image.open(
            image_path
        ) as img:

            print()
            print(
                "Image:",
                image_path
            )

            print(
                "Original size:",
                img.size
            )

            print(
                "Image mode:",
                img.mode
            )

            return img.size

    except Exception as e:

        print(
            "Could not inspect image:",
            e
        )

        return None


# ============================================================
# OPTIONAL OCR
# ============================================================
#
# OCR is NOT required for the vision extraction.
#
# This function is intentionally optional because your
# Tesseract installation currently has an eng.traineddata
# path problem.
#
# Qwen2.5-VL will still receive the ORIGINAL IMAGE.
# ============================================================

def run_optional_tesseract(image_path):

    try:

        import pytesseract

        print()
        print(
            "Attempting optional Tesseract OCR..."
        )

        text = pytesseract.image_to_string(
            image_path,
            lang="eng",
            config="--psm 6"
        )

        if text and text.strip():

            print(
                "Tesseract OCR produced text."
            )

            return text.strip()

        print(
            "Tesseract returned no text."
        )

        return ""

    except Exception as e:

        print(
            "Tesseract unavailable:",
            e
        )

        print(
            "Continuing with Vision AI."
        )

        return ""


# ============================================================
# VISION PROMPT
# ============================================================

VISION_PROMPT = r"""
You are an extremely accurate document-understanding AI.

Your task is to create DIGITAL PRODUCT PASSPORTS from the
uploaded warranty card, invoice, receipt, product document,
service document, or similar document.

IMPORTANT:

A single photograph may contain MULTIPLE PRODUCT TYPES.

For example, a warranty card might contain checkboxes for:

- Washing Machine
- Tumble Dryer
- Dishwasher
- Small Domestic Appliances

BUT only one or some of those boxes may actually be selected.

============================================================
MOST IMPORTANT RULE: CHECKED / SELECTED PRODUCT
============================================================

You MUST inspect the actual checkbox marks in the image.

A product is considered PURCHASED / SELECTED only when the
corresponding checkbox is visibly marked.

Possible marks include:

- ✓
- ✔
- X
- handwritten tick
- dark check mark
- filled checkbox
- handwritten selection mark
- other clearly visible selection indicator

DO NOT create a passport for a product merely because its
name appears in the printed list.

Example:

[ ] Washing Machine
[ ] Tumble Dryer
[ ] Dishwasher
[✓] Small Domestic Appliances

Correct result:

ONE passport:

Product = Small Domestic Appliances

Do NOT create passports for Washing Machine, Tumble Dryer,
or Dishwasher.

============================================================
MULTIPLE SELECTED PRODUCTS
============================================================

If the document contains:

[✓] Washing Machine
[✓] Refrigerator
[ ] Dishwasher

then create TWO passports:

Passport #1 = Washing Machine
Passport #2 = Refrigerator

Each passport must be independent.

Do NOT merge their information.

============================================================
PRODUCT-SPECIFIC INFORMATION
============================================================

For every selected product, determine which model number,
serial number, price, warranty, date, seller, etc. belongs
to that particular product.

If the document clearly associates a field with a selected
product, use it.

If a field cannot be reliably associated with a product,
return null.

DO NOT copy a field from another product just to fill a
missing value.

============================================================
DO NOT HALLUCINATE
============================================================

Never invent:

- product names
- brand
- model numbers
- serial numbers
- prices
- dates
- seller names
- warranty periods
- invoice numbers
- order IDs

If something is not readable or not present:

return null.

============================================================
HANDWRITTEN TEXT
============================================================

Pay special attention to handwritten:

- model numbers
- serial numbers
- dates
- prices
- seller/dealer names
- customer names

Read handwriting carefully.

============================================================
DOCUMENT TYPE
============================================================

Determine the document type.

Examples:

warranty_card
warranty_certificate
invoice
receipt
purchase_receipt
service_document
product_registration
other

============================================================
CATEGORY
============================================================

Use the selected product category.

Examples:

Refrigerator
Washing Machine
Television
Air Conditioner
Microwave
Dishwasher
Small Domestic Appliances

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

Do not write Markdown.

Do not write explanations.

Do not write ```json.

The exact format must be:

{
    "passports": [
        {
            "document_type": null,
            "product": null,
            "brand": null,
            "model": null,
            "serial_number": null,
            "purchase_price": null,
            "currency": null,
            "purchase_date": null,
            "warranty": null,
            "seller": null,
            "category": null,
            "customer_name": null,
            "order_id": null,
            "invoice_number": null,
            "selection": "checked",
            "evidence": null
        }
    ]
}

============================================================
FIELD RULES
============================================================

document_type:
String or null.

product:
The actual selected/purchased product.

brand:
Manufacturer / brand.

model:
Exact model number.

serial_number:
Exact serial number.

purchase_price:
Numeric value only.
Example:
198.00

NOT:
"RM 198.00"

currency:
Currency code/symbol.
Example:
"RM"

purchase_date:
Use ISO format:

YYYY-MM-DD

If date is ambiguous, return null.

warranty:
Preserve meaningful wording.
Example:
"2-YEAR"

seller:
Seller/dealer/company name.

category:
Product category.

customer_name:
Customer name if visible.

order_id:
Order ID if visible.

invoice_number:
Invoice number if visible.

selection:
For included passports this MUST be:

"checked"

evidence:
Brief explanation of why this product was selected.
Example:
"Checkbox beside Small Domestic Appliances is marked."

============================================================
CRITICAL FINAL CHECK
============================================================

Before returning JSON:

1. Count the visibly checked product boxes.
2. Create exactly one passport per checked product.
3. Do not create passports for unchecked products.
4. Do not merge multiple products.
5. Do not invent missing information.
6. Verify model and serial numbers character-by-character.
7. Verify handwritten dates carefully.
8. Return ONLY JSON.
"""


# ============================================================
# CLEAN AI JSON
# ============================================================

def extract_json_from_response(text):

    if not text:

        raise ValueError(
            "Vision model returned empty response."
        )

    text = text.strip()

    # Remove markdown fences if model accidentally adds them.
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = text.strip()

    # Direct JSON
    try:

        return json.loads(
            text
        )

    except json.JSONDecodeError:

        pass

    # Search for first JSON object.
    start = text.find("{")
    end = text.rfind("}")

    if (
        start != -1
        and end != -1
        and end > start
    ):

        candidate = text[
            start:end + 1
        ]

        try:

            return json.loads(
                candidate
            )

        except json.JSONDecodeError:

            pass

    raise ValueError(
        "Could not extract valid JSON from Vision model response.\n"
        + text
    )


# ============================================================
# NORMALIZE VALUE
# ============================================================

def clean_value(value):

    if value is None:

        return None

    if isinstance(
        value,
        str
    ):

        value = value.strip()

        if not value:

            return None

        invalid_values = {
            "none",
            "null",
            "n/a",
            "na",
            "not available",
            "unknown",
            "not found",
            "unavailable"
        }

        if value.lower() in invalid_values:

            return None

        return value

    return value


# ============================================================
# NORMALIZE PASSPORT
# ============================================================

def normalize_passport(item):

    if not isinstance(
        item,
        dict
    ):

        item = {}

    passport = {

        "document_type":
            clean_value(
                item.get("document_type")
            ),

        "product":
            clean_value(
                item.get("product")
            ),

        "brand":
            clean_value(
                item.get("brand")
            ),

        "model":
            clean_value(
                item.get("model")
            ),

        "serial_number":
            clean_value(
                item.get("serial_number")
            ),

        "purchase_price":
            clean_value(
                item.get("purchase_price")
            ),

        "currency":
            clean_value(
                item.get("currency")
            ),

        "purchase_date":
            clean_value(
                item.get("purchase_date")
            ),

        "warranty":
            clean_value(
                item.get("warranty")
            ),

        "seller":
            clean_value(
                item.get("seller")
            ),

        "category":
            clean_value(
                item.get("category")
            ),

        "customer_name":
            clean_value(
                item.get("customer_name")
            ),

        "order_id":
            clean_value(
                item.get("order_id")
            ),

        "invoice_number":
            clean_value(
                item.get("invoice_number")
            ),

        "selection":
            "checked",

        "evidence":
            clean_value(
                item.get("evidence")
            )
    }

    return passport


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicate_passports(passports):

    unique = []

    seen = set()

    for passport in passports:

        key = (

            str(
                passport.get(
                    "product"
                )
            ).lower().strip(),

            str(
                passport.get(
                    "brand"
                )
            ).lower().strip(),

            str(
                passport.get(
                    "model"
                )
            ).lower().strip(),

            str(
                passport.get(
                    "serial_number"
                )
            ).lower().strip()
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        unique.append(
            passport
        )

    return unique


# ============================================================
# VALIDATE SELECTED PRODUCTS
# ============================================================

def validate_passports(passports):

    valid = []

    for passport in passports:

        product = passport.get(
            "product"
        )

        category = passport.get(
            "category"
        )

        # At minimum, a passport must have some product
        # identity.
        if not product and not category:

            print(
                "Skipping passport with no product/category."
            )

            continue

        # Force selection to checked because this program
        # only accepts selected products.
        passport[
            "selection"
        ] = "checked"

        valid.append(
            passport
        )

    return valid


# ============================================================
# CALL OLLAMA VISION
# ============================================================

def analyze_image_with_vision(
    image_path,
    ocr_text=""
):

    print()
    print_separator("=")

    print(
        "PROCESSING IMAGE + VISION AI"
    )

    print_separator("=")

    print()
    print(
        "Vision model:",
        MODEL_NAME
    )

    print(
        "Sending ORIGINAL IMAGE to vision model..."
    )

    image_b64 = image_to_base64(
        image_path
    )

    # Add OCR only as supplementary evidence.
    # The original image remains the primary source.
    supplemental_text = ""

    if ocr_text:

        supplemental_text = """

SUPPLEMENTARY OCR TEXT:
-----------------------
""" + ocr_text[:12000] + """

IMPORTANT:
The OCR text may contain mistakes.
Always verify against the original image.
"""

    final_prompt = (
        VISION_PROMPT
        + supplemental_text
    )

    payload = {

        "model": MODEL_NAME,

        "prompt": final_prompt,

        "images": [
            image_b64
        ],

        "stream": False,

        "format": "json",

        "options": {

            "temperature": 0.0,

            "top_p": 0.1,

            "num_ctx": 8192
        }
    }

    try:

        response = requests.post(

            OLLAMA_URL,

            json=payload,

            timeout=300
        )

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "Could not connect to Ollama.\n"
            "Make sure Ollama is running."
        )

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "Ollama timed out while processing the image."
        )

    if response.status_code != 200:

        raise RuntimeError(
            "Ollama returned HTTP "
            + str(response.status_code)
            + ":\n"
            + response.text
        )

    result = response.json()

    raw_response = result.get(
        "response",
        ""
    )

    print()
    print(
        "Vision response received."
    )

    print()
    print_separator("-")

    print(
        "RAW VISION JSON:"
    )

    print_separator("-")

    print(
        raw_response
    )

    print_separator("-")

    parsed = extract_json_from_response(
        raw_response
    )

    return parsed


# ============================================================
# NORMALIZE MODEL OUTPUT
# ============================================================

def normalize_model_output(data):

    passports = []

    # --------------------------------------------------------
    # Expected:
    # {
    #     "passports": [...]
    # }
    # --------------------------------------------------------

    if isinstance(
        data,
        dict
    ):

        if isinstance(
            data.get("passports"),
            list
        ):

            passports = data[
                "passports"
            ]

        # Support accidental singular output.
        elif (
            "product" in data
            or "model" in data
            or "brand" in data
        ):

            passports = [
                data
            ]

        # Some models may use products.
        elif isinstance(
            data.get("products"),
            list
        ):

            passports = data[
                "products"
            ]

    elif isinstance(
        data,
        list
    ):

        passports = data

    normalized = []

    for item in passports:

        passport = normalize_passport(
            item
        )

        normalized.append(
            passport
        )

    normalized = validate_passports(
        normalized
    )

    normalized = remove_duplicate_passports(
        normalized
    )

    return normalized


# ============================================================
# SAVE PASSPORT JSON
# ============================================================

def save_passports(
    passports,
    image_path
):

    output = {

        "source_image":
            os.path.abspath(
                image_path
            ),

        "passport_count":
            len(passports),

        "passports":
            passports
    }

    # IMPORTANT:
    # Write using absolute path.
    with open(
        JSON_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            indent=4,
            ensure_ascii=False
        )

        f.flush()

    # Verify that the file actually exists.
    if not os.path.exists(
        JSON_FILE
    ):

        raise RuntimeError(
            "Passport JSON was not created."
        )

    # Read it back immediately.
    with open(
        JSON_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        verification = json.load(
            f
        )

    print()
    print_separator("=")

    print(
        "PASSPORT JSON SAVED SUCCESSFULLY"
    )

    print_separator("=")

    print(
        "Absolute path:"
    )

    print(
        JSON_FILE
    )

    print()
    print(
        "Passport count:",
        verification.get(
            "passport_count"
        )
    )

    return JSON_FILE


# ============================================================
# PRINT PASSPORTS
# ============================================================

def print_passports(passports):

    print()
    print_separator("=")

    print(
        "GENERATED DIGITAL PRODUCT PASSPORTS"
    )

    print_separator("=")

    for index, passport in enumerate(
        passports,
        start=1
    ):

        print()
        print_separator("-")

        print(
            f"PASSPORT #{index}"
        )

        print_separator("-")

        print(
            "Product       :",
            passport.get(
                "product"
            )
        )

        print(
            "Brand         :",
            passport.get(
                "brand"
            )
        )

        print(
            "Model         :",
            passport.get(
                "model"
            )
        )

        print(
            "Serial Number :",
            passport.get(
                "serial_number"
            )
        )

        price = passport.get(
            "purchase_price"
        )

        currency = passport.get(
            "currency"
        )

        if price is not None:

            if currency:

                price_display = (
                    f"{currency} {price}"
                )

            else:

                price_display = str(
                    price
                )

        else:

            price_display = None

        print(
            "Price         :",
            price_display
        )

        print(
            "Currency      :",
            currency
        )

        print(
            "Purchase Date :",
            passport.get(
                "purchase_date"
            )
        )

        print(
            "Warranty      :",
            passport.get(
                "warranty"
            )
        )

        print(
            "Seller        :",
            passport.get(
                "seller"
            )
        )

        print(
            "Category      :",
            passport.get(
                "category"
            )
        )

        print(
            "Selection     :",
            passport.get(
                "selection"
            )
        )

        print(
            "Evidence      :",
            passport.get(
                "evidence"
            )
        )

    print()
    print_separator("=")


# ============================================================
# FIND PASSPORT UI
# ============================================================

def find_passport_ui():

    candidates = [

        os.path.join(
            SCRIPT_DIR,
            "product_passport.py"
        ),

        os.path.join(
            SCRIPT_DIR,
            "passport.py"
        ),

        os.path.join(
            SCRIPT_DIR,
            "passport_ui.py"
        ),

        os.path.join(
            SCRIPT_DIR,
            "product_passport_ui.py"
        )
    ]

    for path in candidates:

        if os.path.isfile(
            path
        ):

            return path

    return None


# ============================================================
# LAUNCH PASSPORT UI
# ============================================================

def launch_passport_ui():

    ui_script = find_passport_ui()

    if ui_script is None:

        print()
        print(
            "Passport UI script was not automatically found."
        )

        print(
            "JSON is available at:"
        )

        print(
            JSON_FILE
        )

        return False

    print()
    print_separator("=")

    print(
        "LAUNCHING PRODUCT PASSPORT UI"
    )

    print_separator("=")

    print(
        "UI:",
        ui_script
    )

    print(
        "JSON:",
        JSON_FILE
    )

    try:

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Set the working directory to SCRIPT_DIR.
        #
        # This prevents the old problem where the UI looks
        # for product_passport.json in another directory.
        # ----------------------------------------------------

        subprocess.Popen(

            [
                sys.executable,
                ui_script,
                JSON_FILE
            ],

            cwd=SCRIPT_DIR
        )

        print()
        print(
            "Passport UI started."
        )

        return True

    except Exception as e:

        print()
        print(
            "Could not launch Passport UI:"
        )

        print(
            e
        )

        return False


# ============================================================
# SAVE OCR EVIDENCE
# ============================================================

def save_ocr_evidence(
    image_path,
    ocr_text
):

    evidence = {

        "image":
            os.path.abspath(
                image_path
            ),

        "ocr_text":
            ocr_text,

        "ocr_available":
            bool(
                ocr_text
            )
    }

    try:

        with open(
            EVIDENCE_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                evidence,
                f,
                indent=4,
                ensure_ascii=False
            )

    except Exception as e:

        print(
            "Could not save OCR evidence:",
            e
        )


# ============================================================
# SELECT IMAGE
# ============================================================

def select_image():

    root = tk.Tk()

    root.withdraw()

    root.attributes(
        "-topmost",
        True
    )

    image_path = filedialog.askopenfilename(

        title="Select Product / Warranty Document",

        filetypes=[

            (
                "Image files",
                "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"
            ),

            (
                "All files",
                "*.*"
            )
        ]
    )

    root.destroy()

    return image_path


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():

    print_title(
        "TEXTEMAGE - DIGITAL PRODUCT PASSPORT"
    )

    print(
        "Working directory:"
    )

    print(
        SCRIPT_DIR
    )

    print()

    # --------------------------------------------------------
    # 1. CHECK OLLAMA
    # --------------------------------------------------------

    if not check_ollama():

        messagebox.showerror(
            "TextEmage",
            "Ollama is not available.\n\n"
            f"Make sure {MODEL_NAME} is installed."
        )

        return

    # --------------------------------------------------------
    # 2. SELECT IMAGE
    # --------------------------------------------------------

    image_path = select_image()

    if not image_path:

        print(
            "No image selected."
        )

        return

    # --------------------------------------------------------
    # 3. INSPECT IMAGE
    # --------------------------------------------------------

    inspect_image(
        image_path
    )

    # --------------------------------------------------------
    # 4. OPTIONAL OCR
    # --------------------------------------------------------

    print()
    print_separator("=")

    print(
        "STARTING OPTIONAL DOCUMENT OCR"
    )

    print_separator("=")

    ocr_text = run_optional_tesseract(
        image_path
    )

    save_ocr_evidence(
        image_path,
        ocr_text
    )

    # --------------------------------------------------------
    # 5. VISION AI
    # --------------------------------------------------------

    try:

        ai_result = analyze_image_with_vision(

            image_path,

            ocr_text
        )

    except Exception as e:

        print()
        print_separator("=")

        print(
            "VISION PROCESSING FAILED"
        )

        print_separator("=")

        print(
            str(e)
        )

        messagebox.showerror(
            "TextEmage",
            "Vision processing failed.\n\n"
            + str(e)
        )

        return

    # --------------------------------------------------------
    # 6. NORMALIZE
    # --------------------------------------------------------

    passports = normalize_model_output(
        ai_result
    )

    # --------------------------------------------------------
    # 7. CHECK RESULT
    # --------------------------------------------------------

    if not passports:

        print()
        print_separator("=")

        print(
            "NO SELECTED PRODUCTS DETECTED"
        )

        print_separator("=")

        print(
            "No passport was generated because no selected"
        )

        print(
            "product could be confidently identified."
        )

        messagebox.showwarning(
            "TextEmage",
            "No selected/purchased product was detected."
        )

        return

    # --------------------------------------------------------
    # 8. PRINT
    # --------------------------------------------------------

    print_passports(
        passports
    )

    # --------------------------------------------------------
    # 9. SAVE
    # --------------------------------------------------------

    try:

        save_passports(

            passports,

            image_path
        )

    except Exception as e:

        print()
        print(
            "Could not save passport JSON:"
        )

        print(
            e
        )

        messagebox.showerror(
            "TextEmage",
            "Could not save passport JSON.\n\n"
            + str(e)
        )

        return

    # --------------------------------------------------------
    # 10. LAUNCH UI
    # --------------------------------------------------------

    launch_passport_ui()

    # --------------------------------------------------------
    # FINAL MESSAGE
    # --------------------------------------------------------

    print()
    print_separator("=")

    print(
        "PROCESS COMPLETED"
    )

    print_separator("=")

    print(
        f"{len(passports)} passport(s) generated."
    )

    print()

    print(
        "JSON:"
    )

    print(
        JSON_FILE
    )

    print_separator("=")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()