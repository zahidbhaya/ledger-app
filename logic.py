# at the very top
import os
# ...
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///ledger.db")
from typing import List, Tuple, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import date as _date

# -------------------- DB setup --------------------
DATABASE_URL = "sqlite:///ledger.db"
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# -------------------- Models ----------------------
class UniqueConstraintError(Exception):
    ...


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    email_verified = Column(Boolean, default=True)  # default True so no OTP needed
    otp_code = Column(String, default="")
    otp_expires = Column(Integer, default=0)

    clients = relationship("Client", back_populates="owner", cascade="all, delete-orphan")


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    mobile = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="clients")
    ledger_entries = relationship("LedgerEntry", back_populates="client", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("owner_id", "mobile", name="uq_owner_mobile"),
    )


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    date = Column(String, default="")   # YYYY-MM-DD
    details = Column(String, default="")
    amount_per_hour = Column(Float, default=0.0)
    deposit = Column(Float, default=0.0)
    pending = Column(Float, default=0.0)  # deposit - amount_per_hour

    client = relationship("Client", back_populates="ledger_entries")


def init_db():
    Base.metadata.create_all(engine)


# -------------------- Auth helpers ----------------
def create_user(name: str, phone: str, email: str, password_hash: str, auto_verify: bool = True) -> User:
    db = SessionLocal()
    try:
        # uniqueness check
        if db.query(User).filter((User.email == email) | (User.phone == phone)).first():
            if db.query(User).filter(User.email == email).first():
                raise UniqueConstraintError("Email already registered.")
            else:
                raise UniqueConstraintError("Phone already registered.")
        user = User(
            name=name,
            phone=phone,
            email=email,
            password_hash=password_hash,
            email_verified=True if auto_verify else False,
            otp_code="",
            otp_expires=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def get_user_by_email(email: str) -> Optional[User]:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email).first()
    finally:
        db.close()


def get_user_by_id(uid: int) -> Optional[User]:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == uid).first()
    finally:
        db.close()


def require_auth(session):
    """
    If you want a hard redirect when not logged in, in your route do:
        resp = logic.require_auth(session)
        if resp: return resp
    """
    if not session.get("user_id"):
        from flask import redirect, url_for
        return redirect(url_for("home"))
    return None


# -------------------- Clients ---------------------
def create_client(owner_id: int, name: str, mobile: str) -> Client:
    db = SessionLocal()
    try:
        if db.query(Client).filter(Client.owner_id == owner_id, Client.mobile == mobile).first():
            raise UniqueConstraintError("Client mobile must be unique.")
        c = Client(name=name, mobile=mobile, owner_id=owner_id)
        db.add(c)
        db.commit()
        db.refresh(c)
        return c
    finally:
        db.close()


def update_client(owner_id: int, client_id: int, name: str, mobile: str) -> bool:
    db = SessionLocal()
    try:
        c = db.query(Client).filter(Client.owner_id == owner_id, Client.id == client_id).first()
        if not c:
            return False
        if mobile and mobile != c.mobile:
            if db.query(Client).filter(Client.owner_id == owner_id, Client.mobile == mobile).first():
                raise UniqueConstraintError("Client mobile must be unique.")
            c.mobile = mobile
        if name:
            c.name = name
        db.commit()
        return True
    finally:
        db.close()


def delete_client(owner_id: int, client_id: int) -> bool:
    db = SessionLocal()
    try:
        c = db.query(Client).filter(Client.owner_id == owner_id, Client.id == client_id).first()
        if not c:
            return False
        db.delete(c)
        db.commit()
        return True
    finally:
        db.close()


def search_clients(owner_id: int, query: str) -> List[Client]:
    db = SessionLocal()
    try:
        if not query:
            return []
        q = f"%{query}%"
        return (
            db.query(Client)
            .filter(Client.owner_id == owner_id)
            .filter((Client.name.ilike(q)) | (Client.mobile.ilike(q)))
            .order_by(Client.name.asc())
            .all()
        )
    finally:
        db.close()


def get_all_clients(owner_id: int) -> List[Client]:
    db = SessionLocal()
    try:
        return db.query(Client).filter(Client.owner_id == owner_id).order_by(Client.name.asc()).all()
    finally:
        db.close()


def get_client(owner_id: int, client_id: int) -> Optional[Client]:
    db = SessionLocal()
    try:
        return db.query(Client).filter(Client.owner_id == owner_id, Client.id == client_id).first()
    finally:
        db.close()


# -------------------- Ledger ----------------------
def _normalize_date(date_str: str) -> str:
    """Return YYYY-MM-DD; fallback to today."""
    try:
        if date_str and len(date_str.split("-")[0]) == 4:
            return date_str
        return _date.today().isoformat()
    except Exception:
        return _date.today().isoformat()


