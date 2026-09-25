"""Standalone BYOK Key Manager & Security Sandbox for Project Arkais.

Provides zero-telemetry, client-side credential management across AI providers:
- Multi-tier discovery: Explicit argument -> OS environment -> .env -> User config file
- Secret masking and redaction to prevent accidental logging or exposure
- POSIX 0600 permission enforcement for credential files
- In-memory validation without remote network calls
- Strict zero-telemetry domain enforcement
"""

import os
import re
import json
import stat
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

PROVIDER_ENV_VARS = {
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "linear": ["LINEAR_API_KEY"],
    "ydc": ["YDC_API_KEY"]
}

PROVIDER_KEY_PATTERNS = {
    "openai": re.compile(r"^sk-(proj-)?[A-Za-z0-9_-]{20,}$"),
    "anthropic": re.compile(r"^sk-ant-[A-Za-z0-9_-]{20,}$"),
    "gemini": re.compile(r"^AIza[A-Za-z0-9_-]{30,}$|^[A-Za-z0-9_-]{20,}$"),
    "linear": re.compile(r"^lin_api_[A-Za-z0-9_]{30,}$"),
    "ydc": re.compile(r"^ydc-[A-Za-z0-9_-]{20,}$")
}

OFFICIAL_DOMAINS = {
    "openai": ["api.openai.com"],
    "anthropic": ["api.anthropic.com"],
    "gemini": ["generativelanguage.googleapis.com"],
    "linear": ["api.linear.app"]
}


class RedactedSecret:
    """Encapsulates sensitive credentials, masking them in logs, repr, and str."""

    def __init__(self, value: str):
        if not value or not isinstance(value, str):
            raise ValueError("Secret value must be a non-empty string.")
        self._value = value.strip()

    def get_secret_value(self) -> str:
        """Returns raw secret value strictly for authorized client instantiation."""
        return self._value

    def __repr__(self) -> str:
        return f"RedactedSecret('{self._mask()}')"

    def __str__(self) -> str:
        return self._mask()

    def _mask(self) -> str:
        val = self._value
        if len(val) <= 8:
            return "********"
        prefix = val[:6]
        suffix = val[-4:]
        return f"{prefix}****...{suffix}"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, RedactedSecret):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return False


class CredentialSecurityError(Exception):
    """Raised when security boundaries or permission checks fail."""
    pass


