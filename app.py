from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import date

app = Flask(__name__)

app.secret_key = "bellad_bagewadi_library_secret"

DATABASE = "library.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# CREATE DATABASE
# =========================================================

def create_database():

    conn = get_db()

    cursor = conn.cursor()


    # -----------------------------------------------------
    # STUDENTS TABLE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            registration_no TEXT,

            name TEXT NOT NULL,

            mobile TEXT,

            aadhar TEXT,            

            address TEXT

        )
    """)

    # -----------------------------------------------------
    # BOOKS TABLE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            author TEXT,

            category TEXT DEFAULT 'General',

            quantity INTEGER DEFAULT 1

        )
    """)


    # -----------------------------------------------------
    # TRANSACTIONS TABLE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id INTEGER,

            book_id INTEGER,

            issue_date TEXT,

            return_date TEXT,

            status TEXT

        )
    """)


    # =====================================================
    # FIX OLD BOOK DATABASE
    # =====================================================

    # Get existing books table columns

    columns = cursor.execute(
        "PRAGMA table_info(books)"
    ).fetchall()

    column_names = [column["name"] for column in columns]


    # Add category if old database doesn't have it

    if "category" not in column_names:

        cursor.execute("""
            ALTER TABLE books
            ADD COLUMN category TEXT DEFAULT 'General'
        """)


    # Add quantity if old database doesn't have it

    if "quantity" not in column_names:

        cursor.execute("""
            ALTER TABLE books
            ADD COLUMN quantity INTEGER DEFAULT 1
        """)


    conn.commit()

    conn.close()


# =========================================================
# LOGIN CHECK
# =========================================================

def logged_in():

    return session.get("owner_logged_in", False)


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("home.html")


# =========================================================
# OWNER LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()

        password = request.form.get("password", "").strip()


        if username == "admin" and password == "1234":

            session["owner_logged_in"] = True


            return redirect(url_for("dashboard"))


        return render_template(
            "login.html",
            error="Invalid username or password!"
        )


    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not logged_in():

        return redirect(url_for("login"))


    conn = get_db()


    # Student count

    student_count = conn.execute("""
        SELECT COUNT(*)
        FROM students
    """).fetchone()[0]


    # Book count

    book_count = conn.execute("""
        SELECT COUNT(*)
        FROM books
    """).fetchone()[0]


    # Currently issued

    issued_count = conn.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE status = 'Issued'
    """).fetchone()[0]


    # Returned

    returned_count = conn.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE status = 'Returned'
    """).fetchone()[0]


    conn.close()


    return render_template(
        "dashboard.html",

        students=student_count,

        books=book_count,

        issued=issued_count,

        returned=returned_count
    )

# =========================================================
# STUDENTS
# =========================================================

@app.route("/students")
def students():

    if not logged_in():
        return redirect(url_for("login"))

    conn = get_db()

    student_list = conn.execute("""
        SELECT
            id,
            registration_no,
            name,
            mobile,
            aadhaar,
            address
        FROM students
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    success = session.pop("success_message", None)

    return render_template(
        "students.html",
        students=student_list,
        success=success
    )

# =========================================================
# ADD STUDENT
# =========================================================

@app.route("/students/add", methods=["POST"])
def add_student():

    if not logged_in():
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    mobile = request.form.get("mobile", "").strip()
    aadhaar = request.form.get("aadhaar", "").strip()
    address = request.form.get("address", "").strip()

    if name == "":
        return redirect(url_for("students"))

    conn = get_db()

    next_id = conn.execute(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM students"
    ).fetchone()[0]

    registration_no = f"LIB-{next_id:04d}"

    conn.execute("""
        INSERT INTO students
        (registration_no, name, mobile, aadhaar, address)
        VALUES (?, ?, ?, ?, ?)
    """, (
        registration_no,
        name,
        mobile,
        aadhaar,
        address
    ))

    conn.commit()
    conn.close()

    session["success_message"] = (
        f"Registration Successful! "
        f"Registration No: {registration_no}"
    )

    return redirect(url_for("students"))

# =========================================================
# EDIT STUDENT
# =========================================================

