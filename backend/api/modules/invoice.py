# ======================================================================
# invoice_pdf.py – Professional PDF Invoice Generator
# ======================================================================
"""
A professional PDF invoice generator with identical structure and
formatting to receipt_pdf.py, extended with all fields required for a
legally complete invoice and an optional payment QR code.

Invoice-specific additions over the receipt module:
  - Full InvoiceMetadata: number, order number, issue date, due date,
    payment terms, and a prominent "Amount Due" row
  - Payment QR code (PayPal.me, Stripe, or any URL) rendered beneath
    the details table — stays within the right column, never overlaps
    address text or page margins
  - "OVERDUE" diagonal stamp (mirrors the receipt's PAID stamp)
  - Notes / terms-and-conditions field in the footer

Usage:
    >>> from invoice_pdf import InvoiceData, InvoicePDFGenerator
    >>> from invoice_pdf import BusinessInfo, ClientInfo, InvoiceMetadata, LineItem
    >>> import datetime
    >>> from decimal import Decimal
    >>>
    >>> data = InvoiceData(
    ...     business=BusinessInfo(name="Acme Corp", ...),
    ...     client=ClientInfo(name="Client Ltd", ...),
    ...     meta=InvoiceMetadata(invoice_number="INV-0042", ...),
    ...     line_items=[LineItem(qty=Decimal("5"), description="Dev work", rate=Decimal("120"))],
    ...     payment_url="https://paypal.me/acmecorp",
    ... )
    >>> InvoicePDFGenerator().generate(data, "invoice.pdf")
"""

from __future__ import annotations

import datetime as _dt
import io
import tempfile
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Tuple


# ======================================================================
# DATA MODELS
# ======================================================================

@dataclass
class BusinessInfo:
    """Company (sender) information."""
    name: str = "Architech, LLC"
    address_line1: str = ""
    address_line2: str = "123 Somewhere Street"
    city_state_zip: str = "Your City AZ 12345"
    email: str = "charles.defreese@archtech.io"
    phone: str = ""          # optional; printed if non-empty
    abn_or_tax_id: str = ""  # e.g. "ABN 12 345 678 901" — printed if set


@dataclass
class ClientInfo:
    """Customer (recipient) information."""
    name: str = "Test Business"
    address_line1: str = "123 Somewhere St"
    address_line2: str = "Melbourne, VIC 3000"
    email: str = "test@test.com"
    attention: str = ""      # optional "Attn: ..." line


@dataclass
class InvoiceMetadata:
    """
    All fields required for a legally valid invoice.

    ``payment_terms`` is free text, e.g. "Net 30", "Due on receipt".
    ``po_number`` is the client's purchase-order reference; omitted from
    the table when left blank.
    """
    invoice_number: str = "INV-0001"
    order_number: str = ""                              # client PO / order ref
    invoice_date: _dt.date = field(default_factory=_dt.date.today)
    due_date: _dt.date = field(default_factory=_dt.date.today)
    payment_terms: str = "Net 30"


@dataclass
class LineItem:
    """
    A single billable item.

    ``adjustment_pct`` applies a positive or negative percentage to the
    base ``qty × rate`` amount before tax, e.g. ``Decimal("-10.00")``
    for a 10 % discount.
    """
    qty: Decimal
    description: str
    rate: Decimal = Decimal("0.00")
    details: Optional[str] = None
    adjustment_pct: Decimal = Decimal("0.00")
    sub_total: Decimal = field(init=False)

    def __post_init__(self) -> None:
        base = (self.qty * self.rate).quantize(Decimal("0.01"))
        multiplier = Decimal("1") + self.adjustment_pct / Decimal("100")
        self.sub_total = (base * multiplier).quantize(Decimal("0.01"))


@dataclass
class InvoiceData:
    """Top-level container — everything that ends up on the invoice."""
    business: BusinessInfo
    client: ClientInfo
    meta: InvoiceMetadata
    line_items: List[LineItem]

    # Financial
    tax_rate_pct: Decimal = Decimal("10.00")

    # Payment
    payment_url: str = ""    # QR code target, e.g. "https://paypal.me/yourname"
    bank_name: str = "ANZ Bank"
    account_number: str = "ACC # 1234 1234"
    bsb: str = "BSB # 4321 432"

    # Footer text
    payment_instructions: str = (
        "Payment is due by the date shown above. "
        "Late payments are subject to a fee of 5 % per month."
    )
    terms: str = ""          # optional terms-and-conditions blurb
    notes: str = ""          # optional closing note

    # Presentation
    logo_path: Optional[str] = None
    overdue: bool = False    # renders diagonal "OVERDUE" stamp when True


