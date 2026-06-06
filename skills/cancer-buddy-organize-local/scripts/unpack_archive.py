#!/usr/bin/env python3
"""Unpack archive files and list medical document files.

Supported formats: .zip, .rar, .7z, .tar, .tar.gz/.tgz, .tar.bz2/.tbz2,
.tar.xz/.txz. Tar variants use the stdlib tarfile module; .rar needs
unrar/unar; .7z needs the system 7z (p7zip).
"""

import sys
import os
import json
import time
import tempfile
import zipfile
import tarfile
import shutil
import subprocess
from pathlib import Path

MEDICAL_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".txt", ".xlsx"}


def make_tmp_dir() -> str:
    timestamp = int(time.time() * 1000)
    tmp_dir = os.path.join(tempfile.gettempdir(), f"openclaw_unpack_{timestamp}")
    os.makedirs(tmp_dir, exist_ok=True)
    return tmp_dir


def list_files(directory: str) -> list:
    """Recursively list files with medical extensions."""
    results = []
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in MEDICAL_EXTENSIONS:
                full_path = os.path.join(root, fname)
                results.append({
                    "path": full_path,
                    "name": fname,
                    "ext": ext,
                })
    return results


def sanitize_paths(files: list, tmp_dir: str) -> tuple:
    """If any file path contains non-ASCII chars, flatten all files to tmp_dir
    root with sequential numeric names. Returns (files, sanitized, mapping_file)."""
    has_non_ascii = any(not f["path"].isascii() for f in files)
    if not has_non_ascii:
        return files, False, None

    sorted_files = sorted(files, key=lambda f: f["name"])
    mapping = []
    new_files = []
    dirs_to_remove = set()

    for idx, f in enumerate(sorted_files, start=1):
        orig_path = f["path"]
        orig_name = f["name"]
        ext = f["ext"]
        new_name = f"{idx:04d}{ext}"
        new_path = os.path.join(tmp_dir, new_name)

        shutil.copy2(orig_path, new_path)
        mapping.append({"idx": idx, "orig_name": orig_name, "new_name": new_name})
        new_files.append({"path": new_path, "name": new_name, "ext": ext})

        # Track parent dirs that are not tmp_dir itself (the Chinese subdirs)
        parent = os.path.dirname(orig_path)
        if os.path.normpath(parent) != os.path.normpath(tmp_dir):
            # Walk up to find the top-level subdir under tmp_dir
            rel = os.path.relpath(parent, tmp_dir)
            top_level = rel.split(os.sep)[0]
            dirs_to_remove.add(os.path.join(tmp_dir, top_level))

    # Write mapping file
    mapping_file = os.path.join(tmp_dir, "_mapping.json")
    with open(mapping_file, "w", encoding="utf-8") as mf:
        json.dump(mapping, mf, ensure_ascii=False, indent=2)

    # Remove original Chinese-named subdirectories
    for d in dirs_to_remove:
        if os.path.isdir(d):
            shutil.rmtree(d)

    return new_files, True, mapping_file


def unpack_zip(archive_path: str, output_dir: str) -> None:
    with zipfile.ZipFile(archive_path, "r") as zf:
        zf.extractall(output_dir)


def unpack_rar(archive_path: str, output_dir: str) -> None:
    # Try unrar command first
    try:
        result = subprocess.run(
            ["unrar", "x", "-o+", archive_path, output_dir + "/"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return
    except FileNotFoundError:
        pass

    # Try unar command
    try:
        result = subprocess.run(
            ["unar", "-o", output_dir, archive_path],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return
    except FileNotFoundError:
        pass

    # Fallback to rarfile library
    try:
        import rarfile
        with rarfile.RarFile(archive_path) as rf:
            rf.extractall(output_dir)
        return
    except ImportError:
        pass

    raise RuntimeError(
        "Cannot extract RAR file: none of unrar, unar, or rarfile library is available"
    )


def unpack_7z(archive_path: str, output_dir: str) -> None:
    result = subprocess.run(
        ["7z", "x", f"-o{output_dir}", archive_path, "-y"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"7z extraction failed: {result.stderr}")


def unpack_tar(archive_path: str, output_dir: str) -> None:
    """Extract any tar variant (.tar/.tar.gz/.tgz/.tar.bz2/.tar.xz) safely.

    Uses tarfile with transparent compression auto-detection ("r:*").
    On Python >= 3.12 the "data" extraction filter rejects unsafe members
    (path traversal, absolute paths, special files); on older Pythons we
    guard manually by rejecting members whose resolved path escapes
    output_dir.
    """
    output_root = os.path.realpath(output_dir)
    with tarfile.open(archive_path, "r:*") as tf:
        if hasattr(tarfile, "data_filter"):
            # Python >= 3.12: built-in safe filter.
            tf.extractall(output_dir, filter="data")
        else:
            # Older Python: manually reject members that escape output_dir.
            for member in tf.getmembers():
                target = os.path.realpath(os.path.join(output_dir, member.name))
                if target != output_root and not target.startswith(output_root + os.sep):
                    raise RuntimeError(
                        f"Unsafe tar member (path traversal): {member.name}"
                    )
            tf.extractall(output_dir)


def detect_format(archive_path: str) -> str:
    """Detect archive format from the full lowercased filename.

    Uses the full name (not just the last suffix) so multi-part extensions
    like .tar.gz are recognized instead of collapsing to .gz.
    """
    name = os.path.basename(archive_path).lower()
    if name.endswith(".zip"):
        return "zip"
    if name.endswith(".rar"):
        return "rar"
    if name.endswith(".7z"):
        return "7z"
    if (
        name.endswith(".tar")
        or name.endswith(".tar.gz")
        or name.endswith(".tgz")
        or name.endswith(".tar.bz2")
        or name.endswith(".tbz2")
        or name.endswith(".tar.xz")
        or name.endswith(".txz")
    ):
        return "tar"
    return ""


def main() -> None:
    if len(sys.argv) < 2:
        print(
            json.dumps({"success": False, "error": "Usage: python3 unpack_archive.py [archive_path] [optional_output_dir]"}),
            flush=True,
        )
        sys.exit(1)

    archive_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.isfile(archive_path):
        print(
            json.dumps({"success": False, "error": f"File not found: {archive_path}"}),
            flush=True,
        )
        sys.exit(1)

    fmt = detect_format(archive_path)
    tmp_dir = output_dir or make_tmp_dir()

    try:
        if fmt == "zip":
            unpack_zip(archive_path, tmp_dir)
        elif fmt == "rar":
            unpack_rar(archive_path, tmp_dir)
        elif fmt == "7z":
            unpack_7z(archive_path, tmp_dir)
        elif fmt == "tar":
            unpack_tar(archive_path, tmp_dir)
        else:
            print(
                json.dumps({"success": False, "error": f"Unsupported archive format: {os.path.basename(archive_path)}"}),
                flush=True,
            )
            sys.exit(1)

        files = list_files(tmp_dir)
        files, sanitized, mapping_file = sanitize_paths(files, tmp_dir)
        result = {
            "success": True,
            "tmp_dir": tmp_dir,
            "files": files,
            "total": len(files),
            "sanitized": sanitized,
        }
        if sanitized:
            result["mapping_file"] = mapping_file
        print(json.dumps(result, ensure_ascii=False), flush=True)

    except Exception as e:
        print(
            json.dumps({"success": False, "error": str(e)}),
            flush=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
