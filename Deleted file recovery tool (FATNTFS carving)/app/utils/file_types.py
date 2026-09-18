"""File signature database used for raw carving.

Each entry defines the magic bytes that identify a file type.
Some signatures are stored in hex strings, others with ISO-8859-1
magic strings to keep startup fast.
"""

SKIPPED_EXT_FOR_CARVING = {"txt", "log", "ini", "cfg"}

# signature: (hex string, offset) --- hex is used directly
CARVING_SIGNATURES = {
    "JPEG": ["ffd8ff", "ffd8ffe000104a464946"],
    "PNG": ["89504e470d0a1a0a"],
    "GIF": ["474946383961", "474946383761"],
    "BMP": ["424d4a00", "424d4600", "424d3800", "424d3600", "424d2800"],
    "PDF": ["25504446"],
    "ZIP": ["504b0304", "504b0506", "504b0708"],
    "RAR": ["526172211a0700", "526172211a070100"],
    "7Z": ["377abcaf271c"],
    "GZIP": ["1f8b"],
    "TAR": ["7573746172"],
    "DOCX": ["504b030414000600"],
    "XLSX": ["504b030414000600"],
    "PPTX": ["504b030414000600"],
    "DOC": ["d0cf11e0a1b11ae1"],
    "XLS": ["d0cf11e0a1b11ae1"],
    "PPT": ["d0cf11e0a1b11ae1"],
    "MDB": ["d0cf11e0a1b11ae1"],
    "RTF": ["7b5c727466"],
    "MP3": ["494433", "fff3", "fff2", "fff1", "fffb", "ffff"],
    "MP4": ["0000001866747970", "0000002066747970", "6674797069736f6d"],
    "AVI": ["52494646"],
    "MOV": ["00000018667479706d6f6f76"],
    "MKV": ["1a45dfa3"],
    "WAV": ["52494646"],
    "FLV": ["464c5601"],
    "SQLITE": ["53514c69746520666f726d6174203300"],
    "EXE": ["4d5a"],
    "DLL": ["4d5a"],
    "ISO": ["4344303031"],
    "PGN": ["54616d205d"],
    "ICO": ["00000100"],
    "WEBP": ["52494646"],
    "WMA": ["3026b2758e66cf11a6d900aa0062ce6c"],
    "WMV": ["3026b2758e66cf11a6d900aa0062ce6c"],
    "FLAC": ["664c6143"],
    "OGG": ["4f676753"],
    "BZ2": ["425a68"],
    "XZ": ["fd377a585a00"],
    "CAB": ["4d534346"],
    "LZO": ["8955"],
    "CHM": ["49545346"],
    "THM": ["3c214c4f43414cff"],
    "PSD": ["38425053"],
    "TIFF": ["49492a00", "4d4d002a"],
    "TGA": [],
    "WPS": ["d0cf11e0a1b11ae1"],
    "HTM": ["3c21444f4354595045", "3c68746d6c", "3c48544d4c"],
    "XML": ["3c3f786d6c"],
    "CSV": [],
    "DWG": ["41433130"],
    "EPS": ["252150532d41646f6265"],
    "INDD": ["0606edf5d81d46e5bd31efe7fe74b71d"],
    "SIT": ["53747566664974"],
    "SITX": ["53697421"],
    "VOB": ["000001ba", "000001b3"],
    "MSG": ["d0cf11e0a1b11ae1"],
    "EML": ["4d534746", "52656365697665643a"],
    "LNK": ["4c00000001140200"],
    "PST": ["2142444e"],
    "OST": ["2142444e"],
    "QDF": ["ac9ebd8f "],
    "ZIPX": ["504b0304"],
    "KML": ["3c3f786d6c"],
    "WS": ["3c57534"],
    "VCF": ["424547494e3a5643415244"],
    "ICS": ["424547494e3a56434152444"],
    "XPI": ["504b0304"],
    "JAR": ["504b0304"],
    "APK": ["504b0304"],
    "OGV": ["4f676753"],
    "MID": ["4d546864"],
    "MPG": ["000001ba", "000001b3"],
}

# signature -> canonical extension helpers
SIG_EXT_MAP = {}

# Canonical (lowercase file extension) for each signature family key
EXT_CANON = {
    "JPEG": "jpg", "MPG": "mpg", "HTML": "html", "HTM": "html",
    "WRZ": "wrz",
}

def build_sig_map():
    for ext, sigs in CARVING_SIGNATURES.items():
        for s in sigs:
            SIG_EXT_MAP[s] = ext


def signature_for(ext):
    """Return list of hex signatures for a given extension, or None."""
    return CARVING_SIGNATURES.get(ext.upper())

build_sig_map()