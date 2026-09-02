import os
import json
import base64
import requests
from pathlib import Path

import cv2
from ultralytics import YOLO


# ============================================================
# CONFIGURATION
# ============================================================

YOLO_MODEL = "yolo26n.pt"

# Your Ollama model
OLLAMA_MODEL = "qwen2.5vl:7b"

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

# YOLO confidence
YOLO_CONFIDENCE = 0.10

# NMS IoU
YOLO_IOU = 0.45

# Higher resolution helps large objects and small labels
YOLO_IMAGE_SIZE = 1280

# Minimum acceptable confidence for a YOLO product detection
MIN_PRODUCT_CONFIDENCE = 0.20


# ============================================================
# COCO / GENERAL OBJECT CLASSES
# ============================================================
#
# These are classes that are useful for our project.
#
# IMPORTANT:
# YOLO pretrained models do NOT know every household appliance.
# For example, washing machine is generally NOT a standard COCO
# detection class.
#
# Therefore Qwen2.5-VL is used as a semantic fallback.
# ============================================================

USEFUL_COCO_CLASSES = {
    "refrigerator",
    "microwave",
    "oven",
    "toaster",
    "tv",
    "laptop",
    "computer",
    "cell phone",
    "remote",
    "keyboard",
    "mouse",
    "monitor",
    "hair drier",
    "vacuum",
    "clock",
    "camera",
    "bottle",
    "chair",
    "couch",
    "bed",
    "sink",
    "toilet",
}


# Objects that should NEVER become a product passport
REJECT_CLASSES = {
    "person",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "sports ball",
    "skateboard",
    "surfboard",
    "tennis racket",
    "baseball bat",
    "baseball glove",
    "skis",
    "snowboard",
    "bicycle",
    "motorcycle",
    "car",
    "truck",
    "bus",
    "train",
    "boat",
}


# ============================================================
# PRODUCT KEYWORDS
# ============================================================

PRODUCT_KEYWORDS = [
    "refrigerator",
    "fridge",
    "washing machine",
    "washer",
    "dryer",
    "cloth dryer",
    "dishwasher",
    "air conditioner",
    "air conditioner unit",
    "ac",
    "television",
    "tv",
    "microwave",
    "oven",
    "stove",
    "cooker",
    "rice cooker",
    "vacuum cleaner",
    "vacuum",
    "fan",
    "ceiling fan",
    "table fan",
    "water heater",
    "geyser",
    "iron",
    "electric iron",
    "air purifier",
    "water purifier",
    "printer",
    "monitor",
    "computer",
    "laptop",
    "desktop",
    "speaker",
    "television",
    "camera",
    "coffee machine",
    "toaster",
    "blender",
    "mixer",
    "mixer grinder",
    "food processor",
    "electric kettle",
    "kettle",
]


# ============================================================
# GLOBAL MODEL
# ============================================================

print()
print("=" * 60)
print("INITIALIZING PRODUCT DETECTOR")
print("=" * 60)

try:

    yolo_model = YOLO(YOLO_MODEL)

    print("YOLO model loaded successfully:")
    print(f"  {YOLO_MODEL}")

except Exception as e:

    print()
    print("ERROR: Could not load YOLO model.")
    print(str(e))

    yolo_model = None


# ============================================================
# PATH CLEANING
# ============================================================

def clean_path(path):

    if path is None:
        return ""

    path = path.strip()

    # User may enter:
    # "C:\Users\...\img.jpg"
    # Remove surrounding quotes.
    if len(path) >= 2:

        if (
            (path[0] == '"' and path[-1] == '"')
            or
            (path[0] == "'" and path[-1] == "'")
        ):

            path = path[1:-1]

    return os.path.abspath(path)


# ============================================================
# IMAGE VALIDATION
# ============================================================

def validate_image(image_path):

    image_path = clean_path(image_path)

    print()
    print("Checking image:")
    print(f"  {image_path}")

    if not os.path.exists(image_path):

        print()
        print("ERROR: Image does not exist:")
        print(image_path)

        return None

    image = cv2.imread(image_path)

    if image is None:

        print()
        print("ERROR: OpenCV could not read the image.")

        return None

    height, width = image.shape[:2]

    print("Image found successfully.")
    print(f"  Width  : {width}")
    print(f"  Height : {height}")
    print(f"  Format : {Path(image_path).suffix}")

    return image


# ============================================================
# YOLO DETECTION
# ============================================================

