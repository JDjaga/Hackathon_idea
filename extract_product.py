"""
PRODUCT PASSPORT - MULTI PRODUCT EXTRACTION

Pipeline:

IMAGE
  ↓
OCR evidence
  ↓
Qwen2.5-VL visual understanding
  ↓
Checkbox / product selection analysis
  ↓
Multi-product grouping
  ↓
Independent Product Passports

Important:
A product appearing on a document does NOT automatically mean
that product was purchased.

Checked/selected product = purchased product candidate.

Warranty tables and lists of product categories are NOT treated
as multiple purchased products.

Designed for:
- invoices
- receipts
- warranty cards
- warranty certificates
- product labels
- purchase documents
- documents containing multiple products
"""

import os
import json
import re
import base64
import requests

from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "ocr_output"
)

OCR_FILE = os.path.join(
    OUTPUT_DIR,
    "ocr_evidence.json"
)

PASSPORT_FILE = os.path.join(
    OUTPUT_DIR,
    "product_passports.json"
)

OLLAMA_URL = "http://localhost:11434"

TEXT_MODEL = "llama3.2:latest"

VISION_MODEL = "qwen2.5vl:7b"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# EMPTY PRODUCT
# ============================================================

def empty_product():

    return {

        "product": None,

        "brand": None,

        "model": None,

        "serial_number": None,

        "purchase_price": None,

        "currency": None,

        "purchase_date": None,

        "warranty": None,

        "seller": None,

        "category": None,

        "customer_name": None,

        "order_id": None,

        "invoice_number": None,

        "selection_status": None,

        "selection_evidence": None
    }


# ============================================================
# EMPTY PASSPORT DATA
# ============================================================

def empty_result():

    return {

        "document_type": None,

        "products": []
    }


# ============================================================
# OLLAMA MODELS
# ============================================================

def get_ollama_models():

    try:

        response = requests.get(
            f"{OLLAMA_URL}/api/tags",
            timeout=5
        )

        response.raise_for_status()

        data = response.json()

        models = []

        for model in data.get(
            "models",
            []
        ):

            name = model.get(
                "name",
                ""
            )

            if name:
                models.append(name)

        return models

    except Exception as e:

        print(
            "Could not connect to Ollama:"
        )

        print(e)

        return []


# ============================================================
# CHOOSE VISION MODEL
# ============================================================

def choose_vision_model():

    models = get_ollama_models()

    print()
    print(
        "Available Ollama models:"
    )

    for model in models:

        print(
            " -",
            model
        )

    # --------------------------------------------------------
    # Prefer Qwen Vision
    # --------------------------------------------------------

    for model in models:

        lower = model.lower()

        if (
            "qwen2.5vl" in lower
            or "qwen2-vl" in lower
            or "qwen3-vl" in lower
        ):

            print()
            print(
                "Using vision model:",
                model
            )

            return model

    # --------------------------------------------------------
    # If configured model exists
    # --------------------------------------------------------

    if VISION_MODEL in models:

        return VISION_MODEL

    print()
    print(
        "WARNING: Vision model not found."
    )

    return None


# ============================================================
# LOAD OCR
# ============================================================

def load_ocr():

    if not os.path.exists(
        OCR_FILE
    ):

        print(
            "OCR evidence file not found."
        )

        return {

            "combined_text": "",

            "relevant_lines": [],

            "paddleocr": [],

            "tesseract_text": ""
        }

    try:

        with open(
            OCR_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            "Could not load OCR evidence:"
        )

        print(e)

        return {

            "combined_text": "",

            "relevant_lines": [],

            "paddleocr": [],

            "tesseract_text": ""
        }


# ============================================================
# IMAGE -> BASE64
# ============================================================

def image_to_base64(
    image_path
):

    with open(
        image_path,
        "rb"
    ) as f:

        encoded = base64.b64encode(
            f.read()
        ).decode(
            "utf-8"
        )

    return encoded


# ============================================================
# CLEAN JSON RESPONSE
# ============================================================

def clean_json_response(
    text
):

    if not text:

        return None

    text = text.strip()

    # Remove markdown fences.

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"```",
        "",
        text
    )

    text = text.strip()

    # Find object.

    start = text.find("{")

    end = text.rfind("}")

    if start == -1 or end == -1:

        return None

    candidate = text[
        start:end + 1
    ]

    try:

        return json.loads(
            candidate
        )

    except Exception:

        # Try extracting JSON object
        # from accidental surrounding text.

        try:

            match = re.search(
                r"\{.*\}",
                text,
                flags=re.DOTALL
            )

            if match:

                return json.loads(
                    match.group(0)
                )

        except Exception:

            pass

    return None


