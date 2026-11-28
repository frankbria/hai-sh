"""
What hai does when its local model can't answer: the model isn't pulled, or
Ollama isn't installed or running. Called from ``hai_sh/__main__.py`` only
after a query has failed, so the normal path stays one HTTP round trip.

Rules (docs/design/model-management.md sections 5 and 8):

- Nothing is downloaded without a yes; Enter means No.
- No prompt where nobody can answer: in ``--suggest-only`` (the Ctrl+X Ctrl+H
  binding) hai prints its usual JSON with an empty command and says what to
  run; in a pipe it prints the command and exits non-zero.
- A cloud provider is offered only if one is already configured, with a
  privacy notice, and only on a yes each time.
- hai never installs or starts Ollama; it prints the official commands.
"""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hai_sh import models as m
from hai_sh.model_cli import (
    ask,
    consented_pull,
    hai_model_command,
    is_interactive,
    model_facts,
    ollama_problem_lines,
)

ProviderChoice = Tuple[Any, str]  # (provider instance, provider name)


def suggest_only_json(conversation: str, config_path: Optional[Path] = None) -> str:
    """
    The JSON the shell bindings read, with no command. Shell integration
    files installed before v0.1.5 embed the JSON in a Python triple-quoted
    string, where any JSON escape (a quote, a control character, \\uXXXX)
    breaks it, so hai's own messages contain none: one line, no backslashes,
    no double quotes, no triple quotes.

    A ``--config`` path that can't be written without one of those (an
    apostrophe needs a double quote or a backslash in shell) is shown as
    YOUR_CONFIG_FILE rather than as a command for a different path.
    """
    if config_path is not None:
        raw = str(config_path)
        # The message is collapsed to single spaces, so a run of spaces or
        # any other whitespace in the path wouldn't survive either.
        if "  " in raw or any(c in raw for c in "'\"\\") or any(
            c < " " or c == "\x7f" or (c.isspace() and c != " ") for c in raw
        ):
            quoted = shlex.quote(raw)
            if quoted in conversation:
                conversation = conversation.replace(quoted, "YOUR_CONFIG_FILE") + (
                    " (YOUR_CONFIG_FILE is the file you passed to --config.)"
                )
    text = " ".join(conversation.split())
    text = "".join(c for c in text if c >= " " and c != "\x7f")
    text = text.replace("\\", "/").replace('"', "'")
    while "'''" in text:
        text = text.replace("'''", "'")
    # ensure_ascii=False: a \uXXXX escape is a backslash too.
    return json.dumps({"conversation": text, "command": "", "confidence": 0}, ensure_ascii=False)


def _catalog() -> Optional[m.Catalog]:
    try:
        return m.load_catalog()
    except m.CatalogError:
        return None


def _ollama_provider(config: Dict[str, Any], model: str) -> Optional[ProviderChoice]:
    from hai_sh.providers import get_provider

    section = dict(m.ollama_config(config))
    section["model"] = model
    try:
        return get_provider("ollama", section), "ollama"
    except Exception:
        return None


# --------------------------------------------------------------------------
# Model not installed
# --------------------------------------------------------------------------


def _download_size(model: str) -> str:
    catalog = _catalog()
    entry = catalog.get(model) if catalog else None
    return f" ({m.format_bytes(entry.download_bytes)} download)" if entry else ""


def missing_model_hint(model: str, config_path: Optional[Path] = None) -> str:
    """The command to run, with the download size when hai knows it."""
    return (
        f"To install it{_download_size(model)}, run: "
        f"{hai_model_command('pull ' + shlex.quote(model), config_path)}"
    )


def missing_model_message(model: str, config_path: Optional[Path] = None) -> str:
    """One line for --suggest-only."""
    return (
        f"hai needs the model {model}, which is not installed in Ollama. "
        f"{missing_model_hint(model, config_path)}"
    )


def missing_model_flow(
    config: Dict[str, Any], model: str, config_path: Optional[Path] = None
) -> Optional[ProviderChoice]:
    """
    Interactive only. Offer the pull of ``model`` (default No), another model
    from the catalog, or a configured cloud provider. Returns what to retry the
    query with, or None to stop.
    """
    oc = m.ollama_config(config)
    env = m.detect_environment(oc["base_url"], model)
    catalog = _catalog()
    policy = m.effective_licence_policy(config)
    entry = catalog.get(model) if catalog else None

    print("hai needs a local model to run.")
    print(f"  Ollama:   running ({env.version or 'version unknown'}) at {env.base_url}")
    print(f"  Model:    {model} is not installed")
    for line in model_facts(model, env, catalog):
        print(line)

    check = m.PullCheck(ok=True)
    if env.local:
        check = m.check_pull(
            entry.download_bytes if entry else None,
            entry.memory_bytes if entry else None,
            env.disk_free,
            env.disk_total,
            env.ram_total,
        )
    for msg in check.messages:
        print(f"  Note: {msg}")

    if check.ok:
        answer = ask("Download it now?", "yNo")
    else:
        answer = ask("See other models?", "oN")

    if answer == "y":
        from hai_sh.model_cli import run_pull

        if run_pull(env.base_url, model, config_path=config_path):
            return _ollama_provider(config, model)
        return None

    if answer == "o":
        picked = _pick_other(env, catalog, policy, exclude=model)
        if picked:
            env_other = m.detect_environment(oc["base_url"], picked)
            if env_other.model_installed or consented_pull(env_other, picked, config_path=config_path):
                _offer_default(picked, config_path)
                return _ollama_provider(config, picked)
        # Nothing picked or the download didn't happen: still offer the cloud.
        cloud = offer_cloud(config)
        if cloud:
            return cloud
        return _stop(model, config_path)

    # Declined: an installed catalog model, then a configured cloud provider.
    alternative = _installed_alternative(env, catalog, policy, exclude=model)
    if alternative:
        if ask(f"{alternative} is installed. Use it for this question?", "yN") == "y":
            _offer_default(alternative, config_path)
            return _ollama_provider(config, alternative)
    cloud = offer_cloud(config)
    if cloud:
        return cloud
    return _stop(model, config_path)


