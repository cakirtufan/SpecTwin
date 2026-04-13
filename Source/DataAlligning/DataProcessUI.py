# -*- coding: utf-8 -*-
"""
Created on Mon May  5 11:32:10 2025

@author: ccakir
"""

import dearpygui.dearpygui as dpg
from CalibrationAppUI import CalibrationUI
from AlignAppUI import AligningUI

class DataProcessUI:
    def __init__(self, parent_tag):
        self.parent_tag = parent_tag
        self.calibration_data = {}
        self.aligning_tab_enabled = False
        self.aligning_tab_tag = "aligning_tab"
        self.calibration_tab_tag = "calibration_tab"

        with dpg.group(parent=self.parent_tag):
            with dpg.tab_bar(tag="data_analysis_tabbar"):
                with dpg.tab(label="Calibration", tag=self.calibration_tab_tag):
                    self.build_calibration_tab()

                # Create empty Aligning tab container, but don’t build UI yet
                with dpg.tab(label="Aligning", tag=self.aligning_tab_tag):
                    dpg.add_text("Aligning UI will be available after calibration")
                    dpg.configure_item(self.aligning_tab_tag, show=False)

    def build_calibration_tab(self):
        CalibrationUI(self.calibration_tab_tag, parent_app=self)

    def build_aligning_tab(self):
        # Rebuild AligningUI fresh with current calibration_data
        dpg.delete_item(self.aligning_tab_tag, children_only=True)
        AligningUI(self.aligning_tab_tag, self.calibration_data)

    def enable_aligning_tab(self):
        # When calibration is done, build Aligning UI with latest data
        self.build_aligning_tab()
        dpg.configure_item(self.aligning_tab_tag, show=True)
        self.aligning_tab_enabled = True

