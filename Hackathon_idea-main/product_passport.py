import tkinter as tk
from tkinter import messagebox
import json
import sys
import os


# ============================================================
# COLORS
# ============================================================

BG_COLOR = "#081321"
NAVY = "#182943"
CREAM = "#F7F3E8"
GOLD = "#C8A85A"
GOLD_LIGHT = "#E0C579"
TEXT_DARK = "#14243A"
TEXT_MUTED = "#64738A"
PHOTO_BG = "#E9E3D5"
BORDER = "#C9C1AE"
WHITE = "#FFFFFF"


# ============================================================
# FONT HELPERS
# ============================================================

FONT_TITLE = ("Segoe UI", 30, "bold")
FONT_SUBTITLE = ("Segoe UI", 13)

FONT_PASSPORT_TITLE = ("Georgia", 25, "bold")
FONT_IDENTITY = ("Segoe UI", 25, "bold")
FONT_SECTION = ("Segoe UI", 15, "bold")

FONT_LABEL = ("Segoe UI", 10, "bold")
FONT_VALUE = ("Segoe UI", 14, "bold")

FONT_SMALL = ("Segoe UI", 10)
FONT_SMALL_BOLD = ("Segoe UI", 10, "bold")


# ============================================================
# LOAD JSON
# ============================================================

def load_passport():

    # --------------------------------------------------------
    # textemege.py should pass the exact JSON path
    # --------------------------------------------------------

    if len(sys.argv) > 1:

        json_file = sys.argv[1]

    else:

        # fallback
        json_file = os.path.join(
            os.path.dirname(
                os.path.abspath(__file__)
            ),
            "product_passport.json"
        )

    json_file = os.path.abspath(json_file)

    print()
    print("=" * 70)
    print("PRODUCT PASSPORT UI")
    print("=" * 70)
    print("Loading:", json_file)

    if not os.path.exists(json_file):

        messagebox.showerror(
            "Product Passport",
            f"Passport JSON not found:\n\n{json_file}"
        )

        return None

    try:

        with open(
            json_file,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        print("Passport JSON loaded successfully.")

        return data

    except json.JSONDecodeError as e:

        messagebox.showerror(
            "Product Passport",
            f"Invalid JSON file:\n\n{e}"
        )

        return None

    except Exception as e:

        messagebox.showerror(
            "Product Passport",
            f"Could not load passport:\n\n{e}"
        )

        return None


# ============================================================
# NORMALIZE PASSPORT DATA
# ============================================================

def normalize_passports(data):

    if data is None:
        return []

    # --------------------------------------------------------
    # Case 1:
    # {"passports": [...]}
    # --------------------------------------------------------

    if isinstance(data, dict):

        passports = data.get("passports")

        if isinstance(passports, list):

            return passports

        # ----------------------------------------------------
        # Case 2:
        # Single passport dictionary
        # ----------------------------------------------------

        if any(
            key in data
            for key in [
                "product",
                "brand",
                "model",
                "serial_number",
                "category"
            ]
        ):

            return [data]

    # --------------------------------------------------------
    # Case 3:
    # Direct list
    # --------------------------------------------------------

    if isinstance(data, list):

        return data

    return []


# ============================================================
# SAFE VALUE
# ============================================================

def safe_value(value):

    if value is None:
        return "NOT AVAILABLE"

    if isinstance(value, str):

        value = value.strip()

        if not value:
            return "NOT AVAILABLE"

        return value

    return str(value)


# ============================================================
# GET FIELD
# ============================================================

def get_field(data, *keys):

    for key in keys:

        if key in data:

            value = data.get(key)

            if value is not None:

                if isinstance(value, str):

                    if value.strip():

                        return value.strip()

                else:

                    return value

    return None


# ============================================================
# PURCHASE PRICE
# ============================================================

def get_price(data):

    price = get_field(
        data,
        "purchase_price",
        "price",
        "amount"
    )

    currency = get_field(
        data,
        "currency",
        "price_currency"
    )

    if price is None:

        return "NOT AVAILABLE"

    price = str(price).strip()

    if currency:

        currency = str(currency).strip()

        # Avoid duplicate currency
        if price.upper().startswith(
            currency.upper()
        ):

            return price

        return f"{currency} {price}"

    return price


# ============================================================
# ROUNDED FRAME
# ============================================================

class RoundedFrame(tk.Canvas):

    def __init__(
        self,
        master,
        radius=20,
        bg_color=CREAM,
        border_color=GOLD,
        border_width=2,
        **kwargs
    ):

        super().__init__(
            master,
            highlightthickness=0,
            bg=master.cget("bg"),
            **kwargs
        )

        self.radius = radius
        self.bg_color = bg_color
        self.border_color = border_color
        self.border_width = border_width

        self.bind(
            "<Configure>",
            self._draw
        )

    def _draw(self, event=None):

        self.delete("all")

        w = max(
            self.winfo_width(),
            10
        )

        h = max(
            self.winfo_height(),
            10
        )

        r = min(
            self.radius,
            w // 2,
            h // 2
        )

        # Border
        self.create_round_rect(
            1,
            1,
            w - 1,
            h - 1,
            r,
            fill=self.bg_color,
            outline=self.border_color,
            width=self.border_width
        )

    def create_round_rect(
        self,
        x1,
        y1,
        x2,
        y2,
        radius,
        **kwargs
    ):

        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]

        return self.create_polygon(
            points,
            smooth=True,
            **kwargs
        )


