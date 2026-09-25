"""Configuration settings and runtime parameters for Project Arkais SDK."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ArkaisConfig:
    """Runtime configuration for ArkaisClient."""
    provider: str = "anthropic"
    default_signature: str = "ARKAIS-001-v1.1"
    project_root: Path = field(default_factory=Path.cwd)
    custom_signature_dir: Optional[Path] = None
    references_cache_file: Optional[Path] = None
    contact_email: str = "engineering@geegthink.com"
    explicit_api_key: Optional[str] = None
    enforce_zero_telemetry: bool = True
