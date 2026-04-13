# -*- coding: utf-8 -*-
"""
Created on Wed Sep 24 13:48:24 2025

@author: ccakir
"""

import dearpygui.dearpygui as dpg
import os
import shutil
import numpy as np

from PeriodicTableDPG import PeriodicTableDPG
from EdgeSelectionDPG import EdgeSelectionDPG
from SimulationParamsDPG import SimulationParamsDPG
from Xraydb import XrayDBHandler

from fdmnes_executer import FDMNES_executer
# from plot_ import PlotClass  # şimdilik run stabil olunca bağlarız


class AutoFDMNESUI:
    def __init__(self, parent_tag):
        self.parent = parent_tag
        self.last_job_dir = None

        # AutoFDMNES kökü (fdmnes_Win64 burada)
        self.auto_root = os.path.dirname(__file__)

        self.included_elements = []
        self.edge_panel = None
        self.param_panel = None
        self.simulation_data = None

        # --- plot series tags ---
        self.exafs_series_tag = None
        self.xes_series_tag = None

        # --- XES peak picking state ---
        self.xes_xy = None              # (xs, ys) numpy arrays for current XES plot
        self.xes_peaks = []             # list of dicts: {"E":..., "I":..., "idx":...}
        self.xes_peak_drawlayer = None  # draw layer tag
        self.xes_peak_table = None      # table tag
        self.xes_selected_row = -1      # selected row index
        self.xes_plot_handlers = "xes_plot_handlers"

        with dpg.tab_bar(parent=self.parent, tag="autofdmnes_tabs"):

            # --- Step 1 ---
            with dpg.tab(label="Step 1: Periodic Table", tag="tab_pt"):
                dpg.add_text("Select elements from the periodic table:")
                self.pt = PeriodicTableDPG("tab_pt")

                dpg.add_button(
                    label="Confirm Elements",
                    callback=self.confirm_elements
                )

                dpg.add_text("", tag="pt_warning", parent="tab_pt")

            # --- Step 2 ---
            with dpg.tab(label="Step 2: Edge Selection", tag="tab_edge"):
                dpg.add_text("Select element edges and formulas:")
                self.edge_panel = None

            # --- Step 3 ---
            with dpg.tab(label="Step 3: Simulation Parameters", tag="tab_params"):
                dpg.add_text("Set FDMNES simulation parameters and press Save.")
                self.param_panel = None

            # --- Step 4 ---
            with dpg.tab(label="Step 4: Run Simulation", tag="tab_sim"):
                dpg.add_text("Run FDMNES simulation:")
                dpg.add_button(
                    label="Run Simulation",
                    width=240,
                    callback=self.run_simulation
                )
                dpg.add_separator()
                dpg.add_text("", tag="sim_status", parent="tab_sim")

                dpg.add_spacer(height=8)
                dpg.add_separator()
                dpg.add_spacer(height=8)

                # --- Plots (side-by-side) ---
                with dpg.group(horizontal=True, parent="tab_sim"):

                    # LEFT: XANES (convolved) plot
                    with dpg.child_window(width=720, height=500, border=True):
                        dpg.add_text("XANES (convolved): out_conv.txt")
                        with dpg.plot(height=480, width=-1, tag="plot_exafs"):
                            dpg.add_plot_axis(dpg.mvXAxis, label="Energy", tag="ax_exafs_x")
                            dpg.add_plot_axis(dpg.mvYAxis, label="Intensity", tag="ax_exafs_y")

                    # RIGHT: XES plot + peak picking
                    with dpg.child_window(width=720, height=650, border=True):
                        dpg.add_text("XES: photon_conv_calc*.txt (Shift+Click to pick peak)")
                        with dpg.plot(height=480, width=-1, tag="plot_xes"):
                            dpg.add_plot_axis(dpg.mvXAxis, label="Energy", tag="ax_xes_x")
                            dpg.add_plot_axis(dpg.mvYAxis, label="Intensity", tag="ax_xes_y")

                        # Plot handler registry ONLY for plot_xes (no global mouse handler)
                        with dpg.item_handler_registry(tag=self.xes_plot_handlers):
                            dpg.add_item_clicked_handler(callback=self._on_xes_plot_clicked)
                        dpg.bind_item_handler_registry("plot_xes", self.xes_plot_handlers)

                        # draw layer for peak markers/lines
                        self.xes_peak_drawlayer = dpg.add_draw_layer(parent="plot_xes")

                        # controls
                        with dpg.group(horizontal=True):
                            self.chk_pick_mode = dpg.add_checkbox(label="Peak pick mode", default_value=False)
                            dpg.add_button(label="Clear peaks", callback=self.clear_xes_peaks)
                            dpg.add_button(label="Remove selected", callback=self.remove_selected_xes_peak)
                            dpg.add_button(label="Send peaks to Digital Twin", callback=self.send_peaks_to_digital_twin)



                        # peak table
                        self.xes_peak_table_parent = dpg.add_group()
                        self._rebuild_xes_peak_table(parent=self.xes_peak_table_parent)

    # -------------------------
    # Step 1 -> Step 2
    # -------------------------
    def confirm_elements(self, sender=None, app_data=None, user_data=None):
        self.included_elements = self.pt.get_included_elements()

        if not self.included_elements:
            dpg.set_value("pt_warning", "Please select at least one element.")
            return
        dpg.set_value("pt_warning", "")

        # EdgeSelectionDPG'yi sadece 1 kere oluştur
        if self.edge_panel is None:
            self.edge_panel = EdgeSelectionDPG(
                parent="tab_edge",
                included_elements=self.included_elements,
                xdb=XrayDBHandler()
            )
            # confirm CIF button callback
            dpg.set_item_callback(self.edge_panel.confirm_cif_button, self.confirm_cifs)
        else:
            # panel varsa refresh
            self.edge_panel.included_elements = self.included_elements
            self.edge_panel.refresh_elements()

        # Step 2'ye geç
        dpg.set_value("autofdmnes_tabs", "tab_edge")

    # -------------------------
    # Step 2 -> Step 3
    # -------------------------
    def confirm_cifs(self, sender=None, app_data=None, user_data=None):
        if self.edge_panel is None:
            return

        edge_data = self.edge_panel.get_data_set()
        self.simulation_data = edge_data

        # (basit olsun) her confirm'de yeniden kur
        self.param_panel = SimulationParamsDPG(
            "tab_params",
            edge_data,
            xdb=XrayDBHandler(),
            auto_root=self.auto_root
        )

        # Step 3'e geç
        dpg.set_value("autofdmnes_tabs", "tab_params")

    # -------------------------
    # Step 4: Run
    # -------------------------
    def run_simulation(self, sender=None, app_data=None, user_data=None):
        # guard checks
        if self.edge_panel is None or self.simulation_data is None:
            dpg.set_value("sim_status", "Please complete Step 2 (Edge Selection) first.")
            dpg.set_value("autofdmnes_tabs", "tab_edge")
            return

        if self.param_panel is None:
            dpg.set_value("sim_status", "Please open Step 3 and Save parameters first.")
            dpg.set_value("autofdmnes_tabs", "tab_params")
            return

        # Always fetch latest params (will auto-save if not saved yet)
        params = self.param_panel.get_parameters()
        input_exafs = self.param_panel.get_rendered_exafs_input_path()

        if not input_exafs or not os.path.isfile(input_exafs):
            dpg.set_value(
                "sim_status",
                f"Rendered EXAFS input not found.\nPlease press Save in Step 3.\nPath: {input_exafs}"
            )
            dpg.set_value("autofdmnes_tabs", "tab_params")
            return

        enable_xes = bool(params.get("enable_xes", False))

        # XES input (job copy) only needed if enable_xes
        conv_input = None
        conv_out_name = "photon_conv_calc.txt"
        gaussian = None
        gamma_hole = None

        if enable_xes:
            conv_input = self.param_panel.get_rendered_xes_input_path()

            # Ensure conv_input exists: copy core template into job file (update after EXAFS)
            if conv_input and not os.path.isfile(conv_input):
                core_xes = os.path.join(
                    self.auto_root, "fdmnes_Win64", "Sim", "Test_stand", "out", "core", "XES_inp.txt"
                )
                try:
                    os.makedirs(os.path.dirname(conv_input), exist_ok=True)
                    shutil.copyfile(core_xes, conv_input)
                except Exception as e:
                    dpg.set_value("sim_status", f"Failed to prepare XES input.\n{e}")
                    return

            # output name (UI sets this via params["xes"]["output_file"] if present)
            conv_out_name = params.get("xes", {}).get("output_file", "photon_conv_calc.txt")

            # Gaussian / Gamma_hole come from params["convolution"]
            gaussian = params.get("convolution", {}).get("gaussian", None)
            gamma_hole = params.get("convolution", {}).get("gamma_hole", None)

        # Switch to Step 4 tab
        dpg.set_value("autofdmnes_tabs", "tab_sim")
        dpg.set_value("sim_status", "Running FDMNES... check console output.")

        try:
            executer = FDMNES_executer(
                input_exafs=input_exafs,
                conv_input=conv_input,
                enable_xes=enable_xes,
                conv_out_name=conv_out_name,
                gaussian=gaussian,
                gamma_hole=gamma_hole,
                exe_root=self.auto_root,
            )

            first_out, second_out = executer.run()
            
            filout_base = getattr(executer, "filout_base", None)
            if filout_base:
                # .../jobs/<job>/out/out -> job dir = .../jobs/<job>
                self.last_job_dir = os.path.dirname(os.path.dirname(filout_base))
            

            # LEFT: prefer FiloutBase + "_conv.txt" (XANES convolved)
            xanes_plot_path = None
            filout_base = getattr(executer, "filout_base", None)
            if filout_base:
                cand = filout_base + "_conv.txt"
                if os.path.isfile(cand):
                    xanes_plot_path = cand

            # fallback
            if not xanes_plot_path:
                cand = getattr(executer, "last_out", None)
                if cand and os.path.isfile(cand):
                    xanes_plot_path = cand
                else:
                    xanes_plot_path = first_out

            xanes_ok = self._plot_file(
                path=xanes_plot_path,
                axis_y_tag="ax_exafs_y",
                axis_x_tag="ax_exafs_x",
                series_attr_name="exafs_series_tag",
                label=os.path.basename(xanes_plot_path)
            )

            # RIGHT: XES plot (store xy for peak picking)
            xes_ok = False
            if enable_xes and second_out and os.path.isfile(second_out):
                xes_ok = self._plot_file(
                    path=second_out,
                    axis_y_tag="ax_xes_y",
                    axis_x_tag="ax_xes_x",
                    series_attr_name="xes_series_tag",
                    label=os.path.basename(second_out),
                    store_to="xes"
                )

            msg = f"Run done.\nMain: {first_out}"
            msg += f"\nLeft plot: {xanes_plot_path} ({'OK' if xanes_ok else 'parse failed'})"

            if enable_xes:
                msg += f"\n\nXES: {second_out}"
                msg += f"\nRight plot: {'OK' if xes_ok else 'parse failed'}"

            dpg.set_value("sim_status", msg)

        except Exception as e:
            dpg.set_value("sim_status", f"Simulation failed:\n{e}")

    def send_peaks_to_digital_twin(self, sender=None, app_data=None, user_data=None):
        if not self.xes_peaks:
            dpg.set_value("sim_status", "No peaks selected.")
            return
        if not self.last_job_dir or not os.path.isdir(self.last_job_dir):
            dpg.set_value("sim_status", "No job folder found. Run simulation first.")
            return

        import json
        payload = [{"energy_eV": float(p["E"]), "intensity": float(p["I"])} for p in self.xes_peaks]

        peaks_path = os.path.join(self.last_job_dir, "peaks_selected.json")
        req_path   = os.path.join(self.last_job_dir, "opt_request.json")

        with open(peaks_path, "w", encoding="utf-8") as f:
            json.dump({"peaks": payload}, f, indent=2)

        with open(req_path, "w", encoding="utf-8") as f:
            json.dump({
                "type": "digital_twin_optimization",
                "job_dir": self.last_job_dir.replace("\\", "/"),
                "peaks_file": peaks_path.replace("\\", "/"),
                "peaks": payload,
            }, f, indent=2)

        dpg.set_value("sim_status", f"Sent peaks to Digital Twin.\n{req_path}")

    # -------------------------
    # Peak picking handlers
    # -------------------------
    def _on_xes_plot_clicked(self, sender, app_data, user_data=None):
        if not hasattr(self, "chk_pick_mode") or not dpg.get_value(self.chk_pick_mode):
            return

        if self.xes_xy is None:
            return

        xs, ys = self.xes_xy
        if xs is None or ys is None or len(xs) < 3:
            return

        mx, my = dpg.get_plot_mouse_pos()

        # en yakın x index
        idx0 = int(np.argmin(np.abs(xs - mx)))
        peak_idx = self._find_local_peak(ys, idx0, window=15)

        E = float(xs[peak_idx])
        I = float(ys[peak_idx])

        # duplicate guard
        for p in self.xes_peaks:
            if abs(p["E"] - E) < 0.2:
                return

        self.xes_peaks.append({"E": E, "I": I, "idx": int(peak_idx)})
        self.xes_peaks.sort(key=lambda p: p["E"])
        self._refresh_xes_peaks_ui()

    def _find_local_peak(self, y, idx0, window=15):
        n = len(y)
        lo = max(0, idx0 - window)
        hi = min(n - 1, idx0 + window)
        return lo + int(np.argmax(y[lo:hi + 1]))

    def clear_xes_peaks(self, sender=None, app_data=None, user_data=None):
        self.xes_peaks = []
        self.xes_selected_row = -1
        self._refresh_xes_peaks_ui()

    def remove_selected_xes_peak(self, sender=None, app_data=None, user_data=None):
        if self.xes_selected_row < 0 or self.xes_selected_row >= len(self.xes_peaks):
            return
        self.xes_peaks.pop(self.xes_selected_row)
        self.xes_selected_row = -1
        self._refresh_xes_peaks_ui()

    def _select_xes_peak_row(self, idx):
        self.xes_selected_row = idx

    def _rebuild_xes_peak_table(self, parent):
        # delete existing table if any
        if self.xes_peak_table and dpg.does_item_exist(self.xes_peak_table):
            dpg.delete_item(self.xes_peak_table)

        self.xes_peak_table = dpg.add_table(
            parent=parent,
            header_row=True,
            resizable=True,
            policy=dpg.mvTable_SizingStretchProp,
            borders_innerH=True,
            borders_outerH=True,
            borders_innerV=True,
            borders_outerV=True,
            height=80
        )
        dpg.add_table_column(label="#", parent=self.xes_peak_table, width_fixed=True, init_width_or_weight=30)
        dpg.add_table_column(label="Energy (eV)", parent=self.xes_peak_table)
        dpg.add_table_column(label="Intensity", parent=self.xes_peak_table)

    def _refresh_xes_peaks_ui(self):
        # clear draw layer
        if self.xes_peak_drawlayer and dpg.does_item_exist(self.xes_peak_drawlayer):
            dpg.delete_item(self.xes_peak_drawlayer, children_only=True)

        # rebuild table to avoid DPG column/row quirks across versions
        if hasattr(self, "xes_peak_table_parent") and self.xes_peak_table_parent and dpg.does_item_exist(self.xes_peak_table_parent):
            self._rebuild_xes_peak_table(self.xes_peak_table_parent)

        if self.xes_xy is None:
            return

        xs, ys = self.xes_xy

        for i, p in enumerate(self.xes_peaks):
            E = p["E"]
            I = p["I"]

            # draw peak markers
            dpg.draw_line((E, 0.0), (E, I), color=(255, 0, 0, 255), thickness=1.0, parent=self.xes_peak_drawlayer)
            dpg.draw_circle((E, I), radius=4, color=(255, 0, 0, 255), fill=(255, 0, 0, 120), parent=self.xes_peak_drawlayer)

            # table row
            with dpg.table_row(parent=self.xes_peak_table):
                dpg.add_selectable(
                    label=str(i + 1),
                    callback=lambda s, a, u=i: self._select_xes_peak_row(u)
                )
                dpg.add_text(f"{E:.3f}")
                dpg.add_text(f"{I:.6g}")

    # -------------------------
    # plotting helpers
    # -------------------------
    def _parse_two_columns_robust(self, path):
        import re
        xs, ys = [], []
        if not path or not os.path.isfile(path):
            return xs, ys

        num_re = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith(("#", "!", ";")):
                    continue
                s = s.replace(",", ".")  # EU decimal comma safety
                nums = num_re.findall(s)
                if len(nums) >= 2:
                    try:
                        xs.append(float(nums[0]))
                        ys.append(float(nums[1]))
                    except Exception:
                        pass
        return xs, ys

    def _plot_file(self, path, axis_y_tag, axis_x_tag, series_attr_name, label, store_to=None):
        xs, ys = self._parse_two_columns_robust(path)

        # delete old series if any
        old = getattr(self, series_attr_name, None)
        if old and dpg.does_item_exist(old):
            dpg.delete_item(old)

        if not xs or not ys:
            setattr(self, series_attr_name, None)
            return False

        # store XES curve for peak picking
        if store_to == "xes":
            self.xes_xy = (np.array(xs, dtype=float), np.array(ys, dtype=float))
            # new curve -> clear old picks
            self.xes_peaks = []
            self.xes_selected_row = -1
            self._refresh_xes_peaks_ui()

        # add new series under y-axis
        new_series = dpg.add_line_series(xs, ys, label=label, parent=axis_y_tag)
        setattr(self, series_attr_name, new_series)

        # autoscale
        try:
            dpg.fit_axis_data(axis_x_tag)
            dpg.fit_axis_data(axis_y_tag)
        except Exception:
            pass

        return True
