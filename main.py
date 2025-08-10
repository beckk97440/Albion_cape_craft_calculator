import os
import threading
import requests
import tkinter as tk
from tkinter import ttk

from items_functions import get_cape_id_by_name, ALL_CAPE_ITEMS, ITEM_ID_TO_NAME

BASE_URL = "https://europe.albion-online-data.com/api/v2/stats/prices/"

# Defaults (editable via UI)
TAXES: float = 6.5
SELECTED_ITEM: str = "Heretic Cape"
BASE_CAPE_SELECTED_CITY: str = "Lymhurst"
ARTIFACT_SELECTED_CITY: str = "Lymhurst"
HEART_SELECTED_CITY: str = "Lymhurst"


def get_active_ids_by_cape_type(cape_type: str) -> tuple[list[str], list[str], list[str], list[str]]:
    cape_name_list = [name for name in ALL_CAPE_ITEMS if name.split(" ", 1)[1].split(".")[0] == cape_type]
    cape_id_list: list[str] = []
    base_cape_id_set: set[str] = set()
    crests_id_set: set[str] = set()
    hearts_id_set: set[str] = set()
    for cape in cape_name_list:
        cape_id = get_cape_id_by_name(cape)
        cape_id_list.append(cape_id)
        data = ALL_CAPE_ITEMS[cape]
        base_cape_id_set.add(data["base_cape"])
        crests_id_set.add(data["crest"])
        hearts_id_set.add(data["heart"]["id"])
    # Sort for consistent order
    cape_id_list = sorted(cape_id_list)
    crests_id_list = sorted(crests_id_set)
    hearts_id_list = sorted(hearts_id_set)
    base_cape_id_list = sorted(base_cape_id_set)
    return cape_id_list, list(base_cape_id_list), list(crests_id_list), list(hearts_id_list)


def _fetch_prices(item_ids: list[str], city: str, field: str) -> dict:
    if not item_ids:
        return {}
    item_str = ",".join(item_ids).replace(" ", "")
    url = f"{BASE_URL}{item_str}?locations={city}&qualities=1"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    out: dict[str, int] = {}
    for it in data:
        item_id = it.get("item_id")
        val = it.get(field) or 0
        try:
            out[item_id] = int(val)
        except Exception:
            out[item_id] = 0
    return out


def get_sell_prices_min(item_ids: list[str], city: str) -> dict:
    return _fetch_prices(item_ids, city, "sell_price_min")


def get_buy_prices_max(item_ids: list[str], city: str) -> dict:
    return _fetch_prices(item_ids, city, "buy_price_max")


def get_total_cost(base_cape_price: int, crest_price: int, heart_price: int, heart_quantity: int) -> int:
    return base_cape_price + crest_price + (heart_price * heart_quantity)


def calc_profit(cape_price: int, base_cape_price: int, crest_price: int, heart_price: int, heart_quantity: int, taxes: float) -> int:
    profit = cape_price - (base_cape_price + crest_price + (heart_price * heart_quantity))
    return round(profit * ((100 - taxes) / 100))


def calc_roi(cape_price: int, base_cape_price: int, crest_price: int, heart_price: int, heart_quantity: int, taxes: float) -> float:
    total = get_total_cost(base_cape_price, crest_price, heart_price, heart_quantity)
    if total <= 0:
        return 0.0
    profit = cape_price - total
    profit_after_tax = round(profit * ((100 - taxes) / 100))
    return round((profit_after_tax / total) * 100, 2)


def build_row_for_cape(
    cape_id: str,
    base_cape_prices: dict,
    crest_prices: dict,
    heart_prices: dict,
    cape_prices: dict,
    taxes: float,
) -> list:
    base_cape_id = ""
    crest_id = ""
    heart_id = ""
    heart_quantity = 1
    for name, data in ALL_CAPE_ITEMS.items():
        if get_cape_id_by_name(name) == cape_id:
            base_cape_id = data["base_cape"]
            crest_id = data["crest"]
            heart_id = data["heart"]["id"]
            heart_quantity = data["heart"].get("quantity", 1)
            break

    base_cape_price = int(base_cape_prices.get(base_cape_id, 0) or 0)
    crest_price = int(crest_prices.get(crest_id, 0) or 0)
    heart_price = int(heart_prices.get(heart_id, 0) or 0)
    cape_price = int(cape_prices.get(cape_id, 0) or 0)

    total = get_total_cost(base_cape_price, crest_price, heart_price, heart_quantity)
    profit = calc_profit(cape_price, base_cape_price, crest_price, heart_price, heart_quantity, taxes)
    roi = calc_roi(cape_price, base_cape_price, crest_price, heart_price, heart_quantity, taxes)
    return [cape_price, crest_price, heart_price, heart_quantity, base_cape_price, total, profit, roi]


