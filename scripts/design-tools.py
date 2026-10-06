#!/usr/bin/env python3
"""Read or hydrate the audited design toolchain without running upstream code."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import urllib.error
import urllib.request

PROJECT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = PROJECT / "docs/design/tooling-sources.json"
CACHE = PROJECT / ".design-toolchain"
ALLOWED_SUFFIXES = {".md", ".py", ".csv", ".json", ".js", ".mjs", ".sh", ".cmd"}


def read_url(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Verisento-design-audit"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def hydrate(source: dict) -> dict:
    repo, revision = source["repository"], source["revision"]
    folder = CACHE / "sources" / source["id"]
    paths = set(source.get("files", []))
    prefixes = source.get("directories", [])
    if prefixes:
        url = f"https://api.github.com/repos/{repo}/git/trees/{revision}?recursive=1"
        tree = json.loads(read_url(url))
        if tree.get("truncated"):
            raise ValueError(f"{repo}: truncated tree, refusing incomplete hydration")
        for entry in tree["tree"]:
            path = entry["path"]
            if entry["type"] != "blob" or entry.get("mode") == "120000":
                continue
            if any(path.startswith(prefix.rstrip("/") + "/") for prefix in prefixes):
                if pathlib.PurePosixPath(path).suffix in ALLOWED_SUFFIXES:
                    paths.add(path)

    def fetch(path: str) -> dict:
        relative = pathlib.PurePosixPath(path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe source path: {path}")
        destination = folder.joinpath(*relative.parts)
        raw_url = f"https://raw.githubusercontent.com/{repo}/{revision}/{path}"
        # A cache entry is always scoped to this exact manifest revision.
        data = read_url(raw_url)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return {"path": path, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        files = list(executor.map(fetch, sorted(paths)))
    result = {"id": source["id"], "repository": repo, "revision": revision, "files": files}
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SOURCE-LOCK.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def check(source: dict) -> list[str]:
    folder = CACHE / "sources" / source["id"]
    lock_path = folder / "SOURCE-LOCK.json"
    if not lock_path.exists():
        return [f"{source['id']}: not hydrated"]
    lock = json.loads(lock_path.read_text())
    if lock.get("revision") != source["revision"]:
        return [f"{source['id']}: revision differs from manifest"]
    problems = []
    for entry in lock["files"]:
        target = folder / entry["path"]
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != entry["sha256"]:
            problems.append(f"{source['id']}: missing or changed {entry['path']}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["list", "hydrate", "check"])
    parser.add_argument("--only", nargs="+", help="Source IDs from the manifest")
    args = parser.parse_args()
    sources = json.loads(MANIFEST.read_text())["sources"]
    if args.only:
        unknown = set(args.only) - {item["id"] for item in sources}
        if unknown:
            parser.error("Unknown source IDs: " + ", ".join(sorted(unknown)))
        sources = [item for item in sources if item["id"] in args.only]
    failed = False
    for source in sources:
        if args.action == "list":
            print(f"{source['id']}: {source['repository']}@{source['revision'][:12]} ({source['license']})")
            continue
        try:
            if args.action == "hydrate":
                result = hydrate(source)
                print(f"{source['id']}: hydrated {len(result['files'])} files; no code executed")
            else:
                problems = check(source)
                failed |= bool(problems)
                print("\n".join(problems) if problems else f"{source['id']}: pinned files verified")
        except (OSError, ValueError, urllib.error.URLError) as error:
            failed = True
            print(f"{source['id']}: {error}")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
