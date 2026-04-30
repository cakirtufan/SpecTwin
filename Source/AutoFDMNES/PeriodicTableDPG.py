# -*- coding: utf-8 -*-
"""
Created on Wed Sep 24 13:58:21 2025

@author: ccakir
"""

import dearpygui.dearpygui as dpg


class PeriodicTableDPG:
    def __init__(self, parent):
        self.included_elements = {}
        self.excluded_elements = {}
        self.element_buttons = {}
        self.exclusion_mode = False  

        self.theme_green = self.make_button_theme((0, 200, 0))      # included
        self.theme_red = self.make_button_theme((200, 0, 0))        # excluded

        self.periodic_table_layout = [
            ['H', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', 'He'],
            ['Li', 'Be', '', '', '', '', '', '', '', '', '', '', 'B', 'C', 'N', 'O', 'F', 'Ne'],
            ['Na', 'Mg', '', '', '', '', '', '', '', '', '', '', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar'],
            ['K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr'],
            ['Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe'],
            ['Cs', 'Ba', '', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', '', '', ''],
            ['', '', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu'],
            ['', '', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu']
        ]

        with dpg.group(parent=parent):
            with dpg.table(header_row=False, policy=dpg.mvTable_SizingFixedFit):
                for _ in range(max(len(r) for r in self.periodic_table_layout)):
                    dpg.add_table_column()

                for row in self.periodic_table_layout:
                    with dpg.table_row():
                        for element in row:
                            if element and element.strip():
                                btn_id = dpg.add_button(
                                    label=element,
                                    width=40,
                                    height=40,
                                    callback=self.make_callback(element)
                                )
                                self.element_buttons[element] = btn_id
                            else:
                                dpg.add_spacer(width=40, height=40)

            # Footer bar: confirm button only
            self.footer_bar = dpg.add_group(horizontal=True)
#            dpg.add_button(
#                label="Confirm Included Elements",
#                callback=self.confirm_included_elements,
#                tag="confirm_button",
#                parent=self.footer_bar
#            )

    # --- Factory for safe callback binding ---
    def make_callback(self, element):
        def callback(sender, app_data):
            self.toggle_element(element, sender, app_data)
        return callback

    # --- Themes ---
    def make_button_theme(self, color):
        with dpg.theme() as theme_id:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, color, category=dpg.mvThemeCat_Core)
        return theme_id

    # === Button logic ===
    def toggle_element(self, element, sender=None, app_data=None):
        btn_id = self.element_buttons[element]

        if self.exclusion_mode:
            if element in self.excluded_elements:
                self.excluded_elements.pop(element, None)
                dpg.bind_item_theme(btn_id, 0)
                return
            self.included_elements.pop(element, None)
            self.excluded_elements[element] = True
            dpg.bind_item_theme(btn_id, self.theme_red)
        else:
            if element in self.included_elements:
                self.included_elements.pop(element, None)
                dpg.bind_item_theme(btn_id, 0)
                return
            self.excluded_elements.pop(element, None)
            self.included_elements[element] = True
            dpg.bind_item_theme(btn_id, self.theme_green)

    def confirm_included_elements(self, sender, app_data, user_data=None):
        if not self.included_elements:
            dpg.add_text("⚠️ Please select at least one element.", parent=self.footer_bar)
            return

        # Ask user if they want to exclude
        with dpg.window(label="Exclusion?", modal=True, width=350, height=150, no_close=True) as popup_id:
            dpg.add_text("Do you want to exclude any elements?")
            dpg.add_button(label="Yes", width=100,
                           callback=lambda: self.start_exclusion(popup_id))
            dpg.add_button(label="No", width=100,
                           callback=lambda: self.finish_selection(popup_id))

#    def start_exclusion(self, popup_id):
#        self.exclusion_mode = True
#        dpg.delete_item(popup_id)
#        dpg.configure_item("confirm_button",
#                           label="Finish Selection",
#                           callback=self.finish_selection)

    def finish_selection(self, popup_id=None):
        if popup_id:
            dpg.delete_item(popup_id)

        for btn in self.element_buttons.values():
            dpg.disable_item(btn)
        if dpg.does_item_exist("confirm_button"):
            dpg.disable_item("confirm_button")


    def get_included_elements(self):
        return list(self.included_elements.keys())

#    def get_excluded_elements(self):
#        return list(self.excluded_elements.keys())

