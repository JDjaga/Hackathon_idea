import json
from pathlib import Path
from datetime import datetime


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PASSPORT_FILE = BASE_DIR / "product_passports.json"


# ============================================================
# STORE
# ============================================================

class PassportStore:

    def __init__(
        self,
        filename=PASSPORT_FILE
    ):

        self.filename = Path(
            filename
        )

        self.passports = []

        self.load()

    # ========================================================
    # LOAD
    # ========================================================

    def load(self):

        if not self.filename.exists():

            self.passports = []

            return

        try:

            with open(
                self.filename,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            # ----------------------------------------------
            # OLD SINGLE PASSPORT FORMAT
            # ----------------------------------------------

            if isinstance(data, dict):

                self.passports = [
                    data
                ]

            # ----------------------------------------------
            # NEW MULTIPLE PASSPORT FORMAT
            # ----------------------------------------------

            elif isinstance(data, list):

                self.passports = data

            else:

                self.passports = []

        except Exception as e:

            print(
                "Passport database error:",
                e
            )

            self.passports = []

    # ========================================================
    # SAVE
    # ========================================================

    def save(self):

        with open(
            self.filename,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                self.passports,
                f,
                indent=4,
                ensure_ascii=False
            )

    # ========================================================
    # ADD PASSPORT
    # ========================================================

    def add_passport(
        self,
        passport
    ):

        passport = dict(
            passport
        )

        if "passport_id" not in passport:

            passport["passport_id"] = (
                f"PP-"
                f"{datetime.now().strftime('%Y%m%d%H%M%S')}-"
                f"{len(self.passports) + 1}"
            )

        # Product image information

        if "product_images" not in passport:

            passport["product_images"] = []

        if "linked_products" not in passport:

            passport["linked_products"] = []

        if "created_at" not in passport:

            passport["created_at"] = (
                datetime.now().isoformat()
            )

        self.passports.append(
            passport
        )

        self.save()

        return passport

    # ========================================================
    # GET ALL
    # ========================================================

    def get_all(self):

        return self.passports

    # ========================================================
    # FIND BY ID
    # ========================================================

    def get_by_id(
        self,
        passport_id
    ):

        for passport in self.passports:

            if (
                passport.get("passport_id")
                == passport_id
            ):

                return passport

        return None

    # ========================================================
    # UPDATE
    # ========================================================

    def update(
        self,
        passport_id,
        updates
    ):

        passport = self.get_by_id(
            passport_id
        )

        if passport is None:

            return None

        passport.update(
            updates
        )

        self.save()

        return passport

    # ========================================================
    # ADD PRODUCT IMAGE
    # ========================================================

    def attach_product_image(
        self,
        passport_id,
        image_path,
        detection_info=None
    ):

        passport = self.get_by_id(
            passport_id
        )

        if passport is None:

            return None

        if "product_images" not in passport:

            passport["product_images"] = []

        image_record = {

            "image_path":
                str(image_path),

            "attached_at":
                datetime.now().isoformat(),

            "detection":
                detection_info or {}
        }

        passport[
            "product_images"
        ].append(
            image_record
        )

        self.save()

        return passport

    # ========================================================
    # LINK DETECTION
    # ========================================================

    def link_detection(
        self,
        passport_id,
        detection_info
    ):

        passport = self.get_by_id(
            passport_id
        )

        if passport is None:

            return None

        if "linked_products" not in passport:

            passport[
                "linked_products"
            ] = []

        passport[
            "linked_products"
        ].append(
            detection_info
        )

        self.save()

        return passport


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    store = PassportStore()

    print(
        f"Passports loaded: "
        f"{len(store.get_all())}"
    )

    for passport in store.get_all():

        print(
            passport.get(
                "passport_id",
                "NO-ID"
            ),
            "|",
            passport.get(
                "product",
                "Unknown"
            ),
            "|",
            passport.get(
                "brand",
                "Unknown"
            )
        )