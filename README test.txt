Smash and Grill — Offline Cash Register (Streamlit)
===================================================

This is a simple offline "cash register" web app you run on your own laptop.
It opens in your browser, but it doesn't need internet.

Files in this folder:
- app.py        → the app
- menu.csv      → your editable menu (SKU, Category, Item, UnitPrice)
- receipts/     → generated receipt HTML files
- sales.db      → (auto-created) SQLite database of orders

How to run (Windows/Mac/Linux):
1) Install Python 3.9+ from https://python.org
2) Open Terminal/Command Prompt and run:
   pip install streamlit pandas
3) In Terminal, go to this folder and run:
   streamlit run app.py
4) Your browser will open the app at a local address (e.g., http://localhost:8501).

Basic workflow:
- Pick a Category → select an Item → set Qty → Add to Cart
- Adjust Tax/Service/Discount on the left
- Click "Checkout" → an order is saved to the database and a receipt HTML is created in receipts/
- Click "Download Receipt" to save/print the HTML as PDF (Ctrl/Cmd+P in the browser)

Editing your menu:
- Open menu.csv in Excel or any editor, change rows/prices, save.
- Back in the app, click "Reload Menu" (top-right) to refresh.

Data storage:
- Orders and line items are stored in sales.db (SQLite). You can open it later with any SQLite viewer.