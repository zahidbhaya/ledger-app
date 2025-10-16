from flask import Flask, render_template, request, redirect, url_for, send_file
from datetime import datetime
import json
import os
from fpdf import FPDF

# ---------------- LedgerSystem Class ---------------- #
class LedgerSystem:
    DATA_FILE = "ledger_data.json"

    def __init__(self):
        self.clients = self.load_clients()

    # ---------------- CORE ---------------- #
    def register_client(self, name, client_id):
        if not name or not client_id:
            return "Name and ID required."
        if client_id in self.clients:
            return f"{client_id} already registered."
        self.clients[client_id] = {"name": name, "ledger": []}
        self.save_clients()
        return f"Registered {name} ({client_id})"

    def add_entry(self, client_id, date, detail, amount_hour, amount_deposit):
        if client_id not in self.clients:
            return "Client not found."
        try:
            amount_hour = float(amount_hour)
        except ValueError:
            amount_hour = 0.0
        try:
            amount_deposit = float(amount_deposit)
        except ValueError:
            amount_deposit = 0.0

        pending = amount_hour - amount_deposit
        sr = len(self.clients[client_id]["ledger"]) + 1
        entry = {
            "sr": sr,
            "date": date,
            "detail": detail,
            "amount_hour": amount_hour,
            "amount_deposit": amount_deposit,
            "pending": pending
        }
        self.clients[client_id]["ledger"].append(entry)
        self.save_clients()
        return "Entry added successfully."

    def get_all_clients(self):
        return [
            {"id": cid, "name": data["name"], "ledger": data["ledger"]}
            for cid, data in self.clients.items()
        ]

    def get_client_ledger(self, client_id):
        client = self.clients.get(client_id)
        if not client:
            return {"name": "Unknown Client", "ledger": []}
        total_hour = total_deposit = total_pending = 0.0
        for idx, e in enumerate(client["ledger"], start=1):
            e["sr"] = idx
            e["amount_hour"] = float(e.get("amount_hour", 0))
            e["amount_deposit"] = float(e.get("amount_deposit", 0))
            e["pending"] = e["amount_hour"] - e["amount_deposit"]
            total_hour += e["amount_hour"]
            total_deposit += e["amount_deposit"]
            total_pending += e["pending"]
        client["total_hour"] = total_hour
        client["total_deposit"] = total_deposit
        client["total_pending"] = total_pending
        return client

    def delete_entry(self, client_id, sr):
        client = self.clients.get(client_id)
        if not client:
            return False
        original_len = len(client["ledger"])
        client["ledger"] = [e for e in client["ledger"] if e["sr"] != sr]
        if len(client["ledger"]) == original_len:
            return False
        for idx, e in enumerate(client["ledger"], start=1):
            e["sr"] = idx
        self.save_clients()
        return True

    # ---------------- PDF EXPORT ---------------- #
    def export_clients_pdf(self):
        if not self.clients:
            return "No clients to export."
        filename = f"Clients_List_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Clients List", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(60, 8, "Client Name", 1, 0, "C")
        pdf.cell(60, 8, "Client ID", 1, 0, "C")
        pdf.ln()
        pdf.set_font("Arial", "", 12)
        for c in self.get_all_clients():
            pdf.cell(60, 8, c['name'], 1, 0, "C")
            pdf.cell(60, 8, c['id'], 1, 0, "C")
            pdf.ln()
        pdf.output(filename)
        return filename

    def export_ledger_pdf(self, client_id):
        client = self.get_client_ledger(client_id)
        if not client or not client["ledger"]:
            return "No data to export."
        filename = f"Ledger_{client_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Ledger - {client['name']} ({client_id})", ln=True, align="C")
        pdf.set_font("Arial", "B", 12)
        pdf.ln(5)
        headers = ["Sr", "Date", "Detail", "Amount/hr", "Deposit", "Pending"]
        col_width = 30
        for h in headers:
            pdf.cell(col_width, 8, h, 1, 0, "C")
        pdf.ln()
        pdf.set_font("Arial", "", 12)
        total_hour = total_deposit = total_pending = 0.0
        for e in client["ledger"]:
            pending = e["amount_hour"] - e["amount_deposit"]
            total_hour += e["amount_hour"]
            total_deposit += e["amount_deposit"]
            total_pending += pending
            pdf.cell(col_width, 8, str(e["sr"]), 1, 0, "C")
            pdf.cell(col_width, 8, e["date"], 1, 0, "C")
            pdf.cell(col_width, 8, e["detail"], 1, 0, "C")
            pdf.cell(col_width, 8, f"{e['amount_hour']:.2f}", 1, 0, "C")
            pdf.cell(col_width, 8, f"{e['amount_deposit']:.2f}", 1, 0, "C")
            if pending >= 0:
                pdf.cell(col_width, 8, f"-{pending:.2f}", 1, 0, "C")
            else:
                pdf.cell(col_width, 8, f"+{abs(pending):.2f}", 1, 0, "C")
            pdf.ln()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(col_width*3, 8, "Total", 1, 0, "C")
        pdf.cell(col_width, 8, f"{total_hour:.2f}", 1, 0, "C")
        pdf.cell(col_width, 8, f"{total_deposit:.2f}", 1, 0, "C")
        if total_pending >= 0:
            pdf.cell(col_width, 8, f"-{total_pending:.2f}", 1, 0, "C")
        else:
            pdf.cell(col_width, 8, f"+{abs(total_pending):.2f}", 1, 0, "C")
        pdf.ln()
        pdf.output(filename)
        return filename

    # ---------------- FILE HANDLING ---------------- #
    def save_clients(self):
        try:
            with open(self.DATA_FILE, "w") as f:
                json.dump(self.clients, f, indent=4)
        except Exception as e:
            print(f"⚠️ Error saving data: {e}")

    def load_clients(self):
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading data: {e}")
        return {}

