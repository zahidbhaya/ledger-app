import os
import sys

from fpdf import FPDF

# Determine platform
def get_platform():
    if sys.platform.startswith("linux"):
        return "linux"
    elif sys.platform.startswith("win"):
        return "windows"
    elif sys.platform.startswith("darwin"):
        return "macos"
    else:
        return "unknown"

platform = get_platform()

# Try to import ReportLab (desktop only)
HAS_REPORTLAB = False
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    HAS_REPORTLAB = True
except Exception:
    HAS_REPORTLAB = False

# --- Storage helpers ---
def app_private_path():
    """Return app-private storage path cross-platform."""
    return os.getcwd()

def get_download_path(filename):
    """Best-effort Downloads folder (cross-platform)."""
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
    """Sanitize filename for filesystem safety."""
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in name)

# --- FPDF implementation ---
def _save_with_fpdf(clients, out_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Clients List", ln=1, align="C")
    pdf.ln(5)

    # Table headers
    headers = ["Sr", "Name", "Mobile"]
    col_w = [15, 80, 60]

    pdf.set_font("Helvetica", "B", 11)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, border=1, align="C")
    pdf.ln(8)

    # Table rows
    pdf.set_font("Helvetica", "", 10)
    for idx, (mobile, data_client) in enumerate(clients.items(), 1):
        row = [str(idx), data_client.get("name", ""), mobile]
        for i, c in enumerate(row):
            pdf.cell(col_w[i], 8, str(c), border=1, align="C")
        pdf.ln(8)

    pdf.output(out_path)

# --- ReportLab implementation ---
def _save_with_reportlab(clients, out_path):
    doc = SimpleDocTemplate(out_path, pagesize=A4)
    elements = []

    data = [["Sr", "Name", "Mobile"]]
    for i, (mobile, data_client) in enumerate(clients.items(), 1):
        data.append([str(i), data_client.get("name", ""), mobile])

    table = Table(data, colWidths=[40, 200, 100])
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ])
    table.setStyle(style)
    elements.append(table)

    doc.build(elements)

# --- Public API ---
def save_clients_as_pdf(clients, filename="Clients_List.pdf", save_to_downloads=False):
    """
    Save the list of clients to PDF.

    :param clients: Dict of clients {mobile: {'name': name, 'ledger': []}, ...}
    :param filename: Output PDF filename
    :param save_to_downloads: If True, save to public Downloads folder
    :return: Full path of saved PDF
    """
    filename = safe_filename(filename)
    if save_to_downloads:
        out_path = get_download_path(filename)
    else:
        out_dir = app_private_path()
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, filename)

    try:
        if HAS_REPORTLAB and platform != "android":
            _save_with_reportlab(clients, out_path)
        else:
            _save_with_fpdf(clients, out_path)
        print(f"PDF saved successfully: {out_path}")
        return out_path
    except Exception as e:
        print("PDF export failed:", e)
        raise
