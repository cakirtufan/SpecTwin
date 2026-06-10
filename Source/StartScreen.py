# -*- coding: utf-8 -*-
"""
Created on Mon Apr 14 10:08:23 2025

@author: cakir
"""

import subprocess
import sys
from pathlib import Path

import dearpygui.dearpygui as dpg
import numpy as np
from PIL import Image

source_dir = Path(__file__).resolve().parent
if str(source_dir) not in sys.path:
    sys.path.append(str(source_dir))

from UI import theme as ui_theme


def load_texture(path):
    """Load image as RGBA texture for DearPyGui."""
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    data = (np.array(image) / 255.0).flatten().tolist()
    with dpg.texture_registry():
        return dpg.add_static_texture(width, height, data)


def resolve_assets():
    base_path_image = source_dir / "img"
    base_path_font = source_dir / "fonts"
    assets = {
        "bam": base_path_image / "bam_logo.png",
        "ifw": base_path_image / "ifw_logo.png",
        "spectwin_logo": base_path_image / "spectwin_logo.png",
        "icon": base_path_image / "spectwin_icon.ico",
        "font": base_path_font / "verdana.ttf",
    }

    for path in assets.values():
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

    return assets


def launch_specwin():
    subprocess.Popen([sys.executable, str(source_dir / "SpectwinMain.py")], cwd=source_dir)
    dpg.destroy_context()


def build_start_screen():
    print("Source directory:", source_dir)
    assets = resolve_assets()

    bam_tex = load_texture(assets["bam"])
    ifw_tex = load_texture(assets["ifw"])
    spectwin_tex = load_texture(assets["spectwin_logo"])
    ui_theme.apply_global_theme(source_dir)

    with dpg.theme(tag="start_screen_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (244, 247, 248, 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (24, 33, 38, 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, (92, 107, 115, 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Button, ui_theme.rgba("primary"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (57, 204, 232, 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (24, 149, 176, 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 24, 14, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4, category=dpg.mvThemeCat_Core)

    with dpg.window(
        tag="MainWindow",
        label="",
        width=750,
        height=400,
        no_title_bar=True,
        no_resize=True,
        no_scrollbar=True,
    ):
        dpg.bind_item_theme("MainWindow", "start_screen_theme")
        dpg.add_spacer(height=6)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=250)
            dpg.add_image(spectwin_tex, width=200, height=80)

        dpg.add_spacer(height=8)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=112)
            dpg.add_text(
                "XES simulation, data analysis, and digital twin workflows",
                color=(54, 68, 76, 255),
                wrap=520,
            )

        dpg.add_spacer(height=18)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=118)
            dpg.add_image(bam_tex, width=150, height=60)
            dpg.add_spacer(width=120)
            dpg.add_image(ifw_tex, width=150, height=60)

        dpg.add_spacer(height=20)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=244)
            launch_button = dpg.add_button(label="Launch SpecTwin", width=220, height=40, callback=launch_specwin)
            ui_theme.bind_button_theme(launch_button, "primary")

    return assets


def main():
    dpg.create_context()
    try:
        assets = build_start_screen()
        dpg.create_viewport(
            title="SpecTwin",
            width=750,
            height=400,
            small_icon=str(assets["icon"]),
            large_icon=str(assets["icon"]),
        )
        dpg.setup_dearpygui()
        dpg.set_primary_window("MainWindow", True)
        dpg.show_viewport()
        dpg.start_dearpygui()
    finally:
        dpg.destroy_context()


if __name__ == "__main__":
    main()
