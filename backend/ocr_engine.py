"""
OCR ENGINE
Product Passport Multi-Product Prototype

Pipeline:

IMAGE
  ↓
Image preprocessing
  ↓
PaddleOCR (optional)
  ↓
Tesseract (optional)
  ↓
OCR evidence
  ↓
Qwen2.5-VL visual understanding

Important:
OCR is supporting evidence.

The original image is still passed directly to
Qwen2.5-VL for visual analysis.
"""

import os
import re
import json
import shutil

from PIL import (
    Image,
    ImageEnhance,
    ImageFilter,
    ImageOps
)


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

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# OPTIONAL TESSERACT
# ============================================================

TESSERACT_AVAILABLE = False

try:

    import pytesseract

    from pytesseract import Output

    # --------------------------------------------------------
    # Read custom path
    # --------------------------------------------------------

    tess_candidates = []

    path_file = os.path.join(
        BASE_DIR,
        "tesseract_path.txt"
    )

    if os.path.exists(
        path_file
    ):

        try:

            with open(
                path_file,
                "r",
                encoding="utf-8"
            ) as f:

                custom_path = f.read().strip()

                if custom_path:

                    tess_candidates.append(
                        custom_path
                    )

        except Exception:

            pass

    # Common Windows installation path.

    tess_candidates.extend([

        r"C:\Program Files\Tesseract-OCR\tesseract.exe",

        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",

        os.path.expandvars(
            r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"
        )
    ])

    # Existing PATH.

    which_tesseract = shutil.which(
        "tesseract"
    )

    if which_tesseract:

        tess_candidates.append(
            which_tesseract
        )

    selected_tess = None

    for candidate in tess_candidates:

        if candidate and os.path.exists(
            candidate
        ):

            selected_tess = candidate

            break

    if selected_tess:

        pytesseract.pytesseract.tesseract_cmd = (
            selected_tess
        )

    # --------------------------------------------------------
    # Validate installation
    # --------------------------------------------------------

    try:

        version = pytesseract.get_tesseract_version()

        version_text = str(
            version
        )

        if version_text:

            TESSERACT_AVAILABLE = True

            print()
            print(
                "Tesseract detected:"
            )

            print(
                version_text.splitlines()[0]
            )

    except Exception as e:

        print()
        print(
            "Tesseract detected but language data is unavailable."
        )

        print(
            "Tesseract OCR will be disabled."
        )

        print(
            "Reason:",
            e
        )

except ImportError:

    print(
        "pytesseract is not installed."
    )

    TESSERACT_AVAILABLE = False


# ============================================================
# OPTIONAL PADDLE OCR
# ============================================================

PADDLE_AVAILABLE = False
PADDLE_OCR = None


def create_paddle_ocr():

    global PADDLE_AVAILABLE

    try:

        from paddleocr import PaddleOCR

        print()
        print(
            "Initializing PaddleOCR..."
        )

        try:

            engine = PaddleOCR(

                lang="en",

                use_doc_orientation_classify=False,

                use_doc_unwarping=False,

                use_textline_orientation=True
            )

            PADDLE_AVAILABLE = True

            print(
                "PaddleOCR initialized."
            )

            return engine

        except Exception as e:

            print()
            print(
                "PaddleOCR unavailable."
            )

            print(
                "OCR will continue using other methods."
            )

            print(
                "Reason:",
                e
            )

            PADDLE_AVAILABLE = False

            return None

    except ImportError:

        print(
            "PaddleOCR package is not installed."
        )

        return None


PADDLE_OCR = create_paddle_ocr()


# ============================================================
# LOAD IMAGE
# ============================================================

def load_image(
    image_path
):

    img = Image.open(
        image_path
    )

    if img.mode != "RGB":

        img = img.convert(
            "RGB"
        )

    return img


# ============================================================
# UPSCALE
# ============================================================

def upscale_image(
    img,
    minimum_width=1800
):

    width, height = img.size

    if width >= minimum_width:

        return img

    scale = (
        minimum_width / width
    )

    new_width = int(
        width * scale
    )

    new_height = int(
        height * scale
    )

    return img.resize(
        (
            new_width,
            new_height
        ),
        Image.Resampling.LANCZOS
    )


