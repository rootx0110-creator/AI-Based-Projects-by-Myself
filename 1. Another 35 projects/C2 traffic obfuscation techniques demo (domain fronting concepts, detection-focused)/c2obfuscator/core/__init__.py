"""Core simulation and analysis engines for the C2 obfuscation lab."""

from .obfuscators import (
    ObfuscationTechnique,
    Base64Transform,
    XORTransform,
    RC4Transform,
    AESTransform,
    TransformPipeline,
    get_techniques,
)
from .beacon import BeaconSimulator, BeaconSchedule
from .domain_fronting import DomainFrontingAnalyzer, FrontingRequest
from .detection import DetectionEngine, DetectionResult

__all__ = [
    "ObfuscationTechnique",
    "Base64Transform",
    "XORTransform",
    "RC4Transform",
    "AESTransform",
    "TransformPipeline",
    "get_techniques",
    "BeaconSimulator",
    "BeaconSchedule",
    "DomainFrontingAnalyzer",
    "FrontingRequest",
    "DetectionEngine",
    "DetectionResult",
]