# ======================================================================
# COLOUR THEME
# ======================================================================

@dataclass
class Theme:
    """
    All colours as RGB 0-1 tuples (ReportLab convention).
    Override any field to customise the palette.

    Example — charcoal theme::

        Theme(accent=(0.2, 0.2, 0.2))
    """
    accent: Tuple[float, float, float] = (0.18, 0.56, 0.84)    # steel-blue
    header_text: Tuple[float, float, float] = (1.0, 1.0, 1.0)  # white on accent
    light_grey: Tuple[float, float, float] = (0.93, 0.93, 0.93)
    mid_grey: Tuple[float, float, float] = (0.55, 0.55, 0.55)
    black: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    overdue_stamp: Tuple[float, float, float] = (0.80, 0.20, 0.20)  # red


# ======================================================================
# FORMATTING HELPERS
# ======================================================================

def _money(val: Decimal) -> str:
    return f"${val:,.2f}"


def _pct(val: Decimal) -> str:
    return f"{val:.2f}%"


def _color(t: Tuple[float, float, float]):
    from reportlab.lib.colors import Color
    return Color(*t)


def _make_qr_png(url: str) -> bytes:
    try:
        import qrcode

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    except Exception as e:
        raise RuntimeError(f"QR generation failed: {e}")


# ======================================================================
# PDF GENERATOR
# ======================================================================

