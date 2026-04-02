# ======================================================================
# receipt_pdf.py – Professional PDF Receipt Generator
# ======================================================================
"""
A professional PDF receipt generator that produces clean, organized
receipts modelled on standard invoice/receipt templates.

Features:
  - Data-driven design (fully configurable via dataclasses)
  - Y-cursor layout engine — no hardcoded vertical offsets
  - Two-column header: From/To on the left, invoice details table on the right
  - Line-items table with per-item tax adjustments, sub-totals, and grand total
  - Optional diagonal "PAID" stamp watermark
  - Optional company logo (PNG/JPEG)
  - Configurable accent colour for headers and table highlights
  - ReportLab canvas + Platypus Table for pixel-perfect alignment

Usage:
    >>> from receipt_pdf import ReceiptData, ReceiptPDFGenerator
    >>> import datetime
    >>> from decimal import Decimal
    >>>
    >>> data = ReceiptData(
    ...     business=BusinessInfo(name="Acme Corp", ...),
    ...     client=ClientInfo(name="Test Business", ...),
    ...     invoice=InvoiceInfo(receipt_number="REC-001", ...),
    ...     line_items=[LineItem(qty=Decimal("2"), description="Consulting", rate=Decimal("150"))],
    ... )
    >>> ReceiptPDFGenerator().generate(data, "receipt.pdf")
"""

from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Tuple


# ======================================================================
# DATA MODELS
# ======================================================================

@dataclass
class BusinessInfo:
    """Company information printed in the *From* section."""
    name: str = "Architech, LLC"
    address_line1: str = "Suite 5A-1204"
    address_line2: str = "123 Somewhere Street"
    city_state_zip: str = "Your City AZ 12345"
    email: str = "admin@architech.com"


@dataclass
class ClientInfo:
    """Customer information printed in the *To* section."""
    name: str = "Test Business"
    address_line1: str = "123 Somewhere St"
    address_line2: str = "Melbourne, VIC 3000"
    email: str = "test@test.com"


@dataclass
class InvoiceInfo:
    """Receipt metadata: number, date, and the amount paid."""
    receipt_number: str = "REC-0001"
    receipt_date: _dt.date = field(default_factory=_dt.date.today)
    total_paid: Decimal = Decimal("0.00")


@dataclass
class LineItem:
    """
    A single billable item.

    *adjustment_pct* is a positive or negative percentage applied to the
    base ``qty × rate`` amount, e.g. ``Decimal("10.00")`` for +10 % or
    ``Decimal("-5.00")`` for a 5 % discount.
    """
    qty: Decimal
    description: str
    rate: Decimal = Decimal("0.00")
    details: Optional[str] = None
    adjustment_pct: Decimal = Decimal("0.00")
    # Computed automatically in __post_init__
    sub_total: Decimal = field(init=False)

    def __post_init__(self) -> None:
        base = (self.qty * self.rate).quantize(Decimal("0.01"))
        multiplier = (Decimal("1") + self.adjustment_pct / Decimal("100"))
        self.sub_total = (base * multiplier).quantize(Decimal("0.01"))


@dataclass
class ReceiptData:
    """Top-level container for everything that ends up on the receipt."""
    business: BusinessInfo
    client: ClientInfo
    invoice: InvoiceInfo
    line_items: List[LineItem]

    # Financial
    tax_rate_pct: Decimal = Decimal("10.00")

    # Footer copy
    payment_instructions: str = "Thank you for your payment. This document serves as your official receipt."
    notes: str = "Thanks for choosing us."

    # Bank details
    bank_name: str = "ANZ Bank"
    account_number: str = "ACC # 1234 1234"
    bsb: str = "BSB # 4321 432"

    # Presentation options
    paid: bool = False
    logo_path: Optional[str] = None   # Path to a PNG/JPEG logo file


# ======================================================================
# COLOUR THEME
# ======================================================================

