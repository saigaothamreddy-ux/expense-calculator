# Daily Expense Calculator
A standalone, dark-themed daily expense and income tracker built with Python, CustomTkinter, and SQLite. 

## Features
* **Local Storage:** All financial data is securely stored offline in a local SQLite `.db` file.
* **Dynamic Categories:** Add custom income and expense categories on the fly.
* **Monthly Dashboard:** Tracks your 30-day runway and cash flow automatically.
* **CSV Export:** One-click export of your entire financial history.

## How to Run
1. Install dependencies:
   `pip install -r requirements.txt`
2. Run the application:
   `python app.py`

## Build as an Executable (.exe)
```bash
pip install pyinstaller
pyinstaller --noconsole --onefile app.py