class ByokKeyManager:
    """Zero-telemetry client-side credential manager for Project Arkais."""

    def __init__(self, project_root: Optional[Path] = None, user_config_dir: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.user_config_dir = user_config_dir or (Path.home() / ".config" / "arkais")
        self.user_config_file = self.user_config_dir / "credentials.json"

    def get_key(self, provider: str, explicit_key: Optional[str] = None) -> Optional[RedactedSecret]:
        """Discovers a provider key through the multi-tier resolution hierarchy:
        1. Explicitly supplied runtime key
        2. Process environment variables
        3. Project .env file
        4. User-level credentials store (~/.config/arkais/credentials.json)
        """
        prov = provider.lower().strip()
        if prov not in PROVIDER_ENV_VARS:
            raise ValueError(f"Unknown provider '{provider}'. Supported: {list(PROVIDER_ENV_VARS.keys())}")

        # Tier 1: Explicit argument
        if explicit_key:
            return self._validate_and_wrap(prov, explicit_key, source="explicit")

        # Tier 2: Process Environment
        env_vars = PROVIDER_ENV_VARS[prov]
        for var in env_vars:
            val = os.environ.get(var)
            if val and val.strip():
                return self._validate_and_wrap(prov, val, source=f"env:{var}")

        # Tier 3: Project .env
        dotenv_key = self._read_from_dotenv(env_vars)
        if dotenv_key:
            return self._validate_and_wrap(prov, dotenv_key, source="dotenv")

        # Tier 4: User Config File
        user_key = self._read_from_user_config(prov)
        if user_key:
            return self._validate_and_wrap(prov, user_key, source="user_config")

        return None

    def save_key(self, provider: str, key_value: str, scope: str = "project") -> Path:
        """Saves a key locally to either the project .env or user-level credentials.json.
        Enforces strict POSIX 0600 file permissions (owner read/write only).
        """
        prov = provider.lower().strip()
        if prov not in PROVIDER_ENV_VARS:
            raise ValueError(f"Unknown provider '{provider}'. Supported: {list(PROVIDER_ENV_VARS.keys())}")

        secret = self._validate_and_wrap(prov, key_value, source="save_input")
        raw = secret.get_secret_value()
        primary_var = PROVIDER_ENV_VARS[prov][0]

        if scope == "project":
            target_path = self.project_root / ".env"
            self._write_dotenv_key(target_path, primary_var, raw)
        elif scope == "user":
            target_path = self.user_config_file
            self._write_user_config_key(target_path, prov, raw)
        else:
            raise ValueError(f"Invalid scope '{scope}'. Choose 'project' or 'user'.")

        self.enforce_file_permissions(target_path)
        return target_path

    def validate_key_format(self, provider: str, key: str) -> Tuple[bool, Optional[str]]:
        """Performs non-network regex validation of provider key syntax."""
        prov = provider.lower().strip()
        pattern = PROVIDER_KEY_PATTERNS.get(prov)
        if not pattern:
            return True, None

        if not pattern.match(key.strip()):
            return False, f"Key format invalid for {provider}. Does not match expected pattern."
        return True, None

    def assert_zero_telemetry(self, provider: str, target_endpoint: str):
        """Audit gate: verifies outgoing LLM calls only target verified official domains."""
        prov = provider.lower().strip()
        allowed = OFFICIAL_DOMAINS.get(prov, [])
        if not allowed:
            return

        for domain in allowed:
            if domain in target_endpoint:
                return

        raise CredentialSecurityError(
            f"Zero-Telemetry Violation: Attempted outbound call to unauthorized domain '{target_endpoint}'. "
            f"Allowed domains for {prov}: {allowed}."
        )

    def enforce_file_permissions(self, path: Path):
        """Enforces POSIX 0600 permissions on sensitive credential files."""
        if os.name == 'posix' and path.exists():
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    def check_file_permissions(self, path: Path) -> bool:
        """Returns True if file has secure 0600 (or more restrictive) permissions."""
        if os.name != 'posix' or not path.exists():
            return True
        mode = stat.S_IMODE(os.stat(path).st_mode)
        return (mode & 0o077) == 0

    def _validate_and_wrap(self, provider: str, key: str, source: str) -> RedactedSecret:
        valid, msg = self.validate_key_format(provider, key)
        if not valid:
            raise ValueError(f"Credential format error from source '{source}': {msg}")
        return RedactedSecret(key)

    def _read_from_dotenv(self, env_vars: list) -> Optional[str]:
        dotenv_path = self.project_root / ".env"
        if not dotenv_path.exists():
            return None

        try:
            content = dotenv_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                for var in env_vars:
                    if line.startswith(f"{var}="):
                        val = line.split("=", 1)[1].strip()
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]
                        return val
        except Exception:
            return None
        return None

    def _read_from_user_config(self, provider: str) -> Optional[str]:
        if not self.user_config_file.exists():
            return None

        if not self.check_file_permissions(self.user_config_file):
            raise CredentialSecurityError(
                f"Security Risk: {self.user_config_file} has unsafe permissions. Run chmod 600 {self.user_config_file}."
            )

        try:
            data = json.loads(self.user_config_file.read_text(encoding="utf-8"))
            return data.get(provider)
        except Exception:
            return None

    def _write_dotenv_key(self, path: Path, var_name: str, value: str):
        lines = []
        replaced = False
        if path.exists():
            lines = path.read_text(encoding="utf-8").splitlines()
            new_lines = []
            for line in lines:
                if line.strip().startswith(f"{var_name}="):
                    new_lines.append(f"{var_name}={value}")
                    replaced = True
                else:
                    new_lines.append(line)
            lines = new_lines

        if not replaced:
            lines.append(f"{var_name}={value}")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_user_config_key(self, path: Path, provider: str, value: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data[provider] = value
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