@app.route("/students/edit/<int:id>", methods=["GET", "POST"])
def edit_student(id):

    if not logged_in():

        return redirect(url_for("login"))


    conn = get_db()


    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()


        mobile = request.form.get(
            "mobile",
            ""
        ).strip()


        address = request.form.get(
            "address",
            ""
        ).strip()


        if name == "":

            conn.close()

            return redirect(url_for("students"))


        conn.execute("""
            UPDATE students

            SET
                name = ?,
                mobile = ?,
                address = ?

            WHERE id = ?
        """, (
            name,
            mobile,
            address,
            id
        ))


        conn.commit()

        conn.close()


        return redirect(url_for("students"))


    student = conn.execute("""
        SELECT *
        FROM students
        WHERE id = ?
    """, (id,)).fetchone()


    conn.close()


    if student is None:

        return redirect(url_for("students"))


    return render_template(
        "edit_student.html",
        student=student
    )


# =========================================================
# DELETE STUDENT
# =========================================================

@app.route("/students/delete/<int:id>")
def delete_student(id):

    if not logged_in():

        return redirect(url_for("login"))


    conn = get_db()


    conn.execute("""
        DELETE FROM students
        WHERE id = ?
    """, (id,))


    conn.commit()

    conn.close()


    return redirect(url_for("students"))


# =========================================================
# BOOKS
# =========================================================

@app.route("/books")
def books():

    if not logged_in():

        return redirect(url_for("login"))


    search = request.args.get(
        "search",
        ""
    ).strip()


    conn = get_db()


    if search:

        book_list = conn.execute("""
            SELECT *
            FROM books

            WHERE
                title LIKE ?
                OR author LIKE ?
                OR category LIKE ?

            ORDER BY id DESC
        """, (
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%"
        )).fetchall()


    else:

        book_list = conn.execute("""
            SELECT *
            FROM books
            ORDER BY id DESC
        """).fetchall()


    conn.close()


    return render_template(
        "books.html",

        books=book_list,

        search=search,

        edit_book=None
    )


# =========================================================
# ADD BOOK
# =========================================================

@app.route("/books/add", methods=["POST"])
def add_book():

    if not logged_in():

        return redirect(url_for("login"))


    title = request.form.get(
        "title",
        ""
    ).strip()


    author = request.form.get(
        "author",
        ""
    ).strip()


    category = request.form.get(
        "category",
        ""
    ).strip()


    quantity = request.form.get(
        "quantity",
        "1"
    ).strip()


    if title == "":

        return redirect(url_for("books"))


    if category == "":

        category = "General"


    # Convert quantity to number

    try:

        quantity = int(quantity)

        if quantity < 1:

            quantity = 1

    except ValueError:

        quantity = 1


    conn = get_db()


    conn.execute("""
        INSERT INTO books
        (
            title,
            author,
            category,
            quantity
        )

        VALUES (?, ?, ?, ?)
    """, (
        title,
        author,
        category,
        quantity
    ))


    conn.commit()

    conn.close()


    return redirect(url_for("books"))


# =========================================================
# EDIT BOOK
# =========================================================

@app.route("/books/edit/<int:id>", methods=["GET", "POST"])
def edit_book(id):

    if not logged_in():

        return redirect(url_for("login"))


    conn = get_db()


    # -----------------------------------------------------
    # UPDATE BOOK
    # -----------------------------------------------------

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()


        author = request.form.get(
            "author",
            ""
        ).strip()


        category = request.form.get(
            "category",
            ""
        ).strip()


        quantity = request.form.get(
            "quantity",
            "1"
        ).strip()


        if title == "":

            conn.close()

            return redirect(url_for("books"))


        if category == "":

            category = "General"


        try:

            quantity = int(quantity)

            if quantity < 0:

                quantity = 0

        except ValueError:

            quantity = 0


        conn.execute("""
            UPDATE books

            SET
                title = ?,
                author = ?,
                category = ?,
                quantity = ?

            WHERE id = ?
        """, (
            title,
            author,
            category,
            quantity,
            id
        ))


        conn.commit()

        conn.close()


        return redirect(url_for("books"))


    # -----------------------------------------------------
    # GET BOOK
    # -----------------------------------------------------

    book = conn.execute("""
        SELECT *
        FROM books
        WHERE id = ?
    """, (id,)).fetchone()


    if book is None:

        conn.close()

        return redirect(url_for("books"))


    book_list = conn.execute("""
        SELECT *
        FROM books
        ORDER BY id DESC
    """).fetchall()


    conn.close()


    return render_template(
        "books.html",

        books=book_list,

        search="",

        edit_book=book
    )


