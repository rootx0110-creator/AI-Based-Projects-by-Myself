"""File magic-byte signature database used to identify unknown binaries."""

MAGIC_DB = [
    (b"\x7fELF", "ELF executable"),
    (b"MZ", "DOS/PE Windows executable"),
    (b"PK\x03\x04", "ZIP archive"),
    (b"PK\x05\x06", "ZIP archive (empty)"),
    (b"PK\x07\x08", "ZIP archive (spanned)"),
    (b"\x1f\x8b", "GZIP archive"),
    (b"\x1f\x9d", "Compress (.Z)"),
    (b"\x42\x5a\x68", "BZip2 archive"),
    (b"7z\xbc\xaf\x27\x1c", "7-Zip archive"),
    (b"\xfd7zXZ\x00", "XZ archive"),
    (b"Rar!\x1a\x07", "RAR archive"),
    (b"\x28\xb5\x2f\xfd", "Zstandard archive (Zstd)"),
    (b"%PDF-", "PDF document"),
    (b"\xff\xd8\xff", "JPEG image"),
    (b"\x89PNG\r\n\x1a\n", "PNG image"),
    (b"GIF87a", "GIF image (87a)"),
    (b"GIF89a", "GIF image (89a)"),
    (b"BM", "BMP image"),
    (b"II*\x00", "TIFF image (little-endian)"),
    (b"MM\x00*", "TIFF image (big-endian)"),
    (b"RIFF", "RIFF container (WAV/AVI/WebP)"),
    (b"OggS", "Ogg container"),
    (b"\x00\x00\x01\xba", "MPEG program stream"),
    (b"\x49\x44\x33", "MP3 (ID3 tag)"),
    (b"ID3", "MP3 (ID3 tag)"),
    (b"fLaC", "FLAC audio"),
    (b"\x00\x00\x00\x18ftypmp42", "MP4 video"),
    (b"ftyp", "ISO Base Media (MP4/MOV/M4A)"),
    (b"\x1aE\xdf\xa3", "Matroska/WebM"),
    (b"{\\rtf", "RTF document"),
    (b"<?xml", "XML document"),
    (b"<!DOCTYPE", "HTML/SGML document"),
    (b"<html", "HTML document"),
    (b"#!", "Shell script / interpreter script"),
    (b".ELF", "ELF (perl-safe style)"),
    (b"jar", "Java archive (note: false positive risk)"),
    (b"\xca\xfe\xba\xbe", "Java class / Mach-O fat"),
    (b"\xcf\xfa\xed\xfe", "Mach-O (little-endian 32-bit)"),
    (b"\xce\xfa\xed\xfe", "Mach-O (little-endian 64-bit)"),
    (b"\xfe\xed\xfa\xce", "Mach-O (big-endian 32-bit)"),
    (b"\xfe\xed\xfa\xcf", "Mach-O (big-endian 64-bit)"),
    (b"\x64\x65\x78\x0a\x30\x33\x35\x00", "DEX (Dalvik/Android)"),
    (b"\x30\x82", "ASN.1 DER / certificate"),
    (b"\x00\x00\x00\x0c", "Animated cursor / unknown"),
    (b"SQLite format 3\x00", "SQLite database"),
    (b"\x00\x01\x00\x00", "TrueType font hint"),
    (b"OTTO", "OpenType font"),
    (b"ttcf", "TrueType font collection"),
    (b"wOFF", "Web Open Font Format"),
    (b"wOF2", "Web Open Font Format 2"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "OLE2 / Compound Document"),
    (b"{\\fonttbl", "RTF font table"),
    (b"\xef\xbb\xbf", "UTF-8 BOM text"),
    (b"\xff\xfe", "UTF-16 LE BOM text"),
    (b"\xfe\xff", "UTF-16 BE BOM text"),
]


def identify(raw: bytes) -> str:
    """Return the best-matching file type description for raw bytes."""
    best = "Unknown binary data"
    best_len = 0
    for magic, name in MAGIC_DB:
        if raw.startswith(magic) and len(magic) > best_len:
            best = name
            best_len = len(magic)
    if best_len == 0:
        try:
            raw.decode("ascii")
            best = "Plain ASCII text"
        except UnicodeDecodeError:
            pass
    return best


def head(raw: bytes, size: int = 16) -> str:
    """Return hexadecimal and printable representation of the leading bytes."""
    if len(raw) > size:
        raw = raw[:size]
    return raw.hex(" ").upper()