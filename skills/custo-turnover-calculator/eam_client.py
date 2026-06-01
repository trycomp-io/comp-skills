"""
Comp EaM shared client — imported by every Engineering as Marketing skill.

Handles:
- Local config (~/.comp-skills/config.json): persistent instance_id, email, opt-ins
- First-run registration prompt (email opt-in)
- Telemetry opt-in (default: off)
- Non-blocking calls to the EaM API (skills still work if API is down)

Usage from a skill:

    from eam_client import on_first_run, record_run

    on_first_run(skill_name="pj-vs-clt-calculator", skill_version="1.0.0",
                 source="github")
    # ... skill logic ...
    record_run(skill_name="pj-vs-clt-calculator", skill_version="1.0.0")
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

CONFIG_DIR = Path.home() / ".comp-skills"
CONFIG_PATH = CONFIG_DIR / "config.json"

EAM_API_URL = os.environ.get("EAM_API_URL", "https://eam.comp.vc")
EAM_API_KEY = os.environ.get("EAM_API_KEY", "d93f5abd845b9c882cc971199296b40c9c99b3f27eac81a425c1ad63074ce0b3")


def _load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_config(cfg: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CONFIG_DIR, 0o700)
    except OSError:
        pass
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    # Config holds the user's email and opt-ins — keep it owner-only.
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass


def _ensure_instance_id(cfg: dict[str, Any]) -> str:
    if "instance_id" not in cfg:
        cfg["instance_id"] = str(uuid.uuid4())
        _save_config(cfg)
    return cfg["instance_id"]


def _post(path: str, body: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Best-effort POST. Returns None on any failure (never raises)."""
    if not EAM_API_KEY:
        return None
    req = urllib.request.Request(
        f"{EAM_API_URL}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": EAM_API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None


def _prompt_registration() -> tuple[Optional[str], bool]:
    """
    First-run prompt. Returns (email_or_none, telemetry_opt_in).
    Hook is continuous improvement — not specific examples.
    """
    print(
        "\nEsta skill é mantida pela Comp e melhora continuamente.\n"
        "Informe seu email corporativo para receber atualizações. Pode pular esta etapa.\n"
    )
    try:
        email = input("Email (Enter para pular): ").strip()
    except (EOFError, KeyboardInterrupt):
        email = ""

    email = email if email and "@" in email else None

    print(
        "\nTopa enviar dados anônimos de uso (qual skill, frequência)?\n"
        "Nenhum dado sensível é coletado. Ajuda a Comp a evoluir as ferramentas.\n"
    )
    try:
        telem = input("Telemetria [s/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        telem = ""
    telemetry_opt_in = telem in ("s", "sim", "y", "yes")

    return email, telemetry_opt_in


def on_first_run(skill_name: str, skill_version: str, source: str = "github") -> dict[str, Any]:
    """
    Call at skill startup. Idempotent — only prompts on first run per machine.
    Returns the current config dict.
    """
    cfg = _load_config()
    instance_id = _ensure_instance_id(cfg)

    if "registered" not in cfg:
        # Never prompt on non-interactive stdin (e.g. data piped in) — the prompt
        # would consume the piped payload. Defer registration to an interactive run.
        if not sys.stdin.isatty():
            return cfg
        email, telemetry_opt_in = _prompt_registration()
        cfg["email"] = email
        cfg["telemetry_opt_in"] = telemetry_opt_in
        cfg["registered_at"] = datetime.utcnow().isoformat() + "Z"
        cfg["registered"] = True
        _save_config(cfg)

        if email:
            _post(
                "/register",
                {
                    "email": email,
                    "skill_name": skill_name,
                    "skill_version": skill_version,
                    "instance_id": instance_id,
                    "origem": source,
                },
            )
    else:
        if cfg.get("email"):
            installed = set(cfg.get("skills_installed", []))
            if skill_name not in installed:
                _post(
                    "/register",
                    {
                        "email": cfg["email"],
                        "skill_name": skill_name,
                        "skill_version": skill_version,
                        "instance_id": instance_id,
                        "origem": source,
                    },
                )
                installed.add(skill_name)
                cfg["skills_installed"] = sorted(installed)
                _save_config(cfg)

    return cfg


def record_run(skill_name: str, skill_version: str, event_type: str = "run") -> None:
    """Call after each successful skill execution. No-op if telemetry is off."""
    cfg = _load_config()
    if not cfg.get("telemetry_opt_in"):
        return
    # Anonymous by design: instance_id + skill + timestamp only. No email, no inputs.
    _post(
        "/telemetry",
        {
            "instance_id": cfg.get("instance_id", ""),
            "skill_name": skill_name,
            "skill_version": skill_version,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )
