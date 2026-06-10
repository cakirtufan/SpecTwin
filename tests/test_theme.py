from pathlib import Path

import dearpygui.dearpygui as dpg

from Source.UI import theme


SOURCE_DIR = Path(__file__).resolve().parents[1] / "Source"


def test_design_tokens_match_design_system():
    assert theme.RGB["background"] == (16, 20, 23)
    assert theme.RGB["surface_1"] == (23, 29, 33)
    assert theme.RGB["primary"] == (31, 182, 213)
    assert theme.RGB["secondary"] == (242, 169, 59)
    assert theme.RGB["success"] == (57, 185, 128)
    assert theme.RGB["error"] == (225, 93, 93)
    assert theme.SPACING["sm"] == 8
    assert theme.SPACING["md"] == 16


def test_theme_setup_is_idempotent_in_one_dpg_context():
    dpg.create_context()
    try:
        first_fonts = theme.apply_global_theme(SOURCE_DIR)
        second_fonts = theme.apply_global_theme(SOURCE_DIR)

        assert first_fonts == second_fonts
        assert dpg.does_item_exist(theme.FONT_TAGS["default"])
        assert dpg.does_item_exist(theme.FONT_TAGS["data"])
        assert dpg.does_item_exist(theme.THEME_TAGS["app"])
        assert dpg.does_item_exist(theme.THEME_TAGS["plot"])
        assert dpg.does_item_exist(theme.THEME_TAGS["primary_button"])
        assert dpg.does_item_exist(theme.THEME_TAGS["included_button"])
        assert dpg.does_item_exist(theme.THEME_TAGS["excluded_button"])
    finally:
        dpg.destroy_context()


def test_theme_button_binding_helpers_create_expected_items():
    dpg.create_context()
    try:
        theme.apply_global_theme(SOURCE_DIR)
        with dpg.window(tag="theme_test_window"):
            button = dpg.add_button(label="Run Simulation")
            plot = dpg.add_plot(label="Preview")

        theme.bind_button_theme(button, "primary")
        theme.bind_plot_theme(plot)

        assert dpg.get_item_theme(button) == dpg.get_alias_id(theme.THEME_TAGS["primary_button"])
        assert dpg.get_item_theme(plot) == dpg.get_alias_id(theme.THEME_TAGS["plot"])
    finally:
        dpg.destroy_context()
