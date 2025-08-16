import os
import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st
from io import BytesIO

# ---- PASSWORD PROTECTION ----
def check_password():
    def password_entered():
        if st.session_state["password"] == "sheikh001":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter password to access POS:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter password to access POS:", type="password", on_change=password_entered, key="password")
        st.error("😕 Incorrect password")
        return False
    else:
        return True

if not check_password():
    st.stop()

# ---- APP CONSTANTS ----
APP_TITLE = "Smash and Grill — Cash Register"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MENU_PATH = os.path.join(BASE_DIR, "menu.csv")
DB_PATH = os.path.join(BASE_DIR, "sales.db")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
os.makedirs(RECEIPTS_DIR, exist_ok=True)

# ---- UTILITIES ----
def load_menu():
    if not os.path.exists(MENU_PATH):
        st.error("menu.csv not found. Please add your menu file.")
        return pd.DataFrame(columns=["SKU","Category","Item","UnitPrice"])
    df = pd.read_csv(MENU_PATH)
    required = {"SKU","Category","Item","UnitPrice"}
    if not required.issubset(df.columns):
        st.error("menu.csv must have columns: SKU, Category, Item, UnitPrice")
        return pd.DataFrame(columns=["SKU","Category","Item","UnitPrice"])
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce").fillna(0).astype(float)
    return df

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders(
                order_id TEXT PRIMARY KEY,
                timestamp TEXT,
                cashier TEXT,
                payment_method TEXT,
                subtotal REAL,
                tax REAL,
                service REAL,
                discount REAL,
                total REAL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS order_items(
                order_id TEXT,
                line_no INTEGER,
                sku TEXT,
                item TEXT,
                unit_price REAL,
                qty INTEGER,
                line_total REAL
            )
        """)
        con.commit()

def save_order(order_id, cashier, payment_method, subtotal, tax, service, discount, total, cart):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
            INSERT INTO orders(order_id, timestamp, cashier, payment_method, subtotal, tax, service, discount, total)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (order_id, datetime.now().isoformat(timespec="seconds"), cashier, payment_method,
              float(subtotal), float(tax), float(service), float(discount), float(total)))
        for i, row in enumerate(cart, start=1):
            cur.execute("""
                INSERT INTO order_items(order_id, line_no, sku, item, unit_price, qty, line_total)
                VALUES(?,?,?,?,?,?,?)
            """, (order_id, i, row["SKU"], row["Item"], float(row["UnitPrice"]), int(row["Qty"]), float(row["LineTotal"])))
        con.commit()

def make_receipt_html(order_id, cashier, payment, cart_df, subtotal, tax, service, discount, total):
    rows_html = "\n".join(
        f"<tr><td>{r['Item']}</td><td style='text-align:center'>{int(r['Qty'])}</td><td style='text-align:right'>{r['UnitPrice']:.0f}</td><td style='text-align:right'>{r['LineTotal']:.0f}</td></tr>"
        for _, r in cart_df.iterrows()
    )
    html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Receipt {order_id}</title>
<style>
body {{
    font-family: 'Courier New', monospace;
    width: 58mm;  /* smaller receipt width */
    margin: 0 auto;
    font-size: 11px;
}}
.table {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
.table th, .table td {{ border-bottom: 1px dashed #000; padding: 2px 0; }}
.right {{ text-align: right; }}
.center {{ text-align: center; }}
.summary td {{ padding: 2px 0; }}
.small {{ color: #000; font-size: 10px; }}
</style>
</head>
<body>
<h2 class="center">Smash and Grill</h2>
<div class="small center">Order ID: {order_id} | {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
<div class="small">Cashier: {cashier} | Payment: {payment}</div>

<table class="table">
<thead><tr><th>Item</th><th class="center">Qty</th><th class="right">Unit</th><th class="right">Total</th></tr></thead>
<tbody>
{rows_html}
</tbody>
</table>

<table class="summary" style="width: 100%; margin-top: 6px;">
<tr><td class="right">Subtotal</td><td class="right">{subtotal:.0f}</td></tr>
<tr><td class="right">Tax</td><td class="right">{tax:.0f}</td></tr>
<tr><td class="right">Service</td><td class="right">{service:.0f}</td></tr>
<tr><td class="right">Discount</td><td class="right">-{discount:.0f}</td></tr>
<tr><td class="right"><strong>Grand Total</strong></td><td class="right"><strong>{total:.0f}</strong></td></tr>
</table>

<p class="center small">Thank you for dining with us!</p>
</body>
</html>
"""
    return html

def clear_sales_history():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("DELETE FROM order_items")
        cur.execute("DELETE FROM orders")
        con.commit()

def delete_order(order_id):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
        cur.execute("DELETE FROM orders WHERE order_id=?", (order_id,))
        con.commit()

def excel_download(df, file_name="sales_history.xlsx"):
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return output

# ---- APP STATE ----
@st.cache_data(ttl=1.0)
def cached_menu():
    return load_menu()

def reset_cart():
    st.session_state.cart = []

def add_to_cart(row, qty):
    for item in st.session_state.cart:
        if item["SKU"] == row["SKU"]:
            item["Qty"] += qty
            item["LineTotal"] = item["Qty"] * item["UnitPrice"]
            break
    else:
        st.session_state.cart.append({
            "SKU": row["SKU"],
            "Category": row["Category"],
            "Item": row["Item"],
            "UnitPrice": float(row["UnitPrice"]),
            "Qty": int(qty),
            "LineTotal": float(row["UnitPrice"]) * int(qty)
        })

def cart_dataframe():
    if not st.session_state.cart:
        return pd.DataFrame(columns=["SKU","Category","Item","UnitPrice","Qty","LineTotal"])
    df = pd.DataFrame(st.session_state.cart)
    df["LineTotal"] = (df["UnitPrice"] * df["Qty"]).round(2)
    return df

# ---- MAIN APP ----
def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🍔", layout="wide")
    st.title(APP_TITLE)
    st.caption("Offline POS (local browser app). Edit menu.csv to change items/prices.")

    init_db()

    # Top-right controls
    col_l, col_r = st.columns([5,2])
    with col_r:
        if st.button("🔄 Reload Menu"):
            cached_menu.clear()
            st.success("Menu reloaded.")
        if st.button("🧺 Clear Cart"):
            reset_cart()

    # Load menu
    menu = cached_menu()
    categories = ["All"] + sorted(menu["Category"].dropna().unique().tolist()) if not menu.empty else ["All"]

    # Sidebar: settings
    st.sidebar.header("Settings")
    cashier = st.sidebar.text_input("Cashier Name", value="Cashier")
    payment = st.sidebar.selectbox("Payment Method", ["Cash","Card","Online"], index=0)
    tax_rate = st.sidebar.number_input("Tax Rate (e.g., 0.13 = 13%)", min_value=0.0, max_value=1.0, value=0.13, step=0.01)
    service = st.sidebar.number_input("Service Charges (Rs.)", min_value=0.0, value=0.0, step=10.0)
    discount = st.sidebar.number_input("Discount (Rs.)", min_value=0.0, value=0.0, step=10.0)

    # Item picker
    st.subheader("Add Items")
    c1, c2, c3, c4 = st.columns([2,3,2,2])
    with c1:
        cat = st.selectbox("Category", categories)
    filtered = menu if cat=="All" else menu[menu["Category"]==cat]
    with c2:
        item_name = st.selectbox("Item", filtered["Item"].tolist() if not filtered.empty else [])
    row = filtered[filtered["Item"]==item_name].iloc[0] if (item_name and not filtered.empty) else None
    with c3:
        unit_price = st.number_input("Unit Price", value=float(row["UnitPrice"]) if row is not None else 0.0, step=10.0)
    with c4:
        qty = st.number_input("Qty", min_value=1, value=1, step=1)

    if st.button("➕ Add to Cart", disabled=(row is None)):
        if row is not None:
            row = row.copy()
            row["UnitPrice"] = unit_price
            add_to_cart(row, int(qty))
            st.success(f"Added {item_name} x{qty}")

    # Cart
    st.subheader("Cart")
    df_cart = cart_dataframe()
    st.dataframe(df_cart, use_container_width=True, hide_index=True)

    subtotal = float(df_cart["LineTotal"].sum()) if not df_cart.empty else 0.0
    tax = round(subtotal * tax_rate, 2)
    grand_total = max(0.0, round(subtotal + tax + service - discount, 2))

    t1, t2, t3, t4, t5 = st.columns(5)
    t1.metric("Subtotal", f"{subtotal:.0f} PKR")
    t2.metric("Tax", f"{tax:.0f} PKR")
    t3.metric("Service", f"{service:.0f} PKR")
    t4.metric("Discount", f"{discount:.0f} PKR")
    t5.metric("Grand Total", f"{grand_total:.0f} PKR")

    # Checkout
    st.divider()
    left, right = st.columns([3,2])
    with left:
        order_id = st.text_input("Order ID", value=datetime.now().strftime("SNG-%Y%m%d-%H%M%S"))
    with right:
        amount_tendered = st.number_input("Amount Tendered (Cash only)", min_value=0.0, value=0.0, step=50.0)
        change = amount_tendered - grand_total if payment == "Cash" else 0.0
        st.metric("Change", f"{max(0.0, change):.0f} PKR")

    if st.button("✅ Checkout & Save Order", disabled=df_cart.empty):
        if df_cart.empty:
            st.warning("Cart is empty.")
        else:
            cart_records = df_cart.to_dict(orient="records")
            save_order(order_id, cashier, payment, subtotal, tax, service, discount, grand_total, cart_records)
            html = make_receipt_html(order_id, cashier, payment, df_cart, subtotal, tax, service, discount, grand_total)
            receipt_path = os.path.join(RECEIPTS_DIR, f"receipt-{order_id}.html")
            with open(receipt_path, "w", encoding="utf-8") as f:
                f.write(html)
            st.success(f"Order {order_id} saved.")
            st.download_button("⬇️ Download Receipt", data=html, file_name=f"receipt-{order_id}.html", mime="text/html")
            reset_cart()

    # Sales viewer
    with st.expander("📒 View Recent Sales"):
        try:
            with sqlite3.connect(DB_PATH) as con:
                df_orders = pd.read_sql_query("SELECT * FROM orders ORDER BY timestamp DESC LIMIT 50", con)

            # Download as Excel
            st.download_button(
                "⬇️ Download Recent Sales (Excel)",
                data=excel_download(df_orders),
                file_name="recent_sales.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Delete All
            if st.button("🗑️ Clear All Sales (Irreversible)", key="clear_all_sales"):
                clear_sales_history()
                st.success("All sales history cleared!")
                st.experimental_rerun()

            # Delete individual orders safely
            if not df_orders.empty:
                for i, row in df_orders.iterrows():
                    cols = st.columns([7,1])
                    with cols[0]:
                        st.write(f"{row['order_id']} | {row['timestamp']} | {row['cashier']} | {row['total']}")
                    with cols[1]:
                        btn_key = f"del_{row['order_id']}"
                        if btn_key not in st.session_state:
                            st.session_state[btn_key] = False
                        if st.button("Delete", key=btn_key, help="Delete this order"):
                            delete_order(row['order_id'])
                            st.success(f"Deleted order {row['order_id']}")
                            st.experimental_rerun()

            st.dataframe(df_orders, use_container_width=True, hide_index=True)
        except Exception as e:
            st.info("No sales yet.")
            st.caption(str(e))

if "cart" not in st.session_state:
    reset_cart()

if __name__ == "__main__":
    init_db()
    main()
