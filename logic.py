from datetime import datetime
import json
import os
from fpdf import FPDF  # Make sure fpdf is installed via pip

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
        return self.clients.get(client_id)

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
            # Ensure float conversion
            amount_hour = float(e["amount_hour"])
            amount_deposit = float(e["amount_deposit"])
            pending = amount_hour - amount_deposit
            total_hour += amount_hour
            total_deposit += amount_deposit
            total_pending += pending
            pdf.cell(col_width, 8, str(e["sr"]), 1, 0, "C")
            pdf.cell(col_width, 8, e["date"], 1, 0, "C")
            pdf.cell(col_width, 8, e["detail"], 1, 0, "C")
            pdf.cell(col_width, 8, f"{amount_hour:.2f}", 1, 0, "C")
            pdf.cell(col_width, 8, f"{amount_deposit:.2f}", 1, 0, "C")
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
                    data = json.load(f)
                    # Convert ledger fields to floats for calculations
                    for client in data.values():
                        for entry in client.get("ledger", []):
                            entry["amount_hour"] = float(entry["amount_hour"])
                            entry["amount_deposit"] = float(entry["amount_deposit"])
                            entry["pending"] = float(entry["amount_hour"]) - float(entry["amount_deposit"])
                    return data
            except Exception as e:
                print(f"⚠️ Error loading data: {e}")
        return {}