# ============================================================
# IMAGE VARIANTS
# ============================================================

def create_variants(
    img
):

    variants = []

    upscaled = upscale_image(
        img
    )

    variants.append(
        (
            "original",
            upscaled
        )
    )

    # --------------------------------------------------------
    # Grayscale
    # --------------------------------------------------------

    gray = ImageOps.grayscale(
        upscaled
    )

    gray = ImageOps.autocontrast(
        gray,
        cutoff=1
    )

    gray = ImageEnhance.Contrast(
        gray
    ).enhance(1.8)

    gray = ImageEnhance.Sharpness(
        gray
    ).enhance(2.0)

    variants.append(
        (
            "grayscale",
            gray
        )
    )

    # --------------------------------------------------------
    # Sharpened
    # --------------------------------------------------------

    sharp = upscaled.filter(
        ImageFilter.UnsharpMask(
            radius=2,
            percent=180,
            threshold=3
        )
    )

    sharp = ImageEnhance.Contrast(
        sharp
    ).enhance(1.5)

    variants.append(
        (
            "sharpened",
            sharp
        )
    )

    # --------------------------------------------------------
    # High contrast
    # --------------------------------------------------------

    high_contrast = ImageOps.grayscale(
        upscaled
    )

    high_contrast = ImageOps.autocontrast(
        high_contrast,
        cutoff=2
    )

    high_contrast = ImageEnhance.Contrast(
        high_contrast
    ).enhance(2.5)

    variants.append(
        (
            "high_contrast",
            high_contrast
        )
    )

    # --------------------------------------------------------
    # Threshold light
    # --------------------------------------------------------

    threshold_light = ImageOps.grayscale(
        upscaled
    )

    threshold_light = threshold_light.point(
        lambda x: 255 if x > 160 else 0
    )

    variants.append(
        (
            "threshold_light",
            threshold_light
        )
    )

    # --------------------------------------------------------
    # Threshold dark
    # --------------------------------------------------------

    threshold_dark = ImageOps.grayscale(
        upscaled
    )

    threshold_dark = threshold_dark.point(
        lambda x: 255 if x > 120 else 0
    )

    variants.append(
        (
            "threshold_dark",
            threshold_dark
        )
    )

    return variants


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(
    text
):

    if not text:

        return ""

    text = text.replace(
        "\r",
        "\n"
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# TESSERACT OCR
# ============================================================

def run_tesseract(
    img
):

    if not TESSERACT_AVAILABLE:

        return ""

    results = []

    configs = [

        "--oem 3 --psm 6",

        "--oem 3 --psm 11",

        "--oem 3 --psm 12",

        "--oem 3 --psm 3"
    ]

    for config in configs:

        try:

            text = pytesseract.image_to_string(
                img,
                config=config,
                lang="eng"
            )

            if text and text.strip():

                results.append(
                    normalize_text(
                        text
                    )
                )

        except Exception:

            # Don't spam terminal.
            # OCR failure is non-fatal.

            continue

    if not results:

        return ""

    results.sort(
        key=lambda x: len(x),
        reverse=True
    )

    return results[0]


# ============================================================
# TESSERACT BOXES
# ============================================================

def run_tesseract_boxes(
    img
):

    if not TESSERACT_AVAILABLE:

        return []

    boxes = []

    try:

        data = pytesseract.image_to_data(

            img,

            output_type=Output.DICT,

            config="--oem 3 --psm 11",

            lang="eng"
        )

        count = len(
            data["text"]
        )

        for i in range(
            count
        ):

            text = data["text"][i].strip()

            if not text:

                continue

            try:

                confidence = float(
                    data["conf"][i]
                )

            except Exception:

                confidence = 0

            if confidence < 15:

                continue

            boxes.append(
                {

                    "text": text,

                    "confidence": confidence,

                    "x": data["left"][i],

                    "y": data["top"][i],

                    "width": data["width"][i],

                    "height": data["height"][i]
                }
            )

    except Exception:

        return []

    return boxes


# ============================================================
# PADDLE RESULT PARSER
# ============================================================

def extract_paddle_result(
    result
):

    extracted = []

    # --------------------------------------------------------
    # New API
    # --------------------------------------------------------

    try:

        if hasattr(
            result,
            "json"
        ):

            data = result.json

            if callable(data):

                data = data()

            if isinstance(
                data,
                str
            ):

                data = json.loads(
                    data
                )

            if isinstance(
                data,
                dict
            ):

                res = data.get(
                    "res",
                    data
                )

                texts = (
                    res.get("rec_texts")
                    or res.get("texts")
                    or []
                )

                scores = (
                    res.get("rec_scores")
                    or res.get("scores")
                    or []
                )

                boxes = (
                    res.get("rec_polys")
                    or res.get("dt_polys")
                    or res.get("boxes")
                    or []
                )

                for i, text in enumerate(
                    texts
                ):

                    if not text:

                        continue

                    confidence = 0

                    if i < len(
                        scores
                    ):

                        try:

                            confidence = float(
                                scores[i]
                            )

                        except Exception:

                            confidence = 0

                    box = None

                    if i < len(
                        boxes
                    ):

                        try:

                            box = boxes[i].tolist()

                        except Exception:

                            box = boxes[i]

                    extracted.append(
                        {

                            "text": str(
                                text
                            ).strip(),

                            "confidence": confidence,

                            "box": box
                        }
                    )

                if extracted:

                    return extracted

    except Exception:

        pass

    # --------------------------------------------------------
    # Dict
    # --------------------------------------------------------

    try:

        if isinstance(
            result,
            dict
        ):

            texts = (
                result.get("rec_texts")
                or result.get("texts")
                or []
            )

            scores = (
                result.get("rec_scores")
                or result.get("scores")
                or []
            )

            for i, text in enumerate(
                texts
            ):

                if not text:

                    continue

                confidence = 0

                if i < len(
                    scores
                ):

                    try:

                        confidence = float(
                            scores[i]
                        )

                    except Exception:

                        confidence = 0

                extracted.append(
                    {

                        "text": str(
                            text
                        ).strip(),

                        "confidence": confidence
                    }
                )

            if extracted:

                return extracted

    except Exception:

        pass

    # --------------------------------------------------------
    # Old API
    # --------------------------------------------------------

    try:

        if isinstance(
            result,
            list
        ):

            for item in result:

                if not isinstance(
                    item,
                    list
                ):

                    continue

                for entry in item:

                    try:

                        box = entry[0]

                        text_info = entry[1]

                        text = text_info[0]

                        confidence = float(
                            text_info[1]
                        )

                        extracted.append(
                            {

                                "text": str(
                                    text
                                ).strip(),

                                "confidence": confidence,

                                "box": box
                            }
                        )

                    except Exception:

                        continue

    except Exception:

        pass

    return extracted


# ============================================================
# PADDLE OCR
# ============================================================

def run_paddle(
    img
):

    if not PADDLE_AVAILABLE:

        return []

    temp_path = os.path.join(
        OUTPUT_DIR,
        "_temporary_ocr.png"
    )

    try:

        img.save(
            temp_path
        )

        result = PADDLE_OCR.predict(
            temp_path
        )

        all_results = []

        for item in result:

            extracted = extract_paddle_result(
                item
            )

            all_results.extend(
                extracted
            )

        return all_results

    except Exception:

        return []

    finally:

        try:

            if os.path.exists(
                temp_path
            ):

                os.remove(
                    temp_path
                )

        except Exception:

            pass


# ============================================================
# MERGE OCR
# ============================================================

def merge_text(
    paddle_items,
    tesseract_text
):

    lines = []

    # Paddle.

    for item in paddle_items:

        text = item.get(
            "text",
            ""
        ).strip()

        if text:

            lines.append(
                text
            )

    # Tesseract.

    if tesseract_text:

        for line in tesseract_text.splitlines():

            line = line.strip()

            if line:

                lines.append(
                    line
                )

    # Remove duplicates.

    unique = []

    seen = set()

    for line in lines:

        key = re.sub(
            r"\s+",
            " ",
            line.lower()
        ).strip()

        if not key:

            continue

        if key in seen:

            continue

        seen.add(
            key
        )

        unique.append(
            line
        )

    return "\n".join(
        unique
    )


# ============================================================
# IMPORTANT LABELS
# ============================================================

IMPORTANT_LABELS = [

    "model",

    "model number",

    "model no",

    "serial",

    "serial number",

    "serial no",

    "product code",

    "product id",

    "order",

    "order id",

    "order number",

    "purchase",

    "purchased",

    "bought",

    "date",

    "warranty",

    "seller",

    "sold by",

    "purchased from",

    "merchant",

    "dealer",

    "brand",

    "company",

    "price",

    "amount",

    "total"
]


# ============================================================
# RELEVANT LINES
# ============================================================

def find_relevant_lines(
    text
):

    relevant = []

    lines = text.splitlines()

    for i, line in enumerate(
        lines
    ):

        lower = line.lower()

        matched = False

        for label in IMPORTANT_LABELS:

            if label in lower:

                matched = True

                break

        if not matched:

            continue

        start = max(
            0,
            i - 1
        )

        end = min(
            len(lines),
            i + 3
        )

        for j in range(
            start,
            end
        ):

            candidate = lines[j].strip()

            if candidate:

                relevant.append(
                    candidate
                )

    result = []

    seen = set()

    for line in relevant:

        key = line.lower().strip()

        if key not in seen:

            seen.add(
                key
            )

            result.append(
                line
            )

    return result


# ============================================================
# MAIN OCR
# ============================================================

def process_image(
    image_path
):

    print()
    print(
        "=" * 60
    )

    print(
        "STARTING DOCUMENT OCR"
    )

    print(
        "=" * 60
    )

    print(
        "Image:",
        image_path
    )

    if not os.path.exists(
        image_path
    ):

        raise FileNotFoundError(
            image_path
        )

    original = load_image(
        image_path
    )

    print(
        "Original size:",
        original.size
    )

    variants = create_variants(
        original
    )

    all_paddle = []

    best_tesseract = ""

    # --------------------------------------------------------
    # OCR VARIANTS
    # --------------------------------------------------------

    for name, variant in variants:

        print()
        print(
            "Running OCR variant:",
            name
        )

        # Paddle.

        paddle_results = run_paddle(
            variant
        )

        all_paddle.extend(
            paddle_results
        )

        # Tesseract.

        tess = run_tesseract(
            variant
        )

        if len(tess) > len(
            best_tesseract
        ):

            best_tesseract = tess

    # --------------------------------------------------------
    # CLEAN PADDLE
    # --------------------------------------------------------

    cleaned_paddle = []

    for item in all_paddle:

        text = item.get(
            "text",
            ""
        ).strip()

        confidence = item.get(
            "confidence",
            0
        )

        if not text:

            continue

        if confidence >= 0.30:

            cleaned_paddle.append(
                item
            )

    # --------------------------------------------------------
    # MERGE
    # --------------------------------------------------------

    combined_text = merge_text(
        cleaned_paddle,
        best_tesseract
    )

    relevant_lines = find_relevant_lines(
        combined_text
    )

    # --------------------------------------------------------
    # TESSERACT BOXES
    # --------------------------------------------------------

    position_data = run_tesseract_boxes(
        original
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    evidence = {

        "image": os.path.abspath(
            image_path
        ),

        "image_size": {

            "width": original.size[0],

            "height": original.size[1]
        },

        "paddleocr": cleaned_paddle,

        "tesseract_text": best_tesseract,

        "tesseract_boxes": position_data,

        "combined_text": combined_text,

        "relevant_lines": relevant_lines
    }

    output_file = os.path.join(
        OUTPUT_DIR,
        "ocr_evidence.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            evidence,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print(
        "=" * 60
    )

    print(
        "OCR COMPLETED"
    )

    print(
        "Evidence:",
        output_file
    )

    print(
        "=" * 60
    )

    print()
    print(
        "COMBINED OCR TEXT"
    )

    print(
        "-" * 60
    )

    if combined_text:

        print(
            combined_text
        )

    else:

        print(
            "[No OCR text available]"
        )

    print(
        "-" * 60
    )

    return evidence


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    image = input(
        "Enter image path: "
    ).strip()

    if image:

        process_image(
            image
        )

    else:

        print(
            "No image supplied."
        )