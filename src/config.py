"""
Centralized configuration module.

Loads settings from environment variables and provides a validated,
immutable configuration object used across all layers.

Dependency: None (leaf module).
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class HuggingFaceConfig:
    """Immutable configuration for Hugging Face Inference API."""

    api_key: str
    api_url: str = "https://router.huggingface.co/v1/chat/completions"
    model: str = "Qwen/Qwen2.5-Coder-32B-Instruct"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    exponential_backoff: bool = True


@dataclass(frozen=True)
class MemoryConfig:
    """Configuration for the memory subsystem."""

    max_history: int = 100
    max_snapshots: int = 10


@dataclass(frozen=True)
class EngineConfig:
    """Configuration for the trigger engine."""

    typing_pause_duration: float = 1.0
    max_events_in_queue: int = 100
    syntax_check_debounce: float = 0.5


@dataclass(frozen=True)
class WorkspaceConfig:
    """Configuration for the workspace / file manager."""

    root_dir: str = "workspace"
    max_file_size_bytes: int = 1_000_000  # 1 MB
    allowed_extensions: Tuple[str, ...] = (
        ".py", ".txt", ".json", ".yaml", ".yml",
        ".toml", ".md", ".html", ".css", ".js",
        ".cfg", ".ini", ".env", ".sh", ".bat",
    )


@dataclass(frozen=True)
class RunnerConfig:
    """Configuration for the project execution engine."""

    timeout_seconds: int = 30
    default_entry_points: Tuple[str, ...] = (
        "main.py", "app.py", "run.py", "manage.py",
    )


@dataclass(frozen=True)
class SystemConfig:
    """Top-level system configuration aggregating all sub-configs."""

    hf: HuggingFaceConfig = field(default_factory=lambda: HuggingFaceConfig(api_key=""))
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    runner: RunnerConfig = field(default_factory=RunnerConfig)
    enable_logging: bool = True


class ConfigError(Exception):
    """Raised when configuration is invalid."""
    pass


def load_config() -> SystemConfig:
    """
    Load and validate system configuration from environment variables.

    Returns:
        Fully validated SystemConfig instance.

    Raises:
        ConfigError: If required environment variables are missing.
    """
    api_key = os.getenv("HUGGINGFACE_API_KEY", "")
    if not api_key:
        raise ConfigError(
            "HUGGINGFACE_API_KEY environment variable not set. "
            "Please set it before running the system."
        )

    # Use the new router base URL explicitly
    api_url = os.getenv("HF_API_URL", "https://router.huggingface.co/v1/chat/completions")

    # Keep backward compatibility with user's environment variable shorthand,
    # but map them properly to the actual HF model namespace.
    model_alias = os.getenv("HF_MODEL", "deepseek-coder")
    
    if model_alias == "deepseek-coder":
        actual_model = "Qwen/Qwen2.5-Coder-32B-Instruct"
    elif model_alias == "starcoder":
        actual_model = "bigcode/starcoder2-15b"
    else:
        # If they specify a custom model manually
        actual_model = model_alias

    hf_config = HuggingFaceConfig(
        api_key=api_key,
        api_url=api_url,
        model=actual_model,
    )

    # Workspace configuration
    workspace_dir = os.getenv("WORKSPACE_DIR", "workspace")
    # Resolve relative to project root
    project_root = Path(__file__).resolve().parent.parent
    workspace_path = str(project_root / workspace_dir)
    workspace_config = WorkspaceConfig(root_dir=workspace_path)

    # Runner configuration
    runner_timeout = int(os.getenv("RUNNER_TIMEOUT", "30"))
    runner_config = RunnerConfig(timeout_seconds=runner_timeout)

    return SystemConfig(
        hf=hf_config,
        workspace=workspace_config,
        runner=runner_config,
    )
