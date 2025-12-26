import sqlite3
from datetime import datetime
import streamlit as st
import pandas as pd
import os

DB_FILE = "expenses.db"

DEFAULT_CATEGORIES = [
    "مرتبات",
    "مدفوعات",
    "مشتريات",
    "زباله",
    "كهرباء",
    "انترنت",
    "باقه موبيل",
    "صيانه",
    "ايجار",
    "فيزا",
    "كاش",
    "مصروفات خاصة"
]

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY,
                    date TEXT NOT NULL,
                    category_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (category_id) REFERENCES categories (id)
                )''')
    # Insert default categories if not exist
    for cat in DEFAULT_CATEGORIES:
        c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat,))
    conn.commit()
    conn.close()

def load_categories():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name FROM categories ORDER BY id")
    categories = [row[0] for row in c.fetchall()]
    conn.close()
    return categories

init_db()
CATEGORIES = load_categories()

def get_all_expenses():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT e.id, e.date, c.name, e.amount, e.notes FROM expenses e JOIN categories c ON e.category_id = c.id ORDER BY e.date")
    expenses = c.fetchall()
    conn.close()
    return expenses

def get_totals_by_category():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT c.name, SUM(e.amount) FROM expenses e JOIN categories c ON e.category_id = c.id GROUP BY c.id")
    totals = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return totals

def get_monthly_totals():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT strftime('%Y-%m', e.date) as month_year, SUM(e.amount) FROM expenses e GROUP BY month_year")
    monthly_totals = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return monthly_totals

def get_detailed_monthly_expenses():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT strftime('%Y-%m', e.date) as month_year, e.date, c.name, e.amount, e.notes FROM expenses e JOIN categories c ON e.category_id = c.id ORDER BY month_year, e.date")
    expenses = c.fetchall()
    monthly_expenses = {}
    for row in expenses:
        month_year = row[0]
        if month_year not in monthly_expenses:
            monthly_expenses[month_year] = []
        monthly_expenses[month_year].append({
            "التاريخ": row[1],
            "القسم": row[2],
            "المبلغ": row[3],
            "ملاحظات": row[4]
        })
    conn.close()
    return monthly_expenses

def is_category_used(category_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM expenses WHERE category_id = (SELECT id FROM categories WHERE name = ?)", (category_name,))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

def get_daily_expenses(date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT e.date, c.name, e.amount, e.notes FROM expenses e JOIN categories c ON e.category_id = c.id WHERE e.date = ?", (date,))
    expenses = c.fetchall()
    conn.close()
    return expenses

def get_monthly_expenses(month_year):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT e.date, c.name, e.amount, e.notes FROM expenses e JOIN categories c ON e.category_id = c.id WHERE strftime('%Y-%m', e.date) = ?", (month_year,))
    expenses = c.fetchall()
    conn.close()
    return expenses

def get_visa_cash_expenses(month_year):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT e.date, c.name, e.amount, e.notes FROM expenses e JOIN categories c ON e.category_id = c.id WHERE strftime('%Y-%m', e.date) = ? AND c.name IN ('فيزا', 'كاش', 'مصروفات خاصة', 'مصروفات')", (month_year,))
    expenses = c.fetchall()
    conn.close()
    return expenses

def delete_expense_by_id(expense_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

def get_category_id(category_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def save_categories():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for cat in CATEGORIES:
        c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat,))
    conn.commit()
    conn.close()

def migrate_from_csv():
    if not os.path.exists("expenses.csv"):
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    with open("expenses.csv", "r", encoding="utf-8") as f:
        import csv
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            date, category, amount, notes = row
            # Get or create category_id
            c.execute("SELECT id FROM categories WHERE name = ?", (category,))
            result = c.fetchone()
            if result:
                category_id = result[0]
            else:
                c.execute("INSERT INTO categories (name) VALUES (?)", (category,))
                category_id = c.lastrowid
                CATEGORIES.append(category)  # Update global list
            # Insert expense
            c.execute("INSERT INTO expenses (date, category_id, amount, notes) VALUES (?, ?, ?, ?)", (date, category_id, float(amount), notes))
    conn.commit()
    conn.close()

def add_expense_streamlit():
    st.header("إضافة مصروف")
    category = st.selectbox("القسم", CATEGORIES)
    amount = st.number_input("المبلغ", min_value=0.0, step=0.01)
    date = st.date_input("التاريخ")
    notes = st.text_input("ملاحظات")
    if st.button("إضافة"):
        if amount <= 0:
            st.error("المبلغ يجب أن يكون أكبر من صفر")
            return
        category_id = get_category_id(category)
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO expenses (date, category_id, amount, notes) VALUES (?, ?, ?, ?)", (date.strftime("%Y-%m-%d"), category_id, amount, notes))
        conn.commit()
        conn.close()
        st.success("تم إضافة المصروف بنجاح")
        st.rerun()

def show_expenses_streamlit():
    st.header("عرض كل المصروفات")
    expenses = get_all_expenses()
    if expenses:
        df = pd.DataFrame(expenses, columns=["ID", "التاريخ", "القسم", "المبلغ", "ملاحظات"])
        st.dataframe(df)
        selected_id = st.selectbox("اختر ID للحذف", [exp[0] for exp in expenses])
        if st.button("حذف المصروف المحدد"):
            delete_expense_by_id(selected_id)
            st.success("تم حذف المصروف بنجاح")
            st.rerun()
    else:
        st.write("لا توجد مصروفات بعد")

def total_by_category_streamlit():
    st.header("إجمالي المصروفات حسب القسم")
    totals = get_totals_by_category()
    if totals:
        df = pd.DataFrame(list(totals.items()), columns=["القسم", "المجموع"])
        st.dataframe(df)
    else:
        st.write("لا توجد مصروفات بعد")

def monthly_reports_streamlit():
    st.header("تقارير شهرية")
    monthly_totals = get_monthly_totals()
    if monthly_totals:
        df = pd.DataFrame(list(monthly_totals.items()), columns=["الشهر", "المجموع"])
        st.dataframe(df)
    else:
        st.write("لا توجد مصروفات بعد")

def detailed_monthly_reports_streamlit():
    st.header("تقارير شهرية مفصلة")
    monthly_expenses = get_detailed_monthly_expenses()
    if monthly_expenses:
        for month, expenses in monthly_expenses.items():
            st.subheader(f"الشهر: {month}")
            df = pd.DataFrame(expenses)
            st.dataframe(df)
            total = sum(float(exp['المبلغ']) for exp in expenses)
            st.write(f"الإجمالي: {total:.2f} جنيه")
    else:
        st.write("لا توجد مصروفات بعد")

def add_category_streamlit():
    st.header("إدارة الأقسام")
    new_cat = st.text_input("اسم القسم الجديد")
    if st.button("إضافة قسم"):
        if new_cat and new_cat not in CATEGORIES:
            CATEGORIES.append(new_cat)
            save_categories()
            st.success(f"تم إضافة القسم: {new_cat}")
            st.rerun()
        elif new_cat in CATEGORIES:
            st.error("القسم موجود بالفعل")
        else:
            st.error("أدخل اسم القسم")
    st.subheader("حذف قسم موجود")
    cat_to_delete = st.selectbox("اختر القسم للحذف", CATEGORIES)
    if st.button("حذف"):
        if cat_to_delete in DEFAULT_CATEGORIES:
            st.error("لا يمكن حذف الأقسام الافتراضية")
            return
        if is_category_used(cat_to_delete):
            st.error("لا يمكن حذف القسم لأنه مستخدم في مصروفات")
            return
        CATEGORIES.remove(cat_to_delete)
        save_categories()
        st.success(f"تم حذف القسم: {cat_to_delete}")
        st.rerun()

def daily_closure_streamlit():
    st.header("إغلاق اليوم")
    date = st.date_input("التاريخ")
    visa = st.number_input("مبلغ الفيزا", min_value=0.0, step=0.01)
    cash = st.number_input("مبلغ الكاش", min_value=0.0, step=0.01)
    expenses = st.number_input("مبلغ المصروفات", min_value=0.0, step=0.01)
    notes = st.text_input("ملاحظات")
    if st.button("إدخال"):
        if visa < 0 or cash < 0 or expenses < 0:
            st.error("المبالغ يجب أن تكون موجبة أو صفر")
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        if visa > 0:
            visa_id = get_category_id("فيزا")
            c.execute("INSERT INTO expenses (date, category_id, amount, notes) VALUES (?, ?, ?, ?)", (date.strftime("%Y-%m-%d"), visa_id, visa, notes))
        if cash > 0:
            cash_id = get_category_id("كاش")
            c.execute("INSERT INTO expenses (date, category_id, amount, notes) VALUES (?, ?, ?, ?)", (date.strftime("%Y-%m-%d"), cash_id, cash, notes))
        if expenses > 0:
            expenses_id = get_category_id("مصروفات")
            c.execute("INSERT INTO expenses (date, category_id, amount, notes) VALUES (?, ?, ?, ?)", (date.strftime("%Y-%m-%d"), expenses_id, expenses, notes))
        conn.commit()
        conn.close()
        st.success("تم حفظ الإدخال بنجاح")
        st.rerun()

def main():
    st.title("إدارة المصروفات Salt&Crunch")
    st.sidebar.title("القائمة")
    page = st.sidebar.selectbox("اختر الصفحة", ["إضافة مصروف", "عرض كل المصروفات", "إجمالي المصروفات حسب القسم", "تقارير شهرية", "تقارير شهرية مفصلة", "إضافة قسم", "إغلاق اليوم"])
    if page == "إضافة مصروف":
        add_expense_streamlit()
    elif page == "عرض كل المصروفات":
        show_expenses_streamlit()
    elif page == "إجمالي المصروفات حسب القسم":
        total_by_category_streamlit()
    elif page == "تقارير شهرية":
        monthly_reports_streamlit()
    elif page == "تقارير شهرية مفصلة":
        detailed_monthly_reports_streamlit()
    elif page == "إضافة قسم":
        add_category_streamlit()
    elif page == "إغلاق اليوم":
        daily_closure_streamlit()

if __name__ == "__main__":
    init_db()
    migrate_from_csv()
    main()
