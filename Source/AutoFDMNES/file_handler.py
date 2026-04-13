# -*- coding: utf-8 -*-
"""
FileHandler.py
Moves selected output files from temp folder to results folder, grouped by base name.
"""

import os
import shutil
import glob


class FileHandler:
    def __init__(self, temp_folder, results_folder, patterns=None, clear_all=False):
        """
        temp_folder: where FDMNES writes outputs (e.g. .../out/temp or Filout)
        results_folder: where you want to store organized results (e.g. .../out/jobs/<job_key>/results)
        patterns: list of glob patterns to move
        clear_all: if True, delete everything in temp after moving; if False, delete only matched files
        """
        self.temp_folder = temp_folder
        self.results_folder = results_folder
        self.clear_all = clear_all

        # defaults match your original intent
        self.patterns = patterns or [
            "*_calc_conv.txt",
            "*_photon_conv_calc.txt",
        ]

        os.makedirs(self.results_folder, exist_ok=True)

    def grab_files(self):
        files = []
        for p in self.patterns:
            files.extend(glob.glob(os.path.join(self.temp_folder, p)))
        return sorted(set(files))

    def _base_name(self, file_name):
        """
        Extract base name before known suffixes.
        Example: Bi2O3_photon_conv_calc.txt -> Bi2O3
        """
        suffixes = ["_calc_conv.txt", "_photon_conv_calc.txt"]
        for suf in suffixes:
            if file_name.endswith(suf):
                return file_name[: -len(suf)]
        # fallback: drop extension
        return os.path.splitext(file_name)[0]

    def move_file(self, file_path):
        file_name = os.path.basename(file_path)
        base_name = self._base_name(file_name)

        target_folder = os.path.join(self.results_folder, base_name)
        os.makedirs(target_folder, exist_ok=True)

        target_file_path = os.path.join(target_folder, file_name)

        # overwrite if exists
        if os.path.exists(target_file_path):
            os.remove(target_file_path)

        try:
            shutil.move(file_path, target_file_path)
            print(f"Moved {file_path} -> {target_file_path}")
        except Exception as e:
            print(f"Error moving {file_path}: {e}")

    def clear_temp_folder(self, moved_files=None):
        if self.clear_all:
            files = glob.glob(os.path.join(self.temp_folder, "*"))
        else:
            # only delete what we targeted/moved
            files = moved_files or []

        for file_path in files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

    def process_files(self):
        files = self.grab_files()
        for fp in files:
            self.move_file(fp)
        self.clear_temp_folder(moved_files=files)
