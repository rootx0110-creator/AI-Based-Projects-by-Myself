import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def now_local() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Case:
    id: str
    case_number: str
    title: str
    agency: str
    investigator: str
    role: str
    description: str
    status: str
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def new(
        cls,
        case_number: str,
        title: str,
        agency: str,
        investigator: str,
        role: str,
        description: str,
        status: str = "Open",
        notes: str = "",
    ) -> "Case":
        ts = utcnow()
        return cls(
            id=new_id(),
            case_number=case_number,
            title=title,
            agency=agency,
            investigator=investigator,
            role=role,
            description=description,
            status=status,
            notes=notes,
            created_at=ts,
            updated_at=ts,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Case":
        c = {k: d.get(k, "") for k in (
            "id", "case_number", "title", "agency", "investigator",
            "role", "description", "status", "notes", "created_at", "updated_at")}
        if not c["created_at"]:
            c["created_at"] = utcnow()
            c["updated_at"] = c["created_at"]
        return cls(**c)

    def touch(self) -> None:
        self.updated_at = utcnow()

    @property
    def display(self) -> str:
        return f"{self.case_number} — {self.title}"


@dataclass
class Evidence:
    id: str
    case_id: str
    item_label: str
    source_type: str
    source: str
    target_image: str
    image_format: str
    media_info: str
    size_bytes: int
    hashes: dict = field(default_factory=dict)
    acquired_at: str = ""
    acquired_by: str = ""
    verified: bool = False
    verified_at: str = ""
    status: str = "Pending"

    @classmethod
    def new(
        cls,
        case_id: str,
        item_label: str,
        source_type: str,
        source: str,
        target_image: str,
        image_format: str,
        media_info: str,
    ) -> "Evidence":
        return cls(
            id=new_id(),
            case_id=case_id,
            item_label=item_label,
            source_type=source_type,
            source=source,
            target_image=target_image,
            image_format=image_format,
            media_info=media_info,
            size_bytes=0,
            hashes={},
            acquired_at=utcnow(),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Evidence":
        return cls(
            id=d.get("id") or new_id(),
            case_id=d.get("case_id", ""),
            item_label=d.get("item_label", ""),
            source_type=d.get("source_type", ""),
            source=d.get("source", ""),
            target_image=d.get("target_image", ""),
            image_format=d.get("image_format", ""),
            media_info=d.get("media_info", ""),
            size_bytes=int(d.get("size_bytes", 0) or 0),
            hashes=d.get("hashes") if isinstance(d.get("hashes"), dict) else {},
            acquired_at=d.get("acquired_at") or utcnow(),
            acquired_by=d.get("acquired_by", ""),
            verified=bool(d.get("verified", False)),
            verified_at=d.get("verified_at", ""),
            status=d.get("status", "Pending"),
        )


@dataclass
class CustodyEntry:
    seq: int
    timestamp: str
    actor: str
    role: str
    action: str
    detail: str
    hmac: str
    prev_hmac: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CustodyEntry":
        return cls(
            seq=int(d.get("seq", 0)),
            timestamp=d.get("timestamp", ""),
            actor=d.get("actor", ""),
            role=d.get("role", ""),
            action=d.get("action", ""),
            detail=d.get("detail", ""),
            hmac=d.get("hmac", ""),
            prev_hmac=d.get("prev_hmac", ""),
        )


@dataclass
class VerificationResult:
    image: str
    expected: dict
    actual: dict
    matched: dict
    all_match: bool
    verified_at: str
    verifier: str


@dataclass
class Settings:
    operator: str = ""
    role: str = ""
    workspace: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Settings":
        return cls(
            operator=d.get("operator", ""),
            role=d.get("role", ""),
            workspace=d.get("workspace", ""),
        )


def format_bytes(n) -> str:
    if n is None:
        return "—"
    size = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if abs(size) < 1024.0 or unit == "PiB":
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024.0
    return f"{size:.2f} PiB"