import streamlit as st
import sqlite3
import pandas as pd
from io import StringIO

# ----------- Database Setup & Functions -------------
conn = sqlite3.connect("inventory.db", check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            bought INTEGER DEFAULT 0,
            sold INTEGER DEFAULT 0
        )
    ''')
    conn.commit()

def get_data(search_text=""):
    if search_text:
        query = "SELECT * FROM inventory WHERE name LIKE ? ORDER BY name"
        rows = c.execute(query, ('%' + search_text + '%',)).fetchall()
    else:
        query = "SELECT * FROM inventory ORDER BY name"
        rows = c.execute(query).fetchall()
    df = pd.DataFrame(rows, columns=['ID', 'Name', 'Bought', 'Sold'])
    df['Remaining'] = df['Bought'] - df['Sold']
    return df

def add_item(name, bought, sold):
    c.execute("INSERT INTO inventory (name, bought, sold) VALUES (?, ?, ?)", (name, bought, sold))
    conn.commit()

def update_item(row_id, name, bought, sold):
    c.execute("UPDATE inventory SET name=?, bought=?, sold=? WHERE id=?", (name, bought, sold, row_id))
    conn.commit()

def delete_item(row_id):
    c.execute("DELETE FROM inventory WHERE id=?", (row_id,))
    conn.commit()

# ------------- Streamlit UI -------------------

init_db()

st.set_page_config(page_title="Vendor Inventory Manager", layout="wide")

st.title("📦 Vendor Inventory Management")

# Sidebar for input and operations
with st.sidebar:
    st.header("Manage Inventory")

    operation = st.radio("Operation", ["Add New Item", "Edit Existing Item", "Delete Item"])

    if operation == "Add New Item":
        with st.form(key="add_form"):
            new_name = st.text_input("Item Name")
            new_bought = st.number_input("Bought Quantity", min_value=0, step=1)
            new_sold = st.number_input("Sold Quantity", min_value=0, step=1)
            submit_add = st.form_submit_button("Add Item")
            if submit_add:
                if not new_name.strip():
                    st.error("Item name cannot be empty.")
                elif new_sold > new_bought:
                    st.error("Sold quantity cannot be greater than bought quantity.")
                else:
                    add_item(new_name.strip(), int(new_bought), int(new_sold))
                    st.success(f"Added item '{new_name.strip()}' successfully.")

    else:
        df = get_data()
        if df.empty:
            st.info("No items found in inventory.")
        else:
            item_options = df['Name'] + " (ID: " + df['ID'].astype(str) + ")"
            selected = st.selectbox("Select Item", options=item_options)

            selected_id = int(selected.split("ID: ")[1].rstrip(")"))
            selected_row = df[df['ID'] == selected_id].iloc[0]

            if operation == "Edit Existing Item":
                with st.form(key="edit_form"):
                    edit_name = st.text_input("Item Name", value=selected_row['Name'])
                    edit_bought = st.number_input("Bought Quantity", min_value=0, step=1, value=selected_row['Bought'])
                    edit_sold = st.number_input("Sold Quantity", min_value=0, step=1, value=selected_row['Sold'])
                    submit_edit = st.form_submit_button("Update Item")
                    if submit_edit:
                        if not edit_name.strip():
                            st.error("Item name cannot be empty.")
                        elif edit_sold > edit_bought:
                            st.error("Sold quantity cannot be greater than bought quantity.")
                        else:
                            update_item(selected_id, edit_name.strip(), int(edit_bought), int(edit_sold))
                            st.success(f"Updated item '{edit_name.strip()}' successfully.")

            elif operation == "Delete Item":
                if st.button("Delete Item"):
                    delete_item(selected_id)
                    st.success(f"Deleted item '{selected_row['Name']}' successfully.")

# Main data table area
search_text = st.text_input("🔎 Search Inventory by Name", value="")

df_display = get_data(search_text)

if df_display.empty:
    st.warning("No inventory items found matching the search/filter.")
else:
    st.dataframe(df_display.rename(columns={"Bought": "Bought Qty", "Sold": "Sold Qty", "Remaining": "Quantity Remaining"}), use_container_width=True)

    # CSV Export
    csv_buffer = StringIO()
    df_display.to_csv(csv_buffer, index=False)
    st.download_button(
        label="📥 Download Inventory as CSV",
        data=csv_buffer.getvalue(),
        file_name="vendor_inventory.csv",
        mime="text/csv"
    )
