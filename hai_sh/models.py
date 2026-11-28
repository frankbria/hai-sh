"""
Finding, installing and switching hai's local models.

Pure functions, no printing: the CLI layers (``hai_sh/model_cli.py`` and
``hai_sh/__main__.py``) decide what the user sees. Design and the reasons for
each rule: docs/design/model-management.md.

Every probe of Ollama has a short timeout and degrades to "unknown" instead of
raising, so detection can never be the reason a command fails.
"""

from __future__ import annotations

import json
import os
import re
import platform
import shutil
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import yaml

from hai_sh.providers.ollama import DEFAULT_OLLAMA_MODEL

# What hai may recommend: "any" recommends every catalog entry, "commercial"
# only entries whose licence allows commercial use. A paid build flips this one
# line. A user can tighten it in config (models.licence_policy) but never
# loosen it. See docs/design/model-management.md section 6.2.
DEFAULT_LICENCE_POLICY = "any"
LICENCE_POLICIES = ("any", "commercial")

ROLES = ("default", "lighter", "stronger")

CATALOG_PATH = Path(__file__).parent / "data" / "models.yaml"

# Refuse a pull that would leave less free space than 10% of the disk or 2 GB,
# whichever is larger. The 10% part is capped at 20 GB: on a 1 TB disk an
# uncapped 10% would refuse a 4.6 GB download with 90 GB still free.
MIN_FREE_FRACTION = 0.10
MIN_FREE_BYTES = 2 * 1000**3
MAX_FRACTION_FLOOR_BYTES = 20 * 1000**3
# Warn when a model's memory use is above this share of total RAM.
RAM_WARN_FRACTION = 0.70

PROBE_TIMEOUT = 2

# Official Ollama instructions, from docs.ollama.com/linux and
# ollama.com/download (read 2026-11-28). hai prints these; it never runs them.
OLLAMA_INSTALL_COMMAND = "curl -fsSL https://ollama.com/install.sh | sh"
OLLAMA_DOWNLOAD_URL = "https://ollama.com/download"


# --------------------------------------------------------------------------
# Catalog
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CatalogModel:
    """One recommended model, with the evidence for recommending it."""

    name: str
    role: str
    parameters: str
    download_bytes: int
    loaded_bytes: Optional[int]
    task_accuracy: float
    accuracy_ci: Tuple[float, float]
    refused: int
    median_latency_s: float
    licence: str
    licence_name: str
    commercial_use: bool
    licence_checked: str
    clears_bar: bool

    @property
    def memory_bytes(self) -> int:
        """Memory estimate: the measured loaded size, else the download size."""
        return self.loaded_bytes if self.loaded_bytes else self.download_bytes


@dataclass(frozen=True)
class Catalog:
    """The parsed models.yaml."""

    schema_version: int
    eval_run: str
    hardware: str
    cases: int
    models: Tuple[CatalogModel, ...]

    def get(self, name: str) -> Optional[CatalogModel]:
        """Return the entry for ``name`` (tag-insensitive for ``:latest``)."""
        wanted = normalise_name(name)
        for model in self.models:
            if normalise_name(model.name) == wanted:
                return model
        return None

    @property
    def default(self) -> CatalogModel:
        """The single default entry."""
        return [m for m in self.models if m.role == "default"][0]

    def by_role(self, role: str, policy: str = "any") -> List[CatalogModel]:
        """Entries for ``role`` in preference order, filtered by ``policy``."""
        return [m for m in self.models if m.role == role and allowed_by_policy(m, policy)]

    def recommended(self, policy: str = "any") -> List[CatalogModel]:
        """Every entry hai may recommend under ``policy``, default first."""
        out: List[CatalogModel] = []
        for role in ROLES:
            out.extend(self.by_role(role, policy))
        return out


class CatalogError(ValueError):
    """models.yaml is missing or malformed."""


