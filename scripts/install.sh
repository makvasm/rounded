#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
	printf '%s\n' 'install.sh requires Python 3.' >&2
	exit 1
fi

exec python3 - "$SCRIPT_DIR/.." "$@" <<'PY'
import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import uuid
from pathlib import Path, PurePosixPath


CONTROL = ".rounded-theme-installer"
STATE_NAME = "ownership.json"

# Only these package trees and files are part of the default install.
BASE_MANIFEST = (
    "plasma/look-and-feel/com.github.varlesh.rounded",
    "plasma/look-and-feel/com.github.varlesh.rounded-dark",
    "plasma/desktoptheme/ROUNDED-COLOR",
    "plasma/desktoptheme/ROUNDED-DARK",
    "aurorae/themes/ROUNDED",
    "aurorae/themes/ROUNDED-DARK",
    "color-schemes/ROUNDED.colors",
    "color-schemes/ROUNDEDDARK.colors",
)
OPTIONAL_MANIFEST = {
    "konsole": ("konsole/ROUNDED.colorscheme",),
    "yakuake": ("yakuake/skins/ROUNDED", "yakuake/skins/ROUNDED-DARK"),
}
LEGACY_METADATA = {
    "plasma/look-and-feel/com.github.varlesh.rounded/metadata.desktop": "com.github.varlesh.rounded",
    "plasma/look-and-feel/com.github.varlesh.rounded-dark/metadata.desktop": "com.github.varlesh.rounded-dark",
    "plasma/desktoptheme/ROUNDED-COLOR/metadata.desktop": "ROUNDED-COLOR",
    "plasma/desktoptheme/ROUNDED-DARK/metadata.desktop": "ROUNDED-DARK",
}


class InstallError(Exception):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative_path(value):
    if not isinstance(value, str):
        raise InstallError("unsafe relative path: " + repr(value))
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise InstallError("unsafe relative path: " + value)
    return path


def ensure_no_symlink(path, allow_missing=True):
    path = Path(path)
    chain = list(reversed((path, *path.parents)))
    for part in chain:
        try:
            info = part.lstat()
        except FileNotFoundError:
            if allow_missing:
                continue
            raise InstallError("path does not exist: " + str(part))
        if stat.S_ISLNK(info.st_mode):
            raise InstallError("symlink path is not allowed: " + str(part))


def validate_source(root, relative):
    rel = relative_path(relative)
    source = root.joinpath(*rel.parts)
    ensure_no_symlink(source, allow_missing=False)
    if not source.exists():
        raise InstallError("manifest source does not exist: " + str(source))
    return source


def collect_files(root, entries):
    files = {}
    for entry in entries:
        source = validate_source(root, entry)
        if source.is_file():
            files[entry] = source
            continue
        if not source.is_dir():
            raise InstallError("manifest entry is not a regular file or directory: " + str(source))
        for current, dirs, names in os.walk(source, followlinks=False):
            current_path = Path(current)
            dirs.sort()
            names.sort()
            for name in list(dirs):
                child = current_path / name
                if child.is_symlink():
                    raise InstallError("source symlink is not allowed: " + str(child))
                if not child.is_dir():
                    raise InstallError("source is not a directory: " + str(child))
            for name in names:
                child = current_path / name
                if child.is_symlink() or not child.is_file():
                    raise InstallError("source must contain regular files only: " + str(child))
                rel = child.relative_to(root).as_posix()
                relative_path(rel)
                files[rel] = child
    return files


def load_state(state_path):
    ensure_no_symlink(state_path)
    if not state_path.exists():
        return {"version": 1, "owned": {}, "transactions": []}
    if not state_path.is_file():
        raise InstallError("installer state is not a regular file: " + str(state_path))
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InstallError("cannot read installer state: " + str(exc)) from exc
    if not isinstance(state, dict) or state.get("version") != 1 or not isinstance(state.get("owned"), dict) or not isinstance(state.get("transactions"), list):
        raise InstallError("unsupported or malformed installer state")
    validate_owned(state["owned"], "owned files")
    if any(not isinstance(txid, str) or not re.fullmatch(r"[0-9a-f]{32}", txid) for txid in state["transactions"]):
        raise InstallError("invalid transaction ID in installer state")
    if len(set(state["transactions"])) != len(state["transactions"]):
        raise InstallError("duplicate transaction ID in installer state")
    return state


