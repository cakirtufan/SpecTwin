# -*- coding: utf-8 -*-
"""
Created on Wed Sep 24 14:41:03 2025

@author: ccakir
"""

# edge_selection_dpg.py
import dearpygui.dearpygui as dpg
from mpr import MPR

class EdgeSelectionDPG:
    def __init__(self, parent, included_elements, xdb):
        self.parent = parent
        self.included_elements = included_elements
#        self.excluded_elements = excluded_elements
        self.edge_vars = {}
        self.edge_combos = {}
        self.xdb = xdb
        self.mpr = MPR()
        
        self.cif_dir = {}

        self.formulas = []
        self.mpids = []
        self.selected_formulas = []
        self.selected_mpids = []
        self.selected_edges = []
        self.file_name = None
        self.data_set = None

        self.build_ui()

    def build_ui(self):
        
        with dpg.group(horizontal=False, parent=self.parent):
    
            # --- Edge Selection Section ---
            dpg.add_text("Step 1: Select element and edge")
    
            with dpg.group(horizontal=True):
                self.listbox_tag = dpg.add_combo(
                    items=self.included_elements,
                    # num_items=min(8, len(self.included_elements)),
                    width=350,
                    callback=self.show_edge_selection
                )
                with dpg.group(horizontal=False):
                    self.edge_combo_tag = dpg.add_combo(label="Select Edge", items=[], width=120)
                    self.confirm_button = dpg.add_button(label="Confirm Edge", callback=self.confirm_edges, width=120)
    
            dpg.add_separator()
    
            # --- Formula Search & Selection ---
            dpg.add_text("Step 2: Search and select formulas")
    
            with dpg.group(horizontal=True):
                with dpg.group():
                    self.search_input = dpg.add_input_text(
                        label="Search", width=200,
                        callback=self.filter_formulas
                    )
                    self.results_listbox = dpg.add_listbox(items=[], num_items=10, width=350)
                    with dpg.group(horizontal=True):
                        self.add_button = dpg.add_button(label="Add", width=40, callback=self.add_selected_formulas)
                        self.remove_button = dpg.add_button(label="Remove", width=80, callback=self.remove_selected_formulas)
    
                with dpg.group():
                    dpg.add_text("Selected formulas:")
                    self.selected_listbox = dpg.add_listbox(items=[], num_items=10, width=350)
    
                    # Collect button is placed right below formulas
                    self.simulation_button = dpg.add_button(
                        label="Collect Data for Simulation",
                        callback=self.collect_simulation_data,
                        width=250
                    )
    
            dpg.add_separator()
            
            
            # --- Simulation Data Table ---
            dpg.add_text("Simulation Data Preview:")
            with dpg.table(header_row=True, resizable=True, policy=dpg.mvTable_SizingStretchProp,
                           borders_innerH=True, borders_outerH=True, borders_innerV=True, borders_outerV=True,
                           parent=self.parent) as self.sim_table:
                dpg.add_table_column(label="Element")
                dpg.add_table_column(label="Edge")
                dpg.add_table_column(label="Formula")
                dpg.add_table_column(label="ID")
            
        
            self.confirm_cif_button = dpg.add_button(
                                                    label="Confirm .cif",
                                                    width=200,
                                                    parent = self.parent                                                    
                                                    )

    def show_edge_selection(self, sender, app_data):
        selected_element = app_data
        edges = list(self.xdb.get_edges(selected_element))
        if not edges:
            dpg.add_text(f"No edges found for {selected_element}", parent=self.parent)
            return
        dpg.configure_item(self.edge_combo_tag, items=edges)
        self.edge_vars[selected_element] = edges[0]

    def confirm_edges(self, sender, app_data):
        selected_element = dpg.get_value(self.listbox_tag)
        selected_edge = dpg.get_value(self.edge_combo_tag)
        self.edge_vars[selected_element] = selected_edge
        # dpg.add_text(f"Confirmed edge: {selected_element}-{selected_edge}", parent=self.parent)

        self.formulas, self.mpids = self.mpr.find_id_and_formulas(
            self.included_elements,
        )
        self.update_results(self.formulas, self.mpids)

    def update_results(self, formulas, mpids):
        dpg.configure_item(self.results_listbox, items=[f"{f}, ID: {m}" for f, m in zip(formulas, mpids)])

    def filter_formulas(self, sender, app_data):
        query = app_data.lower()
        filtered = [(f, m) for f, m in zip(self.formulas, self.mpids) if query in f.lower()]
        self.update_results([f for f, _ in filtered], [m for _, m in filtered])

    def add_selected_formulas(self, sender, app_data):
        selected = dpg.get_value(self.results_listbox)
        if not selected:
            return
        formula, mpid = selected.split(", ID: ")
        # check uniqueness by pair, not just formula
        if (formula, mpid) not in zip(self.selected_formulas, self.selected_mpids):
            self.selected_formulas.append(formula)
            self.selected_mpids.append(mpid)
            items = [f"{f}, ID: {m}" for f, m in zip(self.selected_formulas, self.selected_mpids)]
            dpg.configure_item(self.selected_listbox, items=items)
    
    def remove_selected_formulas(self, sender, app_data):
        selected = dpg.get_value(self.selected_listbox)
        if not selected:
            return
        formula, mpid = selected.split(", ID: ")
        pair = (formula, mpid)
        # check against stored pairs
        pairs = list(zip(self.selected_formulas, self.selected_mpids))
        if pair in pairs:
            idx = pairs.index(pair)
            self.selected_formulas.pop(idx)
            self.selected_mpids.pop(idx)
            items = [f"{f}, ID: {m}" for f, m in zip(self.selected_formulas, self.selected_mpids)]
            dpg.configure_item(self.selected_listbox, items=items)

    def collect_simulation_data(self, sender, app_data):
        edges = [{"element": el, "edge": edge} for el, edge in self.edge_vars.items()]
        simulation_data = {"edges": edges, "formulas": self.selected_formulas}
    
        # Clear old table rows
        if dpg.does_item_exist(self.sim_table):
            children = dpg.get_item_children(self.sim_table, 1)  # 1 = rows
            if children:
                for row in children:
                    dpg.delete_item(row)
    
        # Fill table with new data (Element, Edge, Formula, ID)
        for edge in edges:
            element = edge["element"]
            edge_name = edge["edge"]
            for formula, mpid in zip(self.selected_formulas, self.selected_mpids):
                with dpg.table_row(parent=self.sim_table):
                    dpg.add_text(element)
                    dpg.add_text(edge_name)
                    dpg.add_text(formula)
                    dpg.add_text(mpid)
                    
                    key = f"{formula}_{mpid}"
                    if key not in self.cif_dir:
                        
                        self.cif_dir[key] = {}
                        
                    self.file_name = formula + ".cif"
                    self.data_set = simulation_data
                    self.cif_dir[key]["Directory"] = self.mpr.get_cif_data(mpid, formula)
                    self.cif_dir[key]["Edge"] = edge_name
                    self.cif_dir[key]["Element"] = element
    
    def get_data_set(self):
        return self.cif_dir
    
    
    def refresh_elements(self):
        """Refresh listbox with newly selected elements."""
        if self.included_elements:
            dpg.configure_item(self.listbox_tag, items=self.included_elements)
        else:
            dpg.configure_item(self.listbox_tag, items=[])

