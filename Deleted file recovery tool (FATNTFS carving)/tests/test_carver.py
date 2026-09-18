"""Raw carver test with in-memory disk containing known file signatures."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.file_carver import RawCarver


class BytesReader:
    def __init__(self, data):
        self.data = data
    def read(self, offset, length):
        return self.data[offset:offset+length]
    def read_disk_size(self):
        return len(self.data)
    def close(self):
        pass


def make_jpeg():
    return (b"\xff\xd8\xff\xe0" + b"\x00" * 40000 + b"\xff\xd9")

def make_png():
    return (b"\x89PNG\r\n\x1a\n" + b"\x00"*30000 + b"IEND\xaeB`\x82")

def make_pdf():
    return (b"%PDF-1.4\n" + b"0 0 obj\n<<>>\nendobj\n"*500 + b"%%EOF")

def main():
    blob = bytearray(4_000_000)
    p = 0
    # place jpeg at 100000
    jpeg = make_jpeg()
    blob[100000:100000+len(jpeg)] = jpeg
    png = make_png()
    blob[600000:600000+len(png)] = png
    pdf = make_pdf()
    blob[1_200_000:1_200_000+len(pdf)] = pdf
    reader = BytesReader(bytes(blob))
    carver = RawCarver(reader)
    found = carver.scan()
    exts = sorted(set(f.ext for f in found))
    print("carved:", exts)
    assert "jpg" in exts and "png" in exts and "pdf" in exts, f"missing expected types: {exts}"
    for f in found:
        if f.ext == "jpg":
            assert f.offset == 100000, f"jpg offset wrong: {f.offset}"
            assert f.size >= 40002, f"jpg size too small: {f.size}"
    print("RAW CARVER TESTS PASSED")


if __name__ == "__main__":
    main()