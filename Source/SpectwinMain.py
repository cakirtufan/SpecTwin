# -*- coding: utf-8 -*-
"""
Created on Mon Apr 14 11:38:58 2025
@author: cakir
"""

import dearpygui.dearpygui as dpg
import sys
from pathlib import Path

# === Add DigitalTwin module to path ===
source_dir = Path(__file__).resolve().parent

digital_twin_path = str(source_dir / "DigitalTwin")
if digital_twin_path not in sys.path:
    sys.path.append(digital_twin_path)
from DigitalTwinUI import DigitalTwinUI

data_visu_path = str(source_dir / "DataVisualization")
if data_visu_path not in sys.path:
    sys.path.append(data_visu_path)
from DataVisualizationUI import DataVisualizationUI  # <-- from your custom location

data_allign_path = str(source_dir / "DataAlligning")
if data_allign_path not in sys.path:
    sys.path.append(data_allign_path)
from DataProcessUI import DataProcessUI

data_sub_path = str(source_dir / "SubPixel")
if data_sub_path not in sys.path:
    sys.path.append(data_sub_path)
from EvtAnalyzerUI import EvtAnalyzerDPG

data_sub_path = str(source_dir / "MergeData")
if data_sub_path not in sys.path:
    sys.path.append(data_sub_path)
from MergeDataUI import MergeDataUI

autofdmnes_path = str(source_dir / "AutoFDMNES")
if autofdmnes_path not in sys.path:
    sys.path.append(autofdmnes_path)
from AutoFDMNESUI import AutoFDMNESUI

# === Setup DearPyGui ===
dpg.create_context()

base_path_font = source_dir / "fonts"
font_path = base_path_font / "verdana.ttf"
if not font_path.exists():
    raise FileNotFoundError(f"Font file not found: {font_path}")

with dpg.font_registry():
    verdana = dpg.add_font(str(font_path), 18)


# === Callbacks ===
def show_main_content(label):
    dpg.delete_item("content_area", children_only=True)

    if label == "DigitalTwin":
        DigitalTwinUI("content_area")

    elif label == "VisualizeData":
        DataVisualizationUI("content_area")

    elif label == "ProcessData":
        DataProcessUI("content_area")

    elif label == "SubPixelResolution":
        EvtAnalyzerDPG("content_area")
        
    elif label == "Merge .h5/.evt Files":
        MergeDataUI("content_area")
        
    elif label == "AutoFDMNES":
        AutoFDMNESUI("content_area")

    else:
        dpg.add_text(f"--- {label} Module ---", parent="content_area")


def toggle_data_analysis_menu():
    current = dpg.is_item_shown("data_analysis_group")
    dpg.configure_item("data_analysis_group", show=not current)


# === Main Layout ===
with dpg.window(tag="SpecWinWindow", label="SpecTwin", width=1920, height=1080):
    dpg.bind_font(verdana)

    with dpg.group(horizontal=True):

        # Sidebar
        with dpg.child_window(width=220, height=-1):
            dpg.add_text("Menu")
            dpg.add_separator()
            dpg.add_button(label="Digital Twin", callback=lambda: show_main_content("DigitalTwin"))
            dpg.add_button(label="Auto FDMNES", callback=lambda: show_main_content("AutoFDMNES"))
            dpg.add_button(label="Data Processes", callback=toggle_data_analysis_menu)

            with dpg.group(tag="data_analysis_group", show=False):
                dpg.add_button(label="   Merge Data", callback=lambda: show_main_content("Merge .h5/.evt Files"))
                dpg.add_button(label="   Visualize Data", callback=lambda: show_main_content("VisualizeData"))
                dpg.add_button(label="   Allign Data", callback=lambda: show_main_content("ProcessData"))
                dpg.add_button(label="   Process .evt Data", callback=lambda: show_main_content("SubPixelResolution"))

        # Content Area
        with dpg.child_window(tag="content_area", width=-1, height=-1):
            dpg.add_text("Welcome to SpecTwin Control Panel")


# === Launch GUI ===
dpg.create_viewport(title="SpecTwin - Control Panel", width=1920, height=1080)
dpg.setup_dearpygui()
dpg.set_primary_window("SpecWinWindow", True)
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
