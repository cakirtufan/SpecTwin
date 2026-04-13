# -*- coding: utf-8 -*-
"""
Created on Fri Oct 11 16:19:12 2024

@author: cakir
"""

class create_inp:

    def __init__(
        self,
        edge,
        absorber_Z,
        cif_dir,
        out_dir,
        range_line=None,
        eimag=None,
        radius=None,
        enable_green=None,
        enable_density=None,
        enable_density_all=None,
        enable_quadrupole=None,
        enable_energpho=None,
        
    ):
        self.edge = edge
        self.absorber_Z = absorber_Z
        self.cif_dir = cif_dir
        self.out_dir = out_dir

        # new optional params (None => keep template as-is)
        self.range_line = range_line
        self.eimag = eimag
        self.radius = radius

        self.enable_green = enable_green
        self.enable_density = enable_density
        self.enable_density_all = enable_density
        self.enable_quadrupole = enable_quadrupole
        self.enable_energpho = enable_energpho
	

    def _toggle_keyword(self, modified_lines, keyword, enable):
        """
        enable:
          None -> keep as is (do nothing)
          True -> ensure keyword exists (add if missing at end of file before End)
          False -> remove keyword if present
        """
        return  # placeholder (see logic handled in second pass)

    def modify_inp_file(self, input_file):
        with open(input_file, 'r') as file:
            lines = file.readlines()

        modified_lines = []
        skip_next_line = False

        # Track keyword presence for toggles
        present = {
            "Green": False,
            "Density": False,
            "Density_all": False,
            "Quadrupole": False,
            "Energpho": False,
        }

        # First pass: patch value-block keywords + detect toggles
        for i, line in enumerate(lines):
            stripped = line.strip()

            # detect toggle keywords
            if stripped.lower() == "green":
                present["Green"] = True
            if stripped.lower() == "density":
                present["Density"] = True
            if stripped.lower() == "density_all":
                present["Density_all"] = True
            if stripped.lower() == "quadrupole":
                present["Quadrupole"] = True
            if stripped.lower().startswith("energpho"):
                # Energpho may appear with comment
                present["Energpho"] = True

            if stripped.startswith('Filout'):
                modified_lines.append(' Filout\n')
                modified_lines.append(f' {self.out_dir}\n')
                skip_next_line = True

            elif stripped.startswith('Edge'):
                modified_lines.append(' Edge\n')
                modified_lines.append(f' {self.edge}\n')
                skip_next_line = True

            elif stripped.startswith('Z_absorber'):
                modified_lines.append(' Z_absorber\n')
                modified_lines.append(f' {self.absorber_Z}\n')
                skip_next_line = True

            elif stripped.startswith('Cif_file'):
                modified_lines.append(' Cif_file\n')
                modified_lines.append(f' {self.cif_dir}\n')
                skip_next_line = True

            elif stripped.startswith('Range') and self.range_line is not None:
                modified_lines.append(' Range\n')
                modified_lines.append(f' {self.range_line}\n')
                skip_next_line = True

            elif stripped.startswith('Eimag') and self.eimag is not None:
                modified_lines.append(' Eimag\n')
                modified_lines.append(f' {self.eimag}\n')
                skip_next_line = True

            elif stripped.startswith('Radius') and self.radius is not None:
                modified_lines.append(' Radius\n')
                modified_lines.append(f' {self.radius}\n')
                skip_next_line = True

            elif skip_next_line:
                skip_next_line = False
                continue

            else:
                modified_lines.append(line)

        # Second pass: apply toggles by removing/adding keyword lines
        def should_keep(keyword, enable_flag):
            if enable_flag is None:
                return True  # keep as-is
            return bool(enable_flag)

        toggles = [
            ("Green", self.enable_green),
            ("Density", self.enable_density),
            ("Density_all", self.enable_density_all),
            ("Quadrupole", self.enable_quadrupole),
            ("Energpho", self.enable_energpho),
        ]

        # remove unwanted keywords
        filtered = []
        for line in modified_lines:
            s = line.strip().lower()
            drop = False
            for kw, flag in toggles:
                if flag is False:
                    if kw.lower() == "energpho":
                        if s.startswith("energpho"):
                            drop = True
                    else:
                        if s == kw.lower():
                            drop = True
            if not drop:
                filtered.append(line)

        # add missing wanted keywords before End
        # find "End" line index
        end_idx = None
        for idx, line in enumerate(filtered):
            if line.strip().lower() == "end":
                end_idx = idx
                break

        if end_idx is None:
            end_idx = len(filtered)

        to_insert = []
        for kw, flag in toggles:
            if flag is True:
                if not present.get(kw, False):
                    # add keyword (simple line)
                    if kw == "Energpho":
                        to_insert.append(" Energpho\n")
                    else:
                        to_insert.append(f" {kw}\n")

        # insert just before End
        final_lines = filtered[:end_idx] + to_insert + filtered[end_idx:]

        with open(input_file, 'w') as file:
            file.writelines(final_lines)

        print(f"File '{input_file}' modified.")