@dataclass
class Theme:
    """
    Colour theme for the receipt.

    All values are RGB tuples in the 0-1 range (ReportLab convention).
    """
    accent: Tuple[float, float, float] = (0.18, 0.56, 0.84)   # default: steel-blue
    header_text: Tuple[float, float, float] = (1.0, 1.0, 1.0) # white on accent bg
    light_grey: Tuple[float, float, float] = (0.93, 0.93, 0.93)
    mid_grey: Tuple[float, float, float] = (0.55, 0.55, 0.55)
    black: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    paid_stamp: Tuple[float, float, float] = (0.60, 0.60, 0.60)  # mid-grey


# ======================================================================
# FORMATTING HELPERS
# ======================================================================

def _money(val: Decimal) -> str:
    return f"${val:,.2f}"


def _pct(val: Decimal) -> str:
    return f"{val:.2f}%"


def _color(t: Tuple[float, float, float]):
    """Convert an RGB tuple to a ReportLab Color."""
    from reportlab.lib.colors import Color
    return Color(*t)


# ======================================================================
# PDF GENERATOR
# ======================================================================

class ReceiptPDFGenerator:
    """
    Renders a :class:`ReceiptData` instance into a professional A4 PDF.

    Layout uses a *Y-cursor* pattern: every section advances ``self._y``
    downward so nothing is ever positioned by a magic constant offset.

    Parameters
    ----------
    theme : Theme, optional
        Colour scheme.  Defaults to the built-in steel-blue theme.
    """

    # ── Page geometry ────────────────────────────────────────────────
    PAGE_W: float = 595.27   # A4 points
    PAGE_H: float = 841.89
    MARGIN: float = 40.0       # left / right / bottom margin
    MARGIN_TOP: float = 20.0   # top margin — tighter so logo sits near the edge
    INNER_W: float = PAGE_W - 2 * 40.0  # 515.27 pt

    # ── Logo ─────────────────────────────────────────────────────────
    LOGO_H: float = 40.0          # rendered logo height in points
    LOGO_BOTTOM_GAP: float = 48.0 # whitespace below logo before From/To

    # ── Typography ───────────────────────────────────────────────────
    LH: float = 13.0          # default line height
    F_NORMAL = "Helvetica"
    F_BOLD = "Helvetica-Bold"
    F_SMALL = 8
    F_BODY = 9
    F_NORMAL_SIZE = 10
    F_LARGE = 18

    def __init__(self, theme: Optional[Theme] = None) -> None:
        self.theme = theme or Theme()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, data: ReceiptData, output_path: str | Path) -> None:
        """
        Build the PDF and write it to *output_path*.

        Args:
            data: Complete receipt information.
            output_path: Destination file path (will be created/overwritten).
        """
        from reportlab.pdfgen import canvas as rl_canvas

        c = rl_canvas.Canvas(str(output_path), pagesize=(self.PAGE_W, self.PAGE_H))
        c.setTitle(f"Receipt {data.invoice.receipt_number}")
        c.setAuthor(data.business.name)

        self._canvas = c
        self._y = self.PAGE_H - self.MARGIN_TOP  # Y-cursor starts at top margin

        self._draw_header(data)
        self._draw_address_and_details(data)
        self._draw_line_items(data)
        self._draw_footer(data)

        if data.paid:
            self._draw_paid_stamp()

        c.showPage()
        c.save()

    # ------------------------------------------------------------------
    # Section renderers
    # ------------------------------------------------------------------

    def _draw_header(self, data: ReceiptData) -> None:
        """Logo (optional, left) + 'RECEIPT' title (right)."""
        c = self._canvas

        if data.logo_path and Path(data.logo_path).exists():
            # Measure natural image size to preserve aspect ratio exactly
            from reportlab.lib.utils import ImageReader
            img = ImageReader(data.logo_path)
            img_w, img_h = img.getSize()
            aspect = img_w / img_h if img_h else 2.5

            logo_h = self.LOGO_H
            logo_w = logo_h * aspect

            # Draw flush with the top margin
            c.drawImage(
                data.logo_path,
                self.MARGIN,
                self._y - logo_h,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask="auto",
            )

            # "RECEIPT" title vertically centred alongside the logo
            title_y = self._y - logo_h / 2 - self.F_LARGE / 3
            self._text(
                "RECEIPT",
                self.PAGE_W - self.MARGIN, title_y,
                font=self.F_BOLD, size=self.F_LARGE, align="right",
            )

            # Advance cursor past logo height + explicit gap beneath it
            self._y -= logo_h + self.LOGO_BOTTOM_GAP

        else:
            # No logo — just the title and a standard gap
            self._text(
                "RECEIPT",
                self.PAGE_W - self.MARGIN, self._y,
                font=self.F_BOLD, size=self.F_LARGE, align="right",
            )
            self._y -= self.LH * 3

    def _draw_address_and_details(self, data: ReceiptData) -> None:
        """
        Two-column block:
          Left  → From: / To: address blocks
          Right → Invoice details table
        """
        from reportlab.platypus import Table, TableStyle

        c = self._canvas
        top_y = self._y

        # ── Right column: invoice details table ──────────────────────
        detail_rows = [
            ["Receipt Number", data.invoice.receipt_number],
            ["Receipt Date",   data.invoice.receipt_date.strftime("%B %d, %Y")],
            ["Total Paid",     _money(data.invoice.total_paid)],
        ]

        tbl = Table(detail_rows, colWidths=[95, 100])
        tbl.setStyle(TableStyle([
            # All cells
            ("FONTNAME",   (0, 0), (-1, -1), self.F_NORMAL),
            ("FONTSIZE",   (0, 0), (-1, -1), self.F_BODY),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",  (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            # Label column bold
            ("FONTNAME", (0, 0), (0, -1), self.F_BOLD),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.4, _color(self.theme.mid_grey)),
            # Last row highlighted
            ("BACKGROUND", (0, -1), (-1, -1), _color(self.theme.light_grey)),
            ("FONTNAME",   (0, -1), (-1, -1), self.F_BOLD),
        ]))

        tbl_w, tbl_h = tbl.wrapOn(c, 200, 300)
        tbl_x = self.PAGE_W - self.MARGIN - tbl_w
        tbl.drawOn(c, tbl_x, top_y - tbl_h)

        # ── Left column: From / To ────────────────────────────────────
        left_x = self.MARGIN
        ly = top_y

        def _addr_block(label: str, lines: List[str]) -> None:
            nonlocal ly
            self._text(label, left_x, ly, font=self.F_BOLD, size=self.F_NORMAL_SIZE)
            ly -= self.LH
            for line in lines:
                self._text(line, left_x, ly, size=self.F_BODY)
                ly -= self.LH
            ly -= self.LH * 0.6

        b = data.business
        _addr_block("From:", [b.name, b.address_line1, b.address_line2,
                               b.city_state_zip, b.email])

        ly -= self.LH * 1.8  # extra gap between From and To

        cl = data.client
        _addr_block("To:", [cl.name, cl.address_line1, cl.address_line2, cl.email])

        # Advance Y past whichever column is taller, with extra breathing room
        # before the line-items table
        self._y = min(top_y - tbl_h, ly) - self.LH * 5

    def _draw_line_items(self, data: ReceiptData) -> None:
        """Render the service line-items table plus sub-total / tax / total rows."""
        from reportlab.platypus import Table, TableStyle, Paragraph
        from reportlab.lib.styles import ParagraphStyle

        c = self._canvas

        desc_style = ParagraphStyle(
            "desc",
            fontName=self.F_NORMAL,
            fontSize=self.F_BODY,
            leading=11,
        )
        detail_style = ParagraphStyle(
            "detail",
            fontName=self.F_NORMAL,
            fontSize=7,
            leading=10,
            textColor=_color(self.theme.mid_grey),
        )

        # Column widths must sum to INNER_W (515.27)
        col_widths = [55, 210, 80, 60, 80]   # total ≈ 485; pad remainder on desc

        # Header row
        rows = [["Hrs/Qty", "Service", "Rate/Price", "Adjust", "Sub Total"]]

        for li in data.line_items:
            desc_para = Paragraph(li.description, desc_style)
            if li.details:
                desc_para = Paragraph(
                    f"{li.description}<br/>"
                    f"<font name='{self.F_NORMAL}' size='7'>{li.details}</font>",
                    desc_style,
                )
            rows.append([
                str(li.qty),
                desc_para,
                _money(li.rate),
                _pct(li.adjustment_pct),
                _money(li.sub_total),
            ])

        # Totals
        sub_total = sum(li.sub_total for li in data.line_items)
        tax_amount = (sub_total * data.tax_rate_pct / Decimal("100")).quantize(Decimal("0.01"))
        grand_total = (sub_total + tax_amount).quantize(Decimal("0.01"))

        n_items = len(rows)  # header + data rows
        rows.append(["", "", "", "Sub Total", _money(sub_total)])
        rows.append(["", "", "", f"Tax ({_pct(data.tax_rate_pct)})", _money(tax_amount)])
        rows.append(["", "", "", "Total", _money(grand_total)])

        tbl = Table(rows, colWidths=col_widths)

        accent = _color(self.theme.accent)
        h_text = _color(self.theme.header_text)
        lt_grey = _color(self.theme.light_grey)
        mid_grey = _color(self.theme.mid_grey)

        style_cmds = [
            # ── Header row ────────────────────────────────────────────
            ("BACKGROUND",    (0, 0), (-1, 0), accent),
            ("TEXTCOLOR",     (0, 0), (-1, 0), h_text),
            ("FONTNAME",      (0, 0), (-1, 0), self.F_BOLD),
            ("FONTSIZE",      (0, 0), (-1, 0), self.F_BODY),
            ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
            ("VALIGN",        (0, 0), (-1, 0), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),

            # ── Data rows ─────────────────────────────────────────────
            ("FONTNAME",  (0, 1), (-1, n_items - 1), self.F_NORMAL),
            ("FONTSIZE",  (0, 1), (-1, n_items - 1), self.F_BODY),
            ("ALIGN",     (0, 1), (0, n_items - 1), "CENTER"),   # Qty
            ("ALIGN",     (2, 1), (-1, n_items - 1), "RIGHT"),   # Rate → SubTotal
            ("VALIGN",    (0, 1), (-1, n_items - 1), "TOP"),
            ("TOPPADDING",    (0, 1), (-1, n_items - 1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, n_items - 1), 5),
            ("LEFTPADDING",   (0, 1), (-1, n_items - 1), 5),
            ("RIGHTPADDING",  (0, 1), (-1, n_items - 1), 5),
            # Alternating row shading
            *[
                ("BACKGROUND", (0, r), (-1, r), lt_grey)
                for r in range(2, n_items, 2)
            ],
            # Grid for item rows
            ("LINEBELOW", (0, 0), (-1, n_items - 1), 0.4, mid_grey),

            # ── Summary rows (last 3) ─────────────────────────────────
            ("FONTNAME",  (3, n_items), (-1, -1), self.F_BOLD),
            ("FONTSIZE",  (3, n_items), (-1, -1), self.F_BODY),
            ("ALIGN",     (3, n_items), (-1, -1), "RIGHT"),
            ("VALIGN",    (3, n_items), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (3, n_items), (-1, -1), 4),
            ("BOTTOMPADDING", (3, n_items), (-1, -1), 4),
            ("RIGHTPADDING",  (-1, n_items), (-1, -1), 5),
            # Separator above summary block
            ("LINEABOVE", (0, n_items), (-1, n_items), 1.0, _color(self.theme.black)),
            # Total row accent
            ("BACKGROUND", (3, -1), (-1, -1), accent),
            ("TEXTCOLOR",  (3, -1), (-1, -1), h_text),
        ]

        tbl.setStyle(TableStyle(style_cmds))
        tbl_w, tbl_h = tbl.wrapOn(c, self.INNER_W, 600)
        tbl.drawOn(c, self.MARGIN, self._y - tbl_h)

        self._y -= tbl_h + self.LH * 2

    def _draw_footer(self, data: ReceiptData) -> None:
        """Payment instructions, bank details, and notes at the bottom of the page."""
        # Pin the footer to the bottom margin
        fy = self.MARGIN + 70

        self._text(data.payment_instructions, self.MARGIN, fy, size=self.F_SMALL)
        fy -= self.LH * 1.4

        self._text(data.bank_name,     self.MARGIN, fy, font=self.F_BOLD, size=self.F_BODY)
        fy -= self.LH
        self._text(data.account_number, self.MARGIN, fy, size=self.F_SMALL)
        fy -= self.LH
        self._text(data.bsb,            self.MARGIN, fy, size=self.F_SMALL)
        fy -= self.LH
        self._text(data.notes,          self.MARGIN, fy, size=self.F_SMALL)

        # Page number
        self._text(
            "Page 1/1",
            self.PAGE_W - self.MARGIN,
            self.MARGIN / 2,
            size=self.F_SMALL,
            align="right",
        )

    def _draw_paid_stamp(self) -> None:
        """
        Draw a large, semi-transparent diagonal 'PAID' stamp across the
        centre of the page, matching the style shown in the sample invoice.
        """
        c = self._canvas
        from reportlab.lib.colors import Color

        stamp_color = Color(*self.theme.paid_stamp, alpha=0.35)

        cx = self.PAGE_W / 2
        cy = self.PAGE_H / 2

        c.saveState()
        c.setFillColor(stamp_color)
        c.setStrokeColor(stamp_color)
        c.setFont(self.F_BOLD, 90)

        # Rotate 45° counter-clockwise about the page centre
        c.translate(cx, cy)
        c.rotate(45)
        text_w = c.stringWidth("PAID", self.F_BOLD, 90)
        c.drawString(-text_w / 2, -45, "PAID")
        c.restoreState()

    # ------------------------------------------------------------------
    # Drawing primitives
    # ------------------------------------------------------------------

    def _text(
        self,
        text: str,
        x: float,
        y: float,
        font: str = "Helvetica",
        size: int = 10,
        align: str = "left",
        color: Optional[Tuple[float, float, float]] = None,
    ) -> None:
        """Draw a single line of text at canvas coordinates (x, y)."""
        c = self._canvas
        from reportlab.lib.colors import black as rl_black

        c.setFont(font, size)
        c.setFillColor(_color(color) if color else rl_black)

        if align == "right":
            w = c.stringWidth(text, font, size)
            c.drawString(x - w, y, text)
        elif align == "center":
            w = c.stringWidth(text, font, size)
            c.drawString(x - w / 2, y, text)
        else:
            c.drawString(x, y, text)


