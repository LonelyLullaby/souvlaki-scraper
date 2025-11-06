import tkinter as tk
from tkinter import ttk, Listbox, Scrollbar
import webbrowser
import threading

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
            
            if selected_shop != "-- All Restaurants --" and shop_name != selected_shop:
                continue
            
            if search_query not in item_name.lower():
                continue
                
            list_entry = f"€{item_price:<6.2f} --- {item_name} --- (at {shop_name})"
            self.listbox.insert("end", list_entry)

    def on_item_double_click(self, event):
        # --- BUG FIX: Added 'except' block to close 'try' ---
        try:
            selected_index = self.listbox.curselection()[0]
            selected_text = self.listbox.get(selected_index)
        except IndexError:
            return
        except Exception: 
            return # Handles the real bug in the original code
            
        for shop_name, shop_url, item_name, item_price in self.all_results:
            list_entry = f"€{item_price:<6.2f} --- {item_name} --- (at {shop_name})"
            if list_entry == selected_text:
                print(f"Opening shop URL: {shop_url}")
                webbrowser.open_new_tab(shop_url)
                return


# --- 3. THE MAIN INPUT WINDOW ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Souvlaki Scraper")
        self.geometry("400x280") 
        
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        
        # --- Address Input ---
        ttk.Label(self, text="Address:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.address_entry = ttk.Entry(self, width=40)
        self.address_entry.grid(row=1, column=0, columnspan=2, padx=10, sticky="ew")
        self.address_entry.insert(0, "Τρίπολη")
        
        # --- Food Input ---
        ttk.Label(self, text="Food to Search:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.food_entry = ttk.Entry(self, width=40)
        self.food_entry.grid(row=3, column=0, columnspan=2, padx=10, sticky="ew")
        self.food_entry.insert(0, "Σουβλάκι")

        # --- Search Button ---
        self.search_button = ttk.Button(self, text="Find Deals!", command=self.start_scraping)
        self.search_button.grid(row=4, column=0, columnspan=2, padx=10, pady=20)
        
        # --- Status Label ---
        self.status_label = ttk.Label(self, text="Status: Idle")
        self.status_label.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        # --- Credit Label ---
        self.credit_label = ttk.Label(
            self, 
            text="Made by: Dennis Chailazopoulos", 
            font=("TkSmallCaptionFont", 8), 
            foreground="gray"
        )
        self.credit_label.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky="e")
        
    def start_scraping(self):
        address = self.address_entry.get()
        food = self.food_entry.get()
        
        if not address or not food:
            self.status_label.config(text="Status: Please fill out both fields.")
            return

        self.search_button.config(state="disabled")
        self.status_label.config(text="Status: Scraping... this may take a minute...")
        
        threading.Thread(
            target=self.run_scraper_thread, 
            args=(address, food, self.on_scraping_complete),
            daemon=True
        ).start()

    def run_scraper_thread(self, address, food, callback):
        print("Scraper thread started...")
        results = scrape_wolt(address, food)
        
        results.sort(key=lambda x: x[3])
        
        self.after(0, callback, results)

    def on_scraping_complete(self, results):
        print("Scraper thread finished. Showing results.")
        
        if not results:
            self.status_label.config(text="Status: No results found. Try another search.")
        else:
            ResultsWindow(self, results)
        
        self.search_button.config(state="normal")
        self.status_label.config(text="Status: Idle")


# --- 6. START THE APP ---
if __name__ == "__main__":
    app = App()
    app.mainloop()
