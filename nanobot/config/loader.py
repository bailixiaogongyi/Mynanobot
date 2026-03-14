"""Configuration loading utilities."""

import json
from pathlib import Path

from nanobot.config.schema import Config


def get_config_path() -> Path:
    """Get the default configuration file path."""
    return Path.home() / ".nanobot" / "config.json"


def get_data_dir() -> Path:
    """Get the nanobot data directory."""
    from nanobot.utils.helpers import get_data_path
    return get_data_path()


def load_config(config_path: Path | None = None) -> Config:
    """
    Load configuration from file or create default.

    Args:
        config_path: Optional path to config file. Uses default if not provided.

    Returns:
        Loaded configuration object.
    """
    path = config_path or get_config_path()

    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            data = _migrate_config(data)
            return Config.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to load config from {path}: {e}")
            print("Using default configuration.")

    return Config()


def save_config(config: Config, config_path: Path | None = None) -> None:
    """
    Save configuration to file.

    Args:
        config: Configuration to save.
        config_path: Optional path to save to. Uses default if not provided.
    """
    path = config_path or get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump(by_alias=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _migrate_config(data: dict) -> dict:
    """Migrate old config formats to current."""
    # Move tools.exec.restrictToWorkspace → tools.restrictToWorkspace
    tools = data.get("tools", {})
    exec_cfg = tools.get("exec", {})
    if "restrictToWorkspace" in exec_cfg and "restrictToWorkspace" not in tools:
        tools["restrictToWorkspace"] = exec_cfg.pop("restrictToWorkspace")
    
    # Migrate knowledge.index camelCase → snake_case
    knowledge = tools.get("knowledge", {})
    index = knowledge.get("index", {})
    if index:
        field_mappings = {
            "embeddingModel": "embedding_model",
            "persistDir": "persist_dir",
            "chunkSize": "chunk_size",
            "chunkOverlap": "chunk_overlap",
            "useBm25": "use_bm25",
            "useVector": "use_vector",
            "rrfK": "rrf_k",
            "useGraph": "use_graph",
            "useLlmExtract": "use_llm_extract",
            "llmExtractBatch": "llm_extract_batch",
            "llmExtractThreshold": "llm_extract_threshold",
            "fallbackOnLlmError": "fallback_on_llm_error",
        }
        for old_name, new_name in field_mappings.items():
            if old_name in index:
                index[new_name] = index.pop(old_name)
        if "index" not in knowledge:
            knowledge["index"] = index
        
        # 设置默认值启用知识图谱
        if "use_graph" not in index:
            index["use_graph"] = True
        if "use_llm_extract" not in index:
            index["use_llm_extract"] = True
    
    return data