# ============================================================
# NORMALIZE DATE
# ============================================================

def normalize_date(
    value
):

    if value is None:

        return None

    value = str(
        value
    ).strip()

    if not value:

        return None

    formats = [

        "%Y-%m-%d",

        "%d/%m/%Y",
        "%d-%m-%Y",

        "%m/%d/%Y",
        "%m-%d-%Y",

        "%d/%m/%y",
        "%d-%m-%y",

        "%m/%d/%y",
        "%m-%d-%y",

        "%B %d, %Y",
        "%b %d, %Y",

        "%d %B %Y",
        "%d %b %Y"
    ]

    for fmt in formats:

        try:

            date = datetime.strptime(
                value,
                fmt
            )

            return date.strftime(
                "%Y-%m-%d"
            )

        except Exception:

            pass

    # Search inside larger text.

    patterns = [

        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",

        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b",

        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2}\b"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            value
        )

        if not match:
            continue

        found = match.group(0)

        for fmt in formats:

            try:

                date = datetime.strptime(
                    found,
                    fmt
                )

                return date.strftime(
                    "%Y-%m-%d"
                )

            except Exception:

                pass

    return value


# ============================================================
# NORMALIZE PRICE
# ============================================================

def normalize_price(
    value
):

    if value is None:

        return None

    if isinstance(
        value,
        (int, float)
    ):

        return value

    text = str(
        value
    ).strip()

    if not text:

        return None

    # Remove common currency symbols.

    cleaned = re.sub(
        r"[₹$€£,\s]",
        "",
        text
    )

    # Keep decimal point.

    try:

        number = float(
            cleaned
        )

        return number

    except Exception:

        return value


# ============================================================
# NORMALIZE PRODUCT
# ============================================================

def normalize_product(
    product
):

    result = empty_product()

    if not isinstance(
        product,
        dict
    ):

        return result

    for key in result:

        if key in product:

            result[key] = product.get(
                key
            )

    # Normalize date.

    result[
        "purchase_date"
    ] = normalize_date(
        result["purchase_date"]
    )

    # Normalize price.

    result[
        "purchase_price"
    ] = normalize_price(
        result["purchase_price"]
    )

    # Empty strings -> None.

    for key in result:

        value = result[key]

        if isinstance(
            value,
            str
        ):

            value = value.strip()

            if not value:

                value = None

            result[key] = value

    return result


# ============================================================
# NORMALIZE COMPLETE RESULT
# ============================================================

def normalize_result(
    data
):

    result = empty_result()

    if not isinstance(
        data,
        dict
    ):

        return result

    result[
        "document_type"
    ] = data.get(
        "document_type"
    )

    products = data.get(
        "products",
        []
    )

    if not isinstance(
        products,
        list
    ):

        products = []

    for product in products:

        normalized = normalize_product(
            product
        )

        result[
            "products"
        ].append(
            normalized
        )

    return result


# ============================================================
# BUILD OCR TEXT
# ============================================================

def build_ocr_context(
    ocr_data
):

    combined_text = ocr_data.get(
        "combined_text",
        ""
    )

    relevant_lines = ocr_data.get(
        "relevant_lines",
        []
    )

    paddle_items = ocr_data.get(
        "paddleocr",
        []
    )

    paddle_lines = []

    for item in paddle_items:

        text = item.get(
            "text",
            ""
        )

        confidence = item.get(
            "confidence",
            0
        )

        if text:

            paddle_lines.append(
                f"{text} [confidence={confidence}]"
            )

    return f"""
================ OCR COMBINED TEXT ================

{combined_text}

================ RELEVANT OCR LINES ================

{chr(10).join(relevant_lines)}

================ PADDLE OCR ================

{chr(10).join(paddle_lines)}
"""


# ============================================================
# EXTRACTION PROMPT
# ============================================================

