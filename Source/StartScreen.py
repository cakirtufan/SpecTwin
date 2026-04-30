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

    with dpg.font_registry():
        verdana_font = dpg.add_font(str(assets["font"]), 18)

    with dpg.theme() as white_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (255, 255, 255), category=dpg.mvThemeCat_Core)

    with dpg.window(tag="MainWindow", label="", width=800, height=600, no_title_bar=True, no_resize=True):
        dpg.bind_font(verdana_font)
        dpg.add_spacer(height=20)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=230)
            dpg.add_image(spectwin_tex, width=200, height=80)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=130)
            dpg.add_text("A Platform for XES Simulation, Data Analysis and Digital Twin ", color=(60, 60, 60), wrap=500)

        dpg.add_spacer(height=25)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=100)
            dpg.add_image(bam_tex, width=200, height=80)
            dpg.add_spacer(width=100)
            dpg.add_image(ifw_tex, width=200, height=80)

        dpg.add_spacer(height=40)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=230)
            dpg.add_button(label="Launch SpecTwin", width=220, height=40, callback=launch_specwin)

    dpg.bind_theme(white_theme)
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
