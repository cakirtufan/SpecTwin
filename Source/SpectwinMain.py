# -*- coding: utf-8 -*-
"""
Created on Mon Apr 14 11:38:58 2025
@author: cakir
"""

import sys
from pathlib import Path

import dearpygui.dearpygui as dpg

# === Add module folders to path ===
source_dir = Path(__file__).resolve().parent
if str(source_dir) not in sys.path:
    sys.path.append(str(source_dir))

from UI import theme as ui_theme

digital_twin_path = str(source_dir / "DigitalTwin")
if digital_twin_path not in sys.path:
    sys.path.append(digital_twin_path)
from DigitalTwinUI import DigitalTwinUI

data_visu_path = str(source_dir / "DataVisualization")
if data_visu_path not in sys.path:
    sys.path.append(data_visu_path)
from DataVisualizationUI import DataVisualizationUI

data_allign_path = str(source_dir / "DataAlligning")
if data_allign_path not in sys.path:
    sys.path.append(data_allign_path)
from DataProcessUI import DataProcessUI

data_sub_path = str(source_dir / "SubPixel")
if data_sub_path not in sys.path:
    sys.path.append(data_sub_path)
from EvtAnalyzerUI import EvtAnalyzerDPG

merge_data_path = str(source_dir / "MergeData")
if merge_data_path not in sys.path:
    sys.path.append(merge_data_path)
from MergeDataUI import MergeDataUI

autofdmnes_path = str(source_dir / "AutoFDMNES")
if autofdmnes_path not in sys.path:
    sys.path.append(autofdmnes_path)
from AutoFDMNESUI import AutoFDMNESUI


def load_default_font():
    return ui_theme.load_fonts(source_dir)["default"]


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
        ui_theme.add_section_title(f"{label} Module", parent="content_area")


def toggle_data_analysis_menu():
    current = dpg.is_item_shown("data_analysis_group")
    dpg.configure_item("data_analysis_group", show=not current)


def _add_welcome_action(label, description, action):
    with dpg.child_window(width=300, height=164, border=True, no_scrollbar=True):
        ui_theme.add_section_title(label)
        dpg.add_text(description, color=ui_theme.rgba("text_secondary"), wrap=260)
        dpg.add_spacer(height=8)
        button = dpg.add_button(label=label, width=-1, callback=action)
        ui_theme.bind_button_theme(button, "secondary")


def build_main_window():
    ui_theme.apply_global_theme(source_dir)

    with dpg.window(tag="SpecWinWindow", label="SpecTwin", width=1920, height=1080):
        with dpg.group(horizontal=True):
            with dpg.child_window(width=240, height=-1):
                ui_theme.add_section_title("SpecTwin")
                dpg.add_text("Workstation modules", color=ui_theme.rgba("text_muted"))
                dpg.add_separator()
                digital_btn = dpg.add_button(label="Digital Twin", width=-1, callback=lambda: show_main_content("DigitalTwin"))
                auto_btn = dpg.add_button(label="AutoFDMNES", width=-1, callback=lambda: show_main_content("AutoFDMNES"))
                data_btn = dpg.add_button(label="Data Processing", width=-1, callback=toggle_data_analysis_menu)
                ui_theme.bind_button_theme(digital_btn, "secondary")
                ui_theme.bind_button_theme(auto_btn, "secondary")
                ui_theme.bind_button_theme(data_btn, "secondary")

                with dpg.group(tag="data_analysis_group", show=False):
                    dpg.add_button(label="  Merge Data", width=-1, callback=lambda: show_main_content("Merge .h5/.evt Files"))
                    dpg.add_button(label="  Visualize Data", width=-1, callback=lambda: show_main_content("VisualizeData"))
                    dpg.add_button(label="  Align Data", width=-1, callback=lambda: show_main_content("ProcessData"))
                    dpg.add_button(label="  Process .evt Data", width=-1, callback=lambda: show_main_content("SubPixelResolution"))

            with dpg.child_window(tag="content_area", width=-1, height=-1):
                ui_theme.add_section_title("SpecTwin Control Panel")
                dpg.add_text(
                    "Select a module from the left rail to begin a simulation, analysis, or data-processing workflow.",
                    color=ui_theme.rgba("text_secondary"),
                    wrap=720,
                )
                dpg.add_spacer(height=16)
                with dpg.group(horizontal=True):
                    _add_welcome_action(
                        "Digital Twin",
                        "Configure emission lines, simulate spectrometer geometry, and inspect optimization output.",
                        lambda: show_main_content("DigitalTwin"),
                    )
                    _add_welcome_action(
                        "AutoFDMNES",
                        "Select materials, generate FDMNES inputs, run simulations, and route peaks forward.",
                        lambda: show_main_content("AutoFDMNES"),
                    )
                    _add_welcome_action(
                        "Data Processing",
                        "Merge, visualize, align, and process spectroscopy files.",
                        toggle_data_analysis_menu,
                    )


def main():
    dpg.create_context()
    try:
        build_main_window()
        dpg.create_viewport(title="SpecTwin - Control Panel", width=1920, height=1080)
        dpg.setup_dearpygui()
        dpg.set_primary_window("SpecWinWindow", True)
        dpg.show_viewport()
        dpg.start_dearpygui()
    finally:
        dpg.destroy_context()


if __name__ == "__main__":
    main()
