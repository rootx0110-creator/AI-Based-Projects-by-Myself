"""Raw file carver that scans sectors for magic-byte signatures."""
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional

from .disk_reader import DiskReader
from ..utils.file_types import CARVING_SIGNATURES, EXT_CANON

# Extension → (funktional footer detection)
# We detect the end of files using extended footer/frame detectors.

MIN_CARVE_SIZE = 8 * 1024  # avoid false positives smaller than this


@dataclass
class CarvedFile:
    ext: str
    name: str
    offset: int
    size: int
    signature: str

    def to_dict(self):
        return {
            "name": self.name,
            "full_name": self.name,
            "extension": self.ext,
            "size": self.size,
            "start_cluster": "",
            "first_offset": self.offset,
            "attributes": "Carved",
            "created": "Unknown",
            "modified": "Unknown",
            "accessed": "Unknown",
            "fs": "RAW",
            "status": "Carved",
        }


class RawCarver:
    def __init__(self, reader: DiskReader, progress_cb=None, chunk_sectors: int = 2048):
        self.reader = reader
        self.chunk_sectors = chunk_sectors
        self.progress_cb = progress_cb
        self.found: List[CarvedFile] = []
        self.sector_size = 512
        self.scanned_bytes = 0

    def scan(self, disk_size: Optional[int] = None, signature_whitelist: Optional[List[str]] = None) -> List[CarvedFile]:
        """Scan raw device from offset 0 to disk_size (or until EOF)."""
        if not disk_size:
            ds = self.reader.read_disk_size()
            if not ds:
                # Fall back to MBR partition-table estimate
                try:
                    mbr = self.reader.read(0, 512)
                except Exception:
                    mbr = None
                ds = 0
                if mbr and len(mbr) >= 512:
                    largest = 0
                    for part in range(4):
                        p = mbr[446 + part * 16: 446 + part * 16 + 16]
                        rel = struct.unpack("<I", p[8:12])[0] if len(p) == 16 else 0
                        num = struct.unpack("<I", p[12:16])[0] if len(p) == 16 else 0
                        largest = max(largest, (rel + num) * 512)
                    ds = largest
            disk_size = ds or 2_000_000_000  # default 2 GiB estimate
        if disk_size <= 0:
            return []

        sigs = CARVING_SIGNATURES
        if signature_whitelist:
            sigs = {k: v for k, v in sigs.items() if k in signature_whitelist}

        from collections import defaultdict
        sig_bytes_map = defaultdict(list)
        for ext, lst in sigs.items():
            for s in lst:
                try:
                    b = bytes.fromhex(s)
                except Exception:
                    b = b""
                if b:
                    sig_bytes_map[ext].append(b)

        chunk_size = 2 * 1024 * 1024
        overlap = 64
        cursor = 0
        prev_tail = b""
        while cursor < disk_size:
            data = self.reader.read(cursor, chunk_size)
            if not data:
                break
            window = prev_tail + data
            base = cursor - len(prev_tail)
            for ext, patterns in sig_bytes_map.items():
                for pattern in patterns:
                    pos = 0
                    while True:
                        idx = window.find(pattern, pos)
                        if idx < 0:
                            break
                        abs_off = max(base + idx, 0)
                        self._try_extract(ext, abs_off, len(pattern))
                        pos = idx + 1
            prev_tail = window[-overlap:] if len(window) >= overlap else window
            cursor += len(data)
            self.scanned_bytes = cursor
            if cursor % (chunk_size * 4) == 0 and self.progress_cb:
                self.progress_cb(cursor, disk_size)
        if self.progress_cb:
            self.progress_cb(disk_size, disk_size)
        return self.found

    def _detect_end(self, ext: str, start_off: int, sigbytes: bytes) -> Optional[int]:
        """Try to determine the file end offset for a found signature."""
        base = start_off + len(sigbytes)
        try:
            if ext == "JPEG":
                end = self._search_footer(base + 16, 400 * 1024 * 1024,
                                          b"\xff\xd9")
                return end + 2 if end else None
            if ext == "PNG":
                end = self._search_footer(base, 50 * 1024 * 1024,
                                          b"\x49\x45\x4e\x44\xae\x42\x60\x82")
                return end + 8 if end else None
            if ext in ("GIF", "GIF89a"):
                end = self._search_footer(base, 50 * 1024 * 1024, b"\x3b")
                return end + 1 if end else None
            if ext == "PDF":
                # Find %%EOF footer
                end = self._search_footer(base, 40 * 1024 * 1024, b"%%EOF")
                return end + 5 if end else None
            if ext in ("ZIP", "DOCX", "XLSX", "PPTX", "JAR", "APK", "ZIPX", "XPI"):
                # central directory end signature EOCD
                end = self._search_footer(base, 100 * 1024 * 1024,
                                          b"\x50\x4b\x05\x06")
                return end + 22 if end else None
            if ext in ("DOC", "XLS", "PPT", "MDB", "MSG", "WPS"):
                end = self._search_footer(base, 50 * 1024 * 1024,
                                          b"\x00\x00\x00\x00")
                return end if end else None
            if ext == "RAR":
                end = self._search_footer(base, 20 * 1024 * 1024,
                                          b"\x52\x61\x72\x21\x1a\x07\x00")
                return end if end else None
            if ext == "MP3":
                # mp3 same-frame detection heuristic: find 3 consecutive
                # frames OR a large span of 0xFFE
                end = self._search_mp3_end(base, 20 * 1024 * 1024)
                return end if end else None
            if ext in ("MP4", "MOV"):
                end = self._search_footer(base, 200 * 1024 * 1024, b"mdat")
                return end if end else None
            if ext in ("AVI", "WAV", "WEBP", "RIFF"):
                end = self._search_riff_end(base)
                return end if end else None
            if ext == "SQLITE":
                # find header page size & read schema — simpler: search footer
                # for 'SQLite format 3' repeated big bytes, then use page count
                end = self._search_footer(base, 100 * 1024 * 1024,
                                          b"sqlite_autoindex")
                return end if end else None
            if ext == "EXE":
                end = self._search_footer(base, 10 * 1024 * 1024,
                                          b"\x00\x00\x00\x00\x00\x00")
                return end if end else None
            if ext == "ICO":
                return base + 24 * 1024
            if ext == "HTM" or ext == "HTML":
                end = self._search_footer(base, 20 * 1024 * 1024, b"</html>")
                return end + 7 if end else None
            if ext == "XML":
                end = self._search_footer(base, 20 * 1024 * 1024, b"</")
                return end + 2 if end else None
            if ext == "BMP":
                # get width & height then compute minimum size
                try:
                    w = struct.unpack("<i", self.reader.read(start_off + 18, 4))[0]
                    h = struct.unpack("<i", self.reader.read(start_off + 22, 4))[0]
                    bpp = struct.unpack("<H", self.reader.read(start_off + 28, 2))[0]
                    row_size = (w * bpp + 31) // 32 * 4
                    size = 54 + row_size * abs(h)
                    return start_off + size
                except Exception:
                    return None
            if ext == "TIFF":
                # compute using IFD — skip
                return base + 10 * 1024 * 1024
            if ext == "DLL":
                return self._search_footer(base, 5 * 1024 * 1024,
                                           b"\x00\x00\x00\x00") or None
            if ext == "FLV":
                # 4-byte data size after header
                try:
                    dsz = struct.unpack("<I",
                            self.reader.read(start_off + 5, 4))[0]
                    return start_off + 13 + dsz
                except Exception:
                    return start_off + 16 * 1024
        except Exception:
            return None
        # generic: empty detection — just carve a default
        return None

    def _search_footer(self, start: int, limit: int, footer: bytes) -> Optional[int]:
        if limit <= 0:
            return None
        pos = start
        read_size = 64 * 1024
        while pos < start + limit:
            data = self.reader.read(pos, read_size)
            if not data:
                return None
            idx = data.find(footer)
            if idx >= 0:
                return pos + idx
            if len(data) < read_size:
                return None
            pos += read_size - (len(footer) - 1)
        return None

    def _search_mp3_end(self, start: int, limit: int) -> Optional[int]:
        if limit <= 0:
            return None
        pos = start
        read_size = 32 * 1024
        last_frame = None
        last_frame_base = None
        while pos < start + limit:
            data = self.reader.read(pos, read_size)
            if not data:
                return last_frame_base
            for i in range(0, len(data) - 4, 1):
                b0 = data[i]
                if b0 != 0xFF:
                    continue
                b1 = data[i + 1]
                if (b1 & 0xE0) != 0xE0:
                    continue
                ver = (b1 >> 3) & 0x3
                layer = (b1 >> 1) & 0x3
                if ver == 1 or layer == 0:
                    continue
                bitrate_idx = data[i + 2] >> 4
                srate_idx = (data[i + 2] >> 2) & 0x3
                if bitrate_idx == 0 or srate_idx == 3:
                    continue
                brTable = {4: 32000, 3: 40000, 2: 48000, 1: 56000, 0: 64000}
                if ver == 3:  # MPEG-1
                    br = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
                    sr = [44100, 48000, 32000]
                    bpsamp = 8 * br[bitrate_idx] * 1000 // sr[srate_idx]
                    framesize = bpsamp if layer == 3 else bpsamp // 4
                else:
                    br = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
                    sr = [22050, 24000, 16000]
                    sr_idx_pad = srate_idx
                    bpsamp = 8 * br[bitrate_idx] * 1000 // sr[sr_idx_pad]
                    framesize = bpsamp//8 if layer==3 else bpsamp // 16
                if framesize <= 0:
                    continue
                # verify next frame
                nxt = i + framesize
                if nxt + 2 < len(data):
                    if data[nxt] != 0xFF or (data[nxt + 1] & 0xE0) != 0xE0:
                        continue
                last_frame_base = pos + i
                last_frame = framesize
                i += framesize
            pos += read_size
            if last_frame_base and (pos - last_frame_base) > 3 * 1024 * 1024:
                return last_frame_base + last_frame
        return last_frame_base + last_frame if last_frame_base else None

    def _search_riff_end(self, start: int) -> Optional[int]:
        """Read RIFF header size field."""
        try:
            data = self.reader.read(start + 4, 4)
            chunk_size = struct.unpack("<I", data)[0]
            if chunk_size and chunk_size < 8_000_000_000:
                return start + 8 + chunk_size
        except Exception:
            pass
        return None

    def _try_extract(self, ext: str, abs_off: int, siglen: int):
        # Keep nearest duplicates: skip overlapping signatures re-flagged
        for f in self.found:
            if f.ext == ext and abs(f.offset - abs_off) < siglen * 2:
                return
        end = self._detect_end(ext, abs_off, b"")
        if end is None:
            end = abs_off + 32 * 1024  # minimum default carve size
        if end - abs_off < MIN_CARVE_SIZE:
            return
        disp_ext = EXT_CANON.get(ext, ext).lower()
        name = f"{disp_ext}_{abs_off:012d}.{disp_ext}"
        self.found.append(CarvedFile(
            ext=disp_ext,
            name=name,
            offset=abs_off,
            size=end - abs_off,
            signature=ext,
        ))