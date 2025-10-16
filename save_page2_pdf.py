# ── Imports (ReportLab optional; FPDF always) ───────────────────────────────
import os
if os.environ.get("FLASK_RUN_FROM_CLI"):
    raise ImportError("Skip Kivy when running Flask")
from datetime import datetime
from kivy.utils import platform
from fpdf import FPDF

# Try to import ReportLab for desktop use
HAS_REPORTLAB = False
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    HAS_REPORTLAB = True
except Exception:
    HAS_REPORTLAB = False

# ── Storage helpers ─────────────────────────────────────────────────────────
def app_private_path():
    """Return app-private storage path cross-platform."""
    if platform == "android":
        try:
            from android.storage import app_storage_path
            return app_storage_path()
        except Exception:
            pass
    return os.getcwd()

def get_download_path(filename):
    """Best-effort ‘Downloads’ path (may require SAF on modern Android)."""
    if platform == "android":
        try:
            from android.storage import primary_external_storage_path
            download_folder = os.path.join(primary_external_storage_path(), "Download")
        except Exception:
            download_folder = os.path.expanduser("~")
    else:
        download_folder = os.path.join(os.path.expanduser("~"), "Downloads")

    os.makedirs(download_folder, exist_ok=True)
    return os.path.join(download_folder, filename)

def safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in name)

def float_or_0(x):
    try:
        return float(x)
    except Exception:
        return 0.0

# ── FPDF (Android-friendly) implementation ──────────────────────────────────
def _save_with_fpdf(client_name, client_mobile, ledger, out_path):
    pdf = FPDF()  # A4 portrait default
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Client: {client_name} ({client_mobile})", ln=1, align="L")
    pdf.ln(2)

    headers = ["Sr", "Date", "Detail", "Amount/hour", "Amount deposited", "Pending"]
    col_w = [15, 30, 80, 30, 35, 30]

    # Table header
    pdf.set_font("Helvetica", "B", 11)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, border=1, align="C")
    pdf.ln(8)

    # Rows
    pdf.set_font("Helvetica", "", 10)
    total_hour = 0.0
    total_deposit = 0.0

    for row in ledger:
        sr     = str(row[0]) if len(row) > 0 else ""
        date   = str(row[1]) if len(row) > 1 else ""
        detail = str(row[2]) if len(row) > 2 else ""
        hour   = float_or_0(row[3]) if len(row) > 3 else 0.0
        depo   = float_or_0(row[4]) if len(row) > 4 else 0.0
        pend   = depo - hour

        total_hour += hour
        total_deposit += depo

        cells = [sr, date, detail, f"{hour:g}", f"{depo:g}", f"{pend:g}"]

        # Wrap the Detail column with multi_cell
        for i, c in enumerate(cells):
            if i == 2:
                x, y = pdf.get_x(), pdf.get_y()
                pdf.multi_cell(col_w[i], 8, c, border=1)
                new_y = pdf.get_y()
                row_h = new_y - y
                pdf.set_xy(x + col_w[i], y)
                for j in range(i + 1, len(cells)):
                    pdf.cell(col_w[j], row_h, cells[j], border=1, align="C")
                pdf.ln(row_h)
                break
            else:
                pdf.cell(col_w[i], 8, c, border=1, align="C")
        else:
            pdf.ln(8)

    # Totals row
    pdf.set_font("Helvetica", "B", 11)
    pend_total = total_deposit - total_hour
    totals = ["", "", "Total", f"{total_hour:g}", f"{total_deposit:g}", f"{pend_total:g}"]
    for i, c in enumerate(totals):
        pdf.cell(col_w[i], 8, c, border=1, align="C")
    pdf.ln(10)

    pdf.output(out_path)

# ── ReportLab (desktop) implementation ──────────────────────────────────────
def _save_with_reportlab(client_name, client_mobile, ledger, out_path):
    doc = SimpleDocTemplate(out_path, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    header_text = f"Client: {client_name} ({client_mobile})"
    elements.append(Paragraph(header_text, styles['Heading2']))
    elements.append(Spacer(1, 12))

    data = [["Sr", "Date", "Detail", "Amount/hour", "Amount deposited", "Pending"]]

    total_hour = 0.0
    total_deposit = 0.0
    for row in ledger:
        sr     = str(row[0]) if len(row) > 0 else ""
        date   = str(row[1]) if len(row) > 1 else ""
        detail = str(row[2]) if len(row) > 2 else ""
        hour   = float_or_0(row[3]) if len(row) > 3 else 0.0
        depo   = float_or_0(row[4]) if len(row) > 4 else 0.0
        pend   = depo - hour
        data.append([sr, date, detail, f"{hour:g}", f"{depo:g}", f"{pend:g}"])
        total_hour += hour
        total_deposit += depo

    data.append(["", "", "Total", f"{total_hour:g}", f"{total_deposit:g}", f"{(total_deposit - total_hour):g}"])

    table = Table(data, colWidths=[40, 80, 200, 80, 100, 80])
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID',       (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,1), (-1,-2), colors.whitesmoke),
        ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
        ('FONTNAME',   (0,-1), (-1,-1), 'Helvetica-Bold'),
    ])
    table.setStyle(style)
    elements.append(table)

    doc.build(elements)

# ── Public API (KEEPING YOUR ORIGINAL NAME) ─────────────────────────────────
def save_page2_table_as_pdf(client_name, client_mobile, ledger, filename=None, save_to_downloads=False):
    """
    Save Page2 table data to PDF with unique filename and client header.

    - On Android (or when ReportLab isn't available), uses FPDF and saves to
      app-private storage by default (no storage permission needed).
    - On desktop with ReportLab installed, uses ReportLab (your original style).
    - Set save_to_downloads=True to attempt saving to the public Downloads folder.
      (On Android 10+ this may fail without SAF; prefer sharing the file instead.)
    """
    # Filename
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{client_name}_{client_mobile}_{timestamp}.pdf"
    filename = safe_filename(filename.replace(" ", "_"))

    # Output path
    if save_to_downloads:
        out_path = get_download_path(filename)
    else:
        out_dir = app_private_path()
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, filename)

    # Choose backend
    use_reportlab = (HAS_REPORTLAB and platform != "android")
    try:
        if use_reportlab:
            _save_with_reportlab(client_name, client_mobile, ledger, out_path)
        else:
            _save_with_fpdf(client_name, client_mobile, ledger, out_path)
        print(f"PDF saved successfully: {out_path}")
        return out_path
    except Exception as e:
        # Always print an actionable error (will be visible in logcat/console)
        print("PDF export failed:", e)
        raise
