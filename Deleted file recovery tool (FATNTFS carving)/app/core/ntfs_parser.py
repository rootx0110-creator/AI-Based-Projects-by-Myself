"""NTFS filesystem parser focusing on MFT record recovery for deleted files."""
import struct
from dataclasses import dataclass
from typing import List, Optional

from .disk_reader import DiskReader

MFT_SIGNATURE = b"FILE"
ATTRIBUTE_STANDARD_INFO = 0x10
ATTRIBUTE_ATTRIBUTE_LIST = 0x20
ATTRIBUTE_FILE_NAME = 0x30
ATTRIBUTE_DATA = 0x80
ATTRIBUTE_INDEX_ROOT = 0x90
FILE_RECORD_FLAG_IN_USE = 0x0001


@dataclass
class NtfsRecord:
    mft_index: int
    is_in_use: bool
    is_deleted: bool
    file_name: str = ""
    namespace: int = 0
    created: str = ""
    modified: str = ""
    accessed: str = ""
    data_size: int = 0
    is_resident_data: bool = False
    data_runs: List[tuple] = None  # (offset_lcn_delta, length_clusters)
    data_first_vcn: int = 0
    resident_data_offset: int = 0
    resident_data_len: int = 0
    attr_name: str = ""
    extended: bool = False
    file_record_start: int = 0

    def __post_init__(self):
        if self.data_runs is None:
            self.data_runs = []

    def to_dict(self):
        return {
            "name": self.file_name,
            "full_name": self.file_name,
            "extension": self.file_name.rsplit(".", 1)[-1] if "." in self.file_name else "",
            "size": self.data_size,
            "start_cluster": "",
            "first_offset": self.file_record_start,
            "attributes": "Deleted(ntfs)",
            "created": self.created,
            "modified": self.modified,
            "accessed": self.accessed,
            "fs": "NTFS",
            "status": "Deleted",
        }


def parse_ntfs_boot(reader: DiskReader) -> Optional[dict]:
    sec = reader.read_sector(0)
    if not sec or len(sec) < 512:
        return None
    if sec[3:11] != b"NTFS    ":
        return None
    bps = struct.unpack("<H", sec[11:13])[0]
    spc = sec[13]
    mft_lcn = struct.unpack("<Q", sec[48:56])[0]
    mft_mirror_lcn = struct.unpack("<Q", sec[56:64])[0]
    total_sectors = struct.unpack("<Q", sec[40:48])[0]
    return {
        "sector_size": bps,
        "sectors_per_cluster": spc,
        "cluster_size": bps * spc,
        "mft_lcn": mft_lcn,
        "mft_mirror_lcn": mft_mirror_lcn,
        "total_sectors": total_sectors,
        "label": "NTFS",
    }


def _decode_ntfs_time(raw: int) -> str:
    if not raw:
        return "Unknown"
    try:
        import datetime
        epoch = datetime.datetime(1601, 1, 1, 0, 0, 0)
        us = raw // 10
        dt = epoch + datetime.timedelta(microseconds=us)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "Unknown"


def _decode_utf16(bytes_data: bytes) -> str:
    try:
        return bytes_data.decode("utf-16-le", errors="replace")
    except Exception:
        return ""


