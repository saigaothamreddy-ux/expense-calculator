import sys
import os
import sqlite3
import csv
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox, filedialog

# ---------------------------------------------------------
# CONSTANTS & CONFIGURATION
# ---------------------------------------------------------
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

COLOR_INCOME = "#2ECC71"    # Emerald green
COLOR_EXPENSE = "#E74C3C"   # Crimson red
COLOR_CARD = "#212126"      # Deep dark card background
COLOR_MUTED = "#8E8E93"     # Secondary text


def get_db_path() -> str:
    """Ensures database persists next to the executable or script."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "expenses.db")


# ---------------------------------------------------------
# DATABASE MANAGER
# ---------------------------------------------------------
class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Transactions Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    date TEXT NOT NULL,
                    note TEXT
                )
                """
            )
            
            # 2. Dynamic Categories Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    UNIQUE(name, type)
                )
                """
            )
            conn.commit()

            # Seed default categories if empty
            cursor.execute("SELECT COUNT(*) FROM categories")
            if cursor.fetchone()[0] == 0:
                self.seed_default_categories(cursor)
                conn.commit()

            # Seed transactions if empty
            cursor.execute("SELECT COUNT(*) FROM transactions")
            if cursor.fetchone()[0] == 0:
                self.seed_dummy_transactions(cursor)
                conn.commit()

    def seed_default_categories(self, cursor):
        incomes = [
            ("Salary", "Income"), 
            ("Freelance", "Income"),
            ("Investments", "Income"),
            ("Other Income", "Income")
        ]
        expenses = [
            ("Food & Dining", "Expense"), 
            ("Transport & Fuel", "Expense"), 
            ("Utilities & Bills", "Expense"),
            ("Entertainment", "Expense"), 
            ("Shopping", "Expense"),
            ("Health & Fitness", "Expense"), 
            ("Subscriptions", "Expense"), 
            ("Education", "Expense"),
            ("Miscellaneous", "Expense")
        ]
        cursor.executemany("INSERT INTO categories (name, type) VALUES (?, ?)", incomes + expenses)

    def seed_dummy_transactions(self, cursor):
        now_str = datetime.now().strftime("%Y-%m-%d")
        sample_transactions = [
            ("Income", 5000.00, "Freelance", now_str, "Website Project Completion"),
            ("Expense", 120.00, "Subscriptions", now_str, "Monthly software subscription"),
            ("Expense", 450.00, "Food & Dining", now_str, "Grocery run & snacks"),
            ("Expense", 650.00, "Utilities & Bills", now_str, "Monthly internet bill")
        ]
        cursor.executemany(
            "INSERT INTO transactions (type, amount, category, date, note) VALUES (?, ?, ?, ?, ?)",
            sample_transactions
        )

    def get_categories(self, t_type: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM categories WHERE type = ? ORDER BY name", (t_type,))
            return [row[0] for row in cursor.fetchall()]

    def add_category(self, name: str, t_type: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO categories (name, type) VALUES (?, ?)", (name, t_type))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def add_transaction(self, t_type: str, amount: float, category: str, date: str, note: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO transactions (type, amount, category, date, note) VALUES (?, ?, ?, ?, ?)",
                (t_type, amount, category, date, note)
            )
            conn.commit()

    def delete_transaction(self, transaction_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            conn.commit()

    def get_all_transactions(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, type, amount, category, date, note FROM transactions ORDER BY date DESC, id DESC")
            return cursor.fetchall()

    def get_current_month_stats(self):
        current_month = datetime.now().strftime("%Y-%m")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = 'Income' AND date LIKE ?", (current_month + '%',))
            total_income = cursor.fetchone()[0] or 0.0

            cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = 'Expense' AND date LIKE ?", (current_month + '%',))
            total_expense = cursor.fetchone()[0] or 0.0

            balance = total_income - total_expense
            return total_income, total_expense, balance


# ---------------------------------------------------------
# APPLICATION UI
# ---------------------------------------------------------
class ExpenseTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Daily Expense Calculator")
        self.geometry("1100x720")
        self.minsize(980, 620)
        
        self.db = DatabaseManager(get_db_path())

        self.grid_columnconfigure(0, weight=0, minsize=360)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()
        self.refresh_dashboard()

    def _build_left_panel(self):
        left_container = ctk.CTkFrame(self, corner_radius=12, fg_color="#18181C", width=360)
        left_container.grid(row=0, column=0, sticky="nsew", padx=(18, 10), pady=18)
        left_container.grid_propagate(False)

        title_label = ctk.CTkLabel(left_container, text="Add Transaction", font=ctk.CTkFont(size=22, weight="bold"))
        title_label.pack(anchor="w", padx=24, pady=(24, 4))

        subtitle_label = ctk.CTkLabel(left_container, text="Record income or expenses", font=ctk.CTkFont(size=13), text_color=COLOR_MUTED)
        subtitle_label.pack(anchor="w", padx=24, pady=(0, 24))

        self.type_var = ctk.StringVar(value="Expense")
        radio_frame = ctk.CTkFrame(left_container, fg_color="transparent")
        radio_frame.pack(fill="x", padx=24, pady=(0, 20))
        
        self.radio_expense = ctk.CTkRadioButton(radio_frame, text="Expense", variable=self.type_var, value="Expense", command=self._on_type_changed, fg_color=COLOR_EXPENSE, hover_color="#C0392B", font=ctk.CTkFont(size=14, weight="bold"))
        self.radio_expense.pack(side="left", padx=(0, 20))
        self.radio_income = ctk.CTkRadioButton(radio_frame, text="Income", variable=self.type_var, value="Income", command=self._on_type_changed, fg_color=COLOR_INCOME, hover_color="#27AE60", font=ctk.CTkFont(size=14, weight="bold"))
        self.radio_income.pack(side="left")

        self._create_field_label(left_container, "AMOUNT (₹)")
        self.amount_entry = ctk.CTkEntry(left_container, placeholder_text="0.00", height=42, font=ctk.CTkFont(size=15), corner_radius=8)
        self.amount_entry.pack(fill="x", padx=24, pady=(0, 16))

        self._create_field_label(left_container, "DATE (YYYY-MM-DD)")
        self.date_entry = ctk.CTkEntry(left_container, height=42, font=ctk.CTkFont(size=14), corner_radius=8)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.pack(fill="x", padx=24, pady=(0, 16))

        self._create_field_label(left_container, "CATEGORY")
        cat_frame = ctk.CTkFrame(left_container, fg_color="transparent")
        cat_frame.pack(fill="x", padx=24, pady=(0, 16))

        self.category_dropdown = ctk.CTkOptionMenu(
            cat_frame, 
            values=[], 
            height=42, 
            corner_radius=8,
            font=ctk.CTkFont(size=14),
            text_color="#FFFFFF",
            fg_color="#212126",
            button_color="#2A2A30",
            button_hover_color="#3E3E45",
            dropdown_font=ctk.CTkFont(size=13),
            dropdown_fg_color="#212126",
            dropdown_hover_color="#3E3E45",
            dropdown_text_color="#FFFFFF"
        )
        self.category_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        add_cat_btn = ctk.CTkButton(cat_frame, text="+", width=42, height=42, corner_radius=8, font=ctk.CTkFont(size=18, weight="bold"), fg_color="#2E2E33", hover_color="#3E3E45", command=self._prompt_new_category)
        add_cat_btn.pack(side="right")
        
        self._on_type_changed()

        self._create_field_label(left_container, "NOTE (OPTIONAL)")
        self.note_entry = ctk.CTkEntry(left_container, placeholder_text="e.g. Utilities payment", height=42, font=ctk.CTkFont(size=14), corner_radius=8)
        self.note_entry.pack(fill="x", padx=24, pady=(0, 24))

        self.submit_btn = ctk.CTkButton(left_container, text="Add Transaction", height=46, corner_radius=8, font=ctk.CTkFont(size=15, weight="bold"), command=self._handle_add_transaction)
        self.submit_btn.pack(fill="x", padx=24, pady=(0, 12))

        self.status_label = ctk.CTkLabel(left_container, text="", font=ctk.CTkFont(size=13), text_color=COLOR_INCOME)
        self.status_label.pack(anchor="center", padx=24)

    def _create_field_label(self, parent, text):
        lbl = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_MUTED)
        lbl.pack(anchor="w", padx=24, pady=(0, 6))

    def _on_type_changed(self):
        t_type = self.type_var.get()
        categories = self.db.get_categories(t_type)
        if not categories:
            categories = ["Uncategorized"]
            
        self.category_dropdown.configure(values=categories)
        self.category_dropdown.set(categories[0])

    def _prompt_new_category(self):
        t_type = self.type_var.get()
        dialog = ctk.CTkInputDialog(text=f"Enter name for new {t_type.lower()} category:", title="New Category")
        new_cat = dialog.get_input()
        
        if new_cat and new_cat.strip():
            new_cat = new_cat.strip()
            success = self.db.add_category(new_cat, t_type)
            if success:
                self._on_type_changed()
                self.category_dropdown.set(new_cat)
                self._show_status(f"Category '{new_cat}' added.", is_error=False)
            else:
                self._show_status(f"Category '{new_cat}' already exists.", is_error=True)

    def _handle_add_transaction(self):
        amount_raw = self.amount_entry.get().strip()
        date_raw = self.date_entry.get().strip()
        
        try:
            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError
        except ValueError:
            self._show_status("Enter a valid amount greater than 0.", is_error=True)
            return

        try:
            datetime.strptime(date_raw, "%Y-%m-%d")
        except ValueError:
            self._show_status("Use YYYY-MM-DD format for date.", is_error=True)
            return

        t_type = self.type_var.get()
        category = self.category_dropdown.get()
        note = self.note_entry.get().strip() or "No note"

        self.db.add_transaction(t_type, amount, category, date_raw, note)
        self.amount_entry.delete(0, "end")
        self.note_entry.delete(0, "end")
        self._show_status(f"{t_type} added successfully!", is_error=False)
        self.refresh_dashboard()

    def _show_status(self, message: str, is_error: bool = False):
        self.status_label.configure(text=message, text_color=COLOR_EXPENSE if is_error else COLOR_INCOME)
        self.after(3500, lambda: self.status_label.configure(text=""))

    def _build_right_panel(self):
        right_container = ctk.CTkFrame(self, corner_radius=12, fg_color="transparent")
        right_container.grid(row=0, column=1, sticky="nsew", padx=(5, 18), pady=18)
        right_container.grid_rowconfigure(1, weight=1)
        right_container.grid_columnconfigure(0, weight=1)

        cards_frame = ctk.CTkFrame(right_container, fg_color="transparent")
        cards_frame.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        cards_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="cards")

        self.card_balance = self._create_stat_card(cards_frame, 0, "THIS MONTH'S BALANCE", "₹0", "#FFFFFF")
        self.card_income = self._create_stat_card(cards_frame, 1, "THIS MONTH'S INCOME", "₹0", COLOR_INCOME)
        self.card_expense = self._create_stat_card(cards_frame, 2, "THIS MONTH'S EXPENSES", "₹0", COLOR_EXPENSE)

        history_frame = ctk.CTkFrame(right_container, corner_radius=12, fg_color="#18181C")
        history_frame.grid(row=1, column=0, sticky="nsew")
        history_frame.grid_rowconfigure(1, weight=1)
        history_frame.grid_columnconfigure(0, weight=1)

        history_header = ctk.CTkFrame(history_frame, fg_color="transparent")
        history_header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))

        history_title = ctk.CTkLabel(history_header, text="Recent Transactions", font=ctk.CTkFont(size=18, weight="bold"))
        history_title.pack(side="left")

        export_btn = ctk.CTkButton(history_header, text="Export CSV", width=100, height=32, corner_radius=6, fg_color="#2E2E33", hover_color="#3E3E45", font=ctk.CTkFont(size=12, weight="bold"), command=self._export_csv)
        export_btn.pack(side="right")

        self.scroll_list = ctk.CTkScrollableFrame(history_frame, fg_color="transparent", corner_radius=8)
        self.scroll_list.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

    def _create_stat_card(self, parent, column: int, title: str, initial_val: str, val_color: str):
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color="#18181C")
        card.grid(row=0, column=column, sticky="nsew", padx=6)
        
        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_MUTED)
        lbl_title.pack(anchor="w", padx=20, pady=(18, 4))
        
        lbl_val = ctk.CTkLabel(card, text=initial_val, font=ctk.CTkFont(size=26, weight="bold"), text_color=val_color)
        lbl_val.pack(anchor="w", padx=20, pady=(0, 18))
        return lbl_val

    def refresh_dashboard(self):
        inc, exp, bal = self.db.get_current_month_stats()
        self.card_income.configure(text=f"₹{inc:,.0f}")
        self.card_expense.configure(text=f"₹{exp:,.0f}")
        self.card_balance.configure(text=f"₹{bal:,.0f}" if bal >= 0 else f"-₹{abs(bal):,.0f}")

        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        transactions = self.db.get_all_transactions()
        if not transactions:
            ctk.CTkLabel(self.scroll_list, text="No transactions recorded yet.", font=ctk.CTkFont(size=14), text_color=COLOR_MUTED).pack(pady=40)
            return

        for row in transactions:
            self._render_transaction_row(*row)

    def _render_transaction_row(self, t_id, t_type, amount, category, date_str, note):
        is_income = (t_type == "Income")
        accent_color = COLOR_INCOME if is_income else COLOR_EXPENSE
        sign = "+" if is_income else "-"

        item_card = ctk.CTkFrame(self.scroll_list, corner_radius=10, fg_color=COLOR_CARD)
        item_card.pack(fill="x", pady=5, padx=4)

        left_box = ctk.CTkFrame(item_card, fg_color="transparent")
        left_box.pack(side="left", padx=16, pady=12, fill="both", expand=True)

        header_line = ctk.CTkFrame(left_box, fg_color="transparent")
        header_line.pack(anchor="w")

        badge = ctk.CTkLabel(header_line, text=f" {t_type.upper()} ", font=ctk.CTkFont(size=10, weight="bold"), text_color="#FFFFFF", fg_color=accent_color, corner_radius=4)
        badge.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(header_line, text=category, font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF").pack(side="left")
        ctk.CTkLabel(left_box, text=f"{note} • {date_str}", font=ctk.CTkFont(size=13), text_color=COLOR_MUTED).pack(anchor="w", pady=(4, 0))

        right_box = ctk.CTkFrame(item_card, fg_color="transparent")
        right_box.pack(side="right", padx=16, pady=12)

        ctk.CTkLabel(right_box, text=f"{sign}₹{amount:,.0f}", font=ctk.CTkFont(size=18, weight="bold"), text_color=accent_color).pack(side="left", padx=(0, 16))
        ctk.CTkButton(right_box, text="✕", width=30, height=30, corner_radius=15, fg_color="#2E2E33", hover_color=COLOR_EXPENSE, font=ctk.CTkFont(size=14, weight="bold"), command=lambda: self._confirm_delete(t_id)).pack(side="right")

    def _confirm_delete(self, transaction_id: int):
        if messagebox.askyesno("Delete Transaction", "Permanently delete this transaction?"):
            self.db.delete_transaction(transaction_id)
            self.refresh_dashboard()

    def _export_csv(self):
        transactions = self.db.get_all_transactions()
        if not transactions:
            messagebox.showinfo("Export", "No data to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"expenses_export_{datetime.now().strftime('%Y%m%d')}.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(["ID", "Type", "Amount", "Category", "Date", "Note"])
                    for row in transactions:
                        writer.writerow(row)
                messagebox.showinfo("Success", "Data exported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export data:\n{str(e)}")

# ---------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------
if __name__ == "__main__":
    app = ExpenseTrackerApp()
    app.mainloop()
