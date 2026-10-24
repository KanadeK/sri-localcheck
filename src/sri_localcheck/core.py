"""Offline checks of existing SRI declarations against confined local assets."""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
import stat
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote_to_bytes, urljoin, urlsplit

MAX_HTML = 2 * 1024 * 1024
MAX_ASSET = 16 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_ELEMENTS = 1000
MAX_TOKENS = 64
ORIGIN = "https://sri-local.invalid/"
STRENGTH = {"sha256": 32, "sha384": 48, "sha512": 64}
SPACE = re.compile(r"[ \t\r\n\f]+")
BAD_PERCENT = re.compile(r"%(?![0-9a-fA-F]{2})")
RESERVED = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?\Z", re.I)
TOKEN = re.compile(r"(sha256|sha384|sha512)-([A-Za-z0-9+/_-]+={0,2})\Z")


class InputError(ValueError):
    """A fixed-code error, without document values or machine paths."""


def metadata(value: str) -> tuple[str, set[bytes]]:
    """Strict audit policy; unknown, malformed or optional tokens are rejected."""
    tokens = SPACE.split(value.strip(" \t\r\n\f"))
    if not value or not tokens or len(tokens) > MAX_TOKENS:
        raise InputError("invalid_integrity")
    found: dict[str, set[bytes]] = defaultdict(set)
    for token in tokens:
        match = TOKEN.fullmatch(token)
        if not match:
            raise InputError("invalid_integrity")
        algorithm, encoded = match.groups()
        standard = encoded.replace("-", "+").replace("_", "/")
        try:
            # Missing padding is accepted, but redundant padding and nonzero pad bits are not.
            padded = standard + "=" * (-len(standard) % 4)
            digest = base64.b64decode(padded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise InputError("invalid_integrity") from exc
        canonical = base64.b64encode(digest).decode("ascii")
        if len(digest) != STRENGTH[algorithm] or canonical.rstrip("=") != standard.rstrip("="):
            raise InputError("invalid_integrity")
        if "=" in standard and standard != canonical:
            raise InputError("invalid_integrity")
        found[algorithm].add(digest)
    strongest = max(found, key=STRENGTH.__getitem__)
    return strongest, found[strongest]


def validate_components(parts):
    for item in parts:
        if (
            not item
            or item in {".", ".."}
            or item.endswith((".", " "))
            or RESERVED.fullmatch(item)
            or any(ord(char) < 32 or ord(char) == 127 or char in '<>:"\\|?*' for char in item)
        ):
            raise InputError("unsafe_path")


def local_url(value: str, base: str) -> str:
    value = value.strip(" \t\r\n\f")
    if not value or "\\" in value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise InputError("invalid_url")
    if BAD_PERCENT.search(value):
        raise InputError("invalid_url")
    try:
        parsed = urlsplit(value)
        absolute = urljoin(base, value)
        final = urlsplit(absolute)
    except ValueError as exc:
        raise InputError("invalid_url") from exc
    if parsed.scheme or parsed.netloc or value.startswith("//"):
        raise InputError("unverified_external_url")
    if "//" in parsed.path:
        raise InputError("unsafe_path")
    if final.scheme != "https" or final.netloc != "sri-local.invalid":
        raise InputError("unverified_external_url")
    return absolute


def local_path(url: str) -> str:
    try:
        decoded = unquote_to_bytes(urlsplit(url).path).decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise InputError("invalid_url") from exc
    # Remove exactly one root slash; a second slash would be an empty component.
    relative = decoded[1:]
    validate_components(relative.split("/"))
    return relative


def confined(root: Path, relative: str) -> Path:
    parts = relative.split("/")
    validate_components(parts)
    current = root
    for item in parts:
        current = current / item
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise InputError("linked_path")
    if not current.resolve(strict=True).is_relative_to(root):
        raise InputError("unsafe_path")
    if not stat.S_ISREG(info.st_mode):
        raise InputError("not_a_file")
    return current


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.base: str | None = None
        self.base_error = False
        self.elements: list[tuple[int, str, dict, str | None]] = []
        self.bases = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        counts = Counter(key for key, _ in attrs)
        if tag == "base" and "href" in attributes:
            self.bases += 1
            if self.bases == 1:
                self.base = attributes["href"]
                self.base_error = counts["href"] != 1 or self.base is None
            else:
                self.base_error = True
            if "integrity" not in attributes:
                return
        stylesheet = tag == "link" and "stylesheet" in SPACE.split(
            (attributes.get("rel") or "").lower().strip(" \t\r\n\f")
        )
        supported = (tag == "script" and "src" in attributes) or stylesheet
        if not supported and "integrity" not in attributes:
            return
        if len(self.elements) >= MAX_ELEMENTS:
            raise InputError("element_limit")
        error = None
        if not supported:
            error = "unsupported_integrity_element"
        elif any(counts[key] > 1 for key in ("src", "href", "rel", "integrity")):
            error = "duplicate_attribute"
        self.elements.append((self.getpos()[0], tag, attributes, error))

    handle_startendtag = handle_starttag


def hashes(path: Path, budget: dict[str, int]) -> tuple[int, dict[str, bytes]]:
    before = path.stat()
    if before.st_size > MAX_ASSET:
        raise InputError("asset_size_limit")
    if before.st_size > MAX_TOTAL - budget["read"]:
        raise InputError("total_size_limit")
    algorithms = {name: hashlib.new(name) for name in STRENGTH}
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(
            min(65536, MAX_ASSET - size + 1, MAX_TOTAL - budget["read"] + 1)
        ):
            size += len(chunk)
            budget["read"] += len(chunk)
            if size > MAX_ASSET:
                raise InputError("asset_size_limit")
            if budget["read"] > MAX_TOTAL:
                raise InputError("total_size_limit")
            for digest in algorithms.values():
                digest.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ) or size != before.st_size:
        raise InputError("changing_asset")
    return size, {name: digest.digest() for name, digest in algorithms.items()}