def _parse_catalog(data: Dict[str, Any]) -> Catalog:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise CatalogError("models.yaml: unsupported or missing schema_version")
    models = []
    for raw in data.get("models") or []:
        try:
            ci = raw["accuracy_ci"]
            model = CatalogModel(
                name=str(raw["name"]),
                role=str(raw["role"]),
                parameters=str(raw.get("parameters", "")),
                download_bytes=int(raw["download_bytes"]),
                loaded_bytes=int(raw["loaded_bytes"]) if raw.get("loaded_bytes") else None,
                task_accuracy=float(raw["task_accuracy"]),
                accuracy_ci=(float(ci[0]), float(ci[1])),
                refused=int(raw["refused"]),
                median_latency_s=float(raw["median_latency_s"]),
                licence=str(raw["licence"]),
                licence_name=str(raw.get("licence_name") or raw["licence"]),
                commercial_use=bool(raw["commercial_use"]),
                licence_checked=str(raw["licence_checked"]),
                clears_bar=bool(raw["clears_bar"]),
            )
        except (KeyError, TypeError, ValueError, IndexError) as e:
            raise CatalogError(f"models.yaml: bad entry {raw!r}: {e}") from e
        if model.role not in ROLES:
            raise CatalogError(f"models.yaml: {model.name} has unknown role {model.role!r}")
        models.append(model)
    if sum(1 for m in models if m.role == "default") != 1:
        raise CatalogError("models.yaml must have exactly one default model")
    return Catalog(
        schema_version=1,
        eval_run=str(data.get("eval_run", "")),
        hardware=str(data.get("hardware", "")),
        cases=int(data.get("cases", 0)),
        models=tuple(models),
    )


_catalog_cache: Optional[Catalog] = None


def load_catalog(path: Optional[Path] = None) -> Catalog:
    """Load the shipped catalog (cached) or the one at ``path``."""
    global _catalog_cache
    if path is None and _catalog_cache is not None:
        return _catalog_cache
    source = path or CATALOG_PATH
    try:
        data = yaml.safe_load(Path(source).read_text())
    except (OSError, yaml.YAMLError) as e:
        raise CatalogError(f"Cannot read {source}: {e}") from e
    catalog = _parse_catalog(data)
    if path is None:
        _catalog_cache = catalog
    return catalog


def allowed_by_policy(model: CatalogModel, policy: str) -> bool:
    """Whether ``policy`` lets hai recommend ``model``."""
    return policy != "commercial" or model.commercial_use


def effective_licence_policy(config: Optional[Dict[str, Any]] = None) -> str:
    """
    The licence policy in force: "commercial" if the package or the user's
    config says so, otherwise "any". Unknown values in config are ignored.
    """
    if DEFAULT_LICENCE_POLICY == "commercial":
        return "commercial"
    models = (config or {}).get("models")
    user = models.get("licence_policy") if isinstance(models, dict) else None
    return "commercial" if user == "commercial" else "any"


# --------------------------------------------------------------------------
# Names
# --------------------------------------------------------------------------


def normalise_name(name: str) -> str:
    """
    Normalise an Ollama model name for comparison.

    Ollama reports ``llama3.2:latest`` for a configured ``llama3.2``, so a name
    with no tag gets ``:latest``. ``hf.co/...`` names are kept as they are.
    """
    name = (name or "").strip()
    if not name or name.startswith("hf.co/"):
        return name
    last = name.rsplit("/", 1)[-1]
    return name if ":" in last else f"{name}:latest"


def same_model(a: str, b: str) -> bool:
    """True when ``a`` and ``b`` name the same Ollama model."""
    return normalise_name(a) == normalise_name(b)


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------


def display_url(url: str) -> str:
    """``url`` without any ``user:password@`` part, for printing."""
    return re.sub(r"//[^/@]*@", "//", url or "")


def is_local_url(base_url: str) -> bool:
    """True when ``base_url`` points at this machine."""
    try:
        host = (urlparse(base_url or "").hostname or "").lower()
    except ValueError:  # e.g. an unfinished IPv6 address like http://[::1
        return False
    return host in ("localhost", "127.0.0.1", "::1", "0.0.0.0") or host.startswith("127.")


def _get_json(url: str, timeout: float = PROBE_TIMEOUT) -> Optional[Any]:
    import requests

    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            return None
        return response.json()
    except Exception:
        return None


def get_ollama_version(base_url: str) -> Optional[str]:
    """Ollama's version string, or None when it doesn't answer."""
    data = _get_json(f"{base_url.rstrip('/')}/api/version")
    if isinstance(data, dict) and data.get("version"):
        return str(data["version"])
    return None


@dataclass
class InstalledModel:
    """A model Ollama has on disk (from /api/tags)."""

    name: str
    size: int = 0
    parameter_size: str = ""
    quantization: str = ""