class InvoicePDFGenerator:
    """
    Renders an :class:`InvoiceData` instance into a professional A4 PDF.

    Layout uses the same Y-cursor engine as ``ReceiptPDFGenerator`` —
    every section advances ``self._y`` downward so positions never drift
    regardless of how many line items are included.

    Parameters
    ----------
    theme : Theme, optional
        Colour scheme.  Pass a custom ``Theme`` instance to override.
    """

    # ── Page geometry ────────────────────────────────────────────────
    PAGE_W: float = 595.27
    PAGE_H: float = 841.89
    MARGIN: float = 40.0        # left / right / bottom margin
    MARGIN_TOP: float = 20.0    # tighter top margin so the logo sits near the edge
    INNER_W: float = PAGE_W - 2 * 40.0   # 515.27 pt usable width

    # ── Logo ─────────────────────────────────────────────────────────
    LOGO_H: float = 40.0
    LOGO_BOTTOM_GAP: float = 48.0

    # ── Details table (right column) ─────────────────────────────────
    DETAIL_COL_LABEL: float = 105.0
    DETAIL_COL_VALUE: float = 110.0

    # ── QR code ──────────────────────────────────────────────────────
    QR_SIZE: float = 80.0       # rendered side length in points
    QR_GAP: float = 8.0         # gap between details table bottom and QR code

    # ── Typography ───────────────────────────────────────────────────
    LH: float = 13.0
    F_NORMAL = "Helvetica"
    F_BOLD = "Helvetica-Bold"
    F_SMALL = 8
    F_BODY = 9
    F_NORMAL_SIZE = 10
    F_LARGE = 18

    def __init__(self, data: InvoiceData, theme: Optional[Theme] = None) -> None:
        self.theme = theme or Theme()
        self.data: InvoiceData = data

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, output_path: str | Path) -> None:
        """
        Render *data* into a PDF at *output_path*.

        Args:
            data: Complete invoice information.
            output_path: Destination path (created / overwritten).
        """
        from reportlab.pdfgen import canvas as rl_canvas

        c = rl_canvas.Canvas(str(output_path), pagesize=(self.PAGE_W, self.PAGE_H))
        c.setTitle(f"Invoice {self.data.meta.invoice_number}")
        c.setAuthor(self.data.business.name)

        self._canvas = c
        self._y = self.PAGE_H - self.MARGIN_TOP

        self._draw_header(self.data)
        self._draw_address_and_details(self.data)
        self._draw_line_items(self.data)
        self._draw_footer(self.data)

        if self.data.overdue:
            self._draw_overdue_stamp()

        c.showPage()
        c.save()

    # ------------------------------------------------------------------
    # Section renderers
    # ------------------------------------------------------------------

    def _draw_header(self, data: InvoiceData) -> None:
        """Logo (optional, left) + 'INVOICE' title (right)."""
        c = self._canvas

        if data.logo_path and Path(data.logo_path).exists():
            from reportlab.lib.utils import ImageReader
            img = ImageReader(data.logo_path)
            img_w, img_h = img.getSize()
            aspect = img_w / img_h if img_h else 2.5

            logo_h = self.LOGO_H
            logo_w = logo_h * aspect

            c.drawImage(
                data.logo_path,
                self.MARGIN,
                self._y - logo_h,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask="auto",
            )

            title_y = self._y - logo_h / 2 - self.F_LARGE / 3
            self._text(
                "INVOICE",
                self.PAGE_W - self.MARGIN, title_y,
                font=self.F_BOLD, size=self.F_LARGE, align="right",
            )
            self._y -= logo_h + self.LOGO_BOTTOM_GAP

        else:
            self._text(
                "INVOICE",
                self.PAGE_W - self.MARGIN, self._y,
                font=self.F_BOLD, size=self.F_LARGE, align="right",
            )
            self._y -= self.LH * 3

    def _draw_address_and_details(self, data: InvoiceData) -> None:
        """
        Two-column block:
          Left  → From / To address blocks
          Right → Invoice details table + QR code (if payment_url set)
        """
        from reportlab.platypus import Table, TableStyle

        c = self._canvas
        top_y = self._y
        tbl_w = self.DETAIL_COL_LABEL + self.DETAIL_COL_VALUE
        tbl_x = self.PAGE_W - self.MARGIN - tbl_w

        # ── Right column: invoice details table ──────────────────────
        detail_rows = [
            ["Invoice Number", data.meta.invoice_number],
            ["Invoice Date",   data.meta.invoice_date.strftime("%B %d, %Y")],
            ["Due Date",       data.meta.due_date.strftime("%B %d, %Y")],
            ["Payment Terms",  data.meta.payment_terms],
        ]
        if data.meta.order_number:
            detail_rows.insert(1, ["Order / PO #", data.meta.order_number])

        # Calculate grand total for the "Amount Due" row
        sub_total = sum(li.sub_total for li in data.line_items)
        tax_amount = (sub_total * data.tax_rate_pct / Decimal("100")).quantize(Decimal("0.01"))
        self._grand_total = (sub_total + tax_amount).quantize(Decimal("0.01"))

        detail_rows.append(["Amount Due", _money(self._grand_total)])

        tbl = Table(detail_rows, colWidths=[self.DETAIL_COL_LABEL, self.DETAIL_COL_VALUE])
        tbl.setStyle(TableStyle([
            ("FONTNAME",      (0, 0), (-1, -1), self.F_NORMAL),
            ("FONTSIZE",      (0, 0), (-1, -1), self.F_BODY),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            # Label column bold
            ("FONTNAME",  (0, 0), (0, -1), self.F_BOLD),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.4, _color(self.theme.mid_grey)),
            # "Amount Due" row — accented, bold, larger
            ("BACKGROUND", (0, -1), (-1, -1), _color(self.theme.accent)),
            ("TEXTCOLOR",  (0, -1), (-1, -1), _color(self.theme.header_text)),
            ("FONTNAME",   (0, -1), (-1, -1), self.F_BOLD),
            ("FONTSIZE",   (0, -1), (-1, -1), self.F_NORMAL_SIZE),
            ("TOPPADDING",    (0, -1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
        ]))

        tbl_w_actual, tbl_h = tbl.wrapOn(c, tbl_w, 400)
        tbl.drawOn(c, tbl_x, top_y - tbl_h)

        # ── QR code: payment link, placed below the details table ─────
        qr_bottom_y = top_y - tbl_h  # bottom edge of details table
        qr_png = _make_qr_png(data.payment_url) if data.payment_url else b""

        if qr_png:
            # Write PNG bytes to a temp file (ReportLab needs a path or file-like)
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.write(qr_png)
            tmp.flush()
            tmp_path = tmp.name
            tmp.close()

            qr_y = qr_bottom_y - self.QR_GAP - self.QR_SIZE
            # Centre the QR under the details table
            qr_x = tbl_x + (tbl_w - self.QR_SIZE) / 2

            c.drawImage(
                tmp_path,
                qr_x, qr_y,
                width=self.QR_SIZE,
                height=self.QR_SIZE,
                preserveAspectRatio=True,
                mask="auto",
            )

            # Caption beneath QR code
            caption_y = qr_y - self.LH * 0.8
            self._text(
                "www." + self.data.payment_url.removeprefix("https://"),  # strip the https:// prefix for a cleaner look
                tbl_x + tbl_w / 2, caption_y,
                size=self.F_SMALL,
                color=self.theme.mid_grey,
                align="center",
            )

            # Track how far down the right column reaches
            right_col_bottom = caption_y - self.LH
        else:
            right_col_bottom = qr_bottom_y

        # ── Left column: From / To ────────────────────────────────────
        left_x = self.MARGIN
        ly = top_y

        def _addr_block(label: str, lines: List[str]) -> None:
            nonlocal ly
            self._text(label, left_x, ly, font=self.F_BOLD, size=self.F_NORMAL_SIZE)
            ly -= self.LH
            for line in lines:
                if line:
                    self._text(line, left_x, ly, size=self.F_BODY)
                    ly -= self.LH
            ly -= self.LH * 0.6

        b = data.business
        from_lines = [b.name, b.address_line1, b.address_line2, b.city_state_zip, b.email]
        if b.phone:
            from_lines.append(b.phone)
        if b.abn_or_tax_id:
            from_lines.append(b.abn_or_tax_id)
        _addr_block("From:", from_lines)

        ly -= self.LH * 1.8  # breathing room between From and To

        cl = data.client
        to_lines = []
        if cl.attention:
            to_lines.append(f"Attn: {cl.attention}")
        to_lines += [cl.name, cl.address_line1, cl.address_line2, cl.email]
        _addr_block("To:", to_lines)

        # Advance cursor past whichever column is taller + gap before items table
        self._y = min(right_col_bottom, ly) - self.LH * 5

    def _draw_line_items(self, data: InvoiceData) -> None:
        """Render the line-items table plus sub-total / tax / amount-due rows."""
        from reportlab.platypus import Table, TableStyle, Paragraph
        from reportlab.lib.styles import ParagraphStyle

        c = self._canvas

        desc_style = ParagraphStyle(
            "inv_desc",
            fontName=self.F_NORMAL,
            fontSize=self.F_BODY,
            leading=11,
        )

        col_widths = [55, 195, 80, 90, 75]

        rows = [["Hrs/Qty", "Description", "Rate/Price", "Adjust", "Sub Total"]]

        for li in data.line_items:
            if li.details:
                desc_para = Paragraph(
                    f"{li.description}<br/>"
                    f"<font name='{self.F_NORMAL}' size='7'>{li.details}</font>",
                    desc_style,
                )
            else:
                desc_para = Paragraph(li.description, desc_style)

            rows.append([
                str(li.qty),
                desc_para,
                _money(li.rate),
                _pct(li.adjustment_pct),
                _money(li.sub_total),
            ])

        # Totals (reuse cached grand total computed in _draw_address_and_details)
        sub_total = sum(li.sub_total for li in data.line_items)
        tax_amount = (sub_total * data.tax_rate_pct / Decimal("100")).quantize(Decimal("0.01"))
        grand_total = self._grand_total

        n_items = len(rows)
        rows.append(["", "", "", "Sub Total",                  _money(sub_total)])
        rows.append(["", "", "", f"Tax ({_pct(data.tax_rate_pct)})", _money(tax_amount)])
        rows.append(["", "", "", "Amount Due",                 _money(grand_total)])

        tbl = Table(rows, colWidths=col_widths)

        accent   = _color(self.theme.accent)
        h_text   = _color(self.theme.header_text)
        lt_grey  = _color(self.theme.light_grey)
        mid_grey = _color(self.theme.mid_grey)

        style_cmds = [
            # Header row
            ("BACKGROUND",    (0, 0), (-1, 0), accent),
            ("TEXTCOLOR",     (0, 0), (-1, 0), h_text),
            ("FONTNAME",      (0, 0), (-1, 0), self.F_BOLD),
            ("FONTSIZE",      (0, 0), (-1, 0), self.F_BODY),
            ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
            ("VALIGN",        (0, 0), (-1, 0), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),

            # Data rows
            ("FONTNAME",  (0, 1), (-1, n_items - 1), self.F_NORMAL),
            ("FONTSIZE",  (0, 1), (-1, n_items - 1), self.F_BODY),
            ("ALIGN",     (0, 1), (0, n_items - 1), "CENTER"),
            ("ALIGN",     (2, 1), (-1, n_items - 1), "RIGHT"),
            ("VALIGN",    (0, 1), (-1, n_items - 1), "TOP"),
            ("TOPPADDING",    (0, 1), (-1, n_items - 1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, n_items - 1), 5),
            ("LEFTPADDING",   (0, 1), (-1, n_items - 1), 5),
            ("RIGHTPADDING",  (0, 1), (-1, n_items - 1), 5),
            *[
                ("BACKGROUND", (0, r), (-1, r), lt_grey)
                for r in range(2, n_items, 2)
            ],
            ("LINEBELOW", (0, 0), (-1, n_items - 1), 0.4, mid_grey),

            # Summary rows
            ("FONTNAME",  (3, n_items), (-1, -1), self.F_BOLD),
            ("FONTSIZE",  (3, n_items), (-1, -1), self.F_BODY),
            ("ALIGN",     (3, n_items), (-1, -1), "RIGHT"),
            ("VALIGN",    (3, n_items), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (3, n_items), (-1, -1), 4),
            ("BOTTOMPADDING", (3, n_items), (-1, -1), 4),
            ("RIGHTPADDING",  (-1, n_items), (-1, -1), 5),
            ("LINEABOVE", (0, n_items), (-1, n_items), 1.0, _color(self.theme.black)),
            # Amount Due row — accent background
            ("BACKGROUND", (3, -1), (-1, -1), accent),
            ("TEXTCOLOR",  (3, -1), (-1, -1), h_text),
            ("FONTSIZE",   (3, -1), (-1, -1), self.F_NORMAL_SIZE),
        ]

        tbl.setStyle(TableStyle(style_cmds))
        tbl_w, tbl_h = tbl.wrapOn(c, self.INNER_W, 600)
        tbl.drawOn(c, self.MARGIN, self._y - tbl_h)

        self._y -= tbl_h + self.LH * 2

    def _draw_footer(self, data: InvoiceData) -> None:
        """Payment instructions, bank details, optional terms, and page number."""
        c = self._canvas

        # ── Separator line ────────────────────────────────────────────
        sep_y = self.MARGIN + 155
        c.setStrokeColor(_color(self.theme.mid_grey))
        c.setLineWidth(0.4)
        c.line(self.MARGIN, sep_y, self.PAGE_W - self.MARGIN, sep_y)

        fy = sep_y - self.LH * 1.2

        # Payment instructions
        self._text(data.payment_instructions, self.MARGIN, fy, size=self.F_SMALL)
        fy -= self.LH * 1.6

        # Bank details — two short columns
        self._text(data.bank_name,      self.MARGIN, fy, font=self.F_BOLD, size=self.F_BODY)
        fy -= self.LH
        self._text(data.account_number, self.MARGIN, fy, size=self.F_SMALL)
        fy -= self.LH
        self._text(data.bsb,            self.MARGIN, fy, size=self.F_SMALL)
        fy -= self.LH

        if data.notes:
            self._text(data.notes, self.MARGIN, fy, size=self.F_SMALL)
            fy -= self.LH * 1.4

        if data.terms:
            self._text("Terms & Conditions", self.MARGIN, fy,
                       font=self.F_BOLD, size=self.F_SMALL)
            fy -= self.LH
            self._wrapped_text(data.terms, self.MARGIN, fy,
                               max_width=self.INNER_W, size=self.F_SMALL)

        # Page number pinned to bottom margin
        self._text(
            "Page 1/1",
            self.PAGE_W - self.MARGIN,
            self.MARGIN / 2,
            size=self.F_SMALL,
            align="right",
        )

    def _draw_overdue_stamp(self) -> None:
        """Diagonal 'OVERDUE' stamp — mirrors the receipt's PAID stamp."""
        from reportlab.lib.colors import Color

        c = self._canvas
        stamp_color = Color(*self.theme.overdue_stamp, alpha=0.30)

        cx, cy = self.PAGE_W / 2, self.PAGE_H / 2
        c.saveState()
        c.setFillColor(stamp_color)
        c.setStrokeColor(stamp_color)
        c.setFont(self.F_BOLD, 75)
        c.translate(cx, cy)
        c.rotate(45)
        text_w = c.stringWidth("OVERDUE", self.F_BOLD, 75)
        c.drawString(-text_w / 2, -37, "OVERDUE")
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
        """Draw a single line of text at canvas coordinates."""
        from reportlab.lib.colors import black as rl_black
        c = self._canvas
        c.setFont(font, size)
        c.setFillColor(_color(color) if color else rl_black)

        if align == "right":
            c.drawString(x - c.stringWidth(text, font, size), y, text)
        elif align == "center":
            c.drawString(x - c.stringWidth(text, font, size) / 2, y, text)
        else:
            c.drawString(x, y, text)

    def _wrapped_text(
        self,
        text: str,
        x: float,
        y: float,
        max_width: float,
        font: str = "Helvetica",
        size: int = 8,
    ) -> None:
        """Naive word-wrap: draws successive lines of *text* below *y*."""
        c = self._canvas
        c.setFont(font, size)
        words = text.split()
        line: List[str] = []
        for word in words:
            test = " ".join(line + [word])
            if c.stringWidth(test, font, size) <= max_width:
                line.append(word)
            else:
                c.drawString(x, y, " ".join(line))
                y -= self.LH * 0.9
                line = [word]
        if line:
            c.drawString(x, y, " ".join(line))


# ======================================================================
# MAIN – Demo usage
# ======================================================================

if __name__ == "__main__":
    import datetime
    from decimal import Decimal

    data = InvoiceData(
        business=BusinessInfo(
            name="Architech, LLC",
            address_line2="123 Somewhere Street",
            city_state_zip="Your City AZ 12345",
            email="admin@architech.com",
        ),
        client=ClientInfo(
            name="Test Business",
            address_line1="123 Somewhere St",
            address_line2="Melbourne, VIC 3000",
            email="test@test.com",
            attention="Accounts Payable",
        ),
        meta=InvoiceMetadata(
            invoice_number="INV-2024-001",
            order_number="PO-98765",
            invoice_date=datetime.date(2024, 1, 25),
            due_date=datetime.date(2024, 2, 24),
            payment_terms="Net 30",
        ),
        line_items=[
            LineItem(
                qty=Decimal("1.00"),
                description="Web Design",
                details="Custom responsive website — desktop & mobile",
                rate=Decimal("1500.00"),
            ),
            LineItem(
                qty=Decimal("8.00"),
                description="Development",
                details="Front-end implementation (React)",
                rate=Decimal("150.00"),
            ),
            LineItem(
                qty=Decimal("3.00"),
                description="Consulting",
                details="Architecture review & strategy sessions",
                rate=Decimal("200.00"),
                adjustment_pct=Decimal("-10.00"),   # 10 % loyalty discount
            ),
        ],
        tax_rate_pct=Decimal("10.00"),
        payment_url="https://paypal.me/architech",
        bank_name="ANZ Bank",
        account_number="ACC # 1234 1234",
        bsb="",  # BSB not required for international PayPal payments
        payment_instructions=(
            "Payment is due within 30 days of the invoice date. "
            "Late payments incur a 5 % monthly fee."
        ),
        notes="Thank you for your business.",
        terms=(
            "All work remains the intellectual property of Architech, LLC until "
            "payment is received in full. Disputes must be raised within 7 days of "
            "invoice receipt."
        ),
        logo_path="image1.png",
        overdue=False,
    )

    InvoicePDFGenerator(data).generate("demo_invoice.pdf")
    print("Invoice generated: demo_invoice.pdf")