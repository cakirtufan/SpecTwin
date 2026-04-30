# -*- coding: utf-8 -*-
"""
Created on Fri May 16 10:04:37 2025

@author: ccakir
"""

import os
import sys
from pathlib import Path
import dearpygui.dearpygui as dpg
import numpy as np

source_dir = Path(__file__).resolve().parents[1]
utils_path = str(source_dir / "Utils")
if utils_path not in sys.path:
    sys.path.append(utils_path)

from XRFAnalyzer import XRFAnalyzer
from HDF5Reader import HDF5Reader


class MergeDataUI:
    def __init__(self, parent_tag: str):
        self.parent_tag = parent_tag

        # state
        self.filter_mode = ".h5"
        self.recursive = True
        self.selected_dir: str | None = None
        self.file_map: dict[str, str] = {}
        self.file_list: list[str] = []
        self.channels = {"ChannelMin": None, "ChannelMax": None}
        self.selected_for_merge: dict[str, bool] = {}

        # unique tag prefix
        self.prefix = f"dirscan_{self.parent_tag}"

        # tags
        self.element_entry_tag = f"{self.prefix}_element_entry"
        self.emission_combo_tag = f"{self.prefix}_emission_combo"
        self.channel_display_tag = f"{self.prefix}_channel_display"
        self.read_and_display_button_tag = f"{self.prefix}_read_display_btn"
        self.merge_button_tag = f"{self.prefix}_merge_btn"

        # analyzer
        self.analyzer = XRFAnalyzer()
        self.channel_padding = 10

        self._build_layout()

    # ---------------- UI ----------------
    def _build_layout(self):
        with dpg.group(parent=self.parent_tag):
            with dpg.group(horizontal=True):

                # Left panel
                with dpg.child_window(width=380, height=-1):
                    dpg.add_text("Scan directory for files")

                    dpg.add_radio_button(
                        items=[".h5", ".evt"], default_value=".h5",
                        horizontal=True, callback=self._on_filter_change,
                        tag=f"{self.prefix}_filter"
                    )

                    dpg.add_checkbox(
                        label="Recursive", default_value=True,
                        callback=self._on_recursive_toggle,
                        tag=f"{self.prefix}_recursive"
                    )
                    dpg.add_spacer(height=6)

                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Choose Directory", callback=self._choose_directory)
                        dpg.add_button(label="Scan", callback=self._scan_now)

                    dpg.add_spacer(height=6)
                    dpg.add_text("Directory:")
                    self.dir_label_tag = dpg.add_text("-", wrap=360, tag=f"{self.prefix}_dir_label")

                    dpg.add_spacer(height=8)
                    dpg.add_text("Found files:")
                    self.listbox_tag = dpg.add_listbox(
                        items=[], num_items=10, width=-1,
                        callback=self._on_file_select,
                        tag=f"{self.prefix}_listbox"
                    )

                    dpg.add_spacer(height=6)
                    dpg.add_text("Tick files for merge:")
                    self.merge_table_tag = f"{self.prefix}_merge_table"
                    with dpg.group(tag=self.merge_table_tag):
                        dpg.add_text("No files yet.")

                    dpg.add_spacer(height=10)
                    dpg.add_separator()
                    dpg.add_spacer(height=6)

                    dpg.add_text("Detector channel range from element/line")
                    dpg.add_input_text(
                        label="Element", tag=self.element_entry_tag,
                        width=200, hint="e.g., Fe", on_enter=True,
                        callback=self._on_channel_inputs_changed
                    )

                    dpg.add_combo(
                        label="Emission Line",
                        items=["K_alpha", "K_beta", "K_alpha + K_beta"],
                        default_value="K_alpha", width=200,
                        tag=self.emission_combo_tag,
                        callback=self._on_channel_inputs_changed
                    )

                    dpg.add_input_text(
                        label="Detector Channel",
                        tag=self.channel_display_tag, readonly=True, width=200
                    )

                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="Read & Display",
                            tag=self.read_and_display_button_tag,
                            callback=lambda: self._read_and_display()
                        )
                        dpg.add_button(
                            label="Merge",
                            tag=self.merge_button_tag,
                            callback=lambda: self._merge()
                        )

                # Right panel
                with dpg.child_window(width=-1, height=-1):
                    dpg.add_text("Status & Display")
                    self.status_tag = dpg.add_text("", wrap=1000, tag=f"{self.prefix}_status")

                    dpg.add_spacer(height=6)
                    dpg.add_separator()
                    dpg.add_spacer(height=6)

                    self.display_group_tag = f"{self.prefix}_display_group"
                    with dpg.group(tag=self.display_group_tag):
                        dpg.add_text("No data displayed yet.")

            # directory dialog
            self.dir_dialog_tag = f"{self.prefix}_dir_dialog"
            with dpg.file_dialog(
                directory_selector=True, show=False,
                callback=self._dir_selected_callback,
                tag=self.dir_dialog_tag, width=720, height=440
            ):
                dpg.add_file_extension(".*")

    # ---------------- Actions ----------------
    def _read_and_display(self):
        path = self.get_selected_path()
        if not path:
            self._set_status("⚠️ No file selected.")
            return
        if any(v is None for v in self.channels.values()):
            self._set_status("⚠️ Please select element & emission line.")
            return

        data = HDF5Reader(path).read_2d_data(
            self.channels["ChannelMin"], self.channels["ChannelMax"]
        )

        # normalize to 0..1 RGBA
        norm = (data - data.min()) / (data.max() - data.min() + 1e-9)
        rgba = np.stack([norm, norm, norm, np.ones_like(norm)], axis=-1).astype(np.float32)
        rgba_flat = rgba.flatten()

        # ensure registry exists
        if not dpg.does_item_exist("texture_reg"):
            with dpg.texture_registry(tag="texture_reg"):
                pass

        # delete old texture + alias safely
        if dpg.does_item_exist("texture_main"):
            dpg.remove_alias("texture_main")   # remove alias binding
            dpg.delete_item("texture_main")    # delete the actual texture

        # recreate texture with same alias
        dpg.add_static_texture(
            data.shape[1], data.shape[0],
            rgba_flat, parent="texture_reg", tag="texture_main"
        )

        # clear old plot and rebuild
        dpg.delete_item(self.display_group_tag, children_only=True)
        with dpg.plot(label="2D Map", width=600, height=600, parent=self.display_group_tag):
            xaxis = dpg.add_plot_axis(dpg.mvXAxis, label="X")
            yaxis = dpg.add_plot_axis(dpg.mvYAxis, label="Y")
            dpg.add_image_series("texture_main", [0, 0], [data.shape[1], data.shape[0]], parent=yaxis)
            dpg.set_axis_limits(xaxis, 0, data.shape[1])
            dpg.set_axis_limits(yaxis, 0, data.shape[0])



    def _merge(self):
        
        
        print(self.selected_for_merge)
        
        chosen = [self.file_map[d] for d, tick in self.selected_for_merge.items() if tick]
        
        if not chosen:
            self._set_status("⚠️ No files ticked for merge.")
            return

        raw_all = []
        for path in chosen:
            try:
                raw_all.append(HDF5Reader(path).read_raw())
            except Exception as e:
                self._set_status(f"⚠️ Could not read {path}: {e}")
                return

        try:
            raw_stack = np.stack(raw_all, axis=0)
            sum_data_raw = np.sum(raw_stack, axis=0)
        except Exception as e:
            self._set_status(f"⚠️ Merge failed: {e}")
            return

        with dpg.file_dialog(
            directory_selector=False, show=True,
            callback=lambda s, a: self._save_merged(a, sum_data_raw),
            id=f"{self.prefix}_save_dialog", width=700, height=400
        ):
            dpg.add_file_extension(".h5", color=(0, 255, 0, 255))

    def _save_merged(self, app_data, sum_data_raw):
        save_path = app_data["file_path_name"]
        try:
            HDF5Reader(save_path).save_h5(sum_data_raw)
            self._set_status(f"✅ Merged file saved: {os.path.basename(save_path)}")
        except Exception as e:
            self._set_status(f"⚠️ Save failed: {e}")

    # ---------------- Callbacks ----------------
    def _on_filter_change(self, sender, app_data):
        self.filter_mode = app_data
        self._set_status(f"Filter: {self.filter_mode}")

    def _on_recursive_toggle(self, sender, app_data):
        self.recursive = bool(app_data)
        self._set_status(f"Recursive: {self.recursive}")

    def _choose_directory(self):
        if dpg.does_item_exist(self.dir_dialog_tag):
            dpg.show_item(self.dir_dialog_tag)

    def _dir_selected_callback(self, sender, app_data):
        path = app_data.get("file_path_name")
        if not path or not os.path.isdir(path):
            self._set_status("⚠️ Please select a valid directory.")
            return
        self.selected_dir = os.path.normpath(path)
        dpg.set_value(self.dir_label_tag, self.selected_dir)
        self._scan_now()

    def _scan_now(self):
        if not self.selected_dir:
            self._set_status("⚠️ No directory selected.")
            return
        count = self._scan_directory(self.selected_dir, self.filter_mode, self.recursive)
        self._set_status(f"✅ Found {count} file(s) matching {self.filter_mode} "
                         f"{'(recursive)' if self.recursive else ''}.")

    def _on_file_select(self, sender, app_data):
        display = app_data
        fullpath = self.file_map.get(display)
        if fullpath:
            self._set_status(f"Selected: {display}\nPath: {fullpath}")
        else:
            self._set_status("⚠️ Unknown selection.")

    def _on_channel_inputs_changed(self, *args, **kwargs):
        self._compute_and_display_channels()

    def _compute_and_display_channels(self):
        elem = dpg.get_value(self.element_entry_tag).strip()
        emission_ui = dpg.get_value(self.emission_combo_tag)
        if not elem:
            dpg.set_value(self.channel_display_tag, "Missing element")
            return
        try:
            if emission_ui == "K_alpha":
                ch = self.analyzer.run_find_channel(elem, "Ka1")
                start, end = int(ch - self.channel_padding), int(ch + self.channel_padding)
            elif emission_ui == "K_beta":
                ch = self.analyzer.run_find_channel(elem, "Kb1")
                start, end = int(ch - self.channel_padding), int(ch + self.channel_padding)
            else:
                ch1 = self.analyzer.run_find_channel(elem, "Ka1")
                ch2 = self.analyzer.run_find_channel(elem, "Kb1")
                start = int(min(ch1, ch2) - self.channel_padding)
                end = int(max(ch1, ch2) + self.channel_padding)
        except Exception as e:
            dpg.set_value(self.channel_display_tag, f"Error: {e}")
            return
        self.channels["ChannelMin"], self.channels["ChannelMax"] = start, end
        dpg.set_value(self.channel_display_tag, f"{start} - {end}")

    def _scan_directory(self, directory: str, mode: str, recursive: bool) -> int:
        wanted_ext = mode.lower()
        found_paths: list[str] = []
        if recursive:
            for root, _, files in os.walk(directory):
                for fname in files:
                    if fname.lower().endswith(wanted_ext):
                        found_paths.append(os.path.join(root, fname))
        else:
            try:
                for fname in os.listdir(directory):
                    full = os.path.join(directory, fname)
                    if os.path.isfile(full) and fname.lower().endswith(wanted_ext):
                        found_paths.append(full)
            except PermissionError:
                pass

        self.file_map.clear()
        self.file_list.clear()
        dpg.delete_item(self.merge_table_tag, children_only=True)
        self.selected_for_merge.clear()

        for p in sorted(found_paths):
            base = os.path.basename(p)
            display = base.rsplit(".", 1)[0]
            if display in self.file_map:
                i = 2
                new_disp = f"{display} ({i})"
                while new_disp in self.file_map:
                    i += 1
                    new_disp = f"{display} ({i})"
                display = new_disp
        
            self.file_map[display] = p
            self.file_list.append(display)
            self.selected_for_merge[display] = False
        
            checkbox_tag = f"{self.prefix}_chk_{display}"
        
            dpg.add_checkbox(
                label=display,
                default_value=False,
                tag=checkbox_tag,
                parent=self.merge_table_tag,
                callback=self._on_merge_checkbox
            )


        dpg.configure_item(self.listbox_tag, items=self.file_list)
        return len(self.file_list)
    
    def _on_merge_checkbox(self, sender, app_data):
        value = bool(app_data)
        # extract display name back from tag
        tag = dpg.get_item_label(sender)
        self.selected_for_merge[tag] = value
        self._set_status(f"{tag} -> {'✔ included' if value else '✖ excluded'}")



    # ---------------- Helpers ----------------
    def _set_status(self, msg: str):
        if dpg.does_item_exist(self.status_tag):
            dpg.set_value(self.status_tag, msg)
        else:
            print(msg)

    def get_all_paths(self) -> list[str]:
        return [self.file_map[d] for d in self.file_list]

    def get_selected_path(self) -> str | None:
        disp = dpg.get_value(self.listbox_tag)
        return self.file_map.get(disp) if disp else None
