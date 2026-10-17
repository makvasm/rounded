#!/usr/bin/env python3
import os
import json
import fcntl
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
INSTALLER = ROOT / "scripts" / "install.sh"


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rounded installer ")
        self.base = Path(self.temp.name)
        self.data = self.base / "xdg data with spaces"
        self.home = self.base / "home with spaces"
        self.home.mkdir()
        self.env = os.environ.copy()
        self.env.update({"HOME": str(self.home), "XDG_DATA_HOME": str(self.data)})
        self.env.pop("ROUNDED_INSTALLER_TEST_FAIL_AFTER", None)

    def tearDown(self):
        self.temp.cleanup()

    def run_installer(self, *args, check=True, env=None):
        result = subprocess.run(
            ["sh", str(INSTALLER), *args],
            env=env or self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and result.returncode:
            self.fail("installer failed: %s\n%s" % (result.stdout, result.stderr))
        return result

    def test_install_repeat_update_and_uninstall_preserves_changes(self):
        self.run_installer("install")
        installed = self.data / "color-schemes" / "ROUNDED.colors"
        original = installed.read_bytes()
        self.run_installer("install")
        self.assertEqual(original, installed.read_bytes())

        installed.write_bytes(b"user edit")
        result = self.run_installer("uninstall")
        self.assertTrue(installed.exists())
        self.assertEqual(b"user edit", installed.read_bytes())
        self.assertIn("Applied", result.stdout)

    def test_collision_requires_update_and_restore_is_explicit(self):
        target = self.data / "color-schemes" / "ROUNDED.colors"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"pre-existing resource")
        result = self.run_installer("install", check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(b"pre-existing resource", target.read_bytes())

        self.run_installer("install", "--update")
        self.assertNotEqual(b"pre-existing resource", target.read_bytes())
        self.run_installer("uninstall")
        self.assertFalse(target.exists())
        self.run_installer("restore")
        self.assertNotEqual(b"pre-existing resource", target.read_bytes())
        self.run_installer("restore")
        self.assertEqual(b"pre-existing resource", target.read_bytes())

    def test_update_removes_only_stale_unchanged_owned_files(self):
        self.run_installer("install", "--with-konsole")
        optional = self.data / "konsole" / "ROUNDED.colorscheme"
        self.assertTrue(optional.is_file())
        optional.write_bytes(b"modified")
        self.run_installer("install", "--update")
        self.assertEqual(b"modified", optional.read_bytes())

    def test_update_without_optional_flags_preserves_installed_optional_components(self):
        self.run_installer("install", "--with-konsole", "--with-yakuake")
        konsole = self.data / "konsole" / "ROUNDED.colorscheme"
        yakuake = self.data / "yakuake" / "skins" / "ROUNDED" / "title.skin"
        konsole_original = konsole.read_bytes()
        yakuake_original = yakuake.read_bytes()

        self.run_installer("install", "--update")

        self.assertEqual(konsole_original, konsole.read_bytes())
        self.assertEqual(yakuake_original, yakuake.read_bytes())
        self.run_installer("uninstall")
        self.assertFalse(konsole.exists())
        self.assertFalse(yakuake.exists())

    def test_restore_refuses_modified_files_and_keeps_backups(self):
        self.run_installer("install")
        target = self.data / "color-schemes" / "ROUNDED.colors"
        target.write_bytes(b"local modification")

        result = self.run_installer("restore", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Backups were kept", result.stderr)
        backup_dirs = list((self.data / ".rounded-theme-installer" / "backups").iterdir())
        self.assertEqual(1, len(backup_dirs))
        self.assertTrue((backup_dirs[0] / "transaction.json").is_file())
        self.assertEqual(b"local modification", target.read_bytes())

    def test_restore_validates_backup_content_hash(self):
        target = self.data / "color-schemes" / "ROUNDED.colors"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"original resource")
        self.run_installer("install", "--update")
        control = self.data / ".rounded-theme-installer"
        state = json.loads((control / "ownership.json").read_text(encoding="utf-8"))
        txid = state["transactions"][-1]
        transaction_path = control / "backups" / txid / "transaction.json"
        transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
        snapshot = transaction["snapshots"]["color-schemes/ROUNDED.colors"]
        backup = control / "backups" / txid / "files" / snapshot["backup"]
        backup.write_bytes(b"tampered backup")

        result = self.run_installer("restore", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("backup content hash mismatch", result.stderr)
        self.assertTrue(backup.is_file())
        self.assertTrue(transaction_path.is_file())

    def test_restore_rejects_malformed_transaction_fields(self):
        target = self.data / "color-schemes" / "ROUNDED.colors"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"original resource")
        self.run_installer("install", "--update")
        control = self.data / ".rounded-theme-installer"
        state = json.loads((control / "ownership.json").read_text(encoding="utf-8"))
        txid = state["transactions"][-1]
        transaction_path = control / "backups" / txid / "transaction.json"
        original = json.loads(transaction_path.read_text(encoding="utf-8"))

        malformed_transactions = []
        bad_id = json.loads(json.dumps(original))
        bad_id["id"] = "0" * 32
        malformed_transactions.append(bad_id)
        bad_map = json.loads(json.dumps(original))
        bad_map["old_owned"] = []
        malformed_transactions.append(bad_map)
        bad_mode = json.loads(json.dumps(original))
        bad_mode["snapshots"]["color-schemes/ROUNDED.colors"]["mode"] = "0644"
        malformed_transactions.append(bad_mode)
        bad_path = json.loads(json.dumps(original))
        snapshot = bad_path["snapshots"].pop("color-schemes/ROUNDED.colors")
        bad_path["snapshots"]["../outside"] = snapshot
        malformed_transactions.append(bad_path)

        for malformed in malformed_transactions:
            with self.subTest(transaction=malformed):
                transaction_path.write_text(json.dumps(malformed), encoding="utf-8")
                result = self.run_installer("restore", check=False)
                self.assertNotEqual(0, result.returncode)
                self.assertTrue(transaction_path.is_file())
        transaction_path.write_text(json.dumps(original), encoding="utf-8")

    def test_mutating_invocation_waits_for_flock(self):
        self.data.mkdir()
        control = self.data / ".rounded-theme-installer"
        control.mkdir()
        lock_path = control / "lock"
        with lock_path.open("w") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            process = subprocess.Popen(
                ["sh", str(INSTALLER), "install"],
                env=self.env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                with self.assertRaises(subprocess.TimeoutExpired):
                    process.communicate(timeout=0.2)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            stdout, stderr = process.communicate(timeout=30)
        self.assertEqual(0, process.returncode, stdout + stderr)
        self.assertTrue((self.data / "color-schemes" / "ROUNDED.colors").is_file())

    def test_unowned_files_are_never_removed(self):
        target = self.data / "plasma" / "desktoptheme" / "ROUNDED-COLOR" / "local-note.txt"
        target.parent.mkdir(parents=True)
        target.write_text("outside the manifest", encoding="utf-8")
        self.run_installer("install", "--update")
        self.run_installer("uninstall")
        self.assertEqual("outside the manifest", target.read_text(encoding="utf-8"))

    def test_identical_preexisting_files_remain_unowned(self):
        relative = "color-schemes/ROUNDED.colors"
        target = self.data / relative
        target.parent.mkdir(parents=True)
        target.write_bytes((ROOT / relative).read_bytes())
        self.run_installer("install")
        self.run_installer("uninstall")
        self.assertEqual((ROOT / relative).read_bytes(), target.read_bytes())

    def test_update_cleans_only_matching_legacy_metadata_and_restore_recovers_it(self):
        package_ids = {
            "plasma/look-and-feel/com.github.varlesh.rounded": "com.github.varlesh.rounded",
            "plasma/look-and-feel/com.github.varlesh.rounded-dark": "com.github.varlesh.rounded-dark",
            "plasma/desktoptheme/ROUNDED-COLOR": "ROUNDED-COLOR",
            "plasma/desktoptheme/ROUNDED-DARK": "ROUNDED-DARK",
        }
        legacy = {}
        for package, identity in package_ids.items():
            target = self.data / package / "metadata.desktop"
            target.parent.mkdir(parents=True)
            content = ("[Desktop Entry]\nName=legacy\nX-KDE-PluginInfo-Name=%s\n" % identity).encode()
            target.write_bytes(content)
            legacy[target] = content

        unrelated = self.data / "plasma" / "look-and-feel" / "com.github.varlesh.rounded" / "local-metadata.desktop"
        unrelated.write_text("local file", encoding="utf-8")

        self.run_installer("install", "--update")
        for target in legacy:
            self.assertFalse(target.exists())
        self.assertEqual("local file", unrelated.read_text(encoding="utf-8"))

        self.run_installer("restore")
        for target, content in legacy.items():
            self.assertEqual(content, target.read_bytes())
        self.assertEqual("local file", unrelated.read_text(encoding="utf-8"))

    def test_update_preserves_legacy_metadata_with_wrong_package_identity(self):
        target = self.data / "plasma" / "look-and-feel" / "com.github.varlesh.rounded" / "metadata.desktop"
        target.parent.mkdir(parents=True)
        content = b"[Desktop Entry]\nX-KDE-PluginInfo-Name=other.package\n"
        target.write_bytes(content)

        self.run_installer("install", "--update")
        self.assertEqual(content, target.read_bytes())

    def test_xdg_data_home_must_be_absolute_and_empty_uses_default(self):
        env = self.env.copy()
        env["XDG_DATA_HOME"] = "relative/data"
        result = self.run_installer("install", check=False, env=env)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("XDG_DATA_HOME must be an absolute", result.stderr)

        env["XDG_DATA_HOME"] = ""
        self.run_installer("install", env=env)
        self.assertTrue((self.home / ".local" / "share" / "color-schemes" / "ROUNDED.colors").is_file())

    def test_dry_run_has_no_side_effects(self):
        self.run_installer("install", "--dry-run")
        self.assertFalse(self.data.exists())

    def test_dry_run_does_not_create_lock(self):
        self.data.mkdir()
        self.run_installer("install", "--dry-run")
        self.assertFalse((self.data / ".rounded-theme-installer").exists())

    def test_failure_after_replacement_rolls_back_all_files(self):
        env = self.env.copy()
        env["ROUNDED_INSTALLER_TEST_FAIL_AFTER"] = "2"
        result = self.run_installer("install", check=False, env=env)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse((self.data / "color-schemes" / "ROUNDED.colors").exists())
        self.assertFalse((self.data / ".rounded-theme-installer" / "ownership.json").exists())
        state = self.data / ".rounded-theme-installer" / "ownership.json"
        if state.exists():
            metadata = json.loads(state.read_text(encoding="utf-8"))
            metadata["owned"]["color-schemes/ROUNDED.colors"] = "invalid"
            state.write_text(json.dumps(metadata), encoding="utf-8")
            result = self.run_installer("install", check=False)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("malformed hash", result.stderr)
            state.unlink()
        remaining = [path for path in self.data.rglob("*") if path.is_file() and path.name != "lock"]
        self.assertEqual([], remaining)

    def test_rejects_destination_symlinks(self):
        self.data.mkdir(parents=True)
        external = self.base / "outside"
        external.mkdir()
        (self.data / "color-schemes").symlink_to(external, target_is_directory=True)
        result = self.run_installer("install", check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual([], list(external.iterdir()))

    def test_optional_payloads_are_opt_in(self):
        self.run_installer("install")
        self.assertFalse((self.data / "konsole" / "ROUNDED.colorscheme").exists())
        self.assertFalse((self.data / "yakuake" / "skins" / "ROUNDED").exists())
        self.run_installer("uninstall")
        self.run_installer("install", "--with-konsole", "--with-yakuake")
        self.assertTrue((self.data / "konsole" / "ROUNDED.colorscheme").is_file())
        self.assertTrue((self.data / "yakuake" / "skins" / "ROUNDED" / "title.skin").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
