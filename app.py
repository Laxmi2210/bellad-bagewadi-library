from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import date

app = Flask(__name__)

app.secret_key = "bellad_bagewadi_library_secret"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "library.db")


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_database():

    conn = get_db()
    cursor = conn.cursor()

    # -----------------------------------------------------
    # MEMBERS TABLE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_no TEXT,
            member_type TEXT DEFAULT 'Student',
            name TEXT NOT NULL,
            mobile TEXT,
            aadhaar TEXT,
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
    # UPDATE OLD STUDENTS TABLE
    # =====================================================

    student_columns = cursor.execute(
        "PRAGMA table_info(students)"
    ).fetchall()

    student_column_names = [
        column["name"] for column in student_columns
    ]

    # Add registration number
    if "registration_no" not in student_column_names:

        cursor.execute("""
            ALTER TABLE students
            ADD COLUMN registration_no TEXT
        """)

    # Add member type
    if "member_type" not in student_column_names:

        cursor.execute("""
            ALTER TABLE students
            ADD COLUMN member_type TEXT DEFAULT 'Student'
        """)

    # Add Aadhaar
    if "aadhaar" not in student_column_names:

        cursor.execute("""
            ALTER TABLE students
            ADD COLUMN aadhaar TEXT
        """)

        # Copy old aadhar data if it exists
        if "aadhar" in student_column_names:

            cursor.execute("""
                UPDATE students
                SET aadhaar = aadhar
                WHERE aadhaar IS NULL
            """)

    # =====================================================
    # CREATE REGISTRATION NUMBERS FOR OLD RECORDS
    # =====================================================

    old_students = cursor.execute("""
        SELECT id
        FROM students
        WHERE registration_no IS NULL
           OR registration_no = ''
        ORDER BY id
    """).fetchall()

    for student in old_students:

        registration_no = f"LIB-{student['id']:04d}"

        cursor.execute("""
            UPDATE students
            SET registration_no = ?
            WHERE id = ?
        """, (
            registration_no,
            student["id"]
        ))

    # =====================================================
    # BOOK DATABASE UPDATE
    # =====================================================

    book_columns = cursor.execute(
        "PRAGMA table_info(books)"
    ).fetchall()

    book_column_names = [
        column["name"] for column in book_columns
    ]

    if "category" not in book_column_names:

        cursor.execute("""
            ALTER TABLE books
            ADD COLUMN category TEXT DEFAULT 'General'
        """)

    if "quantity" not in book_column_names:

        cursor.execute("""
            ALTER TABLE books
            ADD COLUMN quantity INTEGER DEFAULT 1
        """)

    conn.commit()
    conn.close()


# =========================================================
# LOGIN
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

        username = request.form.get(
            "username", ""
        ).strip()

        password = request.form.get(
            "password", ""
        ).strip()

        if username == "admin" and password == "1234":

            session["owner_logged_in"] = True

            return redirect(
                url_for("dashboard")
            )

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

    return redirect(
        url_for("home")
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    conn = get_db()

    total_members = conn.execute("""
        SELECT COUNT(*)
        FROM students
    """).fetchone()[0]

    student_count = conn.execute("""
        SELECT COUNT(*)
        FROM students
        WHERE member_type = 'Student'
    """).fetchone()[0]

    public_count = conn.execute("""
        SELECT COUNT(*)
        FROM students
        WHERE member_type = 'Public'
    """).fetchone()[0]

    book_count = conn.execute("""
        SELECT COUNT(*)
        FROM books
    """).fetchone()[0]

    issued_count = conn.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE status = 'Issued'
    """).fetchone()[0]

    returned_count = conn.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE status = 'Returned'
    """).fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        students=student_count,
        public=public_count,
        total_members=total_members,
        books=book_count,
        issued=issued_count,
        returned=returned_count
    )


# =========================================================
# REGISTRATION
# =========================================================