# ======================================================================
# MAIN – Demo usage
# ======================================================================

if __name__ == "__main__":
    from decimal import Decimal
    import datetime

    data = ReceiptData(
        business=BusinessInfo(
            name="Architech, LLC",
            address_line1="Suite 5A-1204",
            address_line2="123 Somewhere Street",
            city_state_zip="Your City AZ 12345",
            email="admin@architech.com",
        ),
        client=ClientInfo(
            name="Test Business",
            address_line1="123 Somewhere St",
            address_line2="Melbourne, VIC 3000",
            email="test@test.com",
        ),
        invoice=InvoiceInfo(
            receipt_number="REC-2024-001",
            receipt_date=datetime.date(2024, 1, 25),
            total_paid=Decimal("93.50"),
        ),
        line_items=[
            LineItem(
                qty=Decimal("1.00"),
                description="Web Design",
                details="Custom responsive website build",
                rate=Decimal("85.00"),
            ),
            LineItem(
                qty=Decimal("3.00"),
                description="Consulting",
                details="Strategy and architecture review",
                rate=Decimal("120.00"),
                adjustment_pct=Decimal("-10.00"),  # 10% discount
            ),
        ],
        tax_rate_pct=Decimal("10.00"),
        paid=True,
        logo_path="image1.png",
        notes="Thanks for choosing Architech, LLC",
    )

    ReceiptPDFGenerator().generate(data, "demo_receipt.pdf")
    print("Receipt generated: demo_receipt.pdf")