def run_yolo_detection(image_path):

    if yolo_model is None:

        return []

    print()
    print("=" * 60)
    print("RUNNING YOLO PRODUCT DETECTION")
    print("=" * 60)

    print(f"Image: {image_path}")
    print(f"Confidence threshold: {YOLO_CONFIDENCE}")
    print(f"Image size: {YOLO_IMAGE_SIZE}")

    detections = []

    try:

        results = yolo_model.predict(
            source=image_path,
            conf=YOLO_CONFIDENCE,
            iou=YOLO_IOU,
            imgsz=YOLO_IMAGE_SIZE,
            verbose=False,
            augment=True,
        )

    except Exception as e:

        print()
        print("YOLO inference error:")
        print(str(e))

        return []


    for result in results:

        if result.boxes is None:
            continue

        boxes = result.boxes

        for i in range(len(boxes)):

            cls_id = int(boxes.cls[i].item())

            confidence = float(boxes.conf[i].item())

            xyxy = boxes.xyxy[i].cpu().numpy().astype(int)

            x1, y1, x2, y2 = xyxy.tolist()

            class_name = yolo_model.names.get(
                cls_id,
                str(cls_id)
            )

            class_name = class_name.lower().strip()


            print()
            print("YOLO raw detection:")
            print(f"  Class      : {class_name}")
            print(f"  Confidence : {confidence * 100:.2f}%")
            print(
                f"  Box        : "
                f"({x1}, {y1}) → ({x2}, {y2})"
            )


            # ------------------------------------------------
            # REJECT OBVIOUSLY IRRELEVANT OBJECTS
            # ------------------------------------------------

            if class_name in REJECT_CLASSES:

                print("  Decision   : REJECTED")
                print("  Reason     : irrelevant object")

                continue


            # ------------------------------------------------
            # ACCEPT KNOWN USEFUL CLASSES
            # ------------------------------------------------

            if class_name in USEFUL_COCO_CLASSES:

                if confidence >= MIN_PRODUCT_CONFIDENCE:

                    print("  Decision   : ACCEPTED")
                    print("  Reason     : known useful product class")

                    detections.append(
                        {
                            "product": class_name,
                            "confidence": confidence,
                            "bbox": [
                                x1,
                                y1,
                                x2,
                                y2
                            ],
                            "source": "YOLO"
                        }
                    )

                    continue


            print("  Decision   : NOT USED")


    return detections


# ============================================================
# REMOVE DUPLICATE DETECTIONS
# ============================================================

def remove_duplicate_detections(detections):

    if not detections:
        return []

    final = []

    for detection in detections:

        duplicate = False

        for existing in final:

            same_product = (
                detection["product"]
                ==
                existing["product"]
            )

            if not same_product:
                continue

            x1, y1, x2, y2 = detection["bbox"]

            ex1, ey1, ex2, ey2 = existing["bbox"]

            # Calculate center distance
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2

            ecx = (ex1 + ex2) / 2
            ecy = (ey1 + ey2) / 2

            distance = (
                (cx - ecx) ** 2
                +
                (cy - ecy) ** 2
            ) ** 0.5

            box_width = max(
                x2 - x1,
                ex2 - ex1
            )

            if distance < box_width * 0.25:

                duplicate = True

                # Keep higher confidence
                if (
                    detection["confidence"]
                    >
                    existing["confidence"]
                ):

                    existing.update(detection)

                break


        if not duplicate:

            final.append(detection)


    return final


# ============================================================
# IMAGE → BASE64
# ============================================================

def image_to_base64(image_path):

    try:

        with open(
            image_path,
            "rb"
        ) as f:

            return base64.b64encode(
                f.read()
            ).decode("utf-8")

    except Exception as e:

        print()
        print("Could not encode image:")
        print(str(e))

        return None


# ============================================================
# QWEN VISION FALLBACK
# ============================================================

def qwen_product_detection(image_path):

    print()
    print("=" * 60)
    print("RUNNING QWEN2.5-VL PRODUCT VERIFICATION")
    print("=" * 60)

    print(f"Vision model: {OLLAMA_MODEL}")


    image_base64 = image_to_base64(
        image_path
    )

    if image_base64 is None:

        return []


    prompt = """
You are a product identification vision system.

Analyze the uploaded image carefully.

Your job is to identify REAL HOME APPLIANCES or CONSUMER PRODUCTS
visible in the image.

IMPORTANT RULES:

1. Ignore people.
2. Ignore human body parts.
3. Ignore furniture.
4. Ignore walls and floors.
5. Ignore background objects.
6. Do NOT create a product merely because there is text.
7. Identify only physical products/appliances that are actually visible.
8. If there are multiple products, identify each separately.
9. If an appliance is clearly a refrigerator, return refrigerator.
10. If an appliance is clearly a washing machine, return washing machine.
11. If an appliance is clearly a television, return television.
12. Use common product categories.

Return ONLY valid JSON.

Format:

{
  "products": [
    {
      "product": "refrigerator",
      "brand": "Samsung",
      "confidence": 0.95,
      "description": "Large red refrigerator"
    }
  ]
}

If no actual product can be identified:

{
  "products": []
}

Do not include explanations outside the JSON.
"""


    payload = {

        "model": OLLAMA_MODEL,

        "prompt": prompt,

        "images": [
            image_base64
        ],

        "stream": False,

        "options": {

            "temperature": 0.0

        }
    }


    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=180
        )

        response.raise_for_status()

        data = response.json()

        text = data.get(
            "response",
            ""
        ).strip()


        print()
        print("Qwen raw response:")
        print(text)


        # ----------------------------------------------------
        # Extract JSON
        # ----------------------------------------------------

        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:

            print()
            print("Qwen did not return valid JSON.")

            return []


        json_text = text[
            start:end + 1
        ]


        parsed = json.loads(
            json_text
        )


        products = parsed.get(
            "products",
            []
        )


        final = []


        for product in products:

            product_name = str(
                product.get(
                    "product",
                    ""
                )
            ).strip()


            if not product_name:

                continue


            confidence = float(
                product.get(
                    "confidence",
                    0.0
                )
            )


            # Ignore very uncertain results
            if confidence < 0.45:

                continue


            final.append(
                {
                    "product": product_name,
                    "brand": product.get(
                        "brand"
                    ),
                    "confidence": confidence,
                    "description": product.get(
                        "description"
                    ),
                    "bbox": None,
                    "source": "Qwen2.5-VL"
                }
            )


        return final


    except requests.exceptions.ConnectionError:

        print()
        print("Could not connect to Ollama.")
        print()
        print("Make sure Ollama is running:")
        print()
        print("  ollama serve")
        print()

        return []


    except Exception as e:

        print()
        print("Qwen vision error:")
        print(str(e))

        return []


