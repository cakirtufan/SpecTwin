import ast
import importlib.util
from pathlib import Path

import dearpygui.dearpygui as dpg


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "Source"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_python_sources_parse():
    files = list(SOURCE_DIR.rglob("*.py"))
    assert files

    for path in files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_start_screen_builds_without_showing_viewport():
    start_screen = load_module("StartScreen", SOURCE_DIR / "StartScreen.py")

    dpg.create_context()
    try:
        assets = start_screen.build_start_screen()

        assert dpg.does_item_exist("MainWindow")
        assert assets["font"].exists()
        assert assets["spectwin_logo"].exists()
    finally:
        dpg.destroy_context()


def test_main_window_module_switches_build_without_showing_viewport():
    spectwin_main = load_module("SpectwinMain", SOURCE_DIR / "SpectwinMain.py")

    dpg.create_context()
    try:
        spectwin_main.build_main_window()
        assert dpg.does_item_exist("SpecWinWindow")
        assert dpg.does_item_exist("content_area")

        labels = [
            "DigitalTwin",
            "AutoFDMNES",
            "Merge .h5/.evt Files",
            "VisualizeData",
            "ProcessData",
            "SubPixelResolution",
        ]

        for label in labels:
            spectwin_main.show_main_content(label)
            assert dpg.does_item_exist("content_area")
    finally:
        dpg.destroy_context()


def test_digital_twin_can_be_reopened_without_losing_content():
    spectwin_main = load_module("SpectwinMain_reopen", SOURCE_DIR / "SpectwinMain.py")

    dpg.create_context()
    try:
        spectwin_main.build_main_window()

        for _ in range(2):
            spectwin_main.show_main_content("DigitalTwin")
            children = dpg.get_item_children("content_area")
            child_count = sum(len(items) for items in children.values()) if children else 0

            assert child_count > 0
            assert dpg.does_item_exist("texture_reg")
            assert dpg.does_item_exist("digital_twin_tab_lines")
            assert dpg.does_item_exist("digital_twin_tab_simulation")
            assert dpg.does_item_exist("digital_twin_tab_optimization")
            assert dpg.does_item_exist("digital_twin_tab_results")
            assert dpg.does_item_exist("graph_window")
    finally:
        dpg.destroy_context()


def test_digital_twin_convergence_window_builds_large_layout():
    spectwin_main = load_module("SpectwinMain_convergence", SOURCE_DIR / "SpectwinMain.py")

    dpg.create_context()
    try:
        spectwin_main.build_main_window()

        digital_twin = spectwin_main.DigitalTwinUI("content_area")
        digital_twin._open_convergence_window()

        assert dpg.does_item_exist("conv_window")
        assert dpg.does_item_exist("conv_plot")
        assert dpg.does_item_exist("conv_series_current")
        assert dpg.does_item_exist("conv_series_best")
        assert dpg.get_item_width("conv_window") >= 1000
        assert dpg.get_item_height("conv_window") >= 700
    finally:
        dpg.destroy_context()


def test_core_modules_can_be_reopened_without_duplicate_tags():
    spectwin_main = load_module("SpectwinMain_reopen_modules", SOURCE_DIR / "SpectwinMain.py")

    dpg.create_context()
    try:
        spectwin_main.build_main_window()

        labels = [
            "AutoFDMNES",
            "VisualizeData",
            "ProcessData",
            "Merge .h5/.evt Files",
            "SubPixelResolution",
        ]

        for _ in range(2):
            for label in labels:
                spectwin_main.show_main_content(label)
                children = dpg.get_item_children("content_area")
                child_count = sum(len(items) for items in children.values()) if children else 0
                assert child_count > 0, label
    finally:
        dpg.destroy_context()


def test_autofdmnes_periodic_table_buttons_toggle_off():
    periodic_module = load_module("PeriodicTableDPG_toggle", SOURCE_DIR / "AutoFDMNES" / "PeriodicTableDPG.py")

    dpg.create_context()
    try:
        with dpg.window(tag="periodic_parent"):
            table = periodic_module.PeriodicTableDPG("periodic_parent")

        table.toggle_element("Fe")
        assert table.get_included_elements() == ["Fe"]
        assert dpg.get_item_theme(table.element_buttons["Fe"]) == table.theme_green

        table.toggle_element("Fe")
        assert table.get_included_elements() == []
        assert dpg.get_item_theme(table.element_buttons["Fe"]) is None
    finally:
        dpg.destroy_context()