@app.route("/students")
def students():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    conn = get_db()

    student_list = conn.execute("""
        SELECT
            id,
            registration_no,
            member_type,
            name,
            mobile,
            aadhaar,
            address
        FROM students
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    success = session.pop(
        "success_message",
        None
    )

    return render_template(
        "students.html",
        students=student_list,
        success=success
    )


# =========================================================
# ADD REGISTRATION
# =========================================================

@app.route("/students/add", methods=["POST"])
def add_student():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    member_type = request.form.get(
        "member_type",
        "Student"
    ).strip()

    if member_type not in ["Student", "Public"]:

        member_type = "Student"

    name = request.form.get(
        "name", ""
    ).strip()

    mobile = request.form.get(
        "mobile", ""
    ).strip()

    aadhaar = request.form.get(
        "aadhaar", ""
    ).strip()

    address = request.form.get(
        "address", ""
    ).strip()

    if name == "":

        return redirect(
            url_for("students")
        )

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO students
        (
            member_type,
            name,
            mobile,
            aadhaar,
            address
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        member_type,
        name,
        mobile,
        aadhaar,
        address
    ))

    member_id = cursor.lastrowid

    registration_no = f"LIB-{member_id:04d}"

    conn.execute("""
        UPDATE students
        SET registration_no = ?
        WHERE id = ?
    """, (
        registration_no,
        member_id
    ))

    conn.commit()
    conn.close()

    session["success_message"] = (
        f"Registration Successful! "
        f"{member_type} Registration No: "
        f"{registration_no}"
    )

    return redirect(
        url_for("students")
    )


# =========================================================
# EDIT REGISTRATION
# =========================================================

@app.route(
    "/students/edit/<int:id>",
    methods=["GET", "POST"]
)
def edit_student(id):

    if not logged_in():

        return redirect(
            url_for("login")
        )

    conn = get_db()

    if request.method == "POST":

        member_type = request.form.get(
            "member_type",
            "Student"
        ).strip()

        if member_type not in ["Student", "Public"]:

            member_type = "Student"

        name = request.form.get(
            "name", ""
        ).strip()

        mobile = request.form.get(
            "mobile", ""
        ).strip()

        aadhaar = request.form.get(
            "aadhaar", ""
        ).strip()

        address = request.form.get(
            "address", ""
        ).strip()

        if name == "":

            conn.close()

            return redirect(
                url_for("students")
            )

        conn.execute("""
            UPDATE students
            SET
                member_type = ?,
                name = ?,
                mobile = ?,
                aadhaar = ?,
                address = ?
            WHERE id = ?
        """, (
            member_type,
            name,
            mobile,
            aadhaar,
            address,
            id
        ))

        conn.commit()
        conn.close()

        return redirect(
            url_for("students")
        )

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE id = ?
    """, (
        id,
    )).fetchone()

    conn.close()

    if student is None:

        return redirect(
            url_for("students")
        )

    return render_template(
        "edit_student.html",
        student=student
    )


# =========================================================
# DELETE REGISTRATION
# =========================================================

@app.route("/students/delete/<int:id>")
def delete_student(id):

    if not logged_in():

        return redirect(
            url_for("login")
        )

    conn = get_db()

    conn.execute("""
        DELETE FROM students
        WHERE id = ?
    """, (
        id,
    ))

    conn.commit()
    conn.close()

    return redirect(
        url_for("students")
    )


# =========================================================
# BOOKS
# =========================================================

@app.route("/books")
def books():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    search = request.args.get(
        "search", ""
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
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        )).fetchall()

    else:

        book_list = conn.execute("""
            SELECT *
            FROM books
            ORDER BY id DESC
        """).fetchall()

    conn.close()

    success = session.pop(
        "book_success",
        None
    )

    return render_template(
        "books.html",
        books=book_list,
        search=search,
        edit_book=None,
        success=success
    )


# =========================================================
# ADD BOOK
# =========================================================

@app.route("/books/add", methods=["POST"])
def add_book():

    if not logged_in():

        return redirect(
            url_for("books")
        )

    title = request.form.get(
        "title", ""
    ).strip()

    author = request.form.get(
        "author", ""
    ).strip()

    category = request.form.get(
        "category", ""
    ).strip()

    quantity = request.form.get(
        "quantity", "1"
    ).strip()

    if title == "":

        return redirect(
            url_for("books")
        )

    if category == "":

        category = "General"

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

    session["book_success"] = (
        f"Book Added Successfully! "
        f"Book: {title}"
    )

    return redirect(
        url_for("books")
    )


# =========================================================
# EDIT BOOK
# =========================================================

@app.route(
    "/books/edit/<int:id>",
    methods=["GET", "POST"]
)
def edit_book(id):

    if not logged_in():

        return redirect(
            url_for("books")
        )

    conn = get_db()

    if request.method == "POST":

        title = request.form.get(
            "title", ""
        ).strip()

        author = request.form.get(
            "author", ""
        ).strip()

        category = request.form.get(
            "category", ""
        ).strip()

        quantity = request.form.get(
            "quantity", "1"
        ).strip()

        if title == "":

            conn.close()

            return redirect(
                url_for("books")
            )

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

        return redirect(
            url_for("books")
        )

    book = conn.execute("""
        SELECT *
        FROM books
        WHERE id = ?
    """, (
        id,
    )).fetchone()

    if book is None:

        conn.close()

        return redirect(
            url_for("books")
        )

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
        edit_book=book,
        success=None
    )


# =========================================================
# DELETE BOOK
# =========================================================

@app.route("/books/delete/<int:id>")
def delete_book(id):

    if not logged_in():

        return redirect(
            url_for("books")
        )

    conn = get_db()

    conn.execute("""
        DELETE FROM books
        WHERE id = ?
    """, (
        id,
    ))

    conn.commit()
    conn.close()

    return redirect(
        url_for("books")
    )


# =========================================================
# ISSUE / RETURN
# =========================================================

@app.route("/issue-return")
def issue_return():

    if not logged_in():

        return redirect(
            url_for("login")
        )

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
        transactions=transaction_list,
        today=date.today().isoformat()
    )


# =========================================================
# ISSUE BOOK
# =========================================================

@app.route("/issue", methods=["POST"])
def issue_book():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    student_id = request.form.get(
        "student_id"
    )

    book_id = request.form.get(
        "book_id"
    )

    issue_date = request.form.get(
        "issue_date"
    )

    return_date = request.form.get(
        "return_date"
    )

    if not student_id or not book_id:

        return redirect(
            url_for("issue_return")
        )

    if not issue_date:

        issue_date = date.today().isoformat()

    if not return_date:

        return_date = issue_date

    conn = get_db()

    book = conn.execute("""
        SELECT quantity
        FROM books
        WHERE id = ?
    """, (
        book_id,
    )).fetchone()

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
        """, (
            book_id,
        ))

        conn.commit()

    conn.close()

    return redirect(
        url_for("issue_return")
    )


# =========================================================
# RETURN BOOK
# =========================================================

@app.route("/return/<int:id>")
def return_book(id):

    if not logged_in():

        return redirect(
            url_for("login")
        )

    conn = get_db()

    transaction = conn.execute("""
        SELECT book_id
        FROM transactions
        WHERE id = ?
          AND status = 'Issued'
    """, (
        id,
    )).fetchone()

    if transaction:

        conn.execute("""
            UPDATE transactions
            SET status = 'Returned'
            WHERE id = ?
        """, (
            id,
        ))

        conn.execute("""
            UPDATE books
            SET quantity = quantity + 1
            WHERE id = ?
        """, (
            transaction["book_id"],
        ))

        conn.commit()

    conn.close()

    return redirect(
        url_for("issue_return")
    )


# =========================================================
# HISTORY
# =========================================================

@app.route("/history")
def history():

    if not logged_in():

        return redirect(
            url_for("login")
        )

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
# START
# =========================================================

create_database()


if __name__ == "__main__":

    app.run(
        debug=True
    )