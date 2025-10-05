import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sqlite3
import csv

# ---------- Database Setup ----------
def init_db():
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        bought INTEGER NOT NULL DEFAULT 0,
        sold INTEGER NOT NULL DEFAULT 0
    )''')
    conn.commit()
    conn.close()

# ---------- CRUD Functions ----------
def fetch_items(filter_text=""):
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    if filter_text:
        c.execute("SELECT * FROM items WHERE name LIKE ?", ('%' + filter_text + '%',))
    else:
        c.execute("SELECT * FROM items")
    results = c.fetchall()
    conn.close()
    return results

def add_item(name, bought, sold):
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute("INSERT INTO items (name, bought, sold) VALUES (?, ?, ?)", (name, bought, sold))
    conn.commit()
    conn.close()

def update_item(item_id, name, bought, sold):
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute("UPDATE items SET name=?, bought=?, sold=? WHERE id=?", (name, bought, sold, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

def export_csv(data):
    filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv")])
    if filepath:
        with open(filepath, mode='w', newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["ID", "Name", "Bought", "Sold", "Remaining"])
            for row in data:
                remaining = row[2] - row[3]
                writer.writerow([row[0], row[1], row[2], row[3], remaining])
        messagebox.showinfo("Export", "Inventory exported successfully.")

# --------- Interactive Modal Form for Add/Edit ----------
class ItemForm(simpledialog.Dialog):
    def __init__(self, parent, title, item=None):
        self.item = item
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="Name:").grid(row=0, column=0, sticky='e')
        ttk.Label(master, text="Bought:").grid(row=1, column=0, sticky='e')
        ttk.Label(master, text="Sold:").grid(row=2, column=0, sticky='e')

        self.name_var = tk.StringVar(value=self.item[1] if self.item else "")
        self.bought_var = tk.IntVar(value=self.item[2] if self.item else 0)
        self.sold_var = tk.IntVar(value=self.item[3] if self.item else 0)

        self.entry_name = ttk.Entry(master, textvariable=self.name_var, width=30)
        self.entry_bought = ttk.Entry(master, textvariable=self.bought_var)
        self.entry_sold = ttk.Entry(master, textvariable=self.sold_var)

        self.entry_name.grid(row=0, column=1, padx=5, pady=5)
        self.entry_bought.grid(row=1, column=1, padx=5, pady=5)
        self.entry_sold.grid(row=2, column=1, padx=5, pady=5)

        return self.entry_name

    def validate(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Name cannot be empty.")
            return False
        try:
            bought = int(self.bought_var.get())
            sold = int(self.sold_var.get())
            if bought < 0 or sold < 0:
                messagebox.showwarning("Validation", "Bought and Sold cannot be negative.")
                return False
            if sold > bought:
                messagebox.showwarning("Validation", "Sold cannot be more than Bought.")
                return False
        except Exception:
            messagebox.showwarning("Validation", "Bought and Sold must be integers.")
            return False
        return True

    def apply(self):
        self.result = (self.name_var.get().strip(), int(self.bought_var.get()), int(self.sold_var.get()))

# --------- Main Application -----------
class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vendor Inventory Manager")
        self.geometry("850x450")
        self.style = ttk.Style(self)
        # Use default theme; to improve, can use more advanced themes like clam
        self.style.theme_use('clam')

        self.selected_id = None

        # Search bar frame
        search_frame = ttk.Frame(self)
        search_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(search_frame, text="Search:").pack(side='left')
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.search_items)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side='left', fill='x', expand=True, padx=5)

        ttk.Button(search_frame, text="Clear Search", command=self.clear_search).pack(side='left')

        # Treeview for inventory
        self.tree = ttk.Treeview(self, columns=("Name", "Bought", "Sold", "Remaining"), show="headings", selectmode="browse")
        for col in ("Name", "Bought", "Sold", "Remaining"):
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_tree(c, False))
            self.tree.column(col, anchor='center')
        self.tree.pack(fill='both', expand=True, padx=10, pady=10)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Control buttons frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(btn_frame, text="Add Item", command=self.add_item).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Edit Selected", command=self.edit_item).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_item).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Export CSV", command=self.export_data).pack(side='right', padx=5)

        self.status_var = tk.StringVar()
        status_label = ttk.Label(self, textvariable=self.status_var, relief='sunken', anchor='w')
        status_label.pack(fill='x')
        
        self.load_inventory()

    def load_inventory(self, filter_text=""):
        for row in self.tree.get_children():
            self.tree.delete(row)
        items = fetch_items(filter_text)
        for item in items:
            remaining = item[2] - item[3]
            self.tree.insert("", "end", iid=str(item[0]), values=(item[1], item[2], item[3], remaining))
        self.status_var.set(f"Loaded {len(items)} items.")

    def search_items(self, *args):
        filter_text = self.search_var.get().strip()
        self.load_inventory(filter_text)

    def clear_search(self):
        self.search_var.set("")
        self.load_inventory()

    def add_item(self):
        dialog = ItemForm(self, "Add New Item")
        if dialog.result:
            name, bought, sold = dialog.result
            add_item(name, bought, sold)
            self.load_inventory()
            self.status_var.set(f"Added item '{name}'.")

    def edit_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Edit Item", "Select an item to edit.")
            return
        item_id = int(selected[0])
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("SELECT * FROM items WHERE id=?", (item_id,))
        item = c.fetchone()
        conn.close()
        dialog = ItemForm(self, "Edit Item", item)
        if dialog.result:
            name, bought, sold = dialog.result
            update_item(item_id, name, bought, sold)
            self.load_inventory()
            self.status_var.set(f"Updated item '{name}'.")

    def delete_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Delete Item", "Select an item to delete.")
            return
        item_id = int(selected[0])
        answer = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected item?")
        if answer:
            delete_item(item_id)
            self.load_inventory()
            self.status_var.set("Item deleted.")

    def export_data(self):
        data = []
        for iid in self.tree.get_children():
            values = self.tree.item(iid)['values']
            name, bought, sold, remaining = values
            data.append((int(iid), name, bought, sold))
        export_csv(data)

    def on_double_click(self, event):
        self.edit_item()

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if selected:
            item_id = selected[0]
            self.status_var.set(f"Selected item ID: {item_id}")
        else:
            self.status_var.set("")

    def sort_tree(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        if col in ("Bought", "Sold", "Remaining"):
            l.sort(key=lambda t: int(t[0]), reverse=reverse)
        else:
            l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)
        self.tree.heading(col, command=lambda: self.sort_tree(col, not reverse))


if __name__ == "__main__":
    init_db()
    app = InventoryApp()
    app.mainloop()