# ============================================================
# SCROLLABLE FRAME
# ============================================================

class ScrollableFrame(tk.Frame):

    def __init__(self, master, **kwargs):

        super().__init__(
            master,
            bg=BG_COLOR,
            **kwargs
        )

        self.canvas = tk.Canvas(
            self,
            bg=BG_COLOR,
            highlightthickness=0
        )

        self.scrollbar = tk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview
        )

        self.scrollable_frame = tk.Frame(
            self.canvas,
            bg=BG_COLOR
        )

        self.window_id = self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw"
        )

        self.canvas.configure(
            yscrollcommand=self.scrollbar.set
        )

        self.canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.scrollbar.pack(
            side="right",
            fill="y"
        )

        self.scrollable_frame.bind(
            "<Configure>",
            self._update_scroll_region
        )

        self.canvas.bind(
            "<Configure>",
            self._resize_inner_frame
        )

        # Mouse wheel
        self.canvas.bind_all(
            "<MouseWheel>",
            self._on_mousewheel
        )

        # Linux scrolling
        self.canvas.bind_all(
            "<Button-4>",
            self._on_linux_scroll
        )

        self.canvas.bind_all(
            "<Button-5>",
            self._on_linux_scroll
        )

    def _update_scroll_region(self, event=None):

        self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        )

    def _resize_inner_frame(self, event):

        self.canvas.itemconfig(
            self.window_id,
            width=event.width
        )

    def _on_mousewheel(self, event):

        try:

            self.canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )

        except Exception:
            pass

    def _on_linux_scroll(self, event):

        if event.num == 4:

            self.canvas.yview_scroll(
                -3,
                "units"
            )

        elif event.num == 5:

            self.canvas.yview_scroll(
                3,
                "units"
            )


# ============================================================
# APP
# ============================================================

