"""Tests for the PyInstaller build script."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def load_build_executable_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "build_executable.py"
    spec = importlib.util.spec_from_file_location("build_executable", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestBuildExecutableScript:
    def test_add_data_entries_include_full_package_tree(self):
        module = load_build_executable_module()
        repo_root = Path("/tmp/holodeck-repo")

        assert module.get_add_data_entries(repo_root) == [
            (repo_root / "holodeck", "holodeck"),
        ]

    def test_build_command_packages_full_holodeck_tree(self):
        module = load_build_executable_module()
        repo_root = Path("/tmp/holodeck-repo")
        pyinstaller = Path("/tmp/venv/bin/pyinstaller")
        dist_dir = repo_root / "dist"
        build_dir = repo_root / "build" / "pyinstaller"

        command = module.build_pyinstaller_command(repo_root, pyinstaller, dist_dir, build_dir)

        add_data_flag = module.format_add_data(repo_root / "holodeck", "holodeck")
        assert command[:2] == [str(pyinstaller), "--noconfirm"]
        assert command[-1] == str(repo_root / "scripts" / "run_holodeck.py")
        assert ["--add-data", add_data_flag] == command[command.index("--add-data") : command.index("--add-data") + 2]