def add_ledger_entry(client_id: int, *args) -> LedgerEntry:
    """
    Compatibility:
      NEW form: add_ledger_entry(client_id, date_str, details, amount_per_hour, deposit)
      OLD form: add_ledger_entry(client_id, details, amount_per_hour, deposit, pending)  # pending ignored
    """
    # Unpack flexible args
    if len(args) == 4:
        # Could be (date, details, aph, dep) OR (details, aph, dep, pending) — detect by date pattern
        maybe_date = args[0]
        if isinstance(maybe_date, str) and len(maybe_date) >= 8 and maybe_date[:4].isdigit() and "-" in maybe_date:
            date_str, details, amount_per_hour, deposit = args  # NEW
        else:
            # OLD (no date sent)
            details, amount_per_hour, deposit, _pending = args
            date_str = ""
    elif len(args) == 5:
        date_str, details, amount_per_hour, deposit, _pending = args  # tolerate extra arg
    else:
        raise TypeError("add_ledger_entry expects 4 or 5 arguments after client_id")

    try:
        aph = float(amount_per_hour or 0)
        dep = float(deposit or 0)
    except ValueError:
        raise ValueError("Amounts must be numbers.")

    pend = dep - aph
    db = SessionLocal()
    try:
        entry = LedgerEntry(
            client_id=client_id,
            date=_normalize_date(date_str or ""),
            details=details or "",
            amount_per_hour=aph,
            deposit=dep,
            pending=pend,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    finally:
        db.close()


def get_ledger_entries(client_id: int) -> List[LedgerEntry]:
    db = SessionLocal()
    try:
        return (
            db.query(LedgerEntry)
            .filter(LedgerEntry.client_id == client_id)
            .order_by(LedgerEntry.id.asc())
            .all()
        )
    finally:
        db.close()


def get_ledger_entry(entry_id: int) -> Optional[LedgerEntry]:
    db = SessionLocal()
    try:
        return db.query(LedgerEntry).filter(LedgerEntry.id == entry_id).first()
    finally:
        db.close()


def update_ledger_entry(entry_id: int, *args) -> bool:
    """
    Compatibility:
      NEW: update_ledger_entry(entry_id, date_str, details, amount_per_hour, deposit)
      OLD: update_ledger_entry(entry_id, details, amount_per_hour, deposit, pending)
    """
    if len(args) == 4:
        maybe_date = args[0]
        if isinstance(maybe_date, str) and len(maybe_date) >= 8 and maybe_date[:4].isdigit() and "-" in maybe_date:
            date_str, details, amount_per_hour, deposit = args
        else:
            details, amount_per_hour, deposit, _pending = args
            date_str = ""
    elif len(args) == 5:
        date_str, details, amount_per_hour, deposit, _pending = args
    else:
        raise TypeError("update_ledger_entry expects 4 or 5 arguments after entry_id")

    try:
        aph = float(amount_per_hour or 0)
        dep = float(deposit or 0)
    except ValueError:
        raise ValueError("Amounts must be numbers.")
    pend = dep - aph

    db = SessionLocal()
    try:
        entry = db.query(LedgerEntry).filter(LedgerEntry.id == entry_id).first()
        if not entry:
            return False
        entry.date = _normalize_date(date_str or entry.date or "")
        entry.details = details or ""
        entry.amount_per_hour = aph
        entry.deposit = dep
        entry.pending = pend
        db.commit()
        return True
    finally:
        db.close()


def delete_ledger_entry(entry_id: int) -> bool:
    db = SessionLocal()
    try:
        entry = db.query(LedgerEntry).filter(LedgerEntry.id == entry_id).first()
        if not entry:
            return False
        db.delete(entry)
        db.commit()
        return True
    finally:
        db.close()


def compute_totals(entries: List[LedgerEntry]) -> dict:
    total_aph = sum((e.amount_per_hour or 0) for e in entries)
    total_dep = sum((e.deposit or 0) for e in entries)
    total_pen = total_dep - total_aph
    return {
        "amount_per_hour": round(total_aph, 2),
        "deposit": round(total_dep, 2),
        "pending": round(total_pen, 2),
    }


# -------------------- PDFs ------------------------
def render_clients_pdf(clients: List[Client]) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 50, "Registered Clients")

    y = height - 90
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "#")
    c.drawString(70, y, "Name")
    c.drawString(260, y, "Mobile")

    c.setFont("Helvetica", 11)
    y -= 20
    for idx, cl in enumerate(clients, start=1):
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 11)
        c.drawString(40, y, str(idx))
        c.drawString(70, y, cl.name)
        c.drawString(260, y, cl.mobile)
        y -= 18

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def render_ledger_pdf(client: Client, entries: List[LedgerEntry], totals: dict) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 50, f"{client.name} ({client.mobile})")

    y = height - 90
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "S#")
    c.drawString(70, y, "Date")
    c.drawString(140, y, "Details")
    c.drawRightString(400, y, "Amt/hr")
    c.drawRightString(480, y, "Deposit")
    c.drawRightString(560, y, "Pending")

    c.setFont("Helvetica", 11)
    y -= 20
    for idx, e in enumerate(entries, start=1):
        if y < 80:
            # print the running totals at the bottom before page break
            c.setFont("Helvetica-Bold", 11)
            c.drawRightString(400, 50, f"{totals['amount_per_hour']:.2f}")
            c.drawRightString(480, 50, f"{totals['deposit']:.2f}")
            c.drawRightString(560, 50, f"{totals['pending']:.2f}")
            c.showPage()
            c.setFont("Helvetica", 11)
            y = height - 50

        c.drawString(40, y, str(idx))
        c.drawString(70, y, (e.date or "")[:10])
        c.drawString(140, y, (e.details or "")[:36])
        c.drawRightString(400, y, f"{(e.amount_per_hour or 0):.2f}")
        c.drawRightString(480, y, f"{(e.deposit or 0):.2f}")
        c.drawRightString(560, y, f"{(e.pending or 0):.2f}")
        y -= 18

    # Totals box
    c.setFont("Helvetica-Bold", 12)
    c.line(40, y, 560, y)
    y -= 14
    c.drawString(280, y, "TOTAL")
    c.drawRightString(400, y, f"{totals['amount_per_hour']:.2f}")
    c.drawRightString(480, y, f"{totals['deposit']:.2f}")
    c.drawRightString(560, y, f"{totals['pending']:.2f}")

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
