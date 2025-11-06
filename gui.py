import tkinter as tk
from tkinter import ttk, Listbox, Scrollbar
import webbrowser  # For opening links
import threading   # To run the scraper without freezing the UI

# --- 1. IMPORT OUR SCRAPER ENGINE ---
try:
    from wolt_engine import scrape_wolt
except ImportError:
    print("FATAL ERROR: Could not find 'wolt_engine.py'. Make sure it's in the same folder.")
    exit()

# --- 2. THE RESULTS WINDOW ---
class ResultsWindow(tk.Toplevel):
    def __init__(self, master, results_data):
        super().__init__(master)
        self.title("Wolt Scraper - Results")
        self.geometry("800x600")

        # Store the full, unfiltered list of results
        self.all_results = results_data

        # --- Create Restaurant Filter ---
        ttk.Label(self, text="Filter by Restaurant:").pack(pady=(10, 0))

        shop_names = sorted(list(set([res[0] for res in self.all_results])))

        self.restaurant_filter = ttk.Combobox(self, state="readonly", width=50)
        self.restaurant_filter['values'] = ["-- All Restaurants --"] + shop_names
        self.restaurant_filter.current(0)
        self.restaurant_filter.pack(pady=5)
        self.restaurant_filter.bind("<<ComboboxSelected>>", self.update_list)

        # --- Create Search Bar ---
        ttk.Label(self, text="Search Results:").pack(pady=(10, 0))
        self.search_var = tk.StringVar()
        self.search_bar = ttk.Entry(self, textvariable=self.search_var, width=50)
        self.search_bar.pack(pady=5)
        self.search_var.trace("w", self.update_list)

        # --- Create the Results Listbox ---
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(frame, orient="vertical")
        self.listbox = Listbox(frame, yscrollcommand=scrollbar.set, font=("TkFixedFont", 11), selectmode="single")
        scrollbar.config(command=self.listbox.yview)

        scrollbar.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)

        # --- Add Click-to-Open Functionality ---
        self.listbox.bind("<Double-1>", self.on_item_double_click)

        self.update_list()

    def update_list(self, *args):
        search_query = self.search_var.get().lower()
        selected_shop = self.restaurant_filter.get()

        self.listbox.delete(0, "end")

        for shop_name, shop_url, item_name, item_price in self.all_results:

            # 1. Check Restaurant Filter
            if selected_shop != "-- All Restaurants --" and shop_name != selected_shop:
                continue

            # 2. Check Search Bar Filter
            if search_query not in item_name.lower():
                continue

            list_entry = f"€{item_price:<6.2f} --- {item_name} --- (at {shop_name})"
            self.listbox.insert("end", list_entry)

    def on_item_double_click(self, event):
        try:
            selected_index = self.listbox.curselection