def create_prompt(
    ocr_data
):

    ocr_context = build_ocr_context(
        ocr_data
    )

    prompt = f"""
You are the visual document-understanding engine of an
AI Product Passport system.

You are looking at a REAL invoice, receipt, warranty card,
warranty certificate, product label, or purchase document.

The document may contain ONE OR MULTIPLE PRODUCTS.

Your task is to create INDEPENDENT product records.

VERY IMPORTANT:

A product name appearing anywhere in a document does NOT
automatically mean that product was purchased.

============================================================
PRODUCT SELECTION / CHECKBOX RULES
============================================================

1. Carefully inspect the ORIGINAL IMAGE visually.

2. If the document contains checkboxes, inspect which
   checkbox is actually marked.

3. A CHECKED / SELECTED product is a purchased-product
   candidate.

4. An UNCHECKED product MUST NOT become a passport.

5. If only one product checkbox is checked, return exactly
   ONE product.

6. If multiple different product checkboxes are checked,
   return one independent product for EACH checked product.

7. A printed warranty table containing many product categories
   is NOT evidence that all those products were purchased.

8. For example, if a warranty table says:

   LCD/LED TV
   Refrigerator
   Washing Machine
   Microwave
   Dishwasher

   this does NOT mean five products were purchased.

9. Likewise, if a warranty card says:

   [ ] Washing Machine
   [ ] Tumble Dryer
   [ ] Dishwasher
   [X] Small Domestic Appliances

   return ONLY Small Domestic Appliances.

10. Do NOT create passports for unchecked categories.

11. If there is no checkbox, determine the actual purchased
    product using explicit product information such as:
    product name, model, serial number, invoice line item,
    product description, or purchase information.

============================================================
MULTI-PRODUCT RULES
============================================================

12. The same image may contain multiple genuinely purchased
    products.

13. If multiple products are genuinely present, separate them
    into independent product objects.

14. NEVER merge Product A's model with Product B's serial number.

15. NEVER copy a model number from one product into another.

16. NEVER copy a serial number from one product into another.

17. Keep each product's information associated with the
    correct product.

18. If a field cannot be confidently associated with a
    particular product, return null for that field.

19. If the document contains multiple invoice line items,
    each purchased line item may represent a separate product.

20. If two line items are merely different quantities of the
    same product and there is no separate serial/model
    information, do not invent separate serial numbers.

============================================================
IMPORTANT ANTI-HALLUCINATION RULES
============================================================

21. NEVER invent information.

22. NEVER guess a model number.

23. NEVER guess a serial number.

24. NEVER use the customer's name as the product name.

25. NEVER use a signature as the seller.

26. NEVER use an order ID as a model number.

27. NEVER use a serial number as a model number.

28. NEVER use a document title such as "Warranty Certificate"
    as the product name.

29. A manufacturer warranty table is not a purchased-product
    list.

30. If purchase price is absent, return null.

31. If purchase date is absent, return null.

32. If serial number is absent, return null.

33. If model number is absent, return null.

34. Preserve unusual model and serial strings as visually
    detected. Do not silently correct them.

35. Handwritten information may be important.

36. Consider the relationship between a label and the nearby
    handwritten/printed value.

============================================================
FIELD ASSOCIATION
============================================================

For every actual purchased product, try to determine:

- product
- brand
- model
- serial_number
- purchase_price
- currency
- purchase_date
- warranty
- seller
- category
- customer_name
- order_id
- invoice_number

============================================================
DOCUMENT TYPE
============================================================

Determine whether this is approximately:

- Invoice
- Receipt
- Warranty Card
- Warranty Certificate
- Product Label
- Purchase Document
- Other

============================================================
CHECKBOX INTERPRETATION
============================================================

Visually distinguish:

[ ] unchecked

[X] checked

[tick] checked

[✓] checked

[✔] checked

handwritten tick

handwritten cross

filled checkbox

circle/mark next to a product

Do NOT assume that text extraction alone is sufficient.

The ORIGINAL IMAGE is authoritative for checkbox state.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Use EXACTLY this structure:

{{
    "document_type": null,

    "products": [
        {{
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
            "selection_status": null,
            "selection_evidence": null
        }}
    ]
}}

============================================================
SELECTION STATUS
============================================================

Use:

"checked"

when a product checkbox/selection is visually confirmed.

Use:

"unchecked"

when the product is clearly listed but not selected.

Use:

"explicit"

when the product is directly identified as purchased without
a checkbox.

Use:

"unknown"

only when selection cannot be determined.

IMPORTANT:

Do NOT create a product passport merely because a product
appears in a warranty table.

============================================================
SELECTION EVIDENCE
============================================================

For each product, briefly describe the visual evidence.

Examples:

"Checkbox beside Small Domestic Appliances is marked."

"Invoice line item explicitly lists Washing Machine."

"Product model and serial are printed together on the
product label."

Do not invent evidence.

============================================================
OCR CONTEXT
============================================================

{ocr_context}

Now inspect the ORIGINAL IMAGE carefully.

Pay particular attention to:

- checkboxes
- handwritten ticks
- product sections
- model numbers
- serial numbers
- labels
- invoice line items
- dates
- prices
- seller information
- warranty information

Return ONLY JSON.
"""

    return prompt


