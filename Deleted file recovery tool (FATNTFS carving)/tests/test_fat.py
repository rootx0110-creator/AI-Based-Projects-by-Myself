"""Synthetic FAT12 image test for FATScanner + RecoveryEngine."""
import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.fat_parser import parse_fat_info, FATScanner
from app.core.recovery import RecoveryEngine

SECTOR = 512
CLUSTERS = 256
IMAGE_SIZE = SECTOR * 64  # reserved 1, FAT 9 -> data start at sector 10..64
# Build a minimal FAT12 image
BPS = 512
SPC = 1
RESERVED = 1
NFATS = 1
ROOT_ENTRIES = 32
TOTAL_SECTORS = 64
FATSZ = 4  # 256 entries * 1.5 avg / 512 => ~1 sector, use 2
fs_type = "FAT12"

def build_image():
    img = bytearray(TOTAL_SECTORS * BPS)
    # BPB standard layout: bps(H) spc(B) reserved(H) nfats(B) root(H) total16(H)
    # media(B) fatsz16(H) spt(H) heads(H) hidden(I) total32(I)
    bpb = struct.pack("<HBHBHHBHHHII", BPS, SPC, RESERVED, NFATS, ROOT_ENTRIES,
                      TOTAL_SECTORS, 0xF8, FATSZ, 0, 0, 0, 0)
    img[0x0B:0x0B + len(bpb)] = bpb
    img[3:11] = b"MSDOS5.0".ljust(8, b" ")
    img[36:40] = (0).to_bytes(4, "little")
    img[510:512] = b"\x55\xaa"

    fat_off = RESERVED * BPS
    # FAT[0] = 0xFFF (media), FAT[1] = 0xFFF
    img[fat_off] = 0xF0
    img[fat_off+1] = 0xFF
    img[fat_off+2] = 0xFF
    img[fat_off+3] = 0xFF
    # FAT12 3-byte packed entries for clusters 2 and 3 (e2 -> 3, e3 -> EOF)
    e2, e3 = 0x003, 0xFFF
    img[fat_off + 3] = e2 & 0xFF
    img[fat_off + 4] = ((e2 >> 8) | (e3 << 4)) & 0xFF
    img[fat_off + 5] = (e3 >> 4) & 0xFF

    # data start sector
    data_start = RESERVED + NFATS * FATSZ + (ROOT_ENTRIES * 32 + BPS - 1)//BPS
    # write file content into cluster 2 (sector = data_start + 0)
    content = b"HELLO DELETED FILE RECOVERY CONTENT - \x00TEST\x00DATA" * 10
    sec_off = data_start * BPS
    img[sec_off: sec_off + len(content)] = content

    # root directory entry: deleted file marker 0xE5
    root_off = (RESERVED + NFATS * FATSZ) * BPS
    name8 = b"DELETED1"
    ext3 = b"TXT"
    attr = 0x20
    first = bytearray(name8.ljust(8) + ext3.ljust(3))
    first[0] = 0xE5
    high_clust = 0
    clust_low = 2
    create_time = 0x0000
    create_date = 0x4A21
    access_date = 0x4A21
    size = len(content)
    entry = bytes(first) + bytes([attr]) + struct.pack("<HHHHH",
                                                        0, create_time, create_date, access_date, high_clust)
    entry += struct.pack("<HHH", 0, 0, clust_low) + struct.pack("<I", size)
    img[root_off: root_off + 32] = entry

    return bytes(img), content, data_start, sec_off


class BytesReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
    def read(self, offset, length):
        self.pos = offset
        return self.data[offset:offset + length]
    def read_sector(self, sector, sector_size=512):
        return self.data[sector*sector_size:(sector+1)*sector_size]
    def read_disk_size(self):
        return len(self.data)
    def close(self):
        pass


def main():
    img, content, data_start, sec_off = build_image()
    print("image size:", len(img))
    reader = BytesReader(img)
    fs = parse_fat_info(reader)
    print("FS:", fs.fs_type, "sector_size", fs.sector_size, "data_start", fs.first_data_sector)
    sc = FATScanner(reader, fs)
    found = sc.scan()
    print("found entries:", len(found))
    assert len(found) == 1, f"expected 1 deleted file, found {len(found)}"
    f = found[0]
    print("file:", f.name, f.ext, "size", f.size, "cluster", f.start_cluster)
    eng = RecoveryEngine(reader)
    recovered = eng.recover_fat_file(fs, f.start_cluster, f.size)
    print("recovered len:", len(recovered) if recovered else None)
    assert recovered == content, "recovered bytes mismatch!"
    print("RECOVERY OK: bytes match exactly")
    print("ALL FAT TESTS PASSED")


if __name__ == "__main__":
    main()