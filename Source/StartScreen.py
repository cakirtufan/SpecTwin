# -*- coding: utf-8 -*-
"""
Created on Mon Apr 14 10:08:23 2025

@author: cakir
"""
import dearpygui.dearpygui as dpg
from PIL import Image
import numpy as np
import subprocess
import sys
from pathlib import Path

dpg.create_context()

def load_texture(path):
    """Load image as RGBA texture for DearPyGui"""
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    data = (np.array(image) / 255.0).flatten().tolist()
    with dpg.texture_registry():
        return dpg.add_static_texture(width, height, data)


source_dir = Path(__file__).resolve().parent
print("Source directory:", source_dir)

# === File paths ===
base_path_image = source_dir / "img"
bam_path = base_path_image / "bam_logo.png"
ifw_path = base_path_image / "ifw_logo.png"
spectwin_logo_path = base_path_image / "spectwin_logo.png"
base_path_font = source_dir / "fonts"
verdana_font_path = base_path_font / "verdana.ttf"

# === Check files ===
for path in [bam_path, ifw_path, spectwin_logo_path, verdana_font_path]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

# === Load textures ===
bam_tex = load_texture(bam_path)
ifw_tex = load_texture(ifw_path)
spectwin_tex = load_texture(spectwin_logo_path)

# === Load Verdana Font ===
with dpg.font_registry():
    verdana_font = dpg.add_font(str(verdana_font_path), 18)

# === White background theme ===
with dpg.theme() as white_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (255, 255, 255), category=dpg.mvThemeCat_Core)

def launch_specwin():
    subprocess.Popen([sys.executable, str(source_dir / "SpectwinMain.py")], cwd=source_dir)
    dpg.destroy_context()  # Optional: closes the start screen


# === UI Layout ===
with dpg.window(tag="MainWindow", label="", width=800, height=600, no_title_bar=True, no_resize=True):
    dpg.bind_font(verdana_font)
    dpg.add_spacer(height=20)

    # Centered SpecTwin Logo
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=230)
        dpg.add_image(spectwin_tex, width=200, height=80)

    with dpg.group(horizontal=True):
        dpg.add_spacer(width=130)
        dpg.add_text("A Platform for XES Simulation, Data Analysis and Digital Twin ", color=(60, 60, 60), wrap=500)

    dpg.add_spacer(height=25)

    # Logos BAM & IFW
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=100)
        dpg.add_image(bam_tex, width=200, height=80)
        dpg.add_spacer(width=100)
        dpg.add_image(ifw_tex, width=200, height=80)

    dpg.add_spacer(height=40)

    # Launch Button centered
    with dpg.group(horizontal=True):
        dpg.add_spacer(width=230)
        dpg.add_button(label="Launch SpecTwin", width=220, height=40, callback=launch_specwin)

# === Show viewport ===
icon_path = base_path_image / "spectwin_icon.ico"
dpg.create_viewport(
    title='SpecTwin',
    width=750,
    height=400,
    small_icon=str(icon_path),
    large_icon=str(icon_path)
)
dpg.setup_dearpygui()

dpg.set_primary_window("MainWindow", True)
dpg.bind_theme(white_theme)

dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()