def list_installed(base_url: str) -> Optional[List[InstalledModel]]:
    """Models Ollama has installed, or None when Ollama doesn't answer."""
    data = _get_json(f"{base_url.rstrip('/')}/api/tags")
    if not isinstance(data, dict):
        return None
    models = data.get("models") or []
    if not isinstance(models, list):
        return None
    out = []
    for m in models:
        if not isinstance(m, dict) or not m.get("name"):
            continue
        details = m.get("details")
        details = details if isinstance(details, dict) else {}
        try:
            size = int(m.get("size") or 0)
        except (TypeError, ValueError, OverflowError):  # 1e309 parses as inf
            size = 0
        out.append(
            InstalledModel(
                name=str(m["name"]),
                size=size,
                parameter_size=str(details.get("parameter_size") or ""),
                quantization=str(details.get("quantization_level") or ""),
            )
        )
    return out


def find_installed(
    name: str, installed: Optional[List[InstalledModel]]
) -> Optional[InstalledModel]:
    """The installed model matching ``name``, if any."""
    for model in installed or []:
        if same_model(model.name, name):
            return model
    return None


# Where the Linux install script's ollama service user keeps its models.
SERVICE_MODELS_DIR = Path("/usr/share/ollama/.ollama/models")


def ollama_model_dirs() -> List[Path]:
    """
    Every place this machine's Ollama may keep models that exists:
    ``$OLLAMA_MODELS``, ``~/.ollama/models`` and the Linux service location.
    hai can't tell which one the running Ollama uses (a service ignores the
    user's environment), so the disk check looks at all of them.
    """
    candidates = []
    if os.environ.get("OLLAMA_MODELS"):
        candidates.append(Path(os.environ["OLLAMA_MODELS"]).expanduser())
    candidates.append(Path.home() / ".ollama" / "models")
    candidates.append(SERVICE_MODELS_DIR)
    seen, out = set(), []
    for i, path in enumerate(candidates):
        # $OLLAMA_MODELS counts even before Ollama creates it: that's where it
        # will download to (its disk is measured at the nearest existing parent).
        explicit = i == 0 and bool(os.environ.get("OLLAMA_MODELS"))
        # A .ollama folder without models/ yet (first pull) still says which
        # disk the download will land on.
        if (explicit or path.is_dir() or path.parent.is_dir()) and path not in seen:
            seen.add(path)
            out.append(path)
    return out


def ollama_models_dir() -> Optional[Path]:
    """The first of :func:`ollama_model_dirs`, or None."""
    dirs = ollama_model_dirs()
    return dirs[0] if dirs else None


def free_space_floor(disk_total: int) -> float:
    """Bytes hai keeps free on a disk of this size: 10% (at most 20 GB), never under 2 GB."""
    return max(min(MIN_FREE_FRACTION * disk_total, MAX_FRACTION_FLOOR_BYTES), MIN_FREE_BYTES)


def tightest_disk(dirs: List[Path]) -> Tuple[Optional[Path], Optional[int], Optional[int]]:
    """
    Of the disks holding ``dirs``, the one with the least room above the
    space hai keeps free on it (which depends on the disk's size), with its
    (free, total). A download then passes only if it fits on every disk
    Ollama might be writing to. With no directory, the home disk.
    """
    best: Tuple[Optional[Path], Optional[int], Optional[int]] = (None, None, None)
    best_room: Optional[float] = None
    for path in dirs:
        free, total = disk_space(path)
        if free is None or not total:
            continue
        room = free - free_space_floor(total)
        if best_room is None or room < best_room:
            best, best_room = (path, free, total), room
    if best[1] is None:
        # No models directory yet (first pull). Ollama creates $OLLAMA_MODELS
        # if set, else ~/.ollama/models; measure the disk it will land on.
        if dirs:
            target: Optional[Path] = dirs[0]
        elif os.environ.get("OLLAMA_MODELS"):
            target = Path(os.environ["OLLAMA_MODELS"]).expanduser()
        else:
            # disk_space walks up to the nearest folder that exists, so an
            # existing ~/.ollama on its own mount is the one measured.
            target = Path.home() / ".ollama" / "models"
        free, total = disk_space(target)
        best = (dirs[0] if dirs else None, free, total)
    return best