class AlbionCapeCalculatorApp:
    CITY_CHOICES = [
        "Lymhurst",
        "Caerleon",
        "Bridgewatch",
        "Thetford",
        "Fort Sterling",
        "Martlock",
        "Brecilien",
    ]

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Albion Cape Profit Calculator")
        self.root.geometry("1100x700")
        self.root.minsize(960, 640)

        # State
        self.selected_item = tk.StringVar(value=SELECTED_ITEM)
        self.base_city = tk.StringVar(value=BASE_CAPE_SELECTED_CITY)
        self.crest_city = tk.StringVar(value=ARTIFACT_SELECTED_CITY)
        self.heart_city = tk.StringVar(value=HEART_SELECTED_CITY)
        self.taxes_var = tk.DoubleVar(value=TAXES)

        self.current_image: tk.PhotoImage | None = None

        self._setup_style()
        self._build_layout()
        self._wire_events()

        self.refresh_data()

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        default_font = ("SF Pro Text", 12)
        small_font = ("SF Pro Text", 11)
        style.configure("TLabel", font=default_font)
        style.configure("TButton", font=default_font)
        style.configure("TCombobox", font=default_font)
        style.configure("TSpinbox", font=default_font)
        style.configure("Treeview", font=small_font, rowheight=28, borderwidth=0, relief="flat")
        style.configure("Treeview.Heading", font=("SF Pro Text", 12, "bold"), borderwidth=0)
        style.map("Treeview", background=[("selected", "#e6f0ff")], foreground=[("selected", "#1f3b73")])

    def _build_layout(self):
        controls = ttk.Frame(self.root, padding=(12, 12))
        controls.pack(fill=tk.X)

        # Left image
        left = ttk.Frame(controls)
        left.pack(side=tk.LEFT, padx=(0, 16))
        self.image_label = ttk.Label(left)
        self.image_label.pack()
        self._update_image_preview(self.selected_item.get())

        # Right selectors
        right = ttk.Frame(controls)
        right.pack(side=tk.LEFT, fill=tk.X, expand=True)

        row1 = ttk.Frame(right)
        row1.pack(fill=tk.X, pady=4)
        ttk.Label(row1, text="Cape Type").pack(side=tk.LEFT)
        self.item_combo = ttk.Combobox(row1, textvariable=self.selected_item, state="readonly", width=24)
        self.item_combo["values"] = self._get_item_choices()
        if self.selected_item.get() not in self.item_combo["values"] and self.item_combo["values"]:
            self.selected_item.set(self.item_combo["values"][0])
        self.item_combo.pack(side=tk.LEFT, padx=(8, 20))

        ttk.Label(row1, text="Taxes %").pack(side=tk.LEFT)
        self.taxes_spin = ttk.Spinbox(row1, textvariable=self.taxes_var, from_=0.0, to=100.0, increment=0.1, width=6)
        self.taxes_spin.pack(side=tk.LEFT, padx=(8, 0))
        self.refresh_btn = ttk.Button(row1, text="Refresh", command=self.refresh_data)
        self.refresh_btn.pack(side=tk.RIGHT)

        row2 = ttk.Frame(right)
        row2.pack(fill=tk.X, pady=4)
        ttk.Label(row2, text="Base Cape City").grid(row=0, column=0, sticky="w")
        self.base_combo = ttk.Combobox(row2, textvariable=self.base_city, state="readonly", width=16)
        self.base_combo["values"] = self.CITY_CHOICES
        self.base_combo.grid(row=0, column=1, padx=(8, 16), sticky="w")

        ttk.Label(row2, text="Crest City").grid(row=0, column=2, sticky="w")
        self.crest_combo = ttk.Combobox(row2, textvariable=self.crest_city, state="readonly", width=16)
        self.crest_combo["values"] = self.CITY_CHOICES
        self.crest_combo.grid(row=0, column=3, padx=(8, 16), sticky="w")

        ttk.Label(row2, text="Heart City").grid(row=0, column=4, sticky="w")
        self.heart_combo = ttk.Combobox(row2, textvariable=self.heart_city, state="readonly", width=16)
        self.heart_combo["values"] = self.CITY_CHOICES
        self.heart_combo.grid(row=0, column=5, padx=(8, 16), sticky="w")

        # Status
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self.root, textvariable=self.status_var, anchor="w")
        self.status_label.pack(fill=tk.X, padx=12)

        # Table
        table_frame = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = (
            "name",
            "cape_price",
            "crest_price",
            "heart_price",
            "heart_qty",
            "base_cape_price",
            "total_cost",
            "profit",
            "roi",
        )
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        self.tree.heading("name", text="Tier/Enchant", command=lambda: self._sort_by("name", False))
        self.tree.heading("cape_price", text="BM Sell Price", command=lambda: self._sort_by("cape_price", False))
        self.tree.heading("crest_price", text="Crest", command=lambda: self._sort_by("crest_price", False))
        self.tree.heading("heart_price", text="Heart", command=lambda: self._sort_by("heart_price", False))
        self.tree.heading("heart_qty", text="Heart x", command=lambda: self._sort_by("heart_qty", False))
        self.tree.heading("base_cape_price", text="Base Cape", command=lambda: self._sort_by("base_cape_price", False))
        self.tree.heading("total_cost", text="Total Cost", command=lambda: self._sort_by("total_cost", False))
        self.tree.heading("profit", text="Profit (after tax)", command=lambda: self._sort_by("profit", False))
        self.tree.heading("roi", text="ROI %", command=lambda: self._sort_by("roi", False))

        self.tree.column("name", width=200, anchor="w")
        self.tree.column("cape_price", width=130, anchor="e")
        self.tree.column("crest_price", width=110, anchor="e")
        self.tree.column("heart_price", width=110, anchor="e")
        self.tree.column("heart_qty", width=80, anchor="center")
        self.tree.column("base_cape_price", width=120, anchor="e")
        self.tree.column("total_cost", width=120, anchor="e")
        self.tree.column("profit", width=140, anchor="e")
        self.tree.column("roi", width=80, anchor="e")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.tag_configure("profit_pos", foreground="#0a7f2e")
        self.tree.tag_configure("profit_neg", foreground="#b00020")
        self.tree.tag_configure("odd", background="#f8f9fb")

    def _wire_events(self):
        self.item_combo.bind("<<ComboboxSelected>>", lambda e: self._on_item_change())
        self.base_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_data())
        self.crest_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_data())
        self.heart_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_data())
        self.taxes_spin.bind("<Return>", lambda e: self.refresh_data())
        self.taxes_spin.bind("<FocusOut>", lambda e: self._clamp_taxes_and_refresh())

    def _clamp_taxes_and_refresh(self):
        try:
            v = float(self.taxes_var.get())
        except Exception:
            v = TAXES
        v = max(0.0, min(100.0, v))
        self.taxes_var.set(round(v, 2))
        self.refresh_data()

    def _get_item_choices(self) -> list[str]:
        # Show all names from img folder
        try:
            img_names = [
                os.path.splitext(f)[0]
                for f in os.listdir("img")
                if os.path.isfile(os.path.join("img", f)) and f.lower().endswith(".png")
            ]
        except FileNotFoundError:
            img_names = []
        # If none, fall back to DB-detected types
        return img_names or sorted({name.split(" ", 1)[1].split(".")[0] for name in ALL_CAPE_ITEMS})

    def _on_item_change(self):
        self._update_image_preview(self.selected_item.get())
        self.refresh_data()

    def _update_image_preview(self, item_name: str):
        img_path = os.path.join("img", f"{item_name}.png")
        if os.path.exists(img_path):
            try:
                img = tk.PhotoImage(file=img_path)
                self.current_image = img
                self.image_label.configure(image=self.current_image)
            except Exception:
                self.image_label.configure(image="", text=item_name)
        else:
            self.image_label.configure(image="", text=item_name)

    def refresh_data(self):
        global SELECTED_ITEM, BASE_CAPE_SELECTED_CITY, ARTIFACT_SELECTED_CITY, HEART_SELECTED_CITY, TAXES
        SELECTED_ITEM = self.selected_item.get()
        BASE_CAPE_SELECTED_CITY = self.base_city.get()
        ARTIFACT_SELECTED_CITY = self.crest_city.get()
        HEART_SELECTED_CITY = self.heart_city.get()
        TAXES = float(self.taxes_var.get())

        self.status_var.set(
            f"Loading {SELECTED_ITEM} | Base:{BASE_CAPE_SELECTED_CITY} Crest:{ARTIFACT_SELECTED_CITY} Heart:{HEART_SELECTED_CITY}"
        )
        self.refresh_btn.configure(state=tk.DISABLED)

        def worker():
            try:
                cape_ids, base_ids, crest_ids, heart_ids = get_active_ids_by_cape_type(SELECTED_ITEM)
                if not cape_ids:
                    # No data for this type; just clear table and show status
                    self.root.after(0, lambda: self._populate_table([]))
                    self.root.after(0, lambda: self._on_error(Exception("No data for this cape type in DB")))
                    return

                cape_prices = get_buy_prices_max(cape_ids, "Black Market")
                base_prices = get_sell_prices_min(base_ids, BASE_CAPE_SELECTED_CITY)
                crest_prices = get_sell_prices_min(crest_ids, ARTIFACT_SELECTED_CITY)
                heart_prices = get_sell_prices_min(heart_ids, HEART_SELECTED_CITY)

                rows = []
                for cape_id in cape_ids:
                    data = build_row_for_cape(
                        cape_id, base_prices, crest_prices, heart_prices, cape_prices, float(self.taxes_var.get())
                    )
                    display_name = ITEM_ID_TO_NAME.get(cape_id, cape_id)
                    rows.append((cape_id, display_name, data))

                self.root.after(0, lambda: self._populate_table(rows))
            except Exception as e:
                self.root.after(0, lambda: self._on_error(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_error(self, err: Exception):
        self.status_var.set(f"Error: {err}")
        self.refresh_btn.configure(state=tk.NORMAL)

    def _populate_table(self, rows: list[tuple[str, str, list]]):
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        for idx, (cape_id, display_name, data) in enumerate(rows):
            cape_price, crest_price, heart_price, heart_qty, base_price, total_cost, profit, roi = data

            def fmt(v):
                try:
                    iv = int(v)
                    return "-" if iv == 0 else f"{iv:,}"
                except Exception:
                    return v

            tags = []
            if profit < 0:
                tags.append("profit_neg")
            elif profit > 0:
                tags.append("profit_pos")
            if idx % 2 == 1:
                tags.append("odd")

            self.tree.insert(
                "",
                "end",
                iid=cape_id,
                values=(
                    display_name,
                    fmt(cape_price),
                    fmt(crest_price),
                    fmt(heart_price),
                    heart_qty,
                    fmt(base_price),
                    fmt(total_cost),
                    fmt(profit),
                    f"{roi:.2f}%",
                ),
                tags=tuple(tags),
            )

        if rows:
            self.status_var.set(f"Loaded {len(rows)} rows. Click headers to sort.")
        else:
            self.status_var.set("No rows to display for this selection.")
        self.refresh_btn.configure(state=tk.NORMAL)

    def _sort_by(self, col_key: str, descending: bool):
        items = [(self.tree.set(k, col_key), k) for k in self.tree.get_children("")]

        def parse(v: str):
            if isinstance(v, str) and v.endswith("%"):
                try:
                    return float(v[:-1])
                except Exception:
                    return 0.0
            try:
                return int(str(v).replace(",", ""))
            except Exception:
                return v

        items.sort(key=lambda t: parse(t[0]), reverse=descending)
        for index, (_, k) in enumerate(items):
            self.tree.move(k, "", index)
        self.tree.heading(col_key, command=lambda: self._sort_by(col_key, not descending))


def main():
    root = tk.Tk()
    AlbionCapeCalculatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
