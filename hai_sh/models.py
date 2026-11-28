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
    user = ((config or {}).get("models") or {}).get("licence_policy")
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


def is_local_url(base_url: str) -> bool:
    """True when ``base_url`` points at this machine."""
    host = (urlparse(base_url or "").hostname or "").lower()
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
    out = []
    for m in data.get("models") or []:
        if not isinstance(m, dict) or not m.get("name"):
            continue
        details = m.get("details") or {}
        out.append(
            InstalledModel(
                name=str(m["name"]),
                size=int(m.get("size") or 0),
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


def ollama_models_dir() -> Optional[Path]:
    """
    Where this machine's Ollama keeps models: ``$OLLAMA_MODELS``, else
    ``~/.ollama/models``, else the Linux service location. First that exists.
    """
    candidates = []
    if os.environ.get("OLLAMA_MODELS"):
        candidates.append(Path(os.environ["OLLAMA_MODELS"]).expanduser())
    candidates.append(Path.home() / ".ollama" / "models")
    candidates.append(Path("/usr/share/ollama/.ollama/models"))
    for path in candidates:
        if path.is_dir():
            return path
    return None


def disk_space(path: Optional[Path]) -> Tuple[Optional[int], Optional[int]]:
    """(free, total) bytes for the disk holding ``path``, or (None, None)."""
    probe = path
    if probe is None:
        probe = Path.home()
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
        env.models_dir = ollama_models_dir()
        env.disk_free, env.disk_total = disk_space(env.models_dir)
        env.ram_total = total_ram()
    return env


def ollama_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """The providers.ollama section with defaults filled in."""
    section = dict(((config or {}).get("providers") or {}).get("ollama") or {})
    section.setdefault("base_url", "http://localhost:11434")
    section.setdefault("model", DEFAULT_OLLAMA_MODEL)
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
        floor = max(min(MIN_FREE_FRACTION * disk_total, MAX_FRACTION_FLOOR_BYTES), MIN_FREE_BYTES)
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
        raise PullError(f"Cannot reach Ollama at {base_url}: {e}") from e

    if response.status_code != 200:
        raise PullError(_error_text(response) or f"Ollama returned HTTP {response.status_code}")

    finished = False
    for raw in response.iter_lines():
        if not raw:
            continue
        try:
            event = json.loads(raw)
        except (ValueError, TypeError):
            continue
        if event.get("error"):
            raise PullError(str(event["error"]))
        status = str(event.get("status", ""))
        digest = event.get("digest")
        if digest and event.get("total"):
            layers[digest] = (int(event.get("completed") or 0), int(event["total"]))
        if on_progress:
            done = sum(c for c, _ in layers.values())
            total = sum(t for _, t in layers.values())
            on_progress(PullProgress(status=status, completed=done, total=total))
        if status == "success":
            finished = True
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


def set_config_model(config_path: Path, name: str) -> Tuple[Optional[str], str]:
    """
    Set ``providers.ollama.model`` in ``config_path``, preserving the file.

    Edits the single ``model:`` line under ``providers:`` > ``ollama:`` in
    place, so comments survive. Falls back to a YAML rewrite only when that
    line can't be found. Writes ``<file>.bak`` first and keeps mode 600.

    Returns (old model or None, new model).
    """
    config_path = Path(config_path)
    original = config_path.read_text() if config_path.exists() else ""
    old: Optional[str] = None

    new_text = _edit_model_line(original, name)
    if new_text is not None:
        new_text, old = new_text
    else:
        data = yaml.safe_load(original) if original.strip() else {}
        if not isinstance(data, dict):
            data = {}
        providers = data.setdefault("providers", {}) or {}
        data["providers"] = providers
        ollama = providers.setdefault("ollama", {}) or {}
        providers["ollama"] = ollama
        old = ollama.get("model")
        ollama["model"] = name
        new_text = yaml.safe_dump(data, sort_keys=False, default_flow_style=False)

    if config_path.exists():
        backup = config_path.with_name(config_path.name + ".bak")
        backup.write_text(original)
        backup.chmod(stat.S_IRUSR | stat.S_IWUSR)
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(new_text)
    config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return old, name


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


def old_default_notice(model: str) -> Optional[str]:
    """
    The one-time notice for users still on the v0.1.4 default, or None.
    The caller decides whether this is a TTY and records that it was shown.
    """
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
        f"Your config keeps {OLD_DEFAULT_MODEL}. To switch: hai-model use {new.name}"
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
    providers = (config or {}).get("providers") or {}
    for name, env_var in CLOUD_PROVIDERS:
        section = dict(providers.get(name) or {})
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
