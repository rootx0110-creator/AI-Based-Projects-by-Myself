"""QR-code helpers built on the `qrcode` library (bundled into the exe)."""

import io

import qrcode
from qrcode.constants import ERROR_CORRECT_M

_BORDER = 2
_QR_COLOR = (16, 22, 30)
_BG_COLOR = (255, 255, 255)


def _make(text: str, size: int) -> "qrcode.QRCode":
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=size,
        border=_BORDER,
    )
    qr.add_data(text)
    qr.make(fit=True)
    return qr


def qr_image(text: str, size: int = 8):
    """PIL Image intended for GUI previews."""
    qr = _make(text, size)
    img = qr.make_image(fill_color=_QR_COLOR, back_color=_BG_COLOR)
    return img.convert("RGB")


def qr_png_bytes(text: str, size: int = 6) -> bytes:
    """PNG bytes in memory (for embedding in HTML reports)."""
    img = qr_image(text, size)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def qr_data_uri(text: str, size: int = 6) -> str:
    """``data:image/png;base64,...`` for a self-contained HTML report."""
    import base64

    return "data:image/png;base64," + base64.b64encode(qr_png_bytes(text, size)).decode("ascii")