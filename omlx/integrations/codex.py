"""Codex (OpenAI Codex CLI) integration."""

from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path

from omlx.integrations.base import Integration
from omlx.utils.install import get_cli_prefix


class CodexIntegration(Integration):
    """Codex integration that configures ~/.codex/config.toml for oMLX."""

    CONFIG_PATH = Path.home() / ".codex" / "config.toml"

    def __init__(self):
        super().__init__(
            name="codex",
            display_name="Codex",
            type="config_file",
            install_check="codex",
            install_hint="npm install -g @openai/codex",
        )

    def get_command(
        self, port: int, api_key: str, model: str, host: str = "127.0.0.1"
    ) -> str:
        return (
            f"{get_cli_prefix()} "
            f"launch codex --model {model or 'select-a-model'}"
        )

    def configure(self, port: int, api_key: str, model: str, host: str = "127.0.0.1") -> None:
        config_path = self.CONFIG_PATH
        config_path.parent.mkdir(parents=True, exist_ok=True)

        existing_content = ""
        if config_path.exists():
            # Create backup
            timestamp = int(time.time())
            backup = config_path.with_suffix(f".{timestamp}.bak")
            try:
                shutil.copy2(config_path, backup)
                existing_content = config_path.read_text(encoding="utf-8")
                print(f"Backup: {backup}")
            except OSError as e:
                print(f"Warning: could not create backup or read config: {e}")

        # Parse existing config lines to preserve other settings
        lines = existing_content.splitlines()
        new_lines = []
        skip_section = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                # Skip old oMLX sections
                skip_section = stripped in ("[model_providers.omlx]", "[profiles.omlx]")
                new_lines.append(line)
                continue

            if skip_section:
                continue

            new_lines.append(line)

        # Append new oMLX profile section
        new_lines.append("\n[profiles.omlx]")
        new_lines.append('model_provider = "omlx"')
        new_lines.append(f'model = "{model or "select-a-model"}"')

        # If it is a reasoning model, add reasoning effort
        is_reasoning = bool(re.search(r'\b(thinking|o1|o3|r1)\b', (model or "").lower()))
        if is_reasoning:
            new_lines.append('model_reasoning_effort = "high"')

        # Append new oMLX provider section
        new_lines.append("\n[model_providers.omlx]")
        new_lines.append('name = "oMLX"')
        new_lines.append(f'base_url = "http://{host}:{port}/v1"')
        new_lines.append('env_key = "OMLX_API_KEY"')

        config_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        print(f"Config updated: {config_path}")

    def launch(
        self, port: int, api_key: str, model: str, host: str = "127.0.0.1", **kwargs
    ) -> None:
        self.configure(port, api_key, model, host=host)

        env = os.environ.copy()
        env["OMLX_API_KEY"] = api_key or "omlx"

        args = ["codex"]
        if model:
            args.extend(["-p", "omlx"])

        os.execvpe("codex", args, env)