def disk_space(path: Optional[Path]) -> Tuple[Optional[int], Optional[int]]:
    """(free, total) bytes for the disk holding ``path``, or (None, None)."""
    probe = path
    if probe is None:
        probe = Path.home()
    # A directory Ollama hasn't created yet lives on its nearest existing parent's disk.
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    try:
        usage = shutil.disk_usage(str(probe))
        return usage.free, usage.total
    except OSError:
        return None, None


def total_ram() -> Optional[int]:
    """Total physical memory in bytes, or None when it can't be read."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    if platform.system() == "Darwin":
        try:
            out = subprocess.run(
                ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=2
            )
            return int(out.stdout.strip())
        except (OSError, ValueError, subprocess.SubprocessError):
            return None
    return None


@dataclass
class ModelEnvironment:
    """What hai knows about the machine's Ollama and the configured model."""

    base_url: str
    model: str
    local: bool
    ollama_binary: Optional[str] = None
    version: Optional[str] = None
    installed: Optional[List[InstalledModel]] = None
    models_dir: Optional[Path] = None
    disk_free: Optional[int] = None
    disk_total: Optional[int] = None
    ram_total: Optional[int] = None
    catalog_entry: Optional[CatalogModel] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def running(self) -> bool:
        return self.installed is not None or self.version is not None

    @property
    def model_installed(self) -> bool:
        return find_installed(self.model, self.installed) is not None


def detect_environment(base_url: str, model: str) -> ModelEnvironment:
    """Gather a ModelEnvironment. Never raises."""
    local = is_local_url(base_url)
    env = ModelEnvironment(base_url=base_url.rstrip("/"), model=model, local=local)
    env.version = get_ollama_version(base_url)
    env.installed = list_installed(base_url)
    try:
        env.catalog_entry = load_catalog().get(model)
    except CatalogError:
        env.catalog_entry = None
    if local:
        env.ollama_binary = shutil.which("ollama")
        env.models_dir, env.disk_free, env.disk_total = tightest_disk(ollama_model_dirs())
        env.ram_total = total_ram()
    return env


def ollama_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """The providers.ollama section with defaults filled in."""
    providers = (config or {}).get("providers") if isinstance(config, dict) else None
    ollama = providers.get("ollama") if isinstance(providers, dict) else None
    section = dict(ollama) if isinstance(ollama, dict) else {}
    # A blank or non-text value (base_url: null) means the default, as it does for hai.
    for key, default in (("base_url", "http://localhost:11434"), ("model", DEFAULT_OLLAMA_MODEL)):
        value = section.get(key)
        section[key] = value.strip() if isinstance(value, str) and value.strip() else default
    return section


# --------------------------------------------------------------------------
# Checks before a pull
# --------------------------------------------------------------------------


@dataclass
class PullCheck:
    """Result of checking whether a pull should go ahead."""

    ok: bool
    messages: List[str] = field(default_factory=list)


def check_pull(
    download_bytes: Optional[int],
    memory_bytes: Optional[int],
    disk_free: Optional[int],
    disk_total: Optional[int],
    ram_total: Optional[int],
    force: bool = False,
) -> PullCheck:
    """
    Decide whether a pull may start.

    Stops (unless ``force``) when the download would leave less than 10% of
    the disk (at most 20 GB) or 2 GB free, whichever is larger. Warns, without stopping, when
    the model's memory use is above 70% of RAM. Unknown values skip a check.
    """
    result = PullCheck(ok=True)
    if download_bytes and disk_free is not None and disk_total:
        floor = free_space_floor(disk_total)
        left = disk_free - download_bytes
        if left < floor:
            msg = (
                f"Not enough disk space: the download needs {format_bytes(download_bytes)} "
                f"and would leave {format_bytes(max(left, 0))} free "
                f"(hai keeps at least {format_bytes(floor)} free)."
            )
            if force:
                result.messages.append(msg + " Continuing because of --force.")
            else:
                result.ok = False
                result.messages.append(msg + " Free some space, or pass --force.")
    if memory_bytes and ram_total and memory_bytes > RAM_WARN_FRACTION * ram_total:
        result.messages.append(
            f"This model needs about {format_bytes(memory_bytes)} of memory and this machine "
            f"has {format_bytes(ram_total)}; answers may be slow or fail."
        )
    return result


# --------------------------------------------------------------------------
# Pull
# --------------------------------------------------------------------------


