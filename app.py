from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
import logic
import os
import os
# ...
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "replace-this-with-a-strong-secret-key")

# Initialize DB
logic.init_db()

# ---------- Auth ----------
@app.route("/", methods=["GET"])
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html", view="auth")


@app.post("/signup")
def signup():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")

    if not all([name, phone, email, password, confirm]):
        flash("All fields are required.", "error")
        return redirect(url_for("home"))
    if password != confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for("home"))

    try:
        logic.create_user(
            name=name,
            phone=phone,
            email=email,
            password_hash=generate_password_hash(password),
            auto_verify=True,   # no OTP
        )
        flash("Sign up successful! Please log in.", "success")
        return redirect(url_for("home"))
    except logic.UniqueConstraintError as e:
        flash(str(e), "error")
        return redirect(url_for("home"))


@app.post("/login")
def login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = logic.get_user_by_email(email)
    if not user or not check_password_hash(user.password_hash, password):
        flash("Invalid email or password.", "error")
        return redirect(url_for("home"))
    session["user_id"] = user.id
    session["user_name"] = user.name
    flash(f"Welcome back, {user.name}!", "success")
    return redirect(url_for("dashboard"))


@app.get("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("home"))


# ---------- Dashboard (Page 2) ----------
@app.get("/dashboard")
def dashboard():
    logic.require_auth(session)
    return render_template("index.html", view="dashboard", user_name=session.get("user_name"))


@app.post("/clients/register")
def register_client():
    logic.require_auth(session)
    name = request.form.get("client_name", "").strip()
    mobile = request.form.get("client_mobile", "").strip()
    if not name or not mobile:
        flash("Client name and unique mobile are required.", "error")
        return redirect(url_for("dashboard"))
    try:
        logic.create_client(owner_id=session["user_id"], name=name, mobile=mobile)
        flash("Client registered.", "success")
    except logic.UniqueConstraintError:
        flash("Mobile number is already registered", "error")
    return redirect(url_for("dashboard"))


@app.get("/clients/search")
def search_clients():
    logic.require_auth(session)
    q = request.args.get("q", "").strip()
    results = logic.search_clients(owner_id=session["user_id"], query=q)
    return render_template("index.html", view="search", query=q, results=results)


@app.get("/clients")
def list_clients():
    logic.require_auth(session)
    clients = logic.get_all_clients(owner_id=session["user_id"])
    return render_template("index.html", view="list", clients=clients)


@app.get("/clients/pdf")
def clients_pdf():
    logic.require_auth(session)
    clients = logic.get_all_clients(owner_id=session["user_id"])
    pdf_bytes = logic.render_clients_pdf(clients)
    return send_file(BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True, download_name="clients.pdf")


# ---- Client edit/delete ----
@app.get("/clients/<int:client_id>/edit")
def edit_client_view(client_id):
    logic.require_auth(session)
    client = logic.get_client(session["user_id"], client_id)
    if not client:
        flash("Client not found.", "error")
        return redirect(url_for("list_clients"))
    return render_template("index.html", view="client_edit", client=client)


@app.post("/clients/<int:client_id>/edit")
def edit_client(client_id):
    logic.require_auth(session)
    name = request.form.get("client_name", "")
    mobile = request.form.get("client_mobile", "")
    try:
        logic.update_client(session["user_id"], client_id, name, mobile)
        flash("Client updated.", "success")
    except logic.UniqueConstraintError:
        flash("Mobile number is already registered", "error")
    return redirect(url_for("list_clients"))


@app.post("/clients/<int:client_id>/delete")
def delete_client(client_id):
    logic.require_auth(session)
    ok = logic.delete_client(session["user_id"], client_id)
    flash("Client deleted." if ok else "Client not found.", "success" if ok else "error")
    return redirect(url_for("list_clients"))


# ---------- Ledger (Page 3) ----------
@app.get("/ledger/<int:client_id>")
def ledger(client_id):
    logic.require_auth(session)
    client = logic.get_client(session["user_id"], client_id)
    if not client:
        flash("Client not found.", "error")
        return redirect(url_for("dashboard"))
    entries = logic.get_ledger_entries(client_id)
    totals = logic.compute_totals(entries)
    return render_template("ledger.html", client=client, entries=entries, totals=totals)


@app.get("/ledger/<int:client_id>/entry/<int:entry_id>/edit")
def edit_entry_view(client_id, entry_id):
    logic.require_auth(session)
    client = logic.get_client(session["user_id"], client_id)
    if not client:
        flash("Client not found.", "error")
        return redirect(url_for("dashboard"))

    edit_entry = logic.get_ledger_entry(entry_id)
    # Ownership & client match check
    if not edit_entry or edit_entry.client_id != client_id or client.owner_id != session["user_id"]:
        flash("Entry not found.", "error")
        return redirect(url_for("ledger", client_id=client_id))

    entries = logic.get_ledger_entries(client_id)
    totals = logic.compute_totals(entries)
    return render_template("ledger.html", client=client, entries=entries, totals=totals, edit_entry=edit_entry)


@app.get("/ledger/<int:client_id>/pdf")
def ledger_pdf(client_id):
    logic.require_auth(session)
    client = logic.get_client(session["user_id"], client_id)
    if not client:
        flash("Client not found.", "error")
        return redirect(url_for("dashboard"))
    entries = logic.get_ledger_entries(client_id)
    totals = logic.compute_totals(entries)
    pdf_bytes = logic.render_ledger_pdf(client, entries, totals)
    return send_file(BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True, download_name=f"ledger_{client.name}.pdf")


@app.post("/ledger/<int:client_id>/add")
def add_ledger_row(client_id):
    logic.require_auth(session)
    client = logic.get_client(session["user_id"], client_id)
    if not client:
        flash("Client not found.", "error")
        return redirect(url_for("dashboard"))
    details = request.form.get("details", "").strip()
    date_str = request.form.get("date", "").strip()
    amt_per_hour = request.form.get("amount_per_hour", "0").strip()
    deposit = request.form.get("deposit", "0").strip()
    try:
        logic.add_ledger_entry(client_id, date_str, details, amt_per_hour, deposit)
        flash("Entry added.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("ledger", client_id=client_id))


@app.post("/ledger/<int:client_id>/entry/<int:entry_id>/edit")
def edit_entry(client_id, entry_id):
    logic.require_auth(session)
    details = request.form.get("details", "").strip()
    date_str = request.form.get("date", "").strip()
    amt_per_hour = request.form.get("amount_per_hour", "0").strip()
    deposit = request.form.get("deposit", "0").strip()
    current_password = request.form.get("current_password", "")

    user = logic.get_user_by_id(session["user_id"])
    if not user or not current_password or not check_password_hash(user.password_hash, current_password):
        flash("Incorrect account password.", "error")
        return redirect(url_for("ledger", client_id=client_id))

    # Ownership & client match check BEFORE update
    entry = logic.get_ledger_entry(entry_id)
    client = logic.get_client(session["user_id"], client_id)
    if not entry or not client or entry.client_id != client_id or client.owner_id != session["user_id"]:
        flash("Entry not found.", "error")
        return redirect(url_for("ledger", client_id=client_id))

    try:
        logic.update_ledger_entry(entry_id, date_str, details, amt_per_hour, deposit)
        flash("Entry updated.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("ledger", client_id=client_id))


@app.post("/ledger/<int:client_id>/entry/<int:entry_id>/delete")
def delete_entry(client_id, entry_id):
    logic.require_auth(session)
    current_password = request.form.get("current_password", "")

    user = logic.get_user_by_id(session["user_id"])
    if not user or not current_password or not check_password_hash(user.password_hash, current_password):
        flash("Incorrect account password.", "error")
        return redirect(url_for("ledger", client_id=client_id))

    # Ownership & client match check BEFORE delete
    entry = logic.get_ledger_entry(entry_id)
    client = logic.get_client(session["user_id"], client_id)
    if not entry or not client or entry.client_id != client_id or client.owner_id != session["user_id"]:
        flash("Entry not found.", "error")
        return redirect(url_for("ledger", client_id=client_id))

    ok = logic.delete_ledger_entry(entry_id)
    flash("Entry deleted." if ok else "Entry not found.", "success" if ok else "error")
    return redirect(url_for("ledger", client_id=client_id))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