def check(root: Path, document: Path, *, require_integrity=False) -> dict:
    try:
        root_info = root.lstat()
        if (
            not stat.S_ISDIR(root_info.st_mode)
            or getattr(root_info, "st_file_attributes", 0) & 0x400
        ):
            raise InputError("invalid_root")
        root = root.resolve(strict=True)
        if document.is_absolute():
            raise InputError("document_must_be_relative")
        relative = document.as_posix()
        html_path = confined(root, relative)
        with html_path.open("rb") as stream:
            data = stream.read(MAX_HTML + 1)
    except OSError as exc:
        raise InputError("input_io_error") from exc
    if not data or len(data) > MAX_HTML:
        raise InputError("html_size_limit")
    try:
        text = data.decode("utf-8-sig", errors="strict")
    except UnicodeError as exc:
        raise InputError("html_not_utf8") from exc
    parser = Document()
    parser.feed(text)
    parser.close()
    try:
        base = ORIGIN + quote(relative, safe="/")
    except UnicodeError as exc:
        raise InputError("unsupported_document_path") from exc
    base_error = "invalid_base" if parser.base_error else None
    if parser.base is not None and not base_error:
        try:
            base = local_url(parser.base, base)
        except InputError:
            base_error = "unverified_base"
    checks: list[dict] = []
    cache: dict[str, tuple[int, dict[str, bytes]]] = {}
    budget = {"read": 0}
    for line, tag, attributes, error in parser.elements:
        if "integrity" not in attributes and not require_integrity:
            continue
        row = {"line": line, "element": tag, "status": "fail"}
        try:
            if error:
                raise InputError(error)
            if base_error:
                raise InputError(base_error)
            if "integrity" not in attributes:
                raise InputError("missing_integrity")
            algorithm, candidates = metadata(attributes["integrity"] or "")
            value = attributes.get("src" if tag == "script" else "href")
            url = local_url(value or "", base)
            asset = local_path(url)
            if asset not in cache:
                path = confined(root, asset)
                cache[asset] = hashes(path, budget)
            size, observed = cache[asset]
            row.update(algorithm=algorithm, bytes=size)
            if observed[algorithm] not in candidates:
                raise InputError("integrity_mismatch")
        except InputError as exc:
            row["code"] = str(exc)
        except OSError:
            row["code"] = "asset_io_error"
        else:
            row.update(status="pass", code="match")
        checks.append(row)
    if not checks:
        raise InputError("no_applicable_declarations")
    failed = sum(row["status"] == "fail" for row in checks)
    return {
        "schema": "sri-localcheck/v1",
        "status": "fail" if failed else "pass",
        "html_sha256": hashlib.sha256(data).hexdigest(),
        "require_integrity": bool(require_integrity),
        "checked": len(checks),
        "failed": failed,
        "cached_assets": len(cache),
        "asset_bytes_read": budget["read"],
        "checks": checks,
    }