class NtfsAsminer:
    """Miner scans the raw MFT file records."""

    def __init__(self, reader: DiskReader, boot: dict, progress_cb=None):
        self.reader = reader
        self.boot = boot
        self.cluster_size = boot["cluster_size"]
        self.sector_size = boot["sector_size"]
        self.mft_lcn = boot.get("mft_lcn", 0)
        self.progress_cb = progress_cb
        self.found: List[NtfsRecord] = []

    def _abs_offset(self, lcn: int) -> int:
        return lcn * self.cluster_size

    def read_mft_record(self, record_num: int) -> Optional[bytes]:
        # In live filesystems MFT may itself be fragmented; we handle the
        # common case where the MFT is contiguous near its LCN.
        off = self._abs_offset(self.mft_lcn) + record_num * 1024
        try:
            return self.reader.read(off, 1024)
        except Exception:
            return None

    def scan(self, max_records: int = 200000) -> List[NtfsRecord]:
        record_size = 1024  # typical fixed 1KB MFT entries
        chunk_sectors = 2048
        counter = 0
        while counter < max_records:
            rec = self.read_mft_record(counter)
            if not rec or len(rec) < 50:
                break
            if rec[0:4] != MFT_SIGNATURE:
                # Might still be just an empty area; keep scanning
                counter += 1
                continue
            flags = struct.unpack("<H", rec[22:24])[0]
            in_use = bool(flags & FILE_RECORD_FLAG_IN_USE)
            if not in_use:
                nrec = self._parse_attributes(rec, counter)
                if nrec:
                    self.found.append(nrec)
            counter += 1
            if counter % 512 == 0 and self.progress_cb:
                self.progress_cb(counter, len(self.found))
            if counter >= max_records:
                break
        if self.progress_cb:
            self.progress_cb(counter, len(self.found))
        return self.found

    def _parse_attributes(self, rec: bytes, record_num: int) -> Optional[NtfsRecord]:
        nrec = NtfsRecord(
            mft_index=record_num,
            is_in_use=False,
            is_deleted=True,
            file_record_start=self._abs_offset(self.mft_lcn) + record_num * 1024,
        )
        attrs_offset = struct.unpack("<H", rec[20:22])[0]
        attrs_end = struct.unpack("<I", rec[24:28])[0]
        if attrs_offset < 24 or attrs_offset >= len(rec):
            return None
        pos = attrs_offset
        while pos + 4 < len(rec):
            attr_type = struct.unpack("<I", rec[pos:pos + 4])[0]
            if attr_type == 0xFFFFFFFF:
                break
            len_attr = struct.unpack("<I", rec[pos + 4:pos + 8])[0]
            if len_attr < 16 or pos + len_attr > len(rec):
                break
            non_resident = rec[pos + 8] & 0x01
            name_len = rec[pos + 9]
            name_offset = struct.unpack("<H", rec[pos + 10:pos + 12])[0]
            if attr_type == ATTRIBUTE_FILE_NAME:
                content_off = pos + struct.unpack("<H", rec[pos + 20:pos + 22])[0]
                name_len_chars = struct.unpack("<B", rec[content_off + 64:content_off + 65])[0]
                name_bytes = rec[content_off + 66: content_off + 66 + name_len_chars * 2]
                parsed_name = _decode_utf16(name_bytes)
                nrec.file_name = parsed_name or f"<$MFT-{record_num}>"
                nrec.namespace = rec[content_off + 65] if content_off + 65 < len(rec) else 0
                created = _decode_ntfs_time(struct.unpack("<Q", rec[content_off: content_off + 8])[0])
                modified = _decode_ntfs_time(struct.unpack("<Q", rec[content_off + 8: content_off + 16])[0])
                affected = _decode_ntfs_time(struct.unpack("<Q", rec[content_off + 24: content_off + 32])[0])
                nrec.created = created
                nrec.modified = modified
                nrec.accessed = affected
            elif attr_type == ATTRIBUTE_DATA:
                if not non_resident:
                    nrec.is_resident_data = True
                    content_len = struct.unpack("<I", rec[pos + 16:pos + 20])[0]
                    content_off = pos + struct.unpack("<H", rec[pos + 20:pos + 22])[0]
                    nrec.data_size = content_len
                    nrec.resident_data_offset = content_off
                    nrec.resident_data_len = content_len
                else:
                    data_size = struct.unpack("<Q", rec[pos + 48:pos + 56])[0]
                    run_off = pos + struct.unpack("<H", rec[pos + 32:pos + 34])[0]
                    nrec.data_size = data_size
                    nrec.data_runs = parse_data_runs(rec[run_off:])
            pos += len_attr
        if not nrec.file_name:
            return None
        # Only keep records with some recoverable aspect.
        if nrec.data_size > 0 or nrec.file_name.startswith("$"):
            return nrec
        return None


def parse_data_runs(run_bytes: bytes) -> List[tuple]:
    """Parse NTFS data-run list: (lcn_delta, clusters)."""
    runs = []
    i = 0
    lcn = 0
    while i < len(run_bytes):
        header = run_bytes[i]
        if header == 0:
            break
        size = header & 0x0F
        offset_len = (header >> 4) & 0x0F
        i += 1
        if i + size + offset_len > len(run_bytes):
            break
        length = int.from_bytes(run_bytes[i:i + size], "little") if size else 0
        offset = int.from_bytes(
            run_bytes[i + size: i + size + offset_len], "little", signed=True
        ) if offset_len else 0
        i += size + offset_len
        lcn += offset
        runs.append((lcn, length))
    return runs