@dataclass
class PullProgress:
    """One update from a pull."""

    status: str
    completed: int = 0
    total: int = 0

    @property
    def fraction(self) -> Optional[float]:
        return (self.completed / self.total) if self.total else None


class PullError(RuntimeError):
    """Ollama refused or failed the pull."""


def pull_model(
    base_url: str,
    name: str,
    on_progress: Optional[Callable[[PullProgress], None]] = None,
    timeout: float = 30,
) -> None:
    """
    Pull ``name`` through Ollama's streaming /api/pull.

    Reports overall progress summed across layers. A cancelled pull resumes on
    the next call (Ollama keeps partial layers). Raises PullError on failure.
    """
    import requests

    layers: Dict[str, Tuple[int, int]] = {}
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/api/pull",
            json={"model": name, "stream": True},
            stream=True,
            timeout=timeout,
        )
    except requests.exceptions.RequestException as e:
        raise PullError(f"Cannot reach Ollama at {display_url(base_url)}") from e

    if response.status_code != 200:
        raise PullError(_error_text(response) or f"Ollama returned HTTP {response.status_code}")

    finished = False
    try:
        for raw in response.iter_lines():
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except (ValueError, TypeError):
                continue
            if not isinstance(event, dict):
                raise PullError(f"Ollama sent an unexpected reply while downloading: {raw[:80]!r}")
            if event.get("error"):
                raise PullError(str(event["error"]))
            status = str(event.get("status", ""))
            digest = event.get("digest")
            if digest and event.get("total"):
                try:
                    layers[digest] = (int(event.get("completed") or 0), int(event["total"]))
                except (TypeError, ValueError, OverflowError):
                    pass  # progress is cosmetic; a bad counter doesn't stop the pull
            if on_progress:
                done = sum(c for c, _ in layers.values())
                total = sum(t for _, t in layers.values())
                on_progress(PullProgress(status=status, completed=done, total=total))
            if status == "success":
                # Done: don't wait for a server that keeps the stream open.
                finished = True
                break
    except requests.exceptions.RequestException as e:
        raise PullError(f"The connection to Ollama was lost during the download: {e}") from e
    finally:
        response.close()
    if not finished:
        raise PullError("The download stopped before Ollama reported success.")


def _error_text(response: Any) -> str:
    try:
        data = response.json()
        if isinstance(data, dict) and data.get("error"):
            return str(data["error"])
    except Exception:
        pass
    return ""


# --------------------------------------------------------------------------
# Config edit
# --------------------------------------------------------------------------


def set_config_model(
    config_path: Path, name: str, expected_text: Optional[str] = None
) -> Tuple[Optional[str], str]:
    """
    Set ``providers.ollama.model`` in ``config_path``, preserving the file.

    Edits the single ``model:`` line under ``providers:`` > ``ollama:`` in
    place, so comments survive. Falls back to a YAML rewrite only when that
    line can't be found. Writes ``<file>.bak`` first and keeps mode 600.

    ``expected_text``, when given, is the file's text when the caller read
    its settings (``""`` for a missing file). If the file no longer matches,
    nothing is written: the caller acted on settings that have since changed.

    Returns (old model or None, new model).
    """
    config_path = Path(config_path)
    backup_path = config_path.with_name(config_path.name + ".bak")
    if config_path.exists() and backup_path.exists() and os.path.samefile(config_path, backup_path):
        raise ConfigWriteError(
            f"{config_path} and {backup_path} are the same file, so hai can't keep a "
            "backup. Nothing was changed."
        )
    original = config_path.read_text() if config_path.exists() else ""
    if expected_text is not None and original != expected_text:
        raise ConfigWriteError(
            f"{config_path} changed while hai was working (for example during the "
            "download), so hai won't edit it. Run the command again. Nothing was changed."
        )
    old: Optional[str] = None

    new_text = _edit_model_line(original, name)
    if new_text is not None and not _only_model_changed(original, new_text[0], name):
        new_text = None  # e.g. a multi-line YAML value; rewrite the file instead
    if new_text is not None:
        new_text, old = new_text
    else:
        try:
            data = yaml.safe_load(original) if original.strip() else {}
        except yaml.YAMLError as e:
            raise ConfigWriteError(
                f"{config_path} isn't valid YAML ({e.__class__.__name__}), so hai won't "
                "edit it. Fix the file, or set providers.ollama.model by hand. "
                "Nothing was changed."
            ) from e
        data = {} if data is None else data
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("providers") or {}, dict)
            or not isinstance((data.get("providers") or {}).get("ollama") or {}, dict)
        ):
            raise ConfigWriteError(
                f"{config_path} doesn't have the layout hai expects (providers: ollama: "
                "model:), so hai won't rewrite it. Nothing was changed."
            )
        # Copy both mappings: a YAML alias (``ollama: *shared``) would
        # otherwise carry the new model into every provider sharing it.
        providers = dict(data.get("providers") or {})
        data["providers"] = providers
        ollama = dict(providers.get("ollama") or {})
        providers["ollama"] = ollama
        old = ollama.get("model")
        ollama["model"] = name
        new_text = yaml.safe_dump(data, sort_keys=False, default_flow_style=False)

    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
    # Write the new config to its temporary file first: if hai can't (a
    # symlink into a read-only dotfiles folder), the previous .bak is kept.
    tmp, target = _stage_private(config_path, new_text)
    saved: Optional[Tuple[str, Optional[Path]]] = None
    backup_replaced = False
    try:
        if config_path.exists():
            # Check before touching the backup too, so a refused edit also
            # keeps the previous .bak.
            if config_path.read_text() != original:
                raise ConfigWriteError(
                    f"{config_path} changed while hai was updating it. Nothing was "
                    "changed; run the command again."
                )
            # Keep the previous backup aside, so it can be put back if the
            # final check below refuses the edit.
            saved = _keep_aside(backup_path)
            # Replace the backup itself, even if it is a symlink: never write
            # through it into whatever file it points to.
            replace_private(backup_path, original, follow_symlink=False)
            backup_replaced = True
        # If the file changed since hai read it (an editor saved it
        # meanwhile), stop rather than replace that edit with an older copy.
        _commit_private(tmp, target, expected=original)
    except BaseException:
        _discard(tmp)
        if backup_replaced:
            _put_back(backup_path, saved)
        else:
            _drop_aside(saved)
        raise
    _drop_aside(saved)
    return old, name


def _keep_aside(path: Path) -> Optional[Tuple[str, Optional[Path]]]:
    """
    Hard-link ``path`` (a file or a symlink, never its target) to a hidden
    name next to it, so it can be put back. ("absent", None) if there is no
    ``path``; None if the filesystem can't make the link (nothing to restore).
    """
    if not os.path.lexists(str(path)):
        return ("absent", None)
    aside = path.with_name(f".{path.name}.hai-prev-{os.getpid()}")
    try:
        if os.path.lexists(str(aside)):
            os.unlink(str(aside))
        os.link(str(path), str(aside), follow_symlinks=False)
    except (OSError, NotImplementedError):
        return None
    return ("kept", aside)


def _put_back(path: Path, saved: Optional[Tuple[str, Optional[Path]]]) -> None:
    """Undo replacing ``path``: restore what _keep_aside kept, best effort."""
    if saved is None:
        return
    kind, aside = saved
    try:
        if kind == "absent":
            os.unlink(str(path))
        elif aside is not None:
            os.replace(str(aside), str(path))
    except OSError:
        pass


def _drop_aside(saved: Optional[Tuple[str, Optional[Path]]]) -> None:
    if saved is not None and saved[1] is not None:
        _discard(saved[1])


class ConfigWriteError(OSError):
    """The config could not be replaced safely; nothing was changed."""


def replace_private(
    path: Path, text: str, follow_symlink: bool = True, expected: Optional[str] = None
) -> None:
    """
    Replace ``path`` with ``text`` atomically: write a mode-600 file next to it,
    flush it to disk, then rename it over the old one. If the disk fills up or
    hai is stopped halfway, the old file is still there, whole.

    With ``follow_symlink`` (the config), a symlinked file (dotfiles) keeps
    its link and the file it points to is replaced. Without it (the backup),
    the link itself is replaced and its target is never touched.

    With ``expected``, the file must still hold exactly that text just before
    the rename; otherwise someone else changed it and it is left alone.

    Raises ConfigWriteError, leaving ``path`` unchanged, when the directory
    doesn't allow the temporary file (hai never falls back to rewriting the
    live file in place) or when ``expected`` no longer matches.
    """
    tmp, target = _stage_private(path, text, follow_symlink)
    try:
        _commit_private(tmp, target, expected)
    except BaseException:
        _discard(tmp)
        raise