def validate_owned(owned, description):
    if not isinstance(owned, dict):
        raise InstallError("malformed " + description)
    for rel, file_hash in owned.items():
        try:
            safe_path = managed_path(rel)
        except InstallError:
            safe_path = False
        if not safe_path:
            raise InstallError("unsafe path in " + description + ": " + repr(rel))
        if not isinstance(file_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", file_hash):
            raise InstallError("malformed hash in " + description + ": " + rel)


def managed_path(rel):
    relative_path(rel)
    entries = (*BASE_MANIFEST, *(item for paths in OPTIONAL_MANIFEST.values() for item in paths), *LEGACY_METADATA)
    return any(in_manifest_scope(rel, (entry,)) for entry in entries)


def acquire_lock(control_dir, dry_run):
    lock_path = control_dir / "lock"
    ensure_no_symlink(lock_path)
    if dry_run and not lock_path.exists():
        return None
    flags = os.O_RDONLY if dry_run else os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(str(lock_path), flags, 0o600)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise InstallError("installer lock is not a regular file: " + str(lock_path))
        stream = os.fdopen(fd, "rb" if dry_run else "r+b")
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        return stream
    except OSError as exc:
        raise InstallError("cannot acquire installer lock: " + str(exc)) from exc


def destination(data_home, rel):
    path = data_home.joinpath(*relative_path(rel).parts)
    ensure_no_symlink(path)
    return path


def read_regular(path):
    ensure_no_symlink(path, allow_missing=False)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise InstallError("target is not a regular file: " + str(path))
    return path.read_bytes()


def has_legacy_identity(data, expected):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    in_desktop_entry = False
    identities = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            in_desktop_entry = line == "[Desktop Entry]"
        elif in_desktop_entry and line and not line.startswith(("#", ";")) and "=" in line:
            key, value = line.split("=", 1)
            if key.strip() == "X-KDE-PluginInfo-Name":
                identities.append(value.strip())
    return identities == [expected]


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_no_symlink(path.parent)
    fd, temporary = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def ensure_parent(path, created_dirs):
    missing = []
    parent = path.parent
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    ensure_no_symlink(parent, allow_missing=False)
    for item in reversed(missing):
        item.mkdir()
        created_dirs.append(item)


def prune_empty(paths):
    for path in sorted(paths, key=lambda item: len(item.parts), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


def in_manifest_scope(rel, entries):
    return any(rel == entry or rel.startswith(entry.rstrip("/") + "/") for entry in entries)


def operation_plan(data_home, state, desired, update, uninstall, cleanup_scope=()):
    old_owned = state["owned"]
    actions = {}
    next_owned = {}

    if uninstall:
        for rel, old_hash in old_owned.items():
            target = destination(data_home, rel)
            if not target.exists():
                continue
            content = read_regular(target)
            if digest(content) == old_hash:
                actions[rel] = None
        return actions, {}, old_owned

    for rel, source in desired.items():
        source_data = source.read_bytes()
        source_hash = digest(source_data)
        target = destination(data_home, rel)
        owned_hash = old_owned.get(rel)
        if target.exists():
            target_data = read_regular(target)
            target_hash = digest(target_data)
            if target_hash == source_hash:
                if rel in old_owned:
                    next_owned[rel] = source_hash
                continue
            if owned_hash == target_hash:
                if not update:
                    raise InstallError("installed resource changed; use --update: " + rel)
            elif not update:
                raise InstallError("resource collision; use --update to replace it: " + rel)
            actions[rel] = source_data
        else:
            if owned_hash is not None and not update:
                raise InstallError("owned resource is missing; use --update to reinstall it: " + rel)
            actions[rel] = source_data
        next_owned[rel] = source_hash

    if update:
        for rel, expected_identity in LEGACY_METADATA.items():
            if rel in desired:
                continue
            target = destination(data_home, rel)
            if target.exists() and has_legacy_identity(read_regular(target), expected_identity):
                actions[rel] = None
        for rel, old_hash in old_owned.items():
            if rel in desired or not in_manifest_scope(rel, cleanup_scope):
                if rel not in desired:
                    next_owned[rel] = old_hash
                continue
            target = destination(data_home, rel)
            if target.exists() and digest(read_regular(target)) == old_hash:
                actions[rel] = None
    else:
        for rel, old_hash in old_owned.items():
            if rel not in desired:
                target = destination(data_home, rel)
                if target.exists() and digest(read_regular(target)) == old_hash:
                    next_owned[rel] = old_hash
    return actions, next_owned, old_owned


def make_transaction(data_home, control_dir, actions, old_owned, next_owned):
    txid = uuid.uuid4().hex
    backup_dir = control_dir / "backups" / txid
    backup_dir.mkdir(parents=True)
    snapshots = {}
    try:
        for index, (rel, after) in enumerate(sorted(actions.items())):
            target = destination(data_home, rel)
            existed = target.exists()
            before_hash = None
            mode = None
            if existed:
                before = read_regular(target)
                before_hash = digest(before)
                mode = stat.S_IMODE(target.stat().st_mode)
                backup_file = backup_dir / "files" / str(index)
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                backup_file.write_bytes(before)
            snapshots[rel] = {
                "backup": str(index) if existed else None,
                "before_hash": before_hash,
                "mode": mode,
                "after_hash": digest(after) if after is not None else None,
            }
        transaction = {
            "id": txid,
            "snapshots": snapshots,
            "old_owned": old_owned,
            "next_owned": next_owned,
        }
        tx_file = backup_dir / "transaction.json"
        tx_file.write_text(json.dumps(transaction, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return txid, backup_dir, transaction
    except Exception:
        shutil.rmtree(backup_dir, ignore_errors=True)
        raise


def apply_actions(data_home, control_dir, state_path, state, actions, next_owned):
    if not actions and state["owned"] == next_owned:
        print("No changes needed.")
        return

    state_before = state_path.read_bytes() if state_path.exists() else None
    txid, backup_dir, transaction = make_transaction(data_home, control_dir, actions, state["owned"], next_owned)
    stage_dir = None
    created_dirs = []
    touched = []
    try:
        stage_dir = Path(tempfile.mkdtemp(prefix=".rounded-stage-", dir=data_home))
        staged = {}
        for index, (rel, content) in enumerate(sorted(actions.items())):
            if content is None:
                continue
            staged_file = stage_dir / str(index)
            staged_file.write_bytes(content)
            os.chmod(staged_file, 0o644)
            staged[rel] = staged_file

        fail_after = int(os.environ.get("ROUNDED_INSTALLER_TEST_FAIL_AFTER", "0"))
        replaced = 0
        for rel, content in sorted(actions.items()):
            target = destination(data_home, rel)
            if content is None:
                if target.exists():
                    target.unlink()
                    touched.append(rel)
            else:
                ensure_parent(target, created_dirs)
                os.replace(staged[rel], target)
                touched.append(rel)
                replaced += 1
                if fail_after and replaced >= fail_after:
                    raise OSError("injected test failure after file replacement")

        state["owned"] = next_owned
        state["transactions"].append(txid)
        atomic_json(state_path, state)
        print("Applied %d file change(s)." % len(actions))
    except Exception:
        for rel in reversed(touched):
            target = destination(data_home, rel)
            snapshot = transaction["snapshots"][rel]
            if snapshot["backup"] is None:
                try:
                    target.unlink()
                except FileNotFoundError:
                    pass
            else:
                backup_file = backup_dir / "files" / snapshot["backup"]
                ensure_parent(target, created_dirs)
                shutil.copyfile(backup_file, target)
                os.chmod(target, snapshot["mode"])
        if state_before is None:
            try:
                state_path.unlink()
            except FileNotFoundError:
                pass
        else:
            state_path.write_bytes(state_before)
        shutil.rmtree(backup_dir, ignore_errors=True)
        prune_empty(created_dirs)
        raise
    finally:
        if stage_dir is not None:
            shutil.rmtree(stage_dir, ignore_errors=True)


def restore_latest(data_home, control_dir, state_path, state):
    if not state["transactions"]:
        raise InstallError("there is no saved operation to restore")
    txid = state["transactions"][-1]
    backup_dir = control_dir / "backups" / txid
    ensure_no_symlink(backup_dir, allow_missing=False)
    ensure_no_symlink(backup_dir / "files", allow_missing=True)
    tx_path = backup_dir / "transaction.json"
    ensure_no_symlink(tx_path, allow_missing=False)
    try:
        transaction = json.loads(tx_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InstallError("cannot read backup transaction: " + str(exc)) from exc
    if not isinstance(transaction, dict) or transaction.get("id") != txid or not isinstance(transaction.get("snapshots"), dict):
        raise InstallError("malformed backup transaction")
    validate_owned(transaction.get("old_owned"), "transaction old ownership")
    validate_owned(transaction.get("next_owned"), "transaction next ownership")
    if state["owned"] != transaction["next_owned"]:
        raise InstallError("backup transaction does not match current installer ownership")
    changes = []
    mismatches = []
    used_backups = set()
    for rel, snapshot in transaction["snapshots"].items():
        try:
            safe_path = managed_path(rel)
        except InstallError:
            safe_path = False
        if not safe_path:
            raise InstallError("unsafe path in backup transaction: " + repr(rel))
        if not isinstance(snapshot, dict):
            raise InstallError("malformed backup entry for " + rel)
        backup = snapshot.get("backup")
        before_hash = snapshot.get("before_hash")
        after_hash = snapshot.get("after_hash")
        mode = snapshot.get("mode")
        if after_hash != transaction["next_owned"].get(rel):
            raise InstallError("malformed after hash for " + rel)
        if backup is None:
            if before_hash is not None or mode is not None:
                raise InstallError("malformed before state for " + rel)
        else:
            if not isinstance(backup, str) or not re.fullmatch(r"[0-9]+", backup) or backup in used_backups:
                raise InstallError("malformed backup entry for " + rel)
            used_backups.add(backup)
            if not isinstance(before_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", before_hash):
                raise InstallError("malformed before hash for " + rel)
            if isinstance(mode, bool) or not isinstance(mode, int) or mode < 0 or mode > 0o7777:
                raise InstallError("malformed file mode for " + rel)
            backup_file = backup_dir / "files" / backup
            ensure_no_symlink(backup_file, allow_missing=False)
            try:
                if not stat.S_ISREG(backup_file.lstat().st_mode) or digest(backup_file.read_bytes()) != before_hash:
                    raise InstallError("backup content hash mismatch for " + rel)
            except OSError as exc:
                raise InstallError("cannot read backup for " + rel + ": " + str(exc)) from exc
        target = destination(data_home, rel)
        exists = target.exists()
        current_hash = digest(read_regular(target)) if exists else None
        if current_hash != after_hash:
            mismatches.append(rel)
        changes.append((rel, snapshot))
    if mismatches:
        raise InstallError("restore refused because installed files were modified or removed: " + ", ".join(sorted(mismatches)) + ". Backups were kept.")
    return txid, backup_dir, transaction, changes


def do_restore(data_home, control_dir, state_path, state, dry_run):
    txid, backup_dir, transaction, changes = restore_latest(data_home, control_dir, state_path, state)
    if dry_run:
        print("Would restore %d file(s) from transaction %s." % (len(changes), txid))
        return
    state_before = state_path.read_bytes() if state_path.exists() else None
    created_dirs = []
    touched = []
    current_files = {}
    for rel, _ in changes:
        target = destination(data_home, rel)
        if target.exists():
            current_files[rel] = (read_regular(target), stat.S_IMODE(target.stat().st_mode))
        else:
            current_files[rel] = None
    stage_dir = Path(tempfile.mkdtemp(prefix=".rounded-restore-", dir=data_home))
    staged = {}
    try:
        for index, (rel, snapshot) in enumerate(changes):
            if snapshot["backup"] is None:
                continue
            backup_file = backup_dir / "files" / snapshot["backup"]
            ensure_no_symlink(backup_file, allow_missing=False)
            staged_file = stage_dir / str(index)
            shutil.copyfile(backup_file, staged_file)
            os.chmod(staged_file, snapshot["mode"])
            staged[rel] = staged_file
        for rel, snapshot in changes:
            target = destination(data_home, rel)
            if snapshot["backup"] is None:
                if target.exists():
                    target.unlink()
            else:
                ensure_parent(target, created_dirs)
                os.replace(staged[rel], target)
            touched.append(rel)
        state["owned"] = transaction["old_owned"]
        state["transactions"].pop()
        atomic_json(state_path, state)
    except Exception:
        for rel in reversed(touched):
            target = destination(data_home, rel)
            current = current_files[rel]
            if current is None:
                try:
                    target.unlink()
                except FileNotFoundError:
                    pass
            else:
                ensure_parent(target, created_dirs)
                target.write_bytes(current[0])
                os.chmod(target, current[1])
        if state_before is not None:
            state_path.write_bytes(state_before)
        prune_empty(created_dirs)
        raise
    finally:
        shutil.rmtree(stage_dir, ignore_errors=True)
    shutil.rmtree(backup_dir)
    print("Restored %d file(s) from transaction %s." % (len(changes), txid))


def main():
    parser = argparse.ArgumentParser(description="Safely install the ROUNDED KDE theme for the current user.")
    parser.add_argument("root", help=argparse.SUPPRESS)
    parser.add_argument("command", choices=("install", "uninstall", "restore"))
    parser.add_argument("--dry-run", action="store_true", help="show planned actions without writing files")
    parser.add_argument("--update", action="store_true", help="replace collisions and remove obsolete owned files")
    parser.add_argument("--with-konsole", action="store_true", help="also install the Konsole color scheme")
    parser.add_argument("--with-yakuake", action="store_true", help="also install the Yakuake skins")
    args = parser.parse_args()
    root = Path(args.root).resolve(strict=True)
    home = Path(os.path.abspath(os.path.expanduser(os.environ.get("HOME", str(Path.home())))))
    xdg_value = os.environ.get("XDG_DATA_HOME")
    xdg = Path(os.path.expanduser(xdg_value)) if xdg_value else home / ".local" / "share"
    if not xdg.is_absolute():
        raise InstallError("XDG_DATA_HOME must be an absolute non-root path")
    xdg = Path(os.path.abspath(xdg))
    if xdg == Path("/"):
        raise InstallError("XDG_DATA_HOME must be an absolute non-root path")
    ensure_no_symlink(xdg)
    data_home = xdg
    control_dir = data_home / CONTROL
    backups_dir = control_dir / "backups"
    state_path = control_dir / STATE_NAME
    ensure_no_symlink(control_dir)
    ensure_no_symlink(backups_dir)
    ensure_no_symlink(state_path)

    if args.command != "install" and (args.with_konsole or args.with_yakuake):
        raise InstallError("--with-konsole and --with-yakuake are only valid with install")
    if args.command != "install" and args.update:
        raise InstallError("--update is only valid with install")

    if not args.dry_run:
        if not data_home.exists():
            data_home.mkdir(parents=True)
        ensure_no_symlink(data_home, allow_missing=False)
        if not os.access(data_home, os.W_OK | os.X_OK):
            raise InstallError("XDG data directory is not writable: " + str(data_home))
        control_dir.mkdir(parents=True, exist_ok=True)
        ensure_no_symlink(control_dir, allow_missing=False)
    lock_file = acquire_lock(control_dir, args.dry_run)
    state = load_state(state_path)

    if args.command == "restore":
        do_restore(data_home, control_dir, state_path, state, args.dry_run)
        return

    if args.command == "install":
        entries = list(BASE_MANIFEST)
        if args.with_konsole:
            entries.extend(OPTIONAL_MANIFEST["konsole"])
        if args.with_yakuake:
            entries.extend(OPTIONAL_MANIFEST["yakuake"])
        cleanup_scope = list(entries)
        desired = collect_files(root, entries)
        actions, next_owned, _ = operation_plan(data_home, state, desired, args.update, False, cleanup_scope)
    else:
        if not state["owned"]:
            print("No installed files are recorded.")
            return
        actions, next_owned, _ = operation_plan(data_home, state, {}, True, True)

    if args.dry_run:
        verb = "remove" if args.command == "uninstall" else "install/update"
        print("Would %s %d file(s); no files were changed:" % (verb, len(actions)))
        for rel, content in sorted(actions.items()):
            print("  %s %s" % ("remove" if content is None else "write", rel))
        return

    apply_actions(
        data_home,
        control_dir,
        state_path,
        state,
        actions,
        next_owned,
    )


if __name__ == "__main__":
    try:
        main()
    except (InstallError, OSError, ValueError, KeyError) as exc:
        print("install.sh: %s" % exc, file=sys.stderr)
        sys.exit(1)
PY
