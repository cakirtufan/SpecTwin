# -*- coding: utf-8 -*-
"""
SimulationParamsDPG.py (job-key based + run-key based)
- Saves params.json under out/jobs/<run_key>/  (run_key = job_key + timestamp)
- Renders EXAFS input file from core/EXAFS_inp.txt into out/jobs/<run_key>/
- Ensures FDMNES outputs go into out/jobs/<run_key>/out/  (Filout = .../out/<base>)
- Prepares XES (convolution) settings: Gaussian + Gamma_hole
  (UI'da Lorentzian yerine Gamma_hole kullanılır.)
"""

import os
import json
from datetime import datetime

import dearpygui.dearpygui as dpg


class SimulationParamsDPG:
    def __init__(self, parent, edge_data, xdb, auto_root):
        """
        parent: DPG parent tag (e.g., "tab_params")
        edge_data: dict from EdgeSelectionDPG.get_data_set()
        xdb: XrayDBHandler instance
        auto_root: absolute path to .../AutoFDMNES (where fdmnes_Win64 lives)
        """
        self.parent = parent
        self.edge_data = edge_data
        self.xdb = xdb
        self.auto_root = auto_root

        self.range_inputs = []
        self.params = {}

        # core templates (DO NOT modify)
        self.exafs_template = os.path.join(
            self.auto_root, "fdmnes_Win64", "Sim", "Test_stand", "out", "core", "EXAFS_inp.txt"
        )
        self.xes_template = os.path.join(
            self.auto_root, "fdmnes_Win64", "Sim", "Test_stand", "out", "core", "XES_inp.txt"
        )

        # jobs output base
        self.jobs_root = os.path.join(
            self.auto_root, "fdmnes_Win64", "Sim", "Test_stand", "out", "jobs"
        )
        os.makedirs(self.jobs_root, exist_ok=True)

        # derive lists
        self.job_keys = list(self.edge_data.keys())
        self.cif_files = [self.edge_data[k]["Directory"] for k in self.job_keys]
        self.edges = sorted(list(set([self.edge_data[k]["Edge"] for k in self.job_keys]))) or ["K"]
        self.elements = sorted(list(set([self.edge_data[k]["Element"] for k in self.job_keys])))

        self.z_list = [self.xdb.get_atomic_numbers(el) for el in self.elements] if self.elements else [0]

        # active edge energy (preview)
        self.edge_energy = 0.0

        # job_key selection (logical job)
        self.job_key = self._default_job_key()

        # run_key selection (physical run folder, timestamped) - created on each save
        self.run_key = ""
        self.last_run_dir = ""

        # rendered output paths (set on save)
        self.rendered_exafs_path = ""
        self.rendered_xes_path = ""

        self.build_ui()
        self._recompute_edge_energy_from_ui()
        self.update_plot()

    # -------------------------
    # job helpers
    # -------------------------
    def _default_job_key(self):
        # default to first actual job if present, otherwise create a multi_ timestamp
        if self.job_keys:
            if len(self.job_keys) == 1:
                return self.job_keys[0]
            return self.job_keys[0]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"multi_{ts}"

    def _safe_name(self, s: str) -> str:
        return "".join(c if (c.isalnum() or c in ("_", "-", ".")) else "_" for c in str(s))

    def _job_dir(self, key: str) -> str:
        d = os.path.join(self.jobs_root, self._safe_name(key))
        os.makedirs(d, exist_ok=True)
        return d

    def _make_run_key(self, job_key: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self._safe_name(job_key)}_{ts}"

    # -------------------------
    # UI callbacks
    # -------------------------
    def on_job_change(self, sender=None, app_data=None, user_data=None):
        self.job_key = dpg.get_value(self.job_combo)

        # update defaults based on selected job
        if self.job_key in self.edge_data:
            info = self.edge_data[self.job_key]

            if dpg.does_item_exist(self.cif_file):
                dpg.set_value(self.cif_file, info["Directory"])

            if dpg.does_item_exist(self.edge_combo):
                dpg.set_value(self.edge_combo, info["Edge"])

            z = self.xdb.get_atomic_numbers(info["Element"])
            if dpg.does_item_exist(self.z_absorber):
                dpg.set_value(self.z_absorber, z)

        self._recompute_edge_energy_from_ui()
        self.update_plot()

    def on_edge_change(self, sender=None, app_data=None, user_data=None):
        self._recompute_edge_energy_from_ui()
        self.update_plot()

    def on_absorber_change(self, sender=None, app_data=None, user_data=None):
        self._recompute_edge_energy_from_ui()
        self.update_plot()

    def on_xes_toggle(self, sender, app_data):
        dpg.configure_item(self.container_xes, show=app_data)

    # -------------------------
    # edge energy logic
    # -------------------------
    def _element_from_selected_z(self, z_sel):
        for k in self.edge_data:
            el = self.edge_data[k]["Element"]
            if self.xdb.get_atomic_numbers(el) == z_sel:
                return el
        return self.elements[0] if self.elements else None

    def _recompute_edge_energy_from_ui(self):
        try:
            z_sel = int(dpg.get_value(self.z_absorber))
        except Exception:
            z_sel = int(self.z_list[0]) if self.z_list else 0

        try:
            edge_sel = dpg.get_value(self.edge_combo)
        except Exception:
            edge_sel = self.edges[0] if self.edges else "K"

        el = self._element_from_selected_z(z_sel)
        if el:
            self.edge_energy = self.xdb.get_edge_energy(el, edge_sel)
        else:
            self.edge_energy = 0.0

    # -------------------------
    # UI build
    # -------------------------
    def build_ui(self):
        dpg.add_text("FDMNES Simulation Parameters", parent=self.parent)

        # job chooser
        dpg.add_text("Job", parent=self.parent)
        self.job_combo = dpg.add_combo(
            label="Job key",
            items=self.job_keys if self.job_keys else [self.job_key],
            default_value=self.job_key,
            parent=self.parent,
            callback=self.on_job_change
        )

        # output base name (NOT a filename path; just base like 'out' or 'calc')
        self.out_file = dpg.add_input_text(
            label="Output Base Name",
            default_value="out",
            parent=self.parent
        )

        # range table
        dpg.add_text("Energy Ranges (relative to edge): Start, Step, Stop", parent=self.parent)
        with dpg.table(header_row=True, parent=self.parent):
            dpg.add_table_column(label="Region", init_width_or_weight=70, width_fixed=False)
            dpg.add_table_column(label="Start (eV)", init_width_or_weight=70, width_fixed=False)
            dpg.add_table_column(label="Step (eV)", init_width_or_weight=70, width_fixed=False)
            dpg.add_table_column(label="Stop (eV)", init_width_or_weight=70, width_fixed=False)

            labels = ["Pre-edge", "Edge", "Post-edge"]
            defaults = [(-50.0, 0.5, -2.0), (-2.0, 0.1, 10.0), (10.0, 0.5, 100.0)]

            for lab, vals in zip(labels, defaults):
                with dpg.table_row():
                    dpg.add_text(lab)
                    row = []
                    for v in vals:
                        row.append(dpg.add_input_float(default_value=v, width=150, callback=self.update_plot))
                    self.range_inputs.append(row)

        # plot
        dpg.add_text("Energy Range Preview (absolute eV)", parent=self.parent)
        with dpg.plot(label="Energy Axis", height=200, width=520, parent=self.parent, tag="energy_plot"):
            dpg.add_plot_axis(dpg.mvXAxis, label="Energy (eV)", tag="x_axis")
            dpg.add_plot_axis(dpg.mvYAxis, label="", tag="y_axis")
        self.region_drawlayer = dpg.add_draw_layer(parent="energy_plot")

        # edge selection
        self.edge_combo = dpg.add_combo(
            label="Edge",
            items=self.edges,
            default_value=self.edges[0] if self.edges else "K",
            parent=self.parent,
            callback=self.on_edge_change
        )

        # physics flags
        self.eimag = dpg.add_input_float(label="Eimag", default_value=0.5, parent=self.parent)
        self.green = dpg.add_checkbox(label="Use Green Function", default_value=True, parent=self.parent)
        self.density = dpg.add_checkbox(label="Include Density", default_value=True, parent=self.parent)
        self.density_all = dpg.add_checkbox(label="Density all", default_value=False, parent=self.parent)
        self.quadrupole = dpg.add_checkbox(label="Quadrupole", default_value=False, parent=self.parent)

        # other
        self.radius = dpg.add_input_float(label="Cluster Radius (Å)", default_value=6.0, parent=self.parent)
        self.z_absorber = dpg.add_combo(
            label="Z Absorber",
            default_value=self.z_list[0] if self.z_list else 0,
            parent=self.parent,
            items=self.z_list if self.z_list else [0],
            callback=self.on_absorber_change
        )

        # cif file chooser (full paths)
        default_cif = self.cif_files[0] if self.cif_files else ""
        self.cif_file = dpg.add_combo(
            label="CIF File",
            items=self.cif_files if self.cif_files else [""],
            default_value=default_cif,
            parent=self.parent
        )

        # --- Convolution / XES Parameters ---
        dpg.add_text("Convolution / XES Parameters", parent=self.parent)
        self.conv_gaussian = dpg.add_input_float(label="Gaussian Width (eV)", default_value=1.0, parent=self.parent)
        self.conv_gamma_hole = dpg.add_input_float(label="Gamma_hole (eV)", default_value=0.7, parent=self.parent)

        self.enable_xes = dpg.add_checkbox(
            label="Also generate XES spectrum",
            default_value=False,
            parent=self.parent,
            callback=self.on_xes_toggle
        )

        self.container_xes = dpg.add_group(parent=self.parent, show=False)
        with dpg.group(parent=self.container_xes):
            self.output_file_xes = dpg.add_input_text(
                label="Conv_out file name",
                default_value="photon_conv_calc.txt"
            )

        dpg.add_button(
            label="Save Parameters (and render EXAFS input)",
            parent=self.parent,
            callback=self.save_parameters
        )

        self.status_text = dpg.add_text("", parent=self.parent)

        # init job defaults into UI
        self.on_job_change()

    # -------------------------
    # plot
    # -------------------------
    def update_plot(self, sender=None, app_data=None, user_data=None):
        dpg.delete_item(self.region_drawlayer, children_only=True)

        ranges_eV = []
        for row in self.range_inputs:
            start = dpg.get_value(row[0])
            stop = dpg.get_value(row[2])
            ranges_eV.append((self.edge_energy + start, self.edge_energy + stop))

        colors = [(100, 200, 255, 80), (100, 255, 100, 80), (255, 100, 100, 80)]
        for (start, stop), color in zip(ranges_eV, colors):
            dpg.draw_rectangle(
                pmin=(start, -0.4),
                pmax=(stop, 0.4),
                fill=color,
                color=(0, 0, 0, 0),
                parent=self.region_drawlayer
            )

        if ranges_eV:
            min_x = min(r[0] for r in ranges_eV)
            max_x = max(r[1] for r in ranges_eV)
            dpg.set_axis_limits("x_axis", min_x - 5, max_x + 5)

        dpg.set_axis_limits("y_axis", -1, 1)

    # -------------------------
    # template rendering helpers
    # -------------------------
    def _range_line_from_params(self, rng):
        pre, edge, post = rng
        return f'{pre["start"]} {pre["step"]} {pre["stop"]} {edge["step"]} {edge["stop"]} {post["step"]} {post["stop"]}'

    def _replace_block_value(self, lines, keyword, new_value_line):
        kw_lower = keyword.strip().lower()
        out = []
        i = 0
        while i < len(lines):
            out.append(lines[i])
            if lines[i].strip().lower().startswith(kw_lower):
                if i + 1 < len(lines):
                    out.append(f"   {new_value_line}\n")  # keep 3-space indent
                    i += 2
                    continue
            i += 1
        return out

    def _toggle_keyword_line(self, lines, keyword, enable):
        if enable is None:
            return lines

        kw = keyword.strip()
        kw_lower = kw.lower()

        def is_kw_line(line):
            return line.strip().lower() == kw_lower

        has_kw = any(is_kw_line(l) for l in lines)

        if enable is False:
            return [l for l in lines if not is_kw_line(l)]

        if has_kw:
            return lines

        out = []
        inserted = False
        for l in lines:
            if (not inserted) and l.strip().lower() == "end":
                out.append(f" {kw}\n")
                inserted = True
            out.append(l)
        if not inserted:
            out.append(f" {kw}\n")
        return out

    # -------------------------
    # EXAFS input render
    # -------------------------
    def render_exafs_input(self, params, target_path):
        if not os.path.isfile(self.exafs_template):
            raise FileNotFoundError(f"EXAFS template not found: {self.exafs_template}")

        with open(self.exafs_template, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        # Ensure run out dir exists
        run_dir = os.path.dirname(target_path)
        run_out_dir = os.path.join(run_dir, "out")
        os.makedirs(run_out_dir, exist_ok=True)

        # Filout base MUST be: .../out/<base> (so outputs go INSIDE out/)
        base = params.get("out_file", "out")
        base = (base or "out").strip()
        base = os.path.splitext(base)[0] or "out"
        filout_base = os.path.join(run_out_dir, base).replace("\\", "/")

        rng_line = self._range_line_from_params(params["range"])

        lines = self._replace_block_value(lines, "Filout", filout_base)
        
        
        # CIF: write absolute path to avoid cwd-based re-resolution issues
        cif_raw = (params.get("cif_file") or "").strip().strip('"').strip("'")
        cif_abs = os.path.abspath(cif_raw)
        cif_abs = cif_abs.replace("\\", "/")
        lines = self._replace_block_value(lines, "Cif_file", cif_abs)

        lines = self._replace_block_value(lines, "Edge", params["edge"])
        lines = self._replace_block_value(lines, "Z_absorber", str(params["z_absorber"]))
        lines = self._replace_block_value(lines, "Radius", str(params["radius"]))
        lines = self._replace_block_value(lines, "Eimag", str(params["eimag"]))
        lines = self._replace_block_value(lines, "Range", rng_line)

        # toggles as commands
        lines = self._toggle_keyword_line(lines, "Green", params.get("green"))
        lines = self._toggle_keyword_line(lines, "Density", params.get("density"))
        lines = self._toggle_keyword_line(lines, "Density_all", params.get("density_all"))
        lines = self._toggle_keyword_line(lines, "Quadrupole", params.get("quadrupole"))

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    # -------------------------
    # XES input render (optional utility; executer updates conv template after EXAFS run)
    # -------------------------
    def render_xes_input(self, calc_file_path, conv_out_path, target_path, gaussian, gamma_hole):
        if not os.path.isfile(self.xes_template):
            raise FileNotFoundError(f"XES template not found: {self.xes_template}")

        with open(self.xes_template, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        lines = self._replace_block_value(lines, "Calculation", calc_file_path.replace("\\", "/"))
        lines = self._replace_block_value(lines, "Conv_out", conv_out_path.replace("\\", "/"))
        lines = self._replace_block_value(lines, "Gaussian", str(gaussian))
        lines = self._replace_block_value(lines, "Gamma_hole", str(gamma_hole))

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    # -------------------------
    # params API
    # -------------------------
    def get_parameters(self):
        if not self.params:
            return self.save_parameters()
        return self.params

    def get_job_key(self):
        return self.job_key

    def get_run_key(self):
        return self.run_key

    def get_last_run_dir(self):
        return self.last_run_dir

    def get_rendered_exafs_input_path(self):
        return self.rendered_exafs_path

    def get_rendered_xes_input_path(self):
        return self.rendered_xes_path

    # -------------------------
    # save + render
    # -------------------------
    def save_parameters(self, sender=None, app_data=None, user_data=None):
        # Create a unique run folder every time Save is pressed
        self.run_key = self._make_run_key(self.job_key)
        jdir = self._job_dir(self.run_key)
        self.last_run_dir = jdir

        params = {
            "job_key": self.job_key,
            "run_key": self.run_key,
            "calc_type": "XAFS",
            "out_file": dpg.get_value(self.out_file),
            "range": [
                {"start": dpg.get_value(r[0]), "step": dpg.get_value(r[1]), "stop": dpg.get_value(r[2])}
                for r in self.range_inputs
            ],
            "edge": dpg.get_value(self.edge_combo),
            "eimag": dpg.get_value(self.eimag),
            "green": dpg.get_value(self.green),
            "density": dpg.get_value(self.density),
            "density_all": dpg.get_value(self.density_all),
            "quadrupole": dpg.get_value(self.quadrupole),
            "energpho": dpg.get_value(self.energpho) if hasattr(self, "energpho") else None,
            "radius": dpg.get_value(self.radius),
            "z_absorber": int(dpg.get_value(self.z_absorber)),
            "cif_file": dpg.get_value(self.cif_file),

            # Convolution / XES params
            "convolution": {
                "gaussian": dpg.get_value(self.conv_gaussian),
                "gamma_hole": dpg.get_value(self.conv_gamma_hole),
            },

            "enable_xes": bool(dpg.get_value(self.enable_xes)),
        }

        if params["enable_xes"]:
            params["xes"] = {"output_file": dpg.get_value(self.output_file_xes)}

        # save json
        params_path = os.path.join(jdir, "params.json")
        with open(params_path, "w", encoding="utf-8") as f:
            json.dump(params, f, indent=2)

        # render EXAFS input (always)
        rendered_exafs = os.path.join(jdir, f"EXAFS_inp_{self._safe_name(self.run_key)}.txt")
        self.render_exafs_input(params, rendered_exafs)

        # prepare XES input output path (final update happens after EXAFS run)
        rendered_xes = os.path.join(jdir, f"XES_inp_{self._safe_name(self.run_key)}.txt")
        self.rendered_xes_path = rendered_xes if params["enable_xes"] else ""

        self.params = params
        self.rendered_exafs_path = rendered_exafs

        msg = (
            f"Saved: {params_path}\n"
            f"Run folder: {jdir}\n"
            f"Rendered EXAFS: {rendered_exafs}\n"
            f"Outputs will go to: {os.path.join(jdir, 'out')}\n"
            f"XES enabled: {params.get('enable_xes')}\n"
            f"Prepared XES path: {self.rendered_xes_path or '-'}"
        )
        print(msg)
        dpg.set_value(self.status_text, msg)

        return params
