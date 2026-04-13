# -*- coding: utf-8 -*-
"""
fdmnes_executer.py
- Runs EXAFS using rendered EXAFS input via master (fdmfile.txt)
- DOES NOT search for calc_*
- For XES/convolution step, uses:
    Calculation -> <FiloutBase>_last.txt  (fallback: <FiloutBase>.txt)
    Conv_out    -> <FiloutBase>_conv.txt  OR (if conv_out_name given) <FiloutDir>/<conv_out_name>
- Updates XES_inp (Gaussian + Gamma_hole) then runs second step
"""

from create_conv_inp import create_conv_inp
from create_master_inp import create_master_inp
import subprocess
import os, re, glob
import time


class FDMNES_executer:
    def __init__(
        self,
        input_exafs,
        conv_input=None,
        enable_xes=False,
        gaussian=None,
        gamma_hole=None,
        conv_out_name=None,   # <-- FIX: allow passing desired conv out filename/path
        fdmfile_path=None,
        exe_root=None,
        verbose = True
    ):
        self.input_exafs = input_exafs
        self.conv_input = conv_input
        self.enable_xes = bool(enable_xes)
        self.gaussian = gaussian
        self.gamma_hole = gamma_hole

        # NEW: custom conv out naming
        # examples:
        #   conv_out_name="out_conv.txt"        -> <FiloutDir>/out_conv.txt
        #   conv_out_name="C:/.../out_conv.txt" -> exact path used
        self.conv_out_name = conv_out_name

        self.cwd = exe_root if exe_root is not None else os.getcwd()

        self.fdmfile_path = fdmfile_path if fdmfile_path is not None else os.path.join(
            self.cwd, "fdmnes_Win64", "fdmfile.txt"
        )
        self.exe_path = os.path.join(self.cwd, "fdmnes_Win64", "fdmnes_win64.exe")

        # derived after run
        self.filout_base = None            # e.g. ...\jobs\<run>\out\out
        self.main_out = None               # filout_base + ".txt"
        self.last_out = None               # filout_base + "_last.txt" (preferred)
        self.conv_out_from_exafs = None    # default: filout_base + "_conv.txt" OR custom name/path
        self.verbose = bool(verbose)

    # -------------------------
    # helpers
    # -------------------------
    def _read_block_value(self, inp_path, keyword):
        key = keyword.strip().lower()
        try:
            with open(inp_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return None

        for i, line in enumerate(lines):
            if line.strip().lower().startswith(key):
                if i + 1 < len(lines):
                    return lines[i + 1].strip()
        return None

    def _wait_for_file(self, path, timeout_s=120):
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            if os.path.isfile(path) and os.path.getsize(path) > 0:
                return True
            time.sleep(0.5)
        return False

    def _resolve_filout_base(self):
        """
        Filout in rendered EXAFS input must be a BASE path:
          ...\\jobs\\<run>\\out\\<base>

        FDMNES creates (commonly):
          <base>.txt
          <base>_bav.txt
          <base>_last.txt (often)
          <base>_conv.txt (often)

        If conv_out_name is provided:
          - if it's a filename (no dirs): use <FiloutDir>/<conv_out_name>
          - if it's a full path: use it as-is
        """
        filout = self._read_block_value(self.input_exafs, "Filout")
        if not filout:
            raise ValueError("Filout not found in EXAFS input.")

        filout = filout.strip().strip('"').strip("'")
        filout_os = filout.replace("/", "\\") if os.name == "nt" else filout

        self.filout_base = filout_os
        self.main_out = self.filout_base + ".txt"
        self.last_out = self.filout_base + "_last.txt"

        out_dir = os.path.dirname(self.filout_base)

        # default conv out
        default_conv = self.filout_base + "_conv.txt"

        if self.conv_out_name:
            # if absolute path or contains directory parts -> treat as path
            cand = self.conv_out_name.strip().strip('"').strip("'")
            cand_os = cand.replace("/", "\\") if os.name == "nt" else cand

            if os.path.isabs(cand_os) or os.path.dirname(cand_os):
                # full/relative path provided explicitly
                self.conv_out_from_exafs = cand_os
            else:
                # filename only -> put into filout directory
                self.conv_out_from_exafs = os.path.join(out_dir, cand_os)
        else:
            self.conv_out_from_exafs = default_conv

    def _pick_latest_calc_file(self):
        """
        Picks best 'Calculation' file for XES step.

        Priority:
          1) <base>_last.txt if exists
          2) highest numbered <base>_<N>.txt (e.g. out_3.txt)
          3) <base>.txt
        """
        # 1) _last
        if self.last_out and os.path.isfile(self.last_out):
            return self.last_out

        # 2) numbered: <base>_<N>.txt  (but avoid _conv, _bav etc.)
        pattern = self.filout_base + "_*.txt"
        candidates = glob.glob(pattern)

        num_re = re.compile(rf"^{re.escape(self.filout_base)}_(\d+)\.txt$", re.IGNORECASE)

        numbered = []
        for p in candidates:
            m = num_re.match(p)
            if m:
                try:
                    numbered.append((int(m.group(1)), p))
                except Exception:
                    pass

        if numbered:
            numbered.sort(key=lambda t: t[0])
            return numbered[-1][1]

        # 3) plain
        if self.main_out and os.path.isfile(self.main_out):
            return self.main_out

        return self.main_out  # fallback



    def run_simulation(self):
        fdm_dir = os.path.join(self.cwd, "fdmnes_Win64")

        # Run from fdmnes_Win64
        os.chdir(fdm_dir)

        try:
            if self.verbose:
                # LIVE streaming
                p = subprocess.Popen(
                    [self.exe_path],
                    cwd=fdm_dir,
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                for line in p.stdout:
                    print(line, end="")  # already includes newline
                rc = p.wait()
                return rc

            else:
                # quiet mode (capture)
                result = subprocess.run(
                    [self.exe_path],
                    cwd=fdm_dir,
                    shell=False,
                    capture_output=True,
                    text=True
                )
                if result.stdout:
                    print("Output:", result.stdout)
                if result.stderr:
                    print("Error:", result.stderr)
                return result.returncode

        except Exception as e:
            print(f"Failed to start the executable: {e}")
            return -1


    # -------------------------
    # steps
    # -------------------------
    def run_exafs(self):
        # master -> EXAFS input
        master = create_master_inp(self.input_exafs)
        master.modify_master_inp(self.fdmfile_path)

        # --- NEW: resolve Filout BEFORE running and ensure output dir exists ---
        self._resolve_filout_base()

        out_dir = os.path.dirname(self.filout_base)
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        # now run
        rc = self.run_simulation()
        if rc != 0:
            raise RuntimeError(f"FDMNES EXAFS run failed with return code {rc}")

        # Wait for at least main output
        if not self._wait_for_file(self.main_out, timeout_s=30):
            # maybe numbered output
            time.sleep(0.5)

        calc_latest = self._pick_latest_calc_file()
        if not calc_latest or not os.path.isfile(calc_latest) or os.path.getsize(calc_latest) == 0:
            out_dir = os.path.dirname(self.filout_base)
            files = os.listdir(out_dir) if os.path.isdir(out_dir) else []
            raise FileNotFoundError(
                f"No calculation output found.\nExpected one of: {self.main_out} / {self.last_out} / {self.filout_base}_N.txt\n"
                f"Dir: {out_dir}\nFiles: {files[:80]}"
            )

        print(f"[EXAFS] calc chosen (latest): {calc_latest}")

        print(f"[EXAFS] main_out: {self.main_out}")

        if os.path.isfile(self.last_out):
            print(f"[EXAFS] last_out: {self.last_out} (will be used for XES Calculation)")
        else:
            print(f"[EXAFS] last_out not found yet: {self.last_out} (fallback to main_out for XES Calculation)")

        if os.path.isfile(self.conv_out_from_exafs):
            print(f"[EXAFS] conv_out: {self.conv_out_from_exafs} (XANES convolved)")
        else:
            print(f"[EXAFS] conv_out not found yet: {self.conv_out_from_exafs}")

        return self.main_out


    def run_xes(self):
        if not self.enable_xes:
            return None
        if not self.conv_input:
            raise ValueError("enable_xes=True but conv_input is None")
        if not self.filout_base:
            raise RuntimeError("Run EXAFS first.")

        # Use out_last.txt if it exists, else fallback to out.txt
        calc_for_xes = self._pick_latest_calc_file()


        # Conv_out: custom name/path (if provided) else <FiloutBase>_conv.txt
        conv_for_xes = self.conv_out_from_exafs

        cc = create_conv_inp(
            calc_file_path=calc_for_xes,
            conv_out_path=conv_for_xes,
            gaussian=self.gaussian,
            gamma_hole=self.gamma_hole
        )
        cc.modify_conv_inp_file(self.conv_input)

        master = create_master_inp(self.conv_input)
        master.modify_master_inp(self.fdmfile_path)

        rc = self.run_simulation()
        if rc != 0:
            raise RuntimeError(f"FDMNES XES run failed with return code {rc}")

        print(f"[XES] Calculation: {calc_for_xes}")
        print(f"[XES] Conv_out:    {conv_for_xes}")

        return conv_for_xes

    def run(self):
        first = self.run_exafs()
        second = self.run_xes()
        return first, second
