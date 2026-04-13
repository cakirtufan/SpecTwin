# -*- coding: utf-8 -*-
"""
Created on Wed Apr 16 15:16:15 2025

@author: ccakir
"""

import dearpygui.dearpygui as dpg
import os
import glob
import json
import threading
import numpy as np

from XrayDBHandler import XrayDBHandler
from CrystalSelector import CrystalSelector
from CalcDistance import BraggCalculator
from ExperimentBuilder import BeamLineBuilder
from RunOptimizationv2 import PixelDiffOptimizer
from DGPPlotter import DPGPlotter


class DigitalTwinUI:
    def __init__(self, parent):
        self.parent = parent

        self.auto_root = os.path.dirname(__file__)

        self.xray_db = XrayDBHandler()
        self.crystals = CrystalSelector()

        # Energy pools
        self.selected_energies_sim = []
        self.selected_energies_opt = []
        self.xes_peak_energies = []
        self.hkl = [1, 1, 1]

        # Optimization selections
        self.selection_pairs = []
        self.distance_bounds = (110.0, 140.0)

        # Convergence data
        self._conv_x = []
        self._conv_y = []
        self._conv_best = []

        with dpg.texture_registry(tag="texture_reg", show=False):
            pass

        with dpg.group(horizontal=True, parent=self.parent):

            with dpg.group(horizontal=False):

                with dpg.group(horizontal=True):

                    # ==========================================================
                    # Element Selection
                    # ==========================================================
                    with dpg.child_window(width=550, height=360, border=True):
                        dpg.add_text("Element Selection")
                        self.element_combo = dpg.add_combo(
                            self.xray_db.get_elements(),
                            label="Element",
                            callback=self.update_shells
                        )
                        self.shell_combo = dpg.add_combo([], label="Shell", callback=self.update_lines)
                        self.line_listbox = dpg.add_listbox([], label="Lines", num_items=4)

                        with dpg.group(horizontal=True):
                            dpg.add_button(label="Add Line (Sim)", callback=self.add_line_sim)
                            dpg.add_button(label="Add Line (Opt)", callback=self.add_line_opt)

                        with dpg.group(horizontal=True):
                            dpg.add_button(label="Clear Sim Energies", callback=self.clear_sim_energies)
                            dpg.add_button(label="Clear Opt Energies", callback=self.clear_opt_energies)
                            dpg.add_button(label="Deselect All", callback=self.deselect_all)

                        self.result_text_sim = dpg.add_input_text(
                            multiline=True, readonly=True, width=500, height=80,
                            label="Simulation Energies"
                        )
                        self.result_text_opt = dpg.add_input_text(
                            multiline=True, readonly=True, width=500, height=80,
                            label="Optimization Energies"
                        )

                    # ==========================================================
                    # Crystal Selection
                    # ==========================================================
                    with dpg.child_window(width=550, height=360, border=True):
                        dpg.add_text("Crystal Selection")

                        self.crystal_combo_sim = dpg.add_combo(self.crystals.crystals, label="Crystal")
                        self.hkl_input_sim = dpg.add_input_text(
                            label="hkl (e.g. 1,1,1)",
                            default_value="1,1,1"
                        )

                        self.crystal_info = dpg.add_input_text(
                            multiline=True,
                            readonly=True,
                            width=500,
                            height=80,
                            label="Crystal Info"
                        )

                        dpg.add_button(label="Select Crystal", callback=self.display_crystal_info)

                        self.distance_input = dpg.add_input_float(label="Distance", default_value=110.0)
                        self.num_rep_input = dpg.add_input_int(
                            label="Repeats (xrt iterations)",
                            default_value=1500,
                            min_value=1
                        )

                        dpg.add_button(label="Run Simulation", callback=self.run_simulation)

                    # ==========================================================
                    # Optimization Parameters and Run
                    # ==========================================================
                    with dpg.child_window(width=600, height=360, border=True):
                        dpg.add_text("Optimization Parameters and Run")

                        self.distance_boundary_start = dpg.add_input_float(
                            label="Starting Distance",
                            default_value=110.0
                        )
                        self.distance_boundary_stop = dpg.add_input_float(
                            label="End Distance",
                            default_value=140.0
                        )

                        self.crystal_combo_opt = dpg.add_combo(self.crystals.crystals, label="Crystal")
                        self.hkl_input_opt = dpg.add_input_text(
                            label="hkl (e.g. 1,1,1)",
                            default_value="1,1,1"
                        )

                        self.opt_repeats_input = dpg.add_input_int(
                            label="Repeats (xrt iterations)",
                            default_value=1500,
                            min_value=1
                        )

                        self.opt_calls_input = dpg.add_input_int(
                            label="n_calls",
                            default_value=15,
                            min_value=1
                        )

                        dpg.add_separator()

                        self.optimization_method_combo = dpg.add_combo(
                            items=["Bayesian Optimization", "Random Search", "Grid Search"],
                            default_value="Bayesian Optimization",
                            label="Optimization Method"
                        )

                        self.seed_input = dpg.add_input_text(
                            label="Seeds",
                            default_value="0,1,2,3,4,42,123,456,789,1234",
                            hint="Comma-separated, e.g. 0,1,2,42"
                        )

                        self.bo_acq_combo = dpg.add_combo(
                            items=["LCB", "EI", "PI", "gp_hedge"],
                            default_value="LCB",
                            label="BO acquisition"
                        )

                        self.bo_kappa_input = dpg.add_input_float(
                            label="BO kappa",
                            default_value=1.96
                        )

                        self.bo_n_initial_input = dpg.add_input_int(
                            label="BO n_initial_points",
                            default_value=5,
                            min_value=1
                        )

                        self.opt_hint_text = dpg.add_text("", color=(200, 200, 50), wrap=560)
                        self.run_status_text = dpg.add_text("Status: idle", color=(180, 180, 180), wrap=560)

                        dpg.add_separator()
                        dpg.add_text("Extra target energies")
                        self.manual_energy_input = dpg.add_input_text(
                            label="Manual energies (eV)",
                            default_value="",
                            hint="Comma-separated, e.g. 6404.1, 7058.0"
                        )

                        with dpg.group(horizontal=True):
                            dpg.add_button(label="Add Manual Energies", callback=self.add_manual_energies)
                            dpg.add_button(label="Clear Opt Energies", callback=self.clear_opt_energies)

                        with dpg.group(horizontal=True):
                            dpg.add_button(
                                label="Load peaks (AutoFDMNES)",
                                callback=self.load_peaks_and_start_optimization
                            )
                            dpg.add_button(
                                label="Clear Opt Selections",
                                callback=self.clear_opt_selections
                            )

                        dpg.add_separator()
                        dpg.add_text("Crystal/HKL selections for optimization")

                        self.selection_text = dpg.add_text("No selections yet", wrap=560)

                        dpg.add_button(label="Add Selection", callback=self.add_selection_callback)

                        with dpg.group(horizontal=True):
                            dpg.add_button(label="Run Optimization", callback=self.run_optimization)
                            dpg.add_button(label="Run Optimization (Thread)", callback=self.run_optimization_threaded)

                        dpg.add_separator()
                        self.seed_summary_text = dpg.add_input_text(
                            label="Run Summary",
                            multiline=True,
                            readonly=True,
                            width=560,
                            height=80
                        )

                # ==============================================================
                # Graph Area
                # ==============================================================
                with dpg.child_window(width=-1, height=650, border=True, tag="graph_window"):
                    dpg.add_text("Graph")

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def add_selection_callback(self):
        crystal = dpg.get_value(self.crystal_combo_opt)
        if not crystal:
            print("[Optimization] Please select a crystal.")
            return

        hkl_str = dpg.get_value(self.hkl_input_opt)
        hkl_str = (hkl_str or "").strip()
        try:
            parts = [p.strip() for p in hkl_str.replace(" ", ",").split(",") if p.strip() != ""]
            if len(parts) != 3:
                raise ValueError("HKL must have 3 integers")
            hkl = tuple(int(p) for p in parts)
        except Exception:
            print(f"[Optimization] Invalid HKL: '{hkl_str}'. Use format like 1,1,1")
            return

        pair = (crystal, hkl)
        if pair not in self.selection_pairs:
            self.selection_pairs.append(pair)

        dist_start = dpg.get_value(self.distance_boundary_start)
        dist_stop = dpg.get_value(self.distance_boundary_stop)
        self.distance_bounds = (dist_start, dist_stop)

        self._refresh_selection_text()

    def _refresh_selection_text(self):
        if not self.selection_pairs:
            dpg.set_value(self.selection_text, "No selections yet")
            return

        display_lines = [f"{c} {h}" for c, h in self.selection_pairs]
        display = (
            f"Crystal/HKL Options:\n" + "\n".join(display_lines) + "\n"
            f"Distance Bounds: {self.distance_bounds}"
        )
        dpg.set_value(self.selection_text, f"Selections:\n{display}")

    def _parse_seed_csv(self, s: str):
        if not s:
            return []
        parts = [p.strip() for p in s.replace(";", ",").replace("\n", ",").split(",")]
        out = []
        for p in parts:
            if not p:
                continue
            try:
                out.append(int(p))
            except Exception:
                continue
        return out

    def _reset_convergence_plot(self, method_name="", seed_text=""):
        self._conv_x = []
        self._conv_y = []
        self._conv_best = []

        if dpg.does_item_exist("conv_series_current"):
            dpg.set_value("conv_series_current", [[], []])
        if dpg.does_item_exist("conv_series_best"):
            dpg.set_value("conv_series_best", [[], []])

        if dpg.does_item_exist("conv_method_txt"):
            dpg.set_value("conv_method_txt", f"Method: {method_name}")
        if dpg.does_item_exist("conv_seed_txt"):
            dpg.set_value("conv_seed_txt", f"Seed: {seed_text}")

        self._clear_best_result_labels()

    def _clear_best_result_labels(self):
        defaults = {
            "best_distance_txt": "Best distance : -",
            "best_crystal_txt": "Best crystal  : -",
            "best_hkl_txt": "Best hkl      : -",
            "best_visible_txt": "Visible peaks : -",
            "best_chosen_txt": "Chosen peaks  : -",
            "best_deltax_txt": "deltaX (px)   : -",
            "best_pixeldiff_txt": "pixel_diff    : -",
            "best_coverage_txt": "coverage      : -",
            "best_score_txt": "score         : -",
            "best_obj_txt": "objective     : -",
        }
        for tag, value in defaults.items():
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, value)

    # ------------------------------------------------------------------
    # AutoFDMNES peaks -> Digital Twin optimization
    # ------------------------------------------------------------------
    def load_peaks_and_start_optimization(self, sender=None, app_data=None, user_data=None):
        newest = self._find_latest_opt_request()
        if not newest:
            print("[DigitalTwin] No opt_request.json found under Source/AutoFDMNES (or Source).")
            return

        try:
            with open(newest, "r", encoding="utf-8") as f:
                req = json.load(f)
        except Exception as e:
            print(f"[DigitalTwin] Failed to read opt_request.json: {e}")
            return

        peaks = req.get("peaks", [])
        if not peaks:
            print("[DigitalTwin] opt_request.json has no peaks.")
            return

        peak_energies = []
        for p in peaks:
            try:
                peak_energies.append(float(p.get("energy_eV")))
            except Exception:
                pass

        peak_energies = sorted(set([e for e in peak_energies if np.isfinite(e)]))
        if len(peak_energies) == 0:
            print("[DigitalTwin] No valid peak energies parsed.")
            return

        self.xes_peak_energies = list(peak_energies)
        self.selected_energies_opt = sorted(
            set([float(e) for e in (self.selected_energies_opt + peak_energies) if np.isfinite(e)])
        )

        cur = dpg.get_value(self.result_text_opt) or ""
        cur += f"\n--- Loaded peaks from AutoFDMNES ---\n"
        cur += f"Source: {newest}\n"
        for e in peak_energies:
            cur += f"XES Peak: {e:.3f} eV\n"
        dpg.set_value(self.result_text_opt, cur)

        print("[DigitalTwin] Loaded peak energies:", peak_energies)

    def _find_latest_opt_request(self):
        this_dir = os.path.dirname(os.path.abspath(__file__))
        source_dir = os.path.abspath(os.path.join(this_dir, os.pardir))

        candidates = [
            os.path.join(source_dir, "AutoFDMNES"),
            source_dir,
        ]

        newest = None
        newest_t = -1.0

        for base in candidates:
            pattern = os.path.join(base, "**", "opt_request.json")
            for p in glob.glob(pattern, recursive=True):
                try:
                    t = os.path.getmtime(p)
                except Exception:
                    continue
                if t > newest_t:
                    newest_t = t
                    newest = p

        return newest

    # ------------------------------------------------------------------
    # Convergence window
    # ------------------------------------------------------------------
    def _open_convergence_window(self):
        if dpg.does_item_exist("conv_window"):
            dpg.show_item("conv_window")
            return

        self._conv_x = []
        self._conv_y = []
        self._conv_best = []

        with dpg.window(
            label="Optimization Convergence",
            tag="conv_window",
            width=760,
            height=420,
            pos=(50, 50),
            on_close=lambda: dpg.hide_item("conv_window")
        ):
            dpg.add_text("Method: -", tag="conv_method_txt")
            dpg.add_text("Seed: -", tag="conv_seed_txt")
            dpg.add_separator()

            with dpg.plot(label="Convergence", height=220, width=-1, tag="conv_plot"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Iteration", tag="conv_xaxis")
                dpg.add_plot_axis(dpg.mvYAxis, label="Objective", tag="conv_yaxis")
                dpg.add_line_series([], [], label="Current", parent="conv_yaxis", tag="conv_series_current")
                dpg.add_line_series([], [], label="Best so far", parent="conv_yaxis", tag="conv_series_best")

            dpg.add_spacer(height=8)
            dpg.add_separator()
            dpg.add_spacer(height=8)

            dpg.add_text("Best result:")
            dpg.add_text("Best distance : -", tag="best_distance_txt")
            dpg.add_text("Best crystal  : -", tag="best_crystal_txt")
            dpg.add_text("Best hkl      : -", tag="best_hkl_txt")
            dpg.add_text("Visible peaks : -", tag="best_visible_txt")
            dpg.add_text("Chosen peaks  : -", tag="best_chosen_txt")
            dpg.add_text("deltaX (px)   : -", tag="best_deltax_txt")
            dpg.add_text("pixel_diff    : -", tag="best_pixeldiff_txt")
            dpg.add_text("coverage      : -", tag="best_coverage_txt")
            dpg.add_text("score         : -", tag="best_score_txt")
            dpg.add_text("objective     : -", tag="best_obj_txt")

    def _update_convergence(self, iter_idx, y_current, y_best):
        self._conv_x.append(int(iter_idx))
        self._conv_y.append(float(y_current))
        self._conv_best.append(float(y_best))

        if dpg.does_item_exist("conv_series_current"):
            dpg.set_value("conv_series_current", [self._conv_x, self._conv_y])
        if dpg.does_item_exist("conv_series_best"):
            dpg.set_value("conv_series_best", [self._conv_x, self._conv_best])

        if dpg.does_item_exist("conv_xaxis"):
            dpg.fit_axis_data("conv_xaxis")
        if dpg.does_item_exist("conv_yaxis"):
            dpg.fit_axis_data("conv_yaxis")

    def _fill_best_result_labels_from_payload(self, payload):
        if payload is None or payload.get("metrics") is None or payload.get("debug") is None:
            return

        m = payload["metrics"]
        d = payload["debug"]

        vis = payload.get("visible_peaks", None)
        ch = payload.get("chosen_peaks", None)

        vis_str = vis.tolist() if hasattr(vis, "tolist") else vis
        ch_str = ch.tolist() if hasattr(ch, "tolist") else ch

        dpg.set_value("best_distance_txt", f"Best distance : {payload['distance']:.4f}")
        dpg.set_value("best_crystal_txt", f"Best crystal  : {payload.get('crystal', '-')}")
        dpg.set_value("best_hkl_txt", f"Best hkl      : {payload.get('hkl', '-')}")
        dpg.set_value("best_visible_txt", f"Visible peaks : {vis_str}")
        dpg.set_value("best_chosen_txt", f"Chosen peaks  : {ch_str}")
        dpg.set_value("best_deltax_txt", f"deltaX (px)   : {m.get('deltaX', float('nan')):.3f}")
        dpg.set_value("best_pixeldiff_txt", f"pixel_diff    : {m.get('pixel_diff', float('nan')):.6f} eV/px")
        dpg.set_value("best_coverage_txt", f"coverage      : {payload.get('coverage', 0.0):.2f}")
        dpg.set_value("best_score_txt", f"score         : {d.get('score', float('nan')):.6f}")
        dpg.set_value("best_obj_txt", f"objective     : {-d.get('score', float('nan')):.6f}")

    # ------------------------------------------------------------------
    # Optimization flow
    # ------------------------------------------------------------------
    def run_optimization_threaded(self):
        t = threading.Thread(target=self.run_optimization, daemon=True)
        t.start()

    def run_optimization(self):
        target_candidates = sorted(set([float(e) for e in self.selected_energies_opt if np.isfinite(e)]))
        if len(target_candidates) < 2:
            print("[Optimization] Please select at least TWO target energies (lines or manual).")
            return

        if len(target_candidates) > 2:
            self._open_target_picker(target_candidates)
            return

        self._continue_run_optimization(target_candidates)

    def _continue_run_optimization(self, target_energies):
        target_energies = sorted(set([float(e) for e in target_energies if np.isfinite(e)]))
        if len(target_energies) != 2:
            print("[Optimization] Please choose exactly TWO target energies.")
            return

        dE = abs(float(target_energies[1]) - float(target_energies[0]))
        if dE >= 3.0:
            hint = f"deltaE = {dE:.1f} eV"
        else:
            hint = f"deltaE = {dE:.1f} eV. (Repeat set to 4000 xrt iterations.)"
            dpg.set_value(self.opt_repeats_input, 4000)

        if dpg.does_item_exist(self.opt_hint_text):
            dpg.set_value(self.opt_hint_text, hint)
        else:
            print("[Optimization]", hint)

        repeats = int(dpg.get_value(self.opt_repeats_input))
        n_calls = int(dpg.get_value(self.opt_calls_input))
        method = dpg.get_value(self.optimization_method_combo)
        seeds = self._parse_seed_csv(dpg.get_value(self.seed_input))
        acq_func = dpg.get_value(self.bo_acq_combo)
        kappa = float(dpg.get_value(self.bo_kappa_input))
        n_initial_points = int(dpg.get_value(self.bo_n_initial_input))

        sim_energies = sorted(
            set([float(e) for e in (self.selected_energies_sim + target_energies + self.xes_peak_energies) if np.isfinite(e)])
        )
        if len(sim_energies) < 2:
            print("[Optimization] sim_energies must contain at least 2 energies.")
            return

        self.selected_energies_opt = list(sorted(set(self.selected_energies_opt + target_energies)))

        optimizer = PixelDiffOptimizer(
            crystals=[],
            hkls=[],
            distance_bounds=self.distance_bounds,
            crystal_hkl_pairs=self.selection_pairs,
            sim_energies=sim_energies,
            target_energies=target_energies,
            repeats=repeats,
            enable_best_plots=True,
            plot_container="graph_window",
            plotly_in_browser=False,
        )

        self._open_convergence_window()
        optimizer.set_convergence_plotter(self._update_convergence)
        optimizer.set_best_update_callback(self._fill_best_result_labels_from_payload)

        summary_lines = []
        dpg.set_value(self.seed_summary_text, "")
        dpg.set_value(self.run_status_text, f"Status: running {method}")

        if method == "Grid Search":
            self._reset_convergence_plot(method_name=method, seed_text="N/A")
            dpg.set_value(self.run_status_text, "Status: running Grid Search")

            result = optimizer.grid_search(
                step_mm=1.0,
                verbose=True,
                auto_export_json=True,
                export_filename="grid_search_results.json",
            )

            if optimizer.best_payload is not None and optimizer.best_payload.get("debug") is not None:
                best_score = optimizer.best_payload["debug"].get("score", None)
                best_crystal = optimizer.best_payload.get("crystal", "-")
                best_hkl = optimizer.best_payload.get("hkl", "-")
                best_distance = optimizer.best_payload.get("distance", None)

                summary_lines.append(
                    f"Grid Search | best_score={best_score:.6f} | crystal={best_crystal} | "
                    f"hkl={best_hkl} | distance={best_distance:.3f}"
                )

            dpg.set_value(self.seed_summary_text, "\n".join(summary_lines))
            dpg.set_value(self.run_status_text, "Status: Grid Search finished")
            optimizer.export_results_to_json("optimization_results.json")
            return

        if not seeds:
            print("[Optimization] No valid seeds parsed.")
            dpg.set_value(self.run_status_text, "Status: invalid seeds")
            return

        for seed in seeds:
            self._reset_convergence_plot(method_name=method, seed_text=str(seed))
            dpg.set_value(self.run_status_text, f"Status: running {method}, seed={seed}")

            if method == "Bayesian Optimization":
                result = optimizer.optimize(
                    n_calls=n_calls,
                    include_crystal=True,
                    include_hkl=True,
                    random_state=seed,
                    acq_func=acq_func,
                    kappa=kappa,
                    n_initial_points=n_initial_points,
                    auto_export_json=True,
                    export_filename=f"bo_seed_{seed}.json",
                )
            elif method == "Random Search":
                result = optimizer.random_search(
                    n_calls=n_calls,
                    random_state=seed,
                    auto_export_json=True,
                    export_filename=f"random_seed_{seed}.json",
                )
            else:
                print(f"[Optimization] Unknown method: {method}")
                continue

            best_payload = optimizer.best_payload
            if best_payload is not None and best_payload.get("debug") is not None:
                best_score = best_payload["debug"].get("score", None)
                best_crystal = best_payload.get("crystal", "-")
                best_hkl = best_payload.get("hkl", "-")
                best_distance = best_payload.get("distance", None)

                line = (
                    f"{method} | seed={seed} | best_score={best_score:.6f} | "
                    f"crystal={best_crystal} | hkl={best_hkl} | distance={best_distance:.3f}"
                )
            else:
                line = f"{method} | seed={seed} | no valid result"

            summary_lines.append(line)
            dpg.set_value(self.seed_summary_text, "\n".join(summary_lines))

        dpg.set_value(self.run_status_text, f"Status: {method} finished")
        optimizer.export_results_to_json("optimization_results.json")

    # ------------------------------------------------------------------
    # Target picker modal
    # ------------------------------------------------------------------
    def _open_target_picker(self, target_candidates):
        self._target_picker_candidates = list(target_candidates)

        if dpg.does_item_exist("target_picker_modal"):
            dpg.delete_item("target_picker_modal")

        self._target_picker_selected = set()

        with dpg.window(
            label="Select TWO target energies",
            modal=True,
            show=True,
            tag="target_picker_modal",
            width=520,
            height=420,
            pos=(120, 120),
            no_resize=False,
        ):
            dpg.add_text("You selected more than 2 target energies.")
            dpg.add_text("Please tick exactly TWO energies to continue.")
            dpg.add_separator()
            dpg.add_text("", tag="target_picker_status", color=(255, 120, 120), wrap=480)

            for e in self._target_picker_candidates:
                tag = f"target_chk_{e:.6f}"

                def _make_cb(val):
                    def _cb(sender, app_data, user_data):
                        ee = user_data
                        if app_data:
                            self._target_picker_selected.add(ee)
                        else:
                            self._target_picker_selected.discard(ee)
                        dpg.set_value("target_picker_status", f"Selected: {sorted(self._target_picker_selected)}")
                    return _cb

                dpg.add_checkbox(label=f"{e:.3f} eV", tag=tag, callback=_make_cb(e), user_data=e)

            dpg.add_spacer(height=8)
            with dpg.group(horizontal=True):
                def _ok():
                    chosen = sorted(self._target_picker_selected)
                    if len(chosen) != 2:
                        dpg.set_value("target_picker_status", "Please select exactly TWO energies.")
                        return
                    dpg.delete_item("target_picker_modal")
                    self._continue_run_optimization(chosen)

                def _cancel():
                    dpg.delete_item("target_picker_modal")

                dpg.add_button(label="OK", callback=lambda: _ok())
                dpg.add_button(label="Cancel", callback=lambda: _cancel())

    # ------------------------------------------------------------------
    # XrayDB UI callbacks
    # ------------------------------------------------------------------
    def update_shells(self, sender):
        element = dpg.get_value(self.element_combo)
        lines = self.xray_db.get_lines_by_element(element)
        shells = sorted(set(line[0] for line in lines if line[0] in "KLM"))
        dpg.configure_item(self.shell_combo, items=shells)
        if shells:
            dpg.set_value(self.shell_combo, shells[0])
            self.update_lines(self.shell_combo)

    def update_lines(self, sender):
        element = dpg.get_value(self.element_combo)
        shell = dpg.get_value(self.shell_combo)
        lines = self.xray_db.get_lines_by_element(element)
        filtered = [line for line in lines if line.startswith(shell)]
        dpg.configure_item(self.line_listbox, items=filtered)

    def add_line_sim(self):
        element = dpg.get_value(self.element_combo)
        line = dpg.get_value(self.line_listbox)
        if line:
            energy = self.xray_db.get_line_energy(element, line)
            self.selected_energies_sim.append(float(energy))
            current = dpg.get_value(self.result_text_sim)
            dpg.set_value(
                self.result_text_sim,
                current + f"Element: {element}, Line: {line}, Energy: {energy} eV\n"
            )

    def add_line_opt(self):
        element = dpg.get_value(self.element_combo)
        line = dpg.get_value(self.line_listbox)
        if line:
            energy = self.xray_db.get_line_energy(element, line)
            self.selected_energies_opt.append(float(energy))
            current = dpg.get_value(self.result_text_opt)
            dpg.set_value(
                self.result_text_opt,
                current + f"Element: {element}, Line: {line}, Energy: {energy} eV\n"
            )

    def add_manual_energies(self):
        raw = dpg.get_value(self.manual_energy_input) or ""
        vals = self._parse_energy_csv(raw)
        if not vals:
            print("[Optimization] No valid manual energies parsed.")
            return

        self.selected_energies_opt.extend(vals)
        self.selected_energies_sim.extend(vals)

        current_opt = dpg.get_value(self.result_text_opt)
        for e in vals:
            current_opt += f"Manual Energy: {e} eV\n"
        dpg.set_value(self.result_text_opt, current_opt)

        current_sim = dpg.get_value(self.result_text_sim)
        for e in vals:
            current_sim += f"Manual Energy: {e} eV\n"
        dpg.set_value(self.result_text_sim, current_sim)

        dpg.set_value(self.manual_energy_input, "")

    def clear_opt_energies(self):
        self.selected_energies_opt = []
        dpg.set_value(self.result_text_opt, "")

    def clear_sim_energies(self):
        self.selected_energies_sim = []
        dpg.set_value(self.result_text_sim, "")

    def clear_opt_selections(self):
        self.selection_pairs = []
        dist_start = dpg.get_value(self.distance_boundary_start)
        dist_stop = dpg.get_value(self.distance_boundary_stop)
        self.distance_bounds = (dist_start, dist_stop)
        self._refresh_selection_text()

    def deselect_all(self):
        self.selected_energies_sim = []
        self.selected_energies_opt = []
        dpg.set_value(self.result_text_sim, "")
        dpg.set_value(self.result_text_opt, "")

    # ------------------------------------------------------------------
    # Crystal / simulation
    # ------------------------------------------------------------------
    def display_crystal_info(self):
        crystal = dpg.get_value(self.crystal_combo_sim)
        hkl_input = dpg.get_value(self.hkl_input_sim)
        try:
            self.hkl = [int(x.strip()) for x in hkl_input.split(",")[:3]]
        except Exception:
            self.hkl = [1, 1, 1]

        info = self.crystals.get_crystal_method(crystal, hkl=self.hkl)
        if isinstance(info, str):
            dpg.set_value(self.crystal_info, info)
        else:
            hkl = getattr(info, "hkl", "N/A")
            d = getattr(info, "d", "N/A")
            dpg.set_value(
                self.crystal_info,
                f"Crystal: {crystal}\nHKL: {hkl}\nSpacing d: {d} Å"
            )

    def run_simulation(self):
        crystal = dpg.get_value(self.crystal_combo_sim)
        distance = dpg.get_value(self.distance_input)
        repeats = dpg.get_value(self.num_rep_input)
        energies = sorted(set([float(e) for e in self.selected_energies_sim if np.isfinite(e)]))

        if len(energies) < 1:
            print("[Simulation] No energies selected.")
            return

        mean_energy = float(np.mean(energies))
        bragg = BraggCalculator(mean_energy, distance, crystal, self.hkl)
        theta, c = bragg.main()

        builder = BeamLineBuilder(crystal, distance, c, theta, int(repeats), energies, self.hkl)
        builder.run_simulation()

        image2D = builder.total2D
        image1Dx = builder.total1DX
        image1Dz = builder.total1DZ
        total1DEnergy = builder.total1DEnergy
        total1DEnergy_limits = builder.total1DEnergy_limits
        histo1Dx = builder.histo1Dx

        plotter = DPGPlotter(image2D, image1Dx, image1Dz, total1DEnergy, total1DEnergy_limits, histo1Dx)
        plotter.plot("graph_window")

        print(f"Simulation run with θ={theta}, c={c}, hkl={self.hkl}")

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_energy_csv(s: str):
        if not s:
            return []
        parts = [p.strip() for p in s.replace(";", ",").replace("\n", ",").split(",")]
        out = []
        for p in parts:
            if not p:
                continue
            try:
                out.append(float(p))
            except Exception:
                continue
        return out