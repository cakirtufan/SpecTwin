# -*- coding: utf-8 -*-
"""
create_conv_inp.py
Updates XES_inp.txt (convolution input) in-place.
"""

import os


class create_conv_inp:
    def __init__(self, calc_file_path, conv_out_path, gaussian=None, gamma_hole=None):
        self.calc_file_path = str(calc_file_path).replace("\\", "/")
        self.conv_out_path = str(conv_out_path).replace("\\", "/")
        self.gaussian = gaussian
        self.gamma_hole = gamma_hole

    def _replace_block_value(self, lines, keyword, new_value_line):
        kw = keyword.strip().lower()
        out = []
        i = 0
        while i < len(lines):
            out.append(lines[i])
            if lines[i].strip().lower().startswith(kw):
                if i + 1 < len(lines):
                    out.append(f"   {new_value_line}\n")
                    i += 2
                    continue
            i += 1
        return out

    def modify_conv_inp_file(self, xes_input_path):
        if not os.path.isfile(xes_input_path):
            raise FileNotFoundError(f"XES input not found: {xes_input_path}")

        with open(xes_input_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        lines = self._replace_block_value(lines, "Calculation", self.calc_file_path)
        lines = self._replace_block_value(lines, "Conv_out", self.conv_out_path)

        if self.gaussian is not None:
            lines = self._replace_block_value(lines, "Gaussian", str(self.gaussian))
        if self.gamma_hole is not None:
            lines = self._replace_block_value(lines, "Gamma_hole", str(self.gamma_hole))

        with open(xes_input_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"File '{xes_input_path}' modified.")
        print(f"  Calculation -> {self.calc_file_path}")
        print(f"  Conv_out    -> {self.conv_out_path}")
        if self.gaussian is not None:
            print(f"  Gaussian    -> {self.gaussian}")
        if self.gamma_hole is not None:
            print(f"  Gamma_hole  -> {self.gamma_hole}")
