"""
hai-model: see, install and switch hai's local Ollama models.

    hai-model status            Ollama state, the configured model, disk and memory
    hai-model list              installed models next to the recommended ones
    hai-model pull NAME         download a model, after showing size, disk and licence
    hai-model use NAME          make NAME hai's Ollama model (offers the download)

Nothing is downloaded without a yes. With no terminal to ask in, a download
needs --yes. hai never installs or starts Ollama itself; it prints the
official commands. Design: docs/design/model-management.md.
"""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import List, Optional, TextIO

from hai_sh import __version__
from hai_sh import models as m

# --------------------------------------------------------------------------
# Terminal helpers (shared with hai's missing-model flow in __main__)
# --------------------------------------------------------------------------


def is_interactive() -> bool:
    """A person can answer a prompt: both stdin and stdout are terminals."""
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


def ask(prompt: str, choices: str = "yN") -> str:
    """
    Ask a one-letter question. The capital letter in ``choices`` is the
    default for Enter; returns the chosen lower-case letter. EOF or Ctrl+C
    returns the default.
    """
    default = next((c.lower() for c in choices if c.isupper()), choices[0].lower())
    allowed = {c.lower() for c in choices}
    shown = "/".join(choices)
    while True:
        try:
            answer = input(f"{prompt} [{shown}] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return default
        if not answer:
            return default
        if answer[0] in allowed and (len(answer) == 1 or answer in ("yes", "no")):
            return answer[0]
        print(f"Please answer one of: {', '.join(sorted(allowed))}")


def model_facts(name: str, env: m.ModelEnvironment, catalog: Optional[m.Catalog]) -> List[str]:
    """The lines shown before any download: size, disk, licence, evidence."""
    entry = catalog.get(name) if catalog else None
    lines = []
    size = m.format_bytes(entry.download_bytes) if entry else "unknown until the download starts"
    disk = ""
    if env.local and env.disk_free is not None:
        disk = f"  (disk free: {m.format_bytes(env.disk_free)})"
    elif not env.local:
        disk = "  (on the Ollama host, not this machine)"
    lines.append(f"  Download: {size}{disk}")
    if entry:
        lines.append(f"  Licence:  {entry.licence_name}")
        lines.append(f"  Tested:   {m.describe_model(entry, catalog.cases)}")
    else:
        lines.append("  Licence:  see the model's page on ollama.com")
        lines.append("  Tested:   not tested with hai (eval/README.md explains how to score it)")
    return lines


def _progress_printer(name: str, stream: TextIO):
    tty = hasattr(stream, "isatty") and stream.isatty()
    state = {"last_pct": -1, "last_status": None}

    def show(p: m.PullProgress) -> None:
        frac = p.fraction
        if tty:
            if frac is not None and p.total:
                line = (
                    f"\r  Downloading {name}: {frac * 100:5.1f}% "
                    f"({m.format_bytes(p.completed)} of {m.format_bytes(p.total)})"
                )
            else:
                line = f"\r  {p.status}"
            stream.write(line[:100].ljust(60))
            stream.flush()
            return
        # No terminal: a line per status change and per 10%, not per chunk.
        pct = int(frac * 10) * 10 if frac is not None else -1
        if p.status != state["last_status"] and not p.status.startswith("pulling "):
            stream.write(f"  {p.status}\n")
        elif pct > state["last_pct"]:
            stream.write(f"  {name}: {pct}%\n")
        state["last_pct"] = max(pct, state["last_pct"])
        state["last_status"] = p.status

    def done() -> None:
        if tty:
            stream.write("\n")
            stream.flush()

    return show, done


def hai_model_command(args: str, config_path: Optional[Path] = None) -> str:
    """
    A hai-model command line to show the user. With a config file other than
    the default, it names that file, so the command acts on the same Ollama.
    """
    if config_path is not None:
        from hai_sh.init import get_config_path

        if Path(config_path).expanduser() != get_config_path():
            return f"hai-model --config {shlex.quote(str(config_path))} {args}"
    return f"hai-model {args}"


def run_pull(
    base_url: str,
    name: str,
    stream: Optional[TextIO] = None,
    config_path: Optional[Path] = None,
) -> bool:
    """Pull with a progress line on stderr. Returns True on success."""
    stream = stream or sys.stderr
    show, done = _progress_printer(name, stream)
    try:
        m.pull_model(base_url, name, on_progress=show)
    except KeyboardInterrupt:
        done()
        print(
            f"Download stopped. Run '{hai_model_command('pull ' + name, config_path)}' "
            "to resume where it left off.",
            file=stream,
        )
        return False
    except m.PullError as e:
        done()
        print(f"Download failed: {e}", file=stream)
        return False
    done()
    print(f"{name} is installed.", file=stream)
    return True


def consented_pull(
    env: m.ModelEnvironment,
    name: str,
    assume_yes: bool = False,
    force: bool = False,
    out: Optional[TextIO] = None,
    config_path: Optional[Path] = None,
) -> bool:
    """
    Show the facts, check disk and memory, ask (default No) and pull.
    Without a terminal and without ``assume_yes`` it prints the command to
    run and returns False; it never prompts where nobody can answer.
    """
    out = out or sys.stdout
    catalog = _catalog_or_none()
    entry = catalog.get(name) if catalog else None
    print(f"{name} is not installed in Ollama.", file=out)
    for line in model_facts(name, env, catalog):
        print(line, file=out)

    check = m.PullCheck(ok=True)
    if env.local:
        check = m.check_pull(
            entry.download_bytes if entry else None,
            entry.memory_bytes if entry else None,
            env.disk_free,
            env.disk_total,
            env.ram_total,
            force=force,
        )
    for msg in check.messages:
        print(f"  Note: {msg}", file=out)
    if not check.ok:
        return False

    if not assume_yes:
        if not is_interactive():
            cmd = hai_model_command(f"pull {name} --yes", config_path)
            print(f"Nothing downloaded. To download it, run: {cmd}", file=out)
            return False
        if ask("Download it now?", "yN") != "y":
            cmd = hai_model_command(f"pull {name}", config_path)
            print(f"Nothing downloaded. Later: {cmd}", file=out)
            return False
    return run_pull(env.base_url, name, config_path=config_path)


def _catalog_or_none() -> Optional[m.Catalog]:
    try:
        return m.load_catalog()
    except m.CatalogError:
        return None


def ollama_problem_lines(env: m.ModelEnvironment) -> List[str]:
    """Why Ollama can't be used, and the official commands to fix it."""
    if not env.local:
        return [
            f"Ollama at {env.base_url} is not answering.",
            "That server is on another machine; start Ollama there, or change",
            "providers.ollama.base_url in ~/.hai/config.yaml.",
        ]
    if not env.ollama_binary:
        return [
            "hai needs Ollama to run local models, and it is not installed."
        ] + m.ollama_install_hint()
    return [f"Ollama is installed but not running at {env.base_url}."] + m.ollama_start_hint()


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def _load(args: argparse.Namespace) -> tuple:
    from hai_sh.config import ConfigError, load_config
    from hai_sh.init import get_config_path

    config_path = Path(args.config).expanduser() if args.config else get_config_path()
    try:
        # A missing file gives the defaults (never another config file).
        config = load_config(config_path=config_path, use_pydantic=False)
    except ConfigError as e:
        print(f"Cannot read config: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    return config, config_path


def cmd_status(args: argparse.Namespace) -> int:
    config, config_path = _load(args)
    oc = m.ollama_config(config)
    env = m.detect_environment(oc["base_url"], oc["model"])
    policy = m.effective_licence_policy(config)

    if env.running:
        print(f"Ollama:        running ({env.version or 'version unknown'}) at {env.base_url}")
    else:
        print(f"Ollama:        not reachable at {env.base_url}")
    provider = config.get("provider", "ollama")
    note = "" if provider == "ollama" else f"  (hai's provider is {provider})"
    if env.running:
        state = "installed" if env.model_installed else "NOT installed"
    else:
        state = "unknown"
    print(f"Model:         {env.model}  ({state}){note}")
    entry = env.catalog_entry
    if entry:
        facts = m.describe_model(entry, m.load_catalog().cases)
        print(f"               {entry.role} in hai's catalog: {facts}")
        print(f"               Licence: {entry.licence_name}")
    else:
        print("               not in hai's catalog (untested with hai)")
    print(f"Config:        {config_path}")
    print(f"Licence policy: {policy}")
    if env.local:
        where = env.models_dir or "not found yet"
        print(f"Models dir:    {where}")
        print(f"Disk free:     {m.format_bytes(env.disk_free)}")
        print(f"Memory:        {m.format_bytes(env.ram_total)}")
    else:
        print("Disk/memory:   not checked (Ollama runs on another machine)")

    if not env.running:
        print()
        for line in ollama_problem_lines(env):
            print(line)
        return 1
    if not env.model_installed:
        print()
        print(f"To install it: {hai_model_command('pull ' + env.model, config_path)}")
        return 1
    if m.same_model(env.model, m.OLD_DEFAULT_MODEL):
        notice = m.old_default_notice(env.model)
        if notice:
            print()
            print(notice)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    config, config_path = _load(args)
    oc = m.ollama_config(config)
    policy = m.effective_licence_policy(config)
    installed = m.list_installed(oc["base_url"])
    catalog = m.load_catalog()

    print(f"Recommended (licence policy: {policy}; measured on {catalog.hardware}):")
    rows = []
    for entry in catalog.recommended(policy):
        mark = "*" if m.same_model(entry.name, oc["model"]) else " "
        have = "installed" if m.find_installed(entry.name, installed) else ""
        rows.append(
            (
                f"{mark} {entry.name}",
                entry.role,
                m.format_bytes(entry.download_bytes),
                m.percent(entry.task_accuracy),
                f"{entry.median_latency_s:g} s",
                entry.licence_name,
                have,
            )
        )
    _table(("  model", "role", "download", "accuracy", "median", "licence", ""), rows)
    if policy == "commercial":
        hidden = [e.name for e in catalog.models if not e.commercial_use]
        if hidden:
            print(f"  Not shown under the commercial policy: {', '.join(hidden)}")

    print()
    if installed is None:
        print(f"Installed: unknown (Ollama is not answering at {oc['base_url']})")
        return 1
    if not installed:
        print("Installed: none yet")
        cmd = hai_model_command("pull " + catalog.default.name, config_path)
        print(f"  To install the default: {cmd}")
        return 0
    print("Installed in Ollama:")
    rows = []
    for model in sorted(installed, key=lambda x: x.name):
        mark = "*" if m.same_model(model.name, oc["model"]) else " "
        entry = catalog.get(model.name)
        rows.append(
            (
                f"{mark} {model.name}",
                m.format_bytes(model.size),
                model.parameter_size,
                entry.role if entry else "untested with hai",
            )
        )
    _table(("  model", "size", "params", "in hai's catalog"), rows)
    print("\n* = hai's configured model")
    return 0


def _table(headers: tuple, rows: List[tuple]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        widths = [max(w, len(str(c))) for w, c in zip(widths, row)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers).rstrip())
    for row in rows:
        print(fmt.format(*row).rstrip())


def cmd_pull(args: argparse.Namespace) -> int:
    config, config_path = _load(args)
    oc = m.ollama_config(config)
    env = m.detect_environment(oc["base_url"], args.name)
    if not env.running:
        for line in ollama_problem_lines(env):
            print(line, file=sys.stderr)
        return 1
    if env.model_installed:
        print(f"{args.name} is already installed.")
        return 0
    return 0 if consented_pull(
        env, args.name, assume_yes=args.yes, force=args.force, config_path=config_path
    ) else 1


def cmd_use(args: argparse.Namespace) -> int:
    config, config_path = _load(args)
    oc = m.ollama_config(config)
    name = args.name.strip()
    catalog = _catalog_or_none()

    if not args.no_pull:
        env = m.detect_environment(oc["base_url"], name)
        if not env.running:
            for line in ollama_problem_lines(env):
                print(line, file=sys.stderr)
            print(
                f"Config not changed. To set it anyway: hai-model use {name} --no-pull",
                file=sys.stderr,
            )
            return 1
        if not env.model_installed:
            if not consented_pull(
                env, name, assume_yes=args.yes, force=args.force, config_path=config_path
            ):
                print(f"Config not changed. To set it anyway: hai-model use {name} --no-pull")
                return 1

    if catalog and not catalog.get(name):
        print(f"Note: {name} is not in hai's catalog, so it is untested with hai.")
        print("      eval/README.md in the hai repository explains how to score it.")
    elif catalog:
        entry = catalog.get(name)
        if entry and not m.allowed_by_policy(entry, m.effective_licence_policy(config)):
            print(
                f"Note: {name} is not recommended under your licence policy ({entry.licence_name})."
            )

    old, new = m.set_config_model(config_path, name)
    print(f"providers.ollama.model: {old or '(not set)'} -> {new}  ({config_path})")
    if config.get("provider", "ollama") != "ollama":
        print(
            f"Note: hai's provider is {config.get('provider')}; this applies when it uses Ollama."
        )
    return 0


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hai-model",
        description="See, install and switch hai's local Ollama models.",
    )
    parser.add_argument("--version", action="version", version=f"hai-model {__version__}")
    parser.add_argument(
        "--config", metavar="FILE", help="config file (default: ~/.hai/config.yaml)"
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("status", help="Ollama state, the configured model, disk and memory")
    sub.add_parser("list", help="installed models next to the recommended ones")

    pull = sub.add_parser("pull", help="download a model (shows size, disk and licence first)")
    pull.add_argument("name")
    pull.add_argument("-y", "--yes", action="store_true", help="download without asking")
    pull.add_argument("--force", action="store_true", help="download even when disk space is low")

    use = sub.add_parser("use", help="make NAME hai's Ollama model")
    use.add_argument("name")
    use.add_argument("-y", "--yes", action="store_true", help="download without asking if needed")
    use.add_argument(
        "--no-pull", action="store_true", help="set it without checking or downloading"
    )
    use.add_argument("--force", action="store_true", help="download even when disk space is low")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    commands = {"status": cmd_status, "list": cmd_list, "pull": cmd_pull, "use": cmd_use}
    if not args.command:
        parser.print_help()
        return 0
    try:
        return commands[args.command](args)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