def _stop(model: str, config_path: Optional[Path] = None) -> None:
    print(f"Nothing changed. To install it later: {hai_model_command('pull ' + shlex.quote(model), config_path)}")
    print(f"To see other models: {hai_model_command('list', config_path)}")


def _installed_alternative(
    env: m.ModelEnvironment, catalog: Optional[m.Catalog], policy: str, exclude: str
) -> Optional[str]:
    if not catalog:
        return None
    for entry in catalog.recommended(policy):
        if not m.same_model(entry.name, exclude) and m.find_installed(entry.name, env.installed):
            return entry.name
    return None


def _pick_other(
    env: m.ModelEnvironment, catalog: Optional[m.Catalog], policy: str, exclude: str
) -> Optional[str]:
    from hai_sh import gum

    if not catalog:
        print("hai's model catalog is unavailable; see: hai-model list")
        return None
    options: Dict[str, str] = {}
    entries = [e for e in catalog.recommended(policy) if not m.same_model(e.name, exclude)]
    # Installed first: they need no download.
    entries.sort(key=lambda e: m.find_installed(e.name, env.installed) is None)
    for e in entries:
        have = (
            "installed"
            if m.find_installed(e.name, env.installed)
            else (f"{m.format_bytes(e.download_bytes)} download")
        )
        label = (
            f"{e.name} ({e.role}): {m.percent(e.task_accuracy)}, "
            f"{e.median_latency_s:g} s, {e.licence_name}, {have}"
        )
        options[label] = e.name
    if not options:
        print("No other recommended models. See: hai-model list")
        return None
    choice = gum.choose(list(options) + ["Cancel"], header="Pick a model:")
    return options.get(choice or "")


def _offer_default(name: str, config_path: Optional[Path]) -> None:
    if config_path is None:
        from hai_sh.init import get_config_path

        config_path = get_config_path()
    if ask(f"Make {name} your default model?", "yN") == "y":
        try:
            old, new = m.set_config_model(config_path, name)
        except OSError as e:
            print(f"Config not changed: {e}")
            return
        print(f"providers.ollama.model: {old or '(not set)'} -> {new}")
    else:
        print(f"Using {name} for this question only. To keep it: {hai_model_command('use ' + shlex.quote(name), config_path)}")


# --------------------------------------------------------------------------
# Cloud fallback
# --------------------------------------------------------------------------

_CLOUD_NAMES = {"openai": "OpenAI", "anthropic": "Anthropic"}


def offer_cloud(config: Dict[str, Any]) -> Optional[ProviderChoice]:
    """
    Offer each already-configured cloud provider for this one question, with
    a privacy notice, default No. Never remembered.
    """
    from hai_sh.providers import get_provider

    for name, section in m.configured_cloud_providers(config):
        label = _CLOUD_NAMES.get(name, name)
        print()
        print(f"You have {label} set up. Using it sends your question and shell context")
        print("(current directory, file names, git state, recent commands) to")
        print(f"{label}'s servers instead of keeping it on this machine.")
        if ask(f"Use {label} for this question only?", "yN") != "y":
            continue
        try:
            provider = get_provider(name, section)
        except Exception as e:
            print(f"{label} could not be used: {e}")
            continue
        return provider, name
    return None


# --------------------------------------------------------------------------
# Ollama not installed or not running
# --------------------------------------------------------------------------


def ollama_unavailable_lines(config: Dict[str, Any]) -> Optional[List[str]]:
    """
    Lines explaining why Ollama can't be used, or None when Ollama does answer
    now (then the failure was something else).
    """
    oc = m.ollama_config(config)
    env = m.detect_environment(oc["base_url"], oc["model"])
    if env.running:
        return None
    return ollama_problem_lines(env)


def ollama_unavailable_message(lines: List[str]) -> str:
    """One line for --suggest-only: the reason and the commands, joined."""
    return " ".join(line.strip() for line in lines)


def ollama_unavailable_flow(config: Dict[str, Any], lines: List[str]) -> Optional[ProviderChoice]:
    """Interactive only: explain, then offer a configured cloud provider."""
    for line in lines:
        print(line)
    return offer_cloud(config)


# --------------------------------------------------------------------------
# One-time notice for v0.1.4's default
# --------------------------------------------------------------------------


def stderr_is_tty() -> bool:
    try:
        return sys.stderr.isatty()
    except (AttributeError, ValueError):
        return False


def maybe_show_old_default_notice(config: Dict[str, Any], suggest_only: bool) -> bool:
    """
    Print, once, that the default moved from llama3.2 to the catalog default.
    Only in a terminal, never in --suggest-only. Returns True if printed.
    """
    if suggest_only or not is_interactive() or not stderr_is_tty():
        return False
    priority = config.get("provider_priority") or [config.get("provider", "ollama")]
    if "ollama" not in priority:
        return False
    model = m.ollama_config(config)["model"]
    notice = m.old_default_notice(model)
    if not notice or m.notice_seen(m.OLD_DEFAULT_NOTICE):
        return False
    print(notice, file=sys.stderr)
    m.mark_notice_seen(m.OLD_DEFAULT_NOTICE)
    return True
