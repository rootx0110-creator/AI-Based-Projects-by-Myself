"""FAT12/16/32 filesystem parser with deleted-file recovery support."""
import struct
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .disk_reader import DiskReader

DELETED_MARK = 0xE5
DIR_ENTRY_END = 0x00
UNKNOWN = "Unknown"


@dataclass
class FSInfo:
    fs_type: str = ""
    sector_size: int = 512
    sectors_per_cluster: int = 1
    reserved_sectors: int = 0
    fat_count: int = 1
    root_entries: int = 0
    total_sectors: int = 0
    fat_size_16: int = 0
    fat_size_32: int = 0
    root_cluster_32: int = 2
    first_data_sector: int = 0
    root_dir_sectors: int = 0
    cluster_size: int = 512
    label: str = ""
    free_clusters_hint: int = 0


@dataclass
class FoundFile:
    name: str
    full_name: str
    ext: str
    size: int
    start_cluster: int
    first_offset: int
    attrs: str
    date_created: str
    date_modified: str
    date_accessed: str
    fs: str = "FAT"
    anci_value: int = 0

    def to_dict(self):
        return {
            "name": self.name,
            "full_name": self.full_name,
            "extension": self.ext,
            "size": self.size,
            "start_cluster": self.start_cluster,
            "first_offset": self.first_offset,
            "attributes": self.attrs,
            "created": self.date_created,
            "modified": self.date_modified,
            "accessed": self.date_accessed,
            "fs": self.fs,
            "status": "Deleted",
        }


def parse_fat_info(reader: DiskReader) -> Optional[FSInfo]:
    sec = reader.read_sector(0)
    if not sec:
        return None
    oem = sec[3:11].decode(errors="ignore")
    info = FSInfo()
    info.sector_size = struct.unpack("<H", sec[11:13])[0]
    if info.sector_size <= 0:
        info.sector_size = 512
    info.sectors_per_cluster = sec[13]
    if info.sectors_per_cluster == 0:
        return None
    info.reserved_sectors = struct.unpack("<H", sec[14:16])[0]
    info.fat_count = sec[16]
    info.root_entries = struct.unpack("<H", sec[17:19])[0]
    ts16 = struct.unpack("<H", sec[19:21])[0]
    info.fat_size_16 = struct.unpack("<H", sec[22:24])[0]
    if info.sector_size == 512 and ts16 == 0:
        # FAT32 extended fields
        ts32 = struct.unpack("<I", sec[32:36])[0]
        info.fat_size_32 = struct.unpack("<I", sec[36:40])[0]
        info.root_cluster_32 = struct.unpack("<I", sec[44:48])[0]
        info.total_sectors = ts32
        info.fs_type = "FAT32"
    else:
        info.fat_size_32 = 0
        info.fat_size_16 = struct.unpack("<H", sec[22:24])[0]
        info.total_sectors = ts16
        # Determine FAT16 vs FAT12
        root_dir_sectors = (info.root_entries * 32 + info.sector_size - 1) // info.sector_size
        data_sectors = info.total_sectors - (
            info.reserved_sectors + info.fat_count * info.fat_size_16 + root_dir_sectors
        )
        if data_sectors < 4085:
            info.fs_type = "FAT12"
        else:
            info.fs_type = "FAT16"
    # For FAT32, fatsz = fat_size_32; else fatsz = fat_size_16
    fatsz = info.fat_size_32 or info.fat_size_16
    info.fat_size_16 = max(info.fat_size_16, info.fat_size_32)
    if fatsz == 0:
        return None
    if info.fs_type == "FAT32":
        info.root_dir_sectors = 0
    else:
        info.root_dir_sectors = (info.root_entries * 32 + info.sector_size - 1) // info.sector_size
    info.first_data_sector = (
        info.reserved_sectors
        + info.fat_count * fatsz
        + info.root_dir_sectors
    )
    info.cluster_size = info.sector_size * info.sectors_per_cluster
    try:
        label = sec[43:54].decode(errors="ignore").strip("\x00 ")
        if label:
            info.label = label
        elif info.fs_type == "FAT32":
            label_fat32 = sec[71:82].decode(errors="ignore").strip("\x00 ")
            if label_fat32:
                info.label = label_fat32
    except Exception:
        pass
    return info


