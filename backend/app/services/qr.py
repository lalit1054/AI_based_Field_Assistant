"""QR code image + sticker PDF generation for machines."""

import io

import segno
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.config import get_settings

settings = get_settings()

STICKER_SIZE = (80 * mm, 50 * mm)


def build_qr_url(token: str) -> str:
    return f"{settings.qr_base_url.rstrip('/')}/{token}"


def generate_qr_png(url: str, scale: int = 6) -> bytes:
    qr = segno.make(url, error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=scale, border=2)
    return buf.getvalue()


def build_sticker_pdf(entries: list[tuple[str, str, str]]) -> bytes:
    """entries: list of (token, machine_name, plant_name) — one sticker per page,
    meant to be printed on adhesive label sheets and stuck on the machine.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=STICKER_SIZE)
    width, height = STICKER_SIZE

    for token, machine_name, plant_name in entries:
        qr_png = generate_qr_png(build_qr_url(token))
        qr_size = height - 10 * mm
        c.drawImage(
            ImageReader(io.BytesIO(qr_png)),
            5 * mm,
            5 * mm,
            width=qr_size,
            height=qr_size,
            preserveAspectRatio=True,
        )
        text_x = qr_size + 10 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(text_x, height - 15 * mm, machine_name[:28])
        c.setFont("Helvetica", 8)
        c.drawString(text_x, height - 22 * mm, plant_name[:32])
        c.setFont("Helvetica", 6)
        c.drawString(text_x, height - 28 * mm, token[:20])
        c.showPage()

    c.save()
    return buf.getvalue()