def _stage_private(path: Path, text: str, follow_symlink: bool = True) -> Tuple[Path, Path]:
    """
    Write ``text`` to a flushed mode-600 temporary file next to ``path``.
    Returns (temporary file, file it will replace). See replace_private.
    """
    target = Path(os.path.realpath(str(path))) if follow_symlink else Path(path)
    tmp = target.with_name(f".{target.name}.hai-tmp-{os.getpid()}")
    try:
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as e:
        raise ConfigWriteError(
            f"Can't write {target}: hai needs to create a file in {target.parent} "
            f"({e.strerror}). Nothing was changed.",
        ) from e
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fd = -1
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        if fd >= 0:
            os.close(fd)
        _discard(tmp)
        raise
    return tmp, target


def _commit_private(tmp: Path, target: Path, expected: Optional[str] = None) -> None:
    """Rename ``tmp`` over ``target``, if ``target`` still holds ``expected``."""
    if expected is not None:
        current = target.read_text() if target.exists() else ""
        if current != expected:
            raise ConfigWriteError(
                f"{target} changed while hai was updating it. Nothing was changed; "
                "run the command again."
            )
    os.replace(str(tmp), str(target))


def _discard(tmp: Path) -> None:
    try:
        os.unlink(str(tmp))
    except OSError:
        pass


def _only_model_changed(original: str, edited: str, name: str) -> bool:
    """True if ``edited`` parses and differs from ``original`` only in the model."""
    try:
        before = yaml.safe_load(original) or {}
        after = yaml.safe_load(edited) or {}
    except yaml.YAMLError:
        return False
    try:
        if after["providers"]["ollama"]["model"] != name:
            return False
        # Copy before changing, so a YAML alias shared with another provider
        # shows up as a second change (and the file is rewritten instead).
        before["providers"] = dict(before["providers"])
        before["providers"]["ollama"] = dict(before["providers"]["ollama"])
        before["providers"]["ollama"]["model"] = name
    except (KeyError, TypeError, ValueError):
        return False
    return before == after


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _edit_model_line(text: str, name: str) -> Optional[Tuple[str, Optional[str]]]:
    """Replace the model line under providers.ollama; None if not found."""
    lines = text.splitlines(keepends=True)
    in_providers = in_ollama = False
    providers_indent = ollama_indent = child_indent = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        ind = _indent(line)
        key = stripped.split(":", 1)[0].strip()
        if in_ollama and ind <= ollama_indent:
            in_ollama = False
        if in_providers and ind <= providers_indent:
            in_providers = False
        if not in_providers:
            if key == "providers" and stripped.rstrip().endswith(":") and ind == 0:
                in_providers, providers_indent = True, ind
            continue
        if not in_ollama:
            if key == "ollama" and stripped.split("#", 1)[0].rstrip().endswith(":"):
                in_ollama, ollama_indent, child_indent = True, ind, -1
            continue
        if child_indent < 0:
            child_indent = ind
        if ind == child_indent and key == "model" and ":" in stripped:
            value_part = stripped.split(":", 1)[1]
            comment = ""
            body = value_part
            # Keep a trailing comment that is outside quotes.
            hash_at = _comment_start(value_part)
            if hash_at is not None:
                body, comment = value_part[:hash_at], value_part[hash_at:]
            old_raw = body.strip()
            try:
                old = yaml.safe_load(old_raw) if old_raw else None
            except yaml.YAMLError:
                old = old_raw
            spacing = body[len(body.rstrip()) :] if comment else ""
            newline = "\n" if line.endswith("\n") else ""
            lines[i] = (
                f"{' ' * ind}model: {json.dumps(name)}"
                f"{spacing if spacing else (' ' if comment else '')}{comment.rstrip()}{newline}"
            )
            return "".join(lines), (str(old) if old is not None else None)
    return None


def _comment_start(value: str) -> Optional[int]:
    quote = None
    for i, ch in enumerate(value):
        if quote:
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or value[i - 1] in " \t"):
            return i
    return None


# --------------------------------------------------------------------------
# One-time notices
# --------------------------------------------------------------------------


def _notices_path(hai_dir: Optional[Path] = None) -> Path:
    if hai_dir is None:
        from hai_sh.init import get_hai_dir

        hai_dir = get_hai_dir()
    return Path(hai_dir) / ".notices"