# =========================================================
# DELETE BOOK
# =========================================================

@app.route("/books/delete/<int:id>")
def delete_book(id):

    if not logged_in():

        return redirect(url_for("login"))


    conn = get_db()


    conn.execute("""
        DELETE FROM books
        WHERE id = ?
    """, (id,))


    conn.commit()

    conn.close()


    return redirect(url_for("books"))


# =========================================================
# ISSUE / RETURN
# =========================================================

@app.route("/issue-return")
def issue_return():

    if not logged_in():
        return redirect(url_for("login"))

    conn = get_db()

    student_list = conn.execute("""
        SELECT *
        FROM students
        ORDER BY name
    """).fetchall()

    book_list = conn.execute("""
        SELECT *
        FROM books
        WHERE quantity > 0
        ORDER BY title
    """).fetchall()

    transaction_list = conn.execute("""
        SELECT
            transactions.id,
            students.name AS student_name,
            books.title AS book_title,
            transactions.issue_date,
            transactions.return_date,
            transactions.status
        FROM transactions
        JOIN students
            ON transactions.student_id = students.id
        JOIN books
            ON transactions.book_id = books.id
        ORDER BY transactions.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "issue_return.html",
        students=student_list,
        books=book_list,
        transactions=transaction_list
    )


# =========================================================
# ISSUE BOOK
# =========================================================

@app.route("/issue", methods=["POST"])
def issue_book():

    if not logged_in():
        return redirect(url_for("login"))

    student_id = request.form.get("student_id")
    book_id = request.form.get("book_id")
    issue_date = request.form.get("issue_date")
    return_date = request.form.get("return_date")

    if not student_id or not book_id:
        return redirect(url_for("issue_return"))

    if not issue_date:
        issue_date = date.today().isoformat()

    if not return_date:
        return_date = issue_date

    conn = get_db()

    book = conn.execute("""
        SELECT quantity
        FROM books
        WHERE id = ?
    """, (book_id,)).fetchone()

    if book and book["quantity"] > 0:

        conn.execute("""
            INSERT INTO transactions
            (
                student_id,
                book_id,
                issue_date,
                return_date,
                status
            )
            VALUES (?, ?, ?, ?, 'Issued')
        """, (
            student_id,
            book_id,
            issue_date,
            return_date
        ))

        conn.execute("""
            UPDATE books
            SET quantity = quantity - 1
            WHERE id = ?
        """, (book_id,))

        conn.commit()

    conn.close()

    return redirect(url_for("issue_return"))


# =========================================================
# RETURN BOOK
# =========================================================

@app.route("/return/<int:id>")
def return_book(id):

    if not logged_in():
        return redirect(url_for("login"))

    conn = get_db()

    transaction = conn.execute("""
        SELECT book_id
        FROM transactions
        WHERE id = ?
        AND status = 'Issued'
    """, (id,)).fetchone()

    if transaction:

        # Keep the original expected return date.
        # Only change the status when the book is actually returned.

        conn.execute("""
            UPDATE transactions
            SET status = 'Returned'
            WHERE id = ?
        """, (id,))

        conn.execute("""
            UPDATE books
            SET quantity = quantity + 1
            WHERE id = ?
        """, (transaction["book_id"],))

        conn.commit()

    conn.close()

    return redirect(url_for("issue_return"))



# =========================================================
# TRANSACTION HISTORY
# =========================================================

@app.route("/history")
def history():

    if not logged_in():

        return redirect(url_for("login"))


    conn = get_db()


    transaction_list = conn.execute("""
        SELECT

            transactions.id,

            students.name AS student_name,

            books.title AS book_title,

            transactions.issue_date,

            transactions.return_date,

            transactions.status

        FROM transactions

        JOIN students
        ON transactions.student_id = students.id

        JOIN books
        ON transactions.book_id = books.id

        ORDER BY transactions.id DESC

    """).fetchall()


    conn.close()


    return render_template(

        "history.html",

        transactions=transaction_list

    )


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

   app.run(debug=True)