# ============================================================
# SAVE ANNOTATED IMAGE
# ============================================================

def save_annotated_image(
    image_path,
    detections
):

    image = cv2.imread(
        image_path
    )

    if image is None:

        return None


    for index, detection in enumerate(
        detections,
        start=1
    ):

        bbox = detection.get(
            "bbox"
        )

        if bbox is None:

            continue


        x1, y1, x2, y2 = bbox

        label = (
            f"{detection['product']} "
            f"{detection['confidence'] * 100:.1f}%"
        )


        cv2.rectangle(
            image,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            3
        )


        cv2.putText(
            image,
            label,
            (x1, max(30, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA
        )


    output_path = str(
        Path(image_path).with_name(
            Path(image_path).stem
            + "_detected.jpg"
        )
    )


    cv2.imwrite(
        output_path,
        image
    )


    return output_path


# ============================================================
# FINAL PRODUCT DETECTION
# ============================================================

def detect_products(image_path):

    image_path = clean_path(
        image_path
    )

    image = validate_image(
        image_path
    )

    if image is None:

        return []


    # --------------------------------------------------------
    # STEP 1
    # YOLO
    # --------------------------------------------------------

    yolo_detections = run_yolo_detection(
        image_path
    )


    yolo_detections = remove_duplicate_detections(
        yolo_detections
    )


    # --------------------------------------------------------
    # If YOLO already found products,
    # don't immediately replace them with Qwen.
    # --------------------------------------------------------

    if yolo_detections:

        print()
        print(
            "YOLO found valid product object(s)."
        )

        final_detections = yolo_detections


    else:

        # ----------------------------------------------------
        # STEP 2
        # QWEN VISION FALLBACK
        # ----------------------------------------------------

        print()
        print(
            "YOLO did not find a valid appliance."
        )

        print(
            "Using Qwen2.5-VL as semantic fallback..."
        )


        qwen_detections = qwen_product_detection(
            image_path
        )


        final_detections = qwen_detections


    # --------------------------------------------------------
    # ANNOTATION
    # --------------------------------------------------------

    annotated_path = save_annotated_image(
        image_path,
        final_detections
    )


    # --------------------------------------------------------
    # FINAL OUTPUT
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("FINAL DETECTIONS")
    print("=" * 60)


    if not final_detections:

        print()
        print(
            "No valid products detected."
        )

        return []


    print()
    print(
        f"Detected {len(final_detections)} product(s):"
    )


    for index, detection in enumerate(
        final_detections,
        start=1
    ):

        print()
        print(
            f"Product #{index}"
        )

        print(
            f"  Type       : "
            f"{detection.get('product')}"
        )

        print(
            f"  Confidence : "
            f"{detection.get('confidence', 0) * 100:.2f}%"
        )

        print(
            f"  Source     : "
            f"{detection.get('source')}"
        )


        if detection.get("brand"):

            print(
                f"  Brand      : "
                f"{detection.get('brand')}"
            )


        if detection.get("bbox"):

            x1, y1, x2, y2 = detection[
                "bbox"
            ]

            print(
                f"  Bounding Box: "
                f"({x1}, {y1}) → "
                f"({x2}, {y2})"
            )


        if detection.get("description"):

            print(
                f"  Description: "
                f"{detection.get('description')}"
            )


    if annotated_path:

        print()
        print(
            "Annotated detection image saved:"
        )

        print(
            f"  {annotated_path}"
        )


    print()
    print("=" * 60)
    print("DETECTION COMPLETE")
    print("=" * 60)


    return final_detections


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("HOME APPLIANCE / PRODUCT DETECTOR")
    print("=" * 60)

    print()
    print("Supported pipeline:")
    print("  YOLO26 → appliance filtering → Qwen2.5-VL fallback")

    print()
    print("Enter product image path:")

    image_path = input(
        "> "
    ).strip()


    detect_products(
        image_path
    )