"""
hai-sh: AI-powered terminal assistant

A context-aware wrapper around bash that enables natural language
command generation and execution via LLM assistance.
"""

from hai_sh.init import (
    get_config_path,
    get_hai_dir,
    init_hai_directory,
    verify_hai_directory,
)

__version__ = "0.0.1"
__all__ = [
    "__version__",
    "get_hai_dir",
    "get_config_path",
    "init_hai_directory",
    "verify_hai_directory",
]