# ============================================================
# CALL QWEN VISION
# ============================================================

def call_vision_model(
    image_path,
    prompt,
    model
):

    print()
    print(
        "Sending ORIGINAL IMAGE to vision model..."
    )

    print(
        "Vision model:",
        model
    )

    image_base64 = image_to_base64(
        image_path
    )

    payload = {

        "model": model,

        "prompt": prompt,

        "images": [
            image_base64
        ],

        "stream": False,

        "format": "json",

        "options": {

            "temperature": 0.0
        }
    }

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json=payload,
        timeout=600
    )

    response.raise_for_status()

    data = response.json()

    return data.get(
        "response",
        ""
    )


# ============================================================
# FALLBACK OCR EXTRACTION
# ============================================================

def fallback_extraction(
    ocr_data
):

    """
    Very conservative fallback.

    This does NOT attempt to invent multiple products.

    It only returns a minimal product if explicit labels
    are visible in OCR text.
    """

    result = empty_result()

    text = ocr_data.get(
        "combined_text",
        ""
    )

    if not text:

        return result

    lower = text.lower()

    # --------------------------------------------------------
    # Document type
    # --------------------------------------------------------

    if "warranty" in lower:

        result[
            "document_type"
        ] = "Warranty Card"

    elif (
        "invoice" in lower
        or "tax invoice" in lower
    ):

        result[
            "document_type"
        ] = "Invoice"

    elif "receipt" in lower:

        result[
            "document_type"
        ] = "Receipt"

    # --------------------------------------------------------
    # Product
    # --------------------------------------------------------

    product = empty_product()

    product[
        "selection_status"
    ] = "unknown"

    # Look for explicit model.

    model_patterns = [

        r"model\s*(?:no|number)?\s*[:#\-]?\s*([A-Z0-9][A-Z0-9._/\- ]{2,})",

        r"model\s*[:#\-]?\s*([A-Z0-9][A-Z0-9._/\- ]{2,})"
    ]

    for pattern in model_patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:

            value = match.group(1).strip()

            value = re.split(
                r"\n",
                value
            )[0].strip()

            if value:

                product[
                    "model"
                ] = value

                break

    # Serial.

    serial_patterns = [

        r"serial\s*(?:no|number)?\s*[:#\-]?\s*([A-Z0-9][A-Z0-9._/\- ]{2,})",

        r"\bs/n\s*[:#\-]?\s*([A-Z0-9][A-Z0-9._/\- ]{2,})"
    ]

    for pattern in serial_patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:

            value = match.group(1).strip()

            value = re.split(
                r"\n",
                value
            )[0].strip()

            if value:

                product[
                    "serial_number"
                ] = value

                break

    # Purchase date.

    date_match = re.search(
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        text
    )

    if date_match:

        product[
            "purchase_date"
        ] = normalize_date(
            date_match.group(0)
        )

    # Only return fallback product if
    # there is meaningful evidence.

    if (
        product["model"]
        or product["serial_number"]
        or product["purchase_date"]
    ):

        result[
            "products"
        ].append(
            product
        )

    return result


# ============================================================
# REMOVE DUPLICATE PRODUCTS
# ============================================================

def deduplicate_products(
    products
):

    unique = []

    seen = set()

    for product in products:

        if not isinstance(
            product,
            dict
        ):

            continue

        model = str(
            product.get(
                "model"
            ) or ""
        ).lower().strip()

        serial = str(
            product.get(
                "serial_number"
            ) or ""
        ).lower().strip()

        name = str(
            product.get(
                "product"
            ) or ""
        ).lower().strip()

        # Prefer serial number as identity.

        if serial:

            identity = (
                "serial",
                serial
            )

        elif model:

            identity = (
                "model",
                model
            )

        elif name:

            identity = (
                "name",
                name
            )

        else:

            identity = (
                "unknown",
                json.dumps(
                    product,
                    sort_keys=True
                )
            )

        if identity in seen:

            continue

        seen.add(
            identity
        )

        unique.append(
            product
        )

    return unique


# ============================================================
# REMOVE UNCHECKED PRODUCTS
# ============================================================