def _read_cluster(reader: DiskReader, info: FSInfo, cluster: int) -> Optional[bytes]:
    if cluster < 2:
        return None
    offset = (info.first_data_sector + (cluster - 2) * info.sectors_per_cluster) * info.sector_size
    try:
        return reader.read(offset, info.cluster_size)
    except Exception:
        return None


def _read_dir_sector_offset(reader: DiskReader, info: FSInfo, cluster: int):
    return (info.first_data_sector + (cluster - 2) * info.sectors_per_cluster) * info.sector_size


def _fat_entry(reader: DiskReader, info: FSInfo, fat_offset: int, cluster: int) -> int:
    """Read the entry in the FAT table for `cluster`."""
    if info.fs_type == "FAT32":
        off = fat_offset + cluster * 4
        data = reader.read(off, 4)
        if len(data) < 4:
            return 0x0FFFFFFF
        return struct.unpack("<I", data)[0] & 0x0FFFFFFF
    elif info.fs_type == "FAT16":
        off = fat_offset + cluster * 2
        data = reader.read(off, 2)
        if len(data) < 2:
            return 0xFFFF
        return struct.unpack("<H", data)[0]
    else:  # FAT12
        byte_off = cluster + (cluster // 2)
        off = fat_offset + byte_off
        data = reader.read(off, 2)
        if len(data) < 2:
            return 0xFFF
        val = struct.unpack("<H", data)[0]
        if cluster & 1:
            return (val >> 4) & 0xFFF
        return val & 0xFFF


def _fat_table_offset(reader: DiskReader, info: FSInfo):
    return info.reserved_sectors * info.sector_size


def _parse_dos_date(word: int) -> str:
    if not word:
        return "Unknown"
    day = word & 0x1F
    month = (word >> 5) & 0x0F
    year = ((word >> 9) & 0x7F) + 1980
    return f"{year}-{month:02d}-{day:02d}"


def _parse_dos_time(word: int) -> str:
    if not word:
        return "00:00"
    sec = (word & 0x1F) * 2
    minute = (word >> 5) & 0x3F
    hour = (word >> 11) & 0x1F
    return f"{hour:02d}:{minute:02d}:{sec:02d}"


def _clean(name: bytes) -> str:
    # Deleted directory entries replace the first char of the name with 0xE5;
    # make it readable as a placeholder.
    name = bytes(0x3F if b == 0xE5 else b for b in name)
    return name.decode("cp437", errors="replace").strip().rstrip("\x00 .").strip()


def _attr_string(attr: int) -> str:
    flags = []
    if attr & 0x01:
        flags.append("RO")
    if attr & 0x02:
        flags.append("HID")
    if attr & 0x04:
        flags.append("SYS")
    if attr & 0x10:
        flags.append("DIR")
    if attr & 0x20:
        flags.append("ARC")
    return ",".join(flags) if flags else "-"


class FATScanner:
    def __init__(self, reader: DiskReader, info: FSInfo, progress_cb=None):
        self.reader = reader
        self.info = info
        self.progress_cb = progress_cb
        self.found: List[FoundFile] = []
        self.entry_count = 0
        self.dir_count = 0
        self.fat_offset = _fat_table_offset(reader, info)

    def scan(self) -> List[FoundFile]:
        if self.info.fs_type == "FAT32":
            self._scan_directory(self.info.root_cluster_32, "/")
        else:
            # scan root dir entries for FAT12/16: located at reserved + FATs
            root_off = (self.info.reserved_sectors
                        + self.info.fat_count * self.info.fat_size_16) * self.info.sector_size
            self._scan_root_dir(root_off, "/")
        return self.found

    def _scan_root_dir(self, root_dir_offset: int, path: str):
        """Scan root directory (FAT12/16) cluster-less area."""
        entries_total = self.info.root_entries
        for idx in range(0, entries_total):
            off = root_dir_offset + idx * 32
            data = self.reader.read(off, 32)
            if len(data) < 32:
                break
            if data[0] == 0x00:
                break
            if data[0] == DELETED_MARK:
                self._handle_deleted_entry(data, idx, root_dir_offset, path)
            else:
                attr = data[11]
                # Skip LFN entries
                if attr == 0x0F:
                    continue
                if attr & 0x10:  # directory (subdir)
                    # recurse
                    first_cluster = struct.unpack("<H", data[26:28])[0]
                    if first_cluster > 1:
                        name = _clean(data[0:8])
                        if name:
                            self._scan_directory(first_cluster, f"{path}{name}/")
            self.entry_count += 1

    def _scan_directory(self, cluster: int, path: str):
        """Scan a FAT32 directory tree from cluster onward."""
        visited = set()
        while isinstance(cluster, int) and cluster > 1 and cluster < 0x0FFFFFF8 and cluster not in visited:
            visited.add(cluster)
            data = _read_cluster(self.reader, self.info, cluster)
            if not data:
                break
            for idx in range(0, len(data), 32):
                ent = data[idx:idx + 32]
                if len(ent) < 32:
                    break
                if ent[0] == 0x00:
                    break
                if ent[0] == DELETED_MARK:
                    self._handle_deleted_entry(
                        ent, idx, _read_dir_sector_offset(self.reader, self.info, cluster), path
                    )
                else:
                    attr = ent[11]
                    if attr == 0x0F:
                        continue
                    if attr & 0x10:
                        fc = struct.unpack("<H", ent[26:28])[0]
                        if fc > 1:
                            name = _clean(ent[0:8])
                            if name and name != "." and name != "..":
                                self._scan_directory(fc, f"{path}{name}/")
                    self.entry_count += 1
            cluster = _fat_entry(self.reader, self.info, self.fat_offset, cluster)
        if self.progress_cb:
            self.progress_cb(self.entry_count, len(self.found))

    def _handle_deleted_entry(self, data: bytes, idx: int, base_offset: int, path: str):
        """Process a deleted (0xE5-marked) directory entry."""
        name_raw = data[0:8]
        ext_raw = data[8:11]
        name = _clean(name_raw)
        ext = _clean(ext_raw)
        if not name:
            return
        attr = data[11]
        if attr == 0x0F:  # LFN
            return
        first_cluster = struct.unpack("<H", data[26:28])[0]
        if self.info.fs_type != "FAT12":
            high = struct.unpack("<H", data[20:22])[0]
            first_cluster = (high << 16) | first_cluster
        size = struct.unpack("<I", data[28:32])[0]
        if first_cluster < 2:
            return
        # offset of first cluster data
        offset = (self.info.first_data_sector + (first_cluster - 2) * self.info.sectors_per_cluster) * self.info.sector_size
        cdate = _parse_dos_date(struct.unpack("<H", data[16:18])[0])
        ctime = _parse_dos_time(struct.unpack("<H", data[14:16])[0])
        mdate = _parse_dos_date(struct.unpack("<H", data[24:26])[0])
        mtime = _parse_dos_time(struct.unpack("<H", data[22:24])[0])
        adate = _parse_dos_date(struct.unpack("<H", data[18:20])[0])
        is_dir = bool(attr & 0x10)
        full_name = f"{name}.{ext}" if ext else name
        if is_dir:
            full_name = f"{path}{full_name}/"
        else:
            full_name = f"{path}{full_name}"
        self.found.append(FoundFile(
            name=name,
            full_name=full_name,
            ext=ext if ext else "dir",
            size=0 if is_dir else size,
            start_cluster=first_cluster,
            first_offset=offset,
            attrs=_attr_string(attr),
            date_created=f"{cdate} {ctime}" if ctime != "00:00" else cdate,
            date_modified=f"{mdate} {mtime}" if mtime != "00:00" else mdate,
            date_accessed=adate,
            anci_value=1 if attr == 0x10 else 0,
        ))