# ---------------- Flask App ---------------- #
app = Flask(__name__)
ledger = LedgerSystem()

@app.route("/", methods=["GET"])
def index():
    search_query = request.args.get("search", "").strip()
    show_clients = request.args.get("show_clients") == "1"

    clients = ledger.get_all_clients()
    if search_query:
        clients = [
            c for c in clients
            if search_query.lower() in c["name"].lower() or search_query.lower() in c["id"].lower()
        ]
        show_clients = True

    return render_template("index.html", clients=clients, search_query=search_query, show_clients=show_clients)

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    client_id = request.form.get("mobile", "").strip()
    if client_id in ledger.clients:
        return f"<h3 style='color:red;'>Mobile/ID '{client_id}' already exists!</h3><a href='/'>Back</a>"
    if name and client_id:
        ledger.register_client(name, client_id)
    return redirect(url_for("index"))

@app.route("/ledger/<path:client_id>")
def show_ledger(client_id):
    client = ledger.get_client_ledger(client_id)
    return render_template("ledger.html", client=client, client_id=client_id)

@app.route("/add_entry/<path:client_id>", methods=["POST"])
def add_entry(client_id):
    date = request.form.get("date", "")
    detail = request.form.get("detail", "")
    amount_hour = request.form.get("amount_hour", "0")
    amount_deposit = request.form.get("amount_deposit", "0")
    ledger.add_entry(client_id, date, detail, amount_hour, amount_deposit)
    return redirect(url_for("show_ledger", client_id=client_id))

@app.route("/delete_entry/<path:client_id>/<int:sr>", methods=["POST"])
def delete_entry(client_id, sr):
    password = request.form.get("password", "")
    if password != "ZAB":
        return f"<h3 style='color:red;'>Incorrect password!</h3><a href='/ledger/{client_id}'>Back</a>"
    success = ledger.delete_entry(client_id, sr)
    return ("OK", 200) if success else ("Entry not found", 404)

@app.route("/download_clients_pdf")
def download_clients_pdf():
    filename = ledger.export_clients_pdf()
    return send_file(filename, as_attachment=True)

@app.route("/download_ledger_pdf/<path:client_id>")
def download_ledger_pdf(client_id):
    filename = ledger.export_ledger_pdf(client_id)
    return send_file(filename, as_attachment=True)

# ---------------- Run Flask ---------------- #
if __name__ == "__main__":
    app.run(debug=True)