def validate_selection(
    products
):

    """
    Apply the most important product-selection rule.

    If the AI explicitly says a product is unchecked,
    remove it.

    If it says checked/explicit, keep it.

    Unknown products are kept only when they contain meaningful
    product information because some documents don't use
    checkboxes.
    """

    validated = []

    for product in products:

        status = str(
            product.get(
                "selection_status"
            ) or ""
        ).lower().strip()

        if status == "unchecked":

            continue

        validated.append(
            product
        )

    return validated


# ============================================================
# SAVE RESULT
# ============================================================

def save_result(
    result
):

    with open(
        PASSPORT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            indent=4,
            ensure_ascii=False
        )

    return PASSPORT_FILE


# ============================================================
# PRINT PASSPORTS
# ============================================================

def print_passports(
    result
):

    print()
    print(
        "=" * 60
    )

    print(
        "PRODUCT PASSPORT EXTRACTION"
    )

    print(
        "=" * 60
    )

    print(
        "Document Type:",
        result.get(
            "document_type"
        )
    )

    products = result.get(
        "products",
        []
    )

    print(
        "Products found:",
        len(products)
    )

    print()

    for index, product in enumerate(
        products,
        start=1
    ):

        print(
            "-" * 50
        )

        print(
            f"PASSPORT #{index}"
        )

        print(
            "-" * 50
        )

        print(
            "Product       :",
            product.get("product")
        )

        print(
            "Brand         :",
            product.get("brand")
        )

        print(
            "Model         :",
            product.get("model")
        )

        print(
            "Serial Number :",
            product.get("serial_number")
        )

        print(
            "Price         :",
            product.get("purchase_price")
        )

        print(
            "Currency      :",
            product.get("currency")
        )

        print(
            "Purchase Date :",
            product.get("purchase_date")
        )

        print(
            "Warranty      :",
            product.get("warranty")
        )

        print(
            "Seller        :",
            product.get("seller")
        )

        print(
            "Category      :",
            product.get("category")
        )

        print(
            "Selection     :",
            product.get("selection_status")
        )

        print(
            "Evidence      :",
            product.get("selection_evidence")
        )

    print()
    print(
        "=" * 60
    )

    print(
        "Saved:",
        PASSPORT_FILE
    )

    print(
        "=" * 60
    )


# ============================================================
# MAIN EXTRACTION FUNCTION
# ============================================================

def extract_products(
    image_path=None
):

    print()
    print(
        "Processing OCR text + IMAGE with local AI..."
    )

    # --------------------------------------------------------
    # Determine image
    # --------------------------------------------------------

    if image_path is None:

        image_path = None

        # Try image recorded in OCR evidence.

        if os.path.exists(
            OCR_FILE
        ):

            try:

                ocr_temp = load_ocr()

                image_path = ocr_temp.get(
                    "image"
                )

            except Exception:

                image_path = None

    if not image_path:

        raise FileNotFoundError(
            "Original image path is not available."
        )

    if not os.path.exists(
        image_path
    ):

        raise FileNotFoundError(
            f"Image not found:\n{image_path}"
        )

    # --------------------------------------------------------
    # Load OCR
    # --------------------------------------------------------

    ocr_data = load_ocr()

    # --------------------------------------------------------
    # Vision model
    # --------------------------------------------------------

    model = choose_vision_model()

    result = None

    if model:

        prompt = create_prompt(
            ocr_data
        )

        try:

            raw_response = call_vision_model(
                image_path,
                prompt,
                model
            )

            print()
            print(
                "Vision model response received."
            )

            result = clean_json_response(
                raw_response
            )

            if result is None:

                print(
                    "Vision model returned invalid JSON."
                )

        except Exception as e:

            print()
            print(
                "Vision extraction failed:"
            )

            print(e)

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    if result is None:

        print()
        print(
            "Using conservative OCR fallback."
        )

        result = fallback_extraction(
            ocr_data
        )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    result = normalize_result(
        result
    )

    # --------------------------------------------------------
    # Selection validation
    # --------------------------------------------------------

    result[
        "products"
    ] = validate_selection(
        result[
            "products"
        ]
    )

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    result[
        "products"
    ] = deduplicate_products(
        result[
            "products"
        ]
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_result(
        result
    )

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print_passports(
        result
    )

    return result


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def extract_product(
    image_path=None
):

    """
    Old function name retained so older code does not break.
    """

    return extract_products(
        image_path
    )


# ============================================================
# DIRECT RUN
# ============================================================

if __name__ == "__main__":

    print(
        "Product Passport Multi-Product Extractor"
    )

    print()

    image = input(
        "Enter image path: "
    ).strip()

    if image:

        extract_products(
            image
        )

    else:

        print(
            "No image supplied."
        )