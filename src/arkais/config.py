"""Configuration settings and runtime parameters for Project Arkais SDK."""

import os

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ArkaisConfig:
    """Runtime configuration for ArkaisClient."""
    provider: str = "anthropic"
    default_signature: str = "ARKAIS-v3.0"
    project_root: Path = field(default_factory=Path.cwd)
    custom_signature_dir: Optional[Path] = None
    references_cache_file: Optional[Path] = None
    #: Polite-pool contact identity. Deployment-configured via `ARKAIS_CONTACT_EMAIL`.
    #: There is deliberately no baked-in default: a shared address would be sent under every
    #: user's identity. See D-1 / THE-75.
    contact_email: Optional[str] = field(
        default_factory=lambda: os.environ.get("ARKAIS_CONTACT_EMAIL") or None
    )
    explicit_api_key: Optional[str] = None
    enforce_zero_telemetry: bool = True