class ProductPassportApp:

    def __init__(self, root, data):

        self.root = root

        self.data = data

        self.passports = normalize_passports(
            data
        )

        # ----------------------------------------------------
        # Window
        # ----------------------------------------------------

        self.root.title(
            "Digital Product Passport"
        )

        self.root.geometry(
            "1400x900"
        )

        self.root.minsize(
            900,
            650
        )

        self.root.configure(
            bg=BG_COLOR
        )

        # Allow resizing
        self.root.resizable(
            True,
            True
        )

        # ----------------------------------------------------
        # Keyboard scrolling
        # ----------------------------------------------------

        self.root.bind(
            "<Down>",
            self.scroll_down
        )

        self.root.bind(
            "<Up>",
            self.scroll_up
        )

        self.root.bind(
            "<Next>",
            self.scroll_page_down
        )

        self.root.bind(
            "<Prior>",
            self.scroll_page_up
        )

        self.root.bind(
            "<Home>",
            self.scroll_home
        )

        self.root.bind(
            "<End>",
            self.scroll_end
        )

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        self.create_main_header()

        # ----------------------------------------------------
        # Scroll area
        # ----------------------------------------------------

        self.scroll_frame = ScrollableFrame(
            self.root
        )

        self.scroll_frame.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=(0, 15)
        )

        # ----------------------------------------------------
        # Passport container
        # ----------------------------------------------------

        self.content = (
            self.scroll_frame.scrollable_frame
        )

        if not self.passports:

            self.show_empty()

        else:

            for index, passport in enumerate(
                self.passports
            ):

                self.create_passport(
                    passport,
                    index + 1
                )

        # ----------------------------------------------------
        # Bottom controls
        # ----------------------------------------------------

        self.create_bottom_bar()

    # ========================================================
    # HEADER
    # ========================================================

    def create_main_header(self):

        header = tk.Frame(
            self.root,
            bg=BG_COLOR
        )

        header.pack(
            fill="x",
            pady=(22, 8)
        )

        title = tk.Label(
            header,
            text="DIGITAL PRODUCT PASSPORT",
            font=FONT_TITLE,
            fg=WHITE,
            bg=BG_COLOR
        )

        title.pack()

        subtitle = tk.Label(
            header,
            text="AI-generated product identity record",
            font=FONT_SUBTITLE,
            fg="#91A0B7",
            bg=BG_COLOR
        )

        subtitle.pack(
            pady=(4, 0)
        )

    # ========================================================
    # EMPTY
    # ========================================================

    def show_empty(self):

        frame = tk.Frame(
            self.content,
            bg=CREAM
        )

        frame.pack(
            fill="x",
            padx=20,
            pady=20
        )

        tk.Label(
            frame,
            text="NO PRODUCT PASSPORT DATA",
            font=("Segoe UI", 18, "bold"),
            fg=TEXT_DARK,
            bg=CREAM
        ).pack(
            pady=50
        )

    # ========================================================
    # CREATE PASSPORT
    # ========================================================

    def create_passport(
        self,
        data,
        passport_number
    ):

        # Outer passport
        outer = tk.Frame(
            self.content,
            bg=GOLD,
            padx=2,
            pady=2
        )

        outer.pack(
            fill="x",
            padx=15,
            pady=15
        )

        passport = tk.Frame(
            outer,
            bg=CREAM
        )

        passport.pack(
            fill="both",
            expand=True
        )

        # ----------------------------------------------------
        # NAVY TOP
        # ----------------------------------------------------

        self.create_passport_header(
            passport,
            passport_number
        )

        # ----------------------------------------------------
        # BODY
        # ----------------------------------------------------

        body = tk.Frame(
            passport,
            bg=CREAM
        )

        body.pack(
            fill="x",
            padx=35,
            pady=(25, 30)
        )

        # ----------------------------------------------------
        # 01 PRODUCT IDENTITY
        # ----------------------------------------------------

        self.create_section_title(
            body,
            "01  PRODUCT IDENTITY"
        )

        # Gold line
        self.create_gold_line(
            body
        )

        # Identity area
        identity = tk.Frame(
            body,
            bg=CREAM
        )

        identity.pack(
            fill="x",
            pady=(28, 30)
        )

        # Configure responsive columns
        identity.columnconfigure(
            0,
            weight=1,
            minsize=260
        )

        identity.columnconfigure(
            1,
            weight=2,
            minsize=400
        )

        # ----------------------------------------------------
        # PHOTO PLACEHOLDER
        # ----------------------------------------------------

        photo_frame = tk.Frame(
            identity,
            bg=PHOTO_BG,
            highlightbackground=BORDER,
            highlightthickness=2
        )

        photo_frame.grid(
            row=0,
            column=0,
            rowspan=3,
            sticky="nsew",
            padx=(0, 40),
            pady=0
        )

        photo_frame.configure(
            width=330,
            height=300
        )

        photo_frame.grid_propagate(
            False
        )

        tk.Label(
            photo_frame,
            text="PRODUCT PHOTO",
            font=("Segoe UI", 13, "bold"),
            fg="#657187",
            bg=PHOTO_BG
        ).place(
            relx=0.5,
            rely=0.48,
            anchor="center"
        )

        tk.Label(
            photo_frame,
            text="PHOTO AREA",
            font=("Segoe UI", 9),
            fg="#A8AFC0",
            bg=PHOTO_BG
        ).place(
            relx=0.5,
            rely=0.58,
            anchor="center"
        )

        # ----------------------------------------------------
        # PRODUCT VALUES
        # ----------------------------------------------------

        details = tk.Frame(
            identity,
            bg=CREAM
        )

        details.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        details.columnconfigure(
            0,
            weight=1
        )

        details.columnconfigure(
            1,
            weight=1
        )

        product = safe_value(
            get_field(
                data,
                "product",
                "product_name"
            )
        )

        brand = safe_value(
            get_field(
                data,
                "brand",
                "manufacturer"
            )
        )

        model = safe_value(
            get_field(
                data,
                "model",
                "model_number"
            )
        )

        serial = safe_value(
            get_field(
                data,
                "serial_number",
                "serial",
                "serial_no"
            )
        )

        category = safe_value(
            get_field(
                data,
                "category",
                "product_category"
            )
        )

        document_type = safe_value(
            get_field(
                data,
                "document_type",
                "document"
            )
        )

        self.create_value_block(
            details,
            0,
            0,
            "PRODUCT",
            product
        )

        self.create_value_block(
            details,
            0,
            1,
            "BRAND",
            brand
        )

        self.create_value_block(
            details,
            1,
            0,
            "MODEL",
            model
        )

        self.create_value_block(
            details,
            1,
            1,
            "SERIAL NUMBER",
            serial
        )

        self.create_value_block(
            details,
            2,
            0,
            "CATEGORY",
            category
        )

        self.create_value_block(
            details,
            2,
            1,
            "DOCUMENT TYPE",
            document_type
        )

        # ----------------------------------------------------
        # 02 PURCHASE & WARRANTY
        # ----------------------------------------------------

        self.create_section_title(
            body,
            "02  PURCHASE & WARRANTY"
        )

        self.create_gold_line(
            body
        )

        purchase = tk.Frame(
            body,
            bg=CREAM
        )

        purchase.pack(
            fill="x",
            pady=(27, 25)
        )

        purchase.columnconfigure(
            0,
            weight=1
        )

        purchase.columnconfigure(
            1,
            weight=1
        )

        purchase.columnconfigure(
            2,
            weight=1
        )

        purchase_date = safe_value(
            get_field(
                data,
                "purchase_date",
                "date_of_purchase",
                "date"
            )
        )

        purchase_price = get_price(
            data
        )

        warranty = safe_value(
            get_field(
                data,
                "warranty",
                "warranty_period"
            )
        )

        seller = safe_value(
            get_field(
                data,
                "seller",
                "dealer",
                "seller_dealer"
            )
        )

        self.create_value_block(
            purchase,
            0,
            0,
            "PURCHASE DATE",
            purchase_date
        )

        self.create_value_block(
            purchase,
            0,
            1,
            "PURCHASE PRICE",
            purchase_price
        )

        self.create_value_block(
            purchase,
            0,
            2,
            "WARRANTY",
            warranty
        )

        self.create_value_block(
            purchase,
            1,
            0,
            "SELLER / DEALER",
            seller,
            colspan=3
        )

        # ----------------------------------------------------
        # 03 SOURCE DOCUMENT
        # ----------------------------------------------------

        self.create_section_title(
            body,
            "03  SOURCE DOCUMENT"
        )

        self.create_gold_line(
            body
        )

        source = tk.Frame(
            body,
            bg=CREAM
        )

        source.pack(
            fill="x",
            pady=(22, 5)
        )

        source.columnconfigure(
            0,
            weight=1
        )

        source.columnconfigure(
            1,
            weight=1
        )

        source_file = safe_value(
            get_field(
                data,
                "source_document",
                "source",
                "source_file",
                "filename"
            )
        )

        selection = safe_value(
            get_field(
                data,
                "selection",
                "selection_status"
            )
        )

        evidence = safe_value(
            get_field(
                data,
                "evidence",
                "selection_evidence"
            )
        )

        self.create_value_block(
            source,
            0,
            0,
            "SOURCE DOCUMENT",
            source_file
        )

        self.create_value_block(
            source,
            0,
            1,
            "SELECTION",
            selection
        )

        self.create_value_block(
            source,
            1,
            0,
            "EVIDENCE",
            evidence,
            colspan=2
        )

        # ----------------------------------------------------
        # Passport number
        # ----------------------------------------------------

        footer = tk.Frame(
            passport,
            bg=NAVY,
            height=42
        )

        footer.pack(
            fill="x"
        )

        footer.pack_propagate(
            False
        )

        tk.Label(
            footer,
            text=f"PRODUCT PASSPORT  #{passport_number}",
            font=("Segoe UI", 9, "bold"),
            fg="#D8C486",
            bg=NAVY
        ).pack(
            side="left",
            padx=25
        )

        tk.Label(
            footer,
            text="AI VERIFIED",
            font=("Segoe UI", 9, "bold"),
            fg=WHITE,
            bg=NAVY
        ).pack(
            side="right",
            padx=25
        )

    # ========================================================
    # PASSPORT HEADER
    # ========================================================

    def create_passport_header(
        self,
        parent,
        passport_number
    ):

        header = tk.Frame(
            parent,
            bg=NAVY,
            height=125
        )

        header.pack(
            fill="x"
        )

        header.pack_propagate(
            False
        )

        # Left
        left = tk.Frame(
            header,
            bg=NAVY
        )

        left.pack(
            side="left",
            fill="y",
            padx=35
        )

        tk.Label(
            left,
            text="PRODUCT\nPASSPORT",
            font=FONT_PASSPORT_TITLE,
            fg=WHITE,
            bg=NAVY,
            justify="left"
        ).pack(
            expand=True
        )

        # Center
        center = tk.Frame(
            header,
            bg=NAVY
        )

        center.pack(
            side="left",
            expand=True,
            fill="both"
        )

        tk.Label(
            center,
            text="DIGITAL PRODUCT IDENTITY",
            font=FONT_IDENTITY,
            fg=GOLD_LIGHT,
            bg=NAVY
        ).pack(
            pady=(30, 5)
        )

        tk.Label(
            center,
            text="LIFECYCLE • OWNERSHIP • WARRANTY",
            font=("Segoe UI", 10),
            fg="#A9B6CA",
            bg=NAVY
        ).pack()

        # Right
        right = tk.Frame(
            header,
            bg=NAVY
        )

        right.pack(
            side="right",
            fill="y",
            padx=35
        )

        tk.Label(
            right,
            text="AI\nVERIFIED",
            font=("Segoe UI", 10, "bold"),
            fg=WHITE,
            bg=NAVY,
            justify="center"
        ).pack(
            expand=True
        )

    # ========================================================
    # SECTION TITLE
    # ========================================================

    def create_section_title(
        self,
        parent,
        text
    ):

        tk.Label(
            parent,
            text=text,
            font=FONT_SECTION,
            fg=TEXT_DARK,
            bg=CREAM,
            anchor="w"
        ).pack(
            fill="x"
        )

    # ========================================================
    # GOLD LINE
    # ========================================================

    def create_gold_line(
        self,
        parent
    ):

        line = tk.Frame(
            parent,
            bg=GOLD,
            height=2
        )

        line.pack(
            fill="x",
            pady=(12, 0)
        )

    # ========================================================
    # VALUE BLOCK
    # ========================================================

    def create_value_block(
        self,
        parent,
        row,
        column,
        label,
        value,
        colspan=1
    ):

        frame = tk.Frame(
            parent,
            bg=CREAM
        )

        frame.grid(
            row=row,
            column=column,
            columnspan=colspan,
            sticky="nsew",
            padx=12,
            pady=14
        )

        parent.columnconfigure(
            column,
            weight=1
        )

        tk.Label(
            frame,
            text=label,
            font=FONT_LABEL,
            fg="#60708A",
            bg=CREAM,
            anchor="w"
        ).pack(
            fill="x",
            pady=(0, 8)
        )

        value_label = tk.Label(
            frame,
            text=value,
            font=FONT_VALUE,
            fg=TEXT_DARK,
            bg=CREAM,
            anchor="nw",
            justify="left",
            wraplength=400
        )

        value_label.pack(
            fill="x",
            expand=True
        )

        # ----------------------------------------------------
        # Recalculate wrapping dynamically
        # ----------------------------------------------------

        def resize_wrap(event):

            width = max(
                event.width - 10,
                150
            )

            value_label.configure(
                wraplength=width
            )

        frame.bind(
            "<Configure>",
            resize_wrap
        )

    # ========================================================
    # BOTTOM BAR
    # ========================================================

    def create_bottom_bar(self):

        bar = tk.Frame(
            self.root,
            bg=BG_COLOR,
            height=65
        )

        bar.pack(
            fill="x"
        )

        bar.pack_propagate(
            False
        )

        close_button = tk.Button(
            bar,
            text="CLOSE",
            font=("Segoe UI", 11, "bold"),
            fg=WHITE,
            bg="#23456D",
            activebackground="#315F91",
            activeforeground=WHITE,
            relief="flat",
            bd=0,
            width=15,
            height=1,
            cursor="hand2",
            command=self.root.destroy
        )

        close_button.pack(
            pady=14
        )

    # ========================================================
    # SCROLL CONTROLS
    # ========================================================

    def scroll_down(self, event=None):

        self.scroll_frame.canvas.yview_scroll(
            3,
            "units"
        )

    def scroll_up(self, event=None):

        self.scroll_frame.canvas.yview_scroll(
            -3,
            "units"
        )

    def scroll_page_down(self, event=None):

        self.scroll_frame.canvas.yview_scroll(
            1,
            "pages"
        )

    def scroll_page_up(self, event=None):

        self.scroll_frame.canvas.yview_scroll(
            -1,
            "pages"
        )

    def scroll_home(self, event=None):

        self.scroll_frame.canvas.yview_moveto(
            0
        )

    def scroll_end(self, event=None):

        self.scroll_frame.canvas.yview_moveto(
            1
        )


# ============================================================
# MAIN
# ============================================================

def main():

    data = load_passport()

    if data is None:

        return

    root = tk.Tk()

    app = ProductPassportApp(
        root,
        data
    )

    root.mainloop()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
    