def notice_seen(key: str, hai_dir: Optional[Path] = None) -> bool:
    """Whether the one-time notice ``key`` was already shown."""
    try:
        return key in _notices_path(hai_dir).read_text().split()
    except OSError:
        return False


def mark_notice_seen(key: str, hai_dir: Optional[Path] = None) -> None:
    """Record that ``key`` was shown. Failures are ignored."""
    path = _notices_path(hai_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(key + "\n")
    except OSError:
        pass


OLD_DEFAULT_MODEL = "llama3.2"
OLD_DEFAULT_NOTICE = "default-model-gemma4-e2b"


def old_default_notice(model: str, config_path: Optional[Path] = None) -> Optional[str]:
    """
    The one-time notice for users still on the v0.1.4 default, or None.
    The caller decides whether this is a TTY and records that it was shown.
    With ``config_path`` (the file hai read), the suggested command names it,
    so following it changes that config and not the default one.
    """
    from hai_sh.model_cli import hai_model_command

    if not same_model(model, OLD_DEFAULT_MODEL):
        return None
    try:
        catalog = load_catalog()
    except CatalogError:
        return None
    new = catalog.default
    return (
        f"hai's default local model is now {new.name} "
        f"({percent(new.task_accuracy)} on hai's {catalog.cases}-case test, "
        f"{new.refused} of 7 dangerous requests refused; llama3.2 scored 77% and refused 5 of 7). "
        f"Your config keeps {OLD_DEFAULT_MODEL}. To switch: "
        f"{hai_model_command('use ' + new.name, config_path)}"
    )


# --------------------------------------------------------------------------
# Cloud fallback and install hints
# --------------------------------------------------------------------------

CLOUD_PROVIDERS = (("openai", "OPENAI_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY"))


def configured_cloud_providers(config: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Cloud providers the user already set up: an api_key in config, or the
    provider's usual environment variable. Returns (name, provider config).
    """
    out = []
    providers = (config or {}).get("providers")
    providers = providers if isinstance(providers, dict) else {}
    for name, env_var in CLOUD_PROVIDERS:
        raw = providers.get(name)
        if raw is not None and not isinstance(raw, dict):
            continue  # a malformed section (say, a string) is skipped, not fatal
        section = dict(raw or {})
        key = section.get("api_key") or os.environ.get(env_var)
        if key and str(key).strip():
            section["api_key"] = str(key).strip()
            out.append((name, section))
    return out


def ollama_install_hint(system: Optional[str] = None) -> List[str]:
    """Lines telling the user how to install Ollama. hai never runs these."""
    system = system or platform.system()
    if system == "Darwin":
        return [
            f"Download the Ollama app from {OLLAMA_DOWNLOAD_URL}, or run:",
            f"  {OLLAMA_INSTALL_COMMAND}",
        ]
    return [
        "Install it with the official script (it asks for sudo):",
        f"  {OLLAMA_INSTALL_COMMAND}",
        f"Other options: {OLLAMA_DOWNLOAD_URL}",
    ]


def ollama_start_hint(system: Optional[str] = None) -> List[str]:
    """Lines telling the user how to start Ollama. hai never runs these."""
    system = system or platform.system()
    if system == "Darwin":
        return ["Open the Ollama app, or run in another terminal:", "  ollama serve"]
    return [
        "If Ollama was installed as a service:",
        "  sudo systemctl start ollama",
        "Otherwise, run in another terminal:",
        "  ollama serve",
    ]


# --------------------------------------------------------------------------
# Formatting
# --------------------------------------------------------------------------


def format_bytes(n: Optional[float]) -> str:
    """Decimal units, as Ollama and disk vendors use: 4587156505 -> '4.6 GB'."""
    if n is None:
        return "unknown"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1000 or unit == "TB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1000
    return f"{n:.1f} TB"  # pragma: no cover


def percent(x: float) -> str:
    return f"{round(x * 100)}%"


def describe_model(model: CatalogModel, cases: int) -> str:
    """One line of evidence for a catalog entry."""
    return (
        f"{percent(model.task_accuracy)} on hai's {cases}-case test, "
        f"{model.refused} of 7 dangerous requests refused, "
        f"{model.median_latency_s:g} s median on a CPU-only laptop"
    )
