import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.gui
def test_start_screen_and_main_navigation_with_pywinauto():
    if os.name != "nt":
        pytest.skip("pywinauto GUI smoke test is Windows-only")

    if os.environ.get("RUN_GUI_SMOKE") != "1":
        pytest.skip("set RUN_GUI_SMOKE=1 to launch and drive the desktop GUI")

    try:
        from pywinauto import Desktop, mouse
    except ImportError:
        pytest.skip("pywinauto is not installed")

    proc = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "Source" / "SpectwinMain.py")],
        cwd=REPO_ROOT,
    )

    try:
        desktop = Desktop(backend="win32")
        main = desktop.window(title="SpecTwin - Control Panel")
        main.wait("visible", timeout=20)

        main_rect = main.rectangle()
        sidebar_x = main_rect.left + 85
        menu_y = {
            "digital_twin": main_rect.top + 90,
            "auto_fdmnes": main_rect.top + 120,
            "data_processes": main_rect.top + 150,
            "merge_data": main_rect.top + 180,
            "visualize_data": main_rect.top + 210,
            "align_data": main_rect.top + 240,
            "process_evt": main_rect.top + 270,
        }

        navigation_sequence = [
            "digital_twin",
            "auto_fdmnes",
            "data_processes",
            "merge_data",
            "visualize_data",
            "align_data",
            "process_evt",
            "digital_twin",
            "auto_fdmnes",
            "visualize_data",
            "merge_data",
            "process_evt",
            "align_data",
            "digital_twin",
        ]

        for index, key in enumerate(navigation_sequence, start=1):
            y = menu_y[key]
            mouse.click(coords=(sidebar_x, y))
            time.sleep(0.75)
            assert proc.poll() is None, f"application exited after navigation step {index}: {key}"

        assert proc.poll() is None
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
