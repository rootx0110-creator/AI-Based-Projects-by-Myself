"""Synthetic NTFS MFT test for NtfsAsminer + RecoveryEngine."""
import struct
import sys
import os
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.ntfs_parser import NtfsAsminer, parse_ntfs_boot, _decode_ntfs_time
from app.core.recovery import RecoveryEngine

SECTOR = 512
SPC = 8
CLUSTER = SECTOR * SPC
TOTAL_CLUSTERS = 200
IMAGE = bytearray(TOTAL_CLUSTERS * CLUSTER)


def encode_ntfs_time(dt):
    epoch = datetime.datetime(1601, 1, 1)
    us = int((dt - epoch).total_seconds() * 10_000_000)
    return us & 0xFFFFFFFFFFFFFFFF


def build_boot():
    img = IMAGE
    img[0:512] = b"\x00" * 512
    img[0] = 0xEB
    img[1] = 0x52
    img[2] = 0x90
    img[3:11] = b"NTFS    "
    struct.pack_into("<H", img, 0x0B, SECTOR)
    img[0x0D] = SPC
    struct.pack_into("<H", img, 0x0E, 0)
    struct.pack_into("<Q", img, 0x28, TOTAL_CLUSTERS // SPC + 0)  # total sectors
    struct.pack_into("<Q", img, 0x30, 10)   # mft_lcn
    struct.pack_into("<Q", img, 0x38, 10)   # mft mirror lcn
    img[510:512] = b"\x55\xaa"


def build_mft(cluster=10):
    base = cluster * CLUSTER
    # MFT record 0 (index 0)
    record0 = bytearray(1024)
    record0[0:4] = b"FILE"
    struct.pack_into("<H", record0, 0x04, 0x18)
    struct.pack_into("<H", record0, 0x06, 3)
    struct.pack_into("<H", record0, 0x14, 0x38)  # attrs offset
    struct.pack_into("<H", record0, 0x16, 0x0001)  # in use
    IMAGE[base: base + 1024] = record0


def make_mft_record(index, filename, data=b"", in_use=False):
    rec = bytearray(1024)
    rec[0:4] = b"FILE"
    struct.pack_into("<H", rec, 0x04, 0x18)
    struct.pack_into("<H", rec, 0x06, 3)
    struct.pack_into("<H", rec, 0x14, 0x38)  # attrs offset
    flags = 0x0001 if in_use else 0x0000
    struct.pack_into("<H", rec, 0x16, flags)
    struct.pack_into("<I", rec, 0x18, 0)  # used size
    struct.pack_into("<I", rec, 0x1C, 1024)
    struct.pack_into("<I", rec, 0x2C, index)

    pos = 0x38

    # DATA attribute (resident) - put first so we can reference
    data_attr = bytearray(256)
    struct.pack_into("<I", data_attr, 0x00, 0x80)  # type DATA
    content = data
    attr_len = 24 + len(content)
    struct.pack_into("<I", data_attr, 0x04, attr_len)
    data_attr[0x08] = 0  # resident
    data_attr[0x09] = 0  # name len
    struct.pack_into("<H", data_attr, 0x0A, 0x18)
    struct.pack_into("<H", data_attr, 0x0C, 0)
    struct.pack_into("<H", data_attr, 0x0E, 1)
    struct.pack_into("<I", data_attr, 0x10, len(content))
    struct.pack_into("<H", data_attr, 0x14, 0x18)
    data_attr[0x16] = 0
    data_attr[0x18:0x18+len(content)] = content
    rec[pos:pos+attr_len] = data_attr[:attr_len]
    pos += attr_len

    # FILE_NAME attribute
    fn = struct.pack("<Q", 5)  # parent ref
    t = encode_ntfs_time(datetime.datetime(2025, 6, 1, 12, 0, 0))
    fn += struct.pack("<Q", t) + struct.pack("<Q", t) + struct.pack("<Q", t) + struct.pack("<Q", t)
    fn += struct.pack("<Q", 4096) + struct.pack("<Q", len(content))
    fn += struct.pack("<I", 0x20) + struct.pack("<I", 0)
    nb = filename.encode("utf-16-le")
    fn += bytes([len(nb) // 2, 1])
    fn += nb
    fn_attr = bytearray(256)
    fn_len = 24 + len(fn)
    struct.pack_into("<I", fn_attr, 0x00, 0x30)
    struct.pack_into("<I", fn_attr, 0x04, fn_len)
    fn_attr[0x08] = 0
    fn_attr[0x09] = 0
    struct.pack_into("<H", fn_attr, 0x0A, 0x18)
    struct.pack_into("<H", fn_attr, 0x0C, 0)
    struct.pack_into("<H", fn_attr, 0x0E, 2)
    struct.pack_into("<I", fn_attr, 0x10, len(fn))
    struct.pack_into("<H", fn_attr, 0x14, 0x18)
    fn_attr[0x16] = 0
    fn_attr[0x18:0x18+len(fn)] = fn
    rec[pos:pos+fn_len] = fn_attr[:fn_len]
    pos += fn_len

    # end marker
    struct.pack_into("<I", rec, pos, 0xFFFFFFFF)
    struct.pack_into("<I", rec, 0x18, pos + 4)
    return bytes(rec)


class BytesReader:
    def __init__(self, d):
        self.d = d
    def read(self, offset, length):
        return self.d[offset:offset+length]
    def read_sector(self, sector, sector_size=512):
        return self.d[sector*sector_size:(sector+1)*sector_size]
    def read_disk_size(self):
        return len(self.d)
    def close(self):
        pass


def make_mft_record_nr(index, filename, runs, data_size, in_use=False):
    """Non-resident DATA attribute with cluster runs."""
    rec = bytearray(1024)
    rec[0:4] = b"FILE"
    struct.pack_into("<H", rec, 0x04, 0x18)
    struct.pack_into("<H", rec, 0x06, 3)
    struct.pack_into("<H", rec, 0x14, 0x38)
    flags = 0x0001 if in_use else 0x0000
    struct.pack_into("<H", rec, 0x16, flags)
    struct.pack_into("<I", rec, 0x1C, 1024)
    struct.pack_into("<I", rec, 0x2C, index)
    pos = 0x38

    # Build run list bytes
    run_bytes = b""
    prev_lcn = 0
    for lcn, length in runs:
        delta = lcn - prev_lcn
        prev_lcn = lcn
        # length byte count fits in 1 byte for small values
        l1 = length.to_bytes(1, "little")
        d_bytes = delta.to_bytes(1, "little", signed=True)
        n = max(len(l1), 1)
        m = len(d_bytes)
        header = (m << 4) | n
        run_bytes += bytes([header]) + l1 + d_bytes
    run_bytes += b"\x00"

    attr_len = 64 + len(run_bytes)
    struct.pack_into("<I", rec, pos, 0x80)       # DATA
    struct.pack_into("<I", rec, pos + 4, attr_len)
    rec[pos + 8] = 1                                # non-resident
    rec[pos + 9] = 0
    struct.pack_into("<H", rec, pos + 10, 0x40)
    struct.pack_into("<H", rec, pos + 12, 0)
    struct.pack_into("<H", rec, pos + 14, 3)
    struct.pack_into("<Q", rec, pos + 16, 0)        # start VCN
    struct.pack_into("<Q", rec, pos + 24, 1)        # last VCN
    struct.pack_into("<H", rec, pos + 32, 0x40)     # run list offset
    struct.pack_into("<Q", rec, pos + 40, 4096)     # allocated size
    struct.pack_into("<Q", rec, pos + 48, data_size)
    struct.pack_into("<Q", rec, pos + 56, data_size)
    rec[pos + 64: pos + 64 + len(run_bytes)] = run_bytes
    pos += attr_len

    fn = struct.pack("<Q", 5)
    t = encode_ntfs_time(datetime.datetime(2025, 6, 1, 12, 0, 0))
    fn += struct.pack("<Q", t) * 4
    fn += struct.pack("<Q", 4096) + struct.pack("<Q", data_size)
    fn += struct.pack("<I", 0x20) + struct.pack("<I", 0)
    nb = filename.encode("utf-16-le")
    fn += bytes([len(nb) // 2, 1]) + nb
    fn_len = 24 + len(fn)
    struct.pack_into("<I", rec, pos, 0x30)
    struct.pack_into("<I", rec, pos + 4, fn_len)
    rec[pos + 8] = 0
    rec[pos + 9] = 0
    struct.pack_into("<H", rec, pos + 10, 0x18)
    struct.pack_into("<H", rec, pos + 14, 4)
    struct.pack_into("<I", rec, pos + 16, len(fn))
    struct.pack_into("<H", rec, pos + 20, 0x18)
    rec[pos + 24: pos + 24 + len(fn)] = fn
    pos += fn_len
    struct.pack_into("<I", rec, pos, 0xFFFFFFFF)
    struct.pack_into("<I", rec, 0x18, pos + 4)
    return bytes(rec)


def main():
    build_boot()
    build_mft(10)
    # resident deleted record index 1, in-use index 2
    content = b"NTFS RESIDENT DATA FOR RECOVERY TESTS" * 12
    rec1 = make_mft_record(1, "deleted_photo.jpg", data=content, in_use=False)
    IMAGE[10 * CLUSTER + 1024: 10 * CLUSTER + 2048] = rec1
    rec2 = make_mft_record(2, "live_file.txt", data=b"LIVE", in_use=True)
    IMAGE[10 * CLUSTER + 2048: 10 * CLUSTER + 3072] = rec2

    # non-resident deleted record index 3, data in clusters 60-63
    nr_data = bytes(range(256)) * 64  # 16 KB
    for i, cl in enumerate(range(60, 64)):
        IMAGE[cl * CLUSTER: cl * CLUSTER + CLUSTER] = nr_data[i*CLUSTER:(i+1)*CLUSTER]
    rec3 = make_mft_record_nr(3, "big_video.avi", [(60, 4)], len(nr_data), in_use=False)
    IMAGE[10 * CLUSTER + 3072: 10 * CLUSTER + 4096] = rec3

    reader = BytesReader(bytes(IMAGE))
    boot = parse_ntfs_boot(reader)
    miner = NtfsAsminer(reader, boot)
    found = miner.scan(max_records=50)
    names = sorted(f.file_name for f in found)
    print("found:", names)
    assert found[0].file_name == "deleted_photo.jpg", found[0].file_name
    assert len(found) == 2, f"expected 2 deleted records, got {len(found)}"

    eng = RecoveryEngine(reader)
    got = eng.recover_ntfs_record(boot, found[0])
    assert got == content, "resident mismatch"
    nr_rec = [f for f in found if f.file_name == "big_video.avi"][0]
    got_nr = eng.recover_ntfs_record(boot, nr_rec)
    assert got_nr == nr_data, f"non-resident mismatch (len {len(got_nr or b'')} vs {len(nr_data)})"
    print("NTFS RECOVERY OK (resident + non-resident runs)")
    assert _decode_ntfs_time(encode_ntfs_time(datetime.datetime(2025, 6, 1, 12, 0, 0))) == "2025-06-01 12:00:00"
    print("ALL NTFS TESTS PASSED")


if __name__ == "__main__":
    main()