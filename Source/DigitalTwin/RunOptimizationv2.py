# -*- coding: utf-8 -*-
"""
RunOptimizationv2.py

Cleaned version:
- Bayesian optimization (skopt.gp_minimize)
- Random search baseline
- Paired crystal/HKL search space
- JSON export for all iterations and best history
- Objective based only on:
    * target peak separation
    * effective-path-length-related distance penalty
- Invalid mapping -> large penalty
"""

import json
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks, peak_prominences, peak_widths
from skopt import gp_minimize
from skopt.space import Real, Categorical

# Local imports
from CalcDistance import BraggCalculator
from ExperimentBuilder import BeamLineBuilder
from DGPPlotter import DPGPlotter

import plotly.graph_objects as go
import plotly.io as pio


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _norm(x: float, lo: float, hi: float) -> float:
    return _clamp01((float(x) - lo) / (hi - lo + 1e-12))


class PixelDiffOptimizer:
    """
    Peak selection logic:
      - smoothed 1D spectrum
      - half-max clustering with threshold sweep
      - optional fallback via prominence search
      - strict target mapping (no extreme-peaks fallback)

    Objective:
      score = peak_score - dist_pen
      objective = -score

    Search:
      - Bayesian optimization via gp_minimize
      - random search baseline
    """

    def __init__(
        self,
        crystals,
        hkls,
        distance_bounds,
        crystal_hkl_pairs=None,
        energies=None,              # backward compatibility
        sim_energies=None,          # full energies used in simulation
        target_energies=None,       # subset used for optimization
        repeats=100,
        # Smoothing
        smooth_sigma=0.5,
        # Halfmax clustering
        halfmax_max_gap=3,
        halfmax_fracs=(0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2),
        # Fallback peaks on smooth
        prom_frac_fallback=0.01,
        prom_frac_fallback2=0.002,
        # Separation score
        w_sep=1.0,
        # Distance penalty
        w_dist=0.60,
        dist_power=2.0,
        # Normalization ranges
        expected_dx=(5, 400),
        # Plot controls
        enable_best_plots=True,
        plot_container="graph_window",
        plotly_in_browser=False,
    ):
        self.distance_bounds = tuple(float(x) for x in distance_bounds)

        # --- crystal list (legacy / optional) ---
        self.crystals = [str(c.item() if hasattr(c, "item") else c) for c in list(crystals)]

        # --- HKL list (legacy / optional) ---
        norm_hkls = []
        for h in list(hkls):
            if isinstance(h, np.ndarray):
                h = h.tolist()
            if isinstance(h, (list, tuple)) and len(h) == 3:
                norm_hkls.append(tuple(int(x) for x in h))
            elif isinstance(h, str):
                s = h.replace(" ", ",")
                parts = [p.strip() for p in s.split(",") if p.strip() != ""]
                if len(parts) != 3:
                    raise ValueError(f"Invalid HKL string: {h!r} (expected 'h,k,l')")
                norm_hkls.append(tuple(int(p) for p in parts))
            else:
                raise ValueError(f"Invalid HKL entry: {h!r} (type={type(h)})")

        seen = set()
        self.hkls = []
        for t in norm_hkls:
            if t not in seen:
                seen.add(t)
                self.hkls.append(t)

        # --- paired crystal/HKL search space ---
        self.crystal_hkl_pairs = []
        if crystal_hkl_pairs:
            seen_pairs = set()
            for crystal, hkl in crystal_hkl_pairs:
                crystal = str(crystal.item() if hasattr(crystal, "item") else crystal)

                if isinstance(hkl, np.ndarray):
                    hkl = hkl.tolist()

                if isinstance(hkl, str):
                    s = hkl.replace(" ", ",")
                    parts = [p.strip() for p in s.split(",") if p.strip() != ""]
                    if len(parts) != 3:
                        raise ValueError(f"Invalid HKL string in pair: {hkl!r}")
                    hkl = tuple(int(p) for p in parts)
                else:
                    if not isinstance(hkl, (list, tuple)) or len(hkl) != 3:
                        raise ValueError(f"Invalid HKL in pair: {hkl!r}")
                    hkl = tuple(int(x) for x in hkl)

                pair = (crystal, hkl)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    self.crystal_hkl_pairs.append(pair)

        # --- energies ---
        if sim_energies is None and target_energies is None:
            if energies is None:
                raise ValueError("Provide either energies=... or (sim_energies=..., target_energies=...).")
            sim_energies = energies
            target_energies = energies

        if sim_energies is None or target_energies is None:
            raise ValueError("Both sim_energies and target_energies must be provided (or use energies=...).")

        self.sim_energies = np.asarray(sorted(sim_energies), dtype=float)
        self.target_energies = np.asarray(sorted(target_energies), dtype=float)

        if len(self.sim_energies) < 2:
            raise ValueError("sim_energies must contain at least 2 energies.")
        if len(self.target_energies) < 2:
            raise ValueError("target_energies must contain at least 2 energies.")
        if len(self.target_energies) > len(self.sim_energies):
            raise ValueError("target_energies cannot be longer than sim_energies.")

        self.mean_energy = float(np.mean(self.sim_energies))
        self.repeats = int(repeats)

        # strict mapping target indices inside sim energies
        def _find_indices(simE, targetE, tol=1e-3):
            idxs = []
            for te in targetE:
                j = int(np.argmin(np.abs(simE - te)))
                if abs(simE[j] - te) > tol:
                    return None
                idxs.append(j)
            return idxs

        self._target_indices_in_sim = _find_indices(self.sim_energies, self.target_energies, tol=1e-3)
        if self._target_indices_in_sim is None:
            raise ValueError(
                "target_energies must be contained in sim_energies (within tol=1e-3 eV) for strict mapping."
            )

        # --- parameters ---
        self.smooth_sigma = float(smooth_sigma)
        self.halfmax_max_gap = int(halfmax_max_gap)
        self.halfmax_fracs = tuple(float(x) for x in halfmax_fracs)

        self.prom_frac_fallback = float(prom_frac_fallback)
        self.prom_frac_fallback2 = float(prom_frac_fallback2)

        self.w_sep = float(w_sep)
        self.w_dist = float(w_dist)
        self.dist_power = float(dist_power)

        self.expected_dx = expected_dx

        self.enable_best_plots = bool(enable_best_plots)
        self.plot_container = plot_container
        self.plotly_in_browser = bool(plotly_in_browser)

        # bookkeeping
        self.best_obj = np.inf
        self.best_payload = None

        self.history = []       # only new bests
        self.all_history = []   # every iteration
        self.best_history = []  # best-so-far progression

        self._convergence_plotter = None
        self._iter_counter = 0
        self._best_seen = np.inf
        self._best_update_callback = None

        # run metadata
        self._last_search_method = None
        self._last_random_state = None
        self._last_acq_func = None
        self._last_kappa = None
        self._last_n_calls = None
        self._last_n_initial_points = None

        # compute global normalization bounds for effective path length
        self.expected_eff_dist = self._compute_expected_eff_dist_bounds()
        print(
            "expected_eff_min", float(self.expected_eff_dist[0]),
            "expected_eff_max", float(self.expected_eff_dist[1]),
            flush=True
        )

    # ------------------------------------------------------------------
    # callbacks / helpers
    # ------------------------------------------------------------------
    def set_best_update_callback(self, callback):
        self._best_update_callback = callback

    def set_convergence_plotter(self, plotter_callable):
        self._convergence_plotter = plotter_callable
        self._iter_counter = 0
        self._best_seen = np.inf

    def _on_iter(self, result):
        try:
            y_current = float(result.func_vals[-1])
            if y_current < self._best_seen:
                self._best_seen = y_current
            self._iter_counter += 1
            if self._convergence_plotter is not None:
                self._convergence_plotter(self._iter_counter, y_current, float(self._best_seen))
        except Exception:
            return

    def _pair_to_str(self, pair):
        crystal, hkl = pair
        return f"{crystal}|{hkl[0]},{hkl[1]},{hkl[2]}"

    def _pair_str_to_tuple(self, s):
        crystal, hkl_str = str(s).split("|")
        parts = [p.strip() for p in hkl_str.split(",") if p.strip() != ""]
        if len(parts) != 3:
            raise ValueError(f"Bad pair category string: {s!r}")
        return crystal, [int(parts[0]), int(parts[1]), int(parts[2])]

    def _to_json_friendly(self, obj):
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (list, tuple)):
            return [self._to_json_friendly(x) for x in obj]
        if isinstance(obj, dict):
            return {str(k): self._to_json_friendly(v) for k, v in obj.items()}
        return str(obj)

    def _make_iteration_record(self, iteration_number, obj, distance, crystal, hkl, payload):
        record = {
            "iter": int(iteration_number),
            "objective": float(obj),
            "distance": float(distance),
            "crystal": str(crystal),
            "hkl": [int(x) for x in hkl],
            "valid_payload": payload is not None,
        }

        if payload is not None:
            record.update({
                "coverage": float(payload.get("coverage", 0.0)),
                "halfmax_thr": float(payload["halfmax_thr"]) if payload.get("halfmax_thr") is not None else None,
                "halfmax_best_frac": float(payload["halfmax_best_frac"]) if payload.get("halfmax_best_frac") is not None else None,
                "halfmax_clusters": self._to_json_friendly(payload.get("halfmax_clusters")),
                "visible_peaks": self._to_json_friendly(payload.get("visible_peaks")),
                "chosen_peaks": self._to_json_friendly(payload.get("chosen_peaks")),
                "metrics": self._to_json_friendly(payload.get("metrics")),
                "debug": self._to_json_friendly(payload.get("debug")),
                "pixel": self._to_json_friendly(payload.get("pixel")),
                "y_raw": self._to_json_friendly(payload.get("y_raw")),
                "y_s": self._to_json_friendly(payload.get("y_s")),
            })
        else:
            record.update({
                "coverage": None,
                "halfmax_thr": None,
                "halfmax_best_frac": None,
                "halfmax_clusters": None,
                "visible_peaks": None,
                "chosen_peaks": None,
                "metrics": None,
                "debug": None,
                "pixel": None,
                "y_raw": None,
                "y_s": None,
            })

        return record

    def _compute_expected_eff_dist_bounds(self):
        pairs = []

        if len(self.crystal_hkl_pairs) > 0:
            pairs = self.crystal_hkl_pairs
        else:
            for c in self.crystals:
                for h in self.hkls:
                    pairs.append((c, h))

        if len(pairs) == 0:
            raise ValueError("No crystal/HKL combinations available to compute effective distance bounds.")

        theta_vals = []

        for crystal, hkl in pairs:
            try:
                bragg = BraggCalculator(self.mean_energy, self.distance_bounds[0], crystal, list(hkl))
                theta, _ = bragg.main()
                theta_vals.append(float(theta))
            except Exception:
                continue

        if len(theta_vals) == 0:
            raise ValueError("Could not compute any theta values for effective distance bounds.")

        theta_min = min(theta_vals)
        theta_max = max(theta_vals)

        eff_min = float(self.distance_bounds[0]) / (np.cos(theta_min) + 1e-12)
        eff_max = float(self.distance_bounds[-1]) / (np.cos(theta_max) + 1e-12)

        return (eff_min, eff_max)

    # ------------------------------------------------------------------
    # peak detection helpers
    # ------------------------------------------------------------------
    def _augment_visible_within_clusters(self, y_s, clusters, reps, min_prom_frac=0.01, max_per_cluster=3):
        y_s = np.asarray(y_s, dtype=float)
        mx = float(np.max(y_s)) if len(y_s) else 0.0
        if mx <= 0:
            return np.asarray(reps, dtype=int)

        prom_thr = mx * float(min_prom_frac)
        out = set(int(r) for r in reps)

        for (a, b) in clusters:
            a, b = int(a), int(b)
            if b - a < 3:
                continue
            seg = y_s[a:b+1]
            pk, props = find_peaks(seg, prominence=prom_thr)
            if len(pk) == 0:
                continue

            pk = pk.astype(int) + a
            prom = props.get("prominences", np.ones_like(pk, dtype=float))

            take = np.argsort(prom)[-min(max_per_cluster, len(pk)):]
            for p in pk[take]:
                out.add(int(p))

        return np.array(sorted(out), dtype=int)

    def _halfmax_clusters(self, y, frac=0.5, max_gap=3):
        y = np.asarray(y, dtype=float)
        mx = float(np.max(y)) if len(y) else 0.0
        if mx <= 0:
            return [], [], 0.0

        thr = mx * float(frac)
        idx = np.where(y >= thr)[0]
        if len(idx) == 0:
            return [], [], thr

        clusters = []
        s = int(idx[0])
        prev = int(idx[0])

        for k in idx[1:]:
            k = int(k)
            if k - prev <= max_gap:
                prev = k
            else:
                clusters.append((s, prev))
                s = k
                prev = k
        clusters.append((s, prev))

        reps = []
        for a, b in clusters:
            seg = y[a:b+1]
            reps.append(int(a + np.argmax(seg)))

        return clusters, reps, thr

    def _visible_peaks_by_threshold_sweep(self, y_s, M_expected):
        best = None

        for frac in self.halfmax_fracs:
            clusters, reps, thr = self._halfmax_clusters(y_s, frac=frac, max_gap=self.halfmax_max_gap)
            reps = np.array(sorted(reps), dtype=int)
            k = len(reps)
            if k < 2:
                continue

            score = abs(k - M_expected) + 0.05 * (1.0 - frac)
            if best is None or score < best[0]:
                best = (score, reps, frac, thr, clusters)

        if best is None:
            return np.array([], dtype=int), None, None, []

        _, reps, frac, thr, clusters = best
        return reps, frac + 0.06, thr, clusters

    def _peaks_by_prominence(self, y_s, prom_frac):
        mx = float(np.max(y_s)) if len(y_s) else 0.0
        if mx <= 0:
            return np.array([], dtype=int), np.array([], dtype=float), 0.0
        prom_thr = mx * float(prom_frac)
        peaks, props = find_peaks(y_s, prominence=prom_thr)
        prom = props.get("prominences", np.ones_like(peaks, dtype=float))
        return peaks.astype(int), prom.astype(float), prom_thr

    @staticmethod
    def _select_M_strongest_ordered(peaks, y_s, M):
        peaks = np.asarray(peaks, dtype=int)
        if len(peaks) <= M:
            return np.sort(peaks)
        heights = np.array([y_s[int(p)] for p in peaks], dtype=float)
        top = np.argsort(heights)[-M:]
        return np.sort(peaks[top]).astype(int)

    def _choose_target_peaks_strict(self, visible_peaks_sorted):
        visible = np.asarray(visible_peaks_sorted, dtype=int)
        K = int(len(visible))
        if K < 2:
            return None

        M = int(len(self.sim_energies))
        idxs = self._target_indices_in_sim
        if idxs is None or len(idxs) < 2:
            return None

        i1, i2 = int(idxs[0]), int(idxs[1])

        def map_idx(i_sim: int) -> int:
            if M == 1:
                return 0
            return int(np.clip(np.round(i_sim * (K - 1) / (M - 1)), 0, K - 1))

        j1 = map_idx(i1)
        j2 = map_idx(i2)

        if j1 == j2:
            if j2 < K - 1:
                j2 += 1
            elif j1 > 0:
                j1 -= 1
            else:
                return None

        p1 = int(visible[min(j1, j2)])
        p2 = int(visible[max(j1, j2)])

        if p2 <= p1:
            return None

        return np.array([p1, p2], dtype=int)

    def _compute_metrics(self, y_s, visible_peaks_sorted, chosen_peaks, coverage):
        y_s = np.asarray(y_s, dtype=float)
        visible_peaks_sorted = np.asarray(visible_peaks_sorted, dtype=int)
        chosen_peaks = np.asarray(chosen_peaks, dtype=int)

        if len(chosen_peaks) < 2:
            return None

        p1, p2 = int(chosen_peaks[0]), int(chosen_peaks[1])
        deltaX = float(p2 - p1)
        if deltaX <= 0 or not np.isfinite(deltaX):
            return None

        prom_vals, _, _ = peak_prominences(y_s, chosen_peaks)
        mean_prom = float(np.mean(prom_vals)) if len(prom_vals) else 0.0

        baseline = float(np.median(y_s))
        noise = float(np.std(y_s - baseline)) + 1e-12
        peak_h = float((y_s[p1] + y_s[p2]) / 2.0)
        snr = float(max(0.0, peak_h - baseline) / noise)

        dE = float(self.target_energies[1] - self.target_energies[0])
        pixel_diff = float(dE / deltaX)

        return {
            "visible_peaks": visible_peaks_sorted,
            "chosen_peaks": np.array([p1, p2], dtype=int),
            "deltaX": deltaX,
            "mean_prom": mean_prom,
            "snr": snr,
            "pixel_diff": pixel_diff,
            "coverage": float(coverage),
            "baseline": baseline,
            "noise": noise,
        }

    # ------------------------------------------------------------------
    # score
    # ------------------------------------------------------------------
    def _score(self, distance, metrics, theta):
        if metrics is None:
            return 1e6, None

        dx_n = _norm(metrics["deltaX"], self.expected_dx[0], self.expected_dx[1])
        peak_score = self.w_sep * dx_n

        eff_dist = float(distance) / (np.cos(theta) + 1e-12)
        d_n = _norm(eff_dist, self.expected_eff_dist[0], self.expected_eff_dist[1])
        dist_pen = self.w_dist * (d_n ** self.dist_power)

        score = peak_score - dist_pen
        obj = -score

        debug = {
            "dx_n": dx_n,
            "peak_score": peak_score,
            "dist_pen": dist_pen,
            "score": score,
            "theta": float(theta),
            "eff_dist": float(eff_dist),
            "expected_eff_min": float(self.expected_eff_dist[0]),
            "expected_eff_max": float(self.expected_eff_dist[1]),
        }
        return obj, debug

    # ------------------------------------------------------------------
    # simulation run
    # ------------------------------------------------------------------
    def run_experiment(self, distance, crystal, hkl, allow_plot=False):
        if isinstance(hkl, tuple):
            hkl = list(hkl)

        bragg = BraggCalculator(self.mean_energy, distance, crystal, hkl)
        theta, c = bragg.main()

        builder = BeamLineBuilder(crystal, distance, c, theta, self.repeats, self.sim_energies, hkl)
        builder.run_simulation()

        pixel = np.arange(len(builder.histo1Dx))
        y_raw = np.asarray(builder.histo1Dx, dtype=float)
        y_s = gaussian_filter1d(y_raw, sigma=self.smooth_sigma)

        mx = float(np.max(y_s)) if len(y_s) else 0.0
        if mx <= 0:
            print("[signal] mx<=0 -> no signal", flush=True)
            return 1e6, None

        M = int(len(self.sim_energies))

        visible, best_frac, thr, clusters = self._visible_peaks_by_threshold_sweep(y_s, M_expected=M)

        visible = self._augment_visible_within_clusters(
            y_s,
            clusters=clusters,
            reps=visible,
            min_prom_frac=self.prom_frac_fallback2,
            max_per_cluster=3,
        )
        print(f"[visible+aug] visible={visible.tolist()} (K={len(visible)})", flush=True)

        n_visible = len(visible)
        coverage = n_visible / max(1, M)

        print(
            f"[halfmax-sweep] best_frac={best_frac} thr={thr:.3f} clusters={n_visible} "
            f"reps={visible.tolist()} (coverage={coverage:.2f}, M={M})",
            flush=True
        )

        if len(visible) > M:
            visible = self._select_M_strongest_ordered(visible, y_s, M)
            n_visible = len(visible)
            coverage = n_visible / max(1, M)
            print(f"[halfmax-sweep] reduced visible->M (strongest ordered): {visible.tolist()}", flush=True)

        if n_visible < 2:
            peaks1, _, thr1 = self._peaks_by_prominence(y_s, self.prom_frac_fallback)
            if len(peaks1) < 2:
                peaks2, _, thr2 = self._peaks_by_prominence(y_s, self.prom_frac_fallback2)
                peaks_use, thr_use = peaks2, thr2
            else:
                peaks_use, thr_use = peaks1, thr1

            if len(peaks_use) < 2:
                print("[fallback] still <2 peaks -> penalize", flush=True)
                return 1e6, None

            visible = np.sort(peaks_use).astype(int)

            if len(visible) > M:
                visible = self._select_M_strongest_ordered(visible, y_s, M)

            n_visible = len(visible)
            coverage = n_visible / max(1, M)

            print(
                f"[fallback] thr={thr_use:.3f} peaks={visible.tolist()} (coverage={coverage:.2f})",
                flush=True
            )

        chosen = self._choose_target_peaks_strict(visible)
        print(
            f"[choose] M={M}, K={len(visible)}, target_idxs={self._target_indices_in_sim}, "
            f"chosen={chosen.tolist() if chosen is not None else None}",
            flush=True
        )

        if chosen is None:
            print("[choose] could not choose 2 target peaks -> penalize", flush=True)
            return 1e6, None

        metrics = self._compute_metrics(y_s, visible, chosen, coverage)
        if metrics is None:
            print("[metrics] metrics=None", flush=True)
            return 1e6, None

        obj, debug = self._score(distance, metrics, theta)

        payload = {
            "distance": float(distance),
            "crystal": crystal,
            "hkl": hkl,
            "pixel": pixel,
            "y_raw": y_raw,
            "y_s": y_s,
            "halfmax_thr": float(thr) if thr is not None else None,
            "halfmax_best_frac": best_frac,
            "halfmax_clusters": clusters,
            "visible_peaks": visible,
            "chosen_peaks": chosen,
            "coverage": float(coverage),
            "metrics": metrics,
            "debug": debug,
            "builder": builder,
        }

        if allow_plot and self.enable_best_plots:
            self._plot_payload(payload)

        return float(obj), payload

    # ------------------------------------------------------------------
    # plotting
    # ------------------------------------------------------------------
    def _plot_payload(self, payload):
        builder = payload["builder"]

        plotter = DPGPlotter(
            builder.total2D,
            builder.total1DX,
            builder.total1DZ,
            builder.total1DEnergy,
            builder.total1DEnergy_limits,
            builder.histo1Dx,
        )
        plotter.plot(self.plot_container)

        if self.plotly_in_browser:
            pio.renderers.default = "browser"

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=payload["pixel"], y=payload["y_raw"], mode="lines", name="Raw intensity"))
        fig.add_trace(go.Scatter(x=payload["pixel"], y=payload["y_s"], mode="lines", name="Smoothed intensity"))

        thr = payload.get("halfmax_thr", None)
        if thr is not None and np.isfinite(thr):
            fig.add_trace(
                go.Scatter(
                    x=[payload["pixel"][0], payload["pixel"][-1]],
                    y=[thr, thr],
                    mode="lines",
                    name=f"thr (best_frac={payload.get('halfmax_best_frac')})",
                )
            )

        vis = payload.get("visible_peaks", [])
        if vis is not None and len(vis) > 0:
            fig.add_trace(
                go.Scatter(
                    x=vis,
                    y=[payload["y_s"][int(p)] for p in vis],
                    mode="markers",
                    name="Visible peaks",
                )
            )

        ch = payload.get("chosen_peaks", None)
        if ch is not None and len(ch) >= 2:
            fig.add_trace(
                go.Scatter(
                    x=[int(ch[0]), int(ch[1])],
                    y=[payload["y_s"][int(ch[0])], payload["y_s"][int(ch[1])]],
                    mode="markers",
                    name="Chosen target peaks",
                )
            )

        fig.show()

    # ------------------------------------------------------------------
    # internal reset before a new search
    # ------------------------------------------------------------------
    def _reset_search_state(self):
        self.best_obj = np.inf
        self.best_payload = None
        self.history = []
        self.all_history = []
        self.best_history = []

        self._last_search_method = None
        self._last_random_state = None
        self._last_acq_func = None
        self._last_kappa = None
        self._last_n_calls = None
        self._last_n_initial_points = None

    # ------------------------------------------------------------------
    # bayesian optimization
    # ------------------------------------------------------------------
    def optimize(
        self,
        n_calls=20,
        include_crystal=True,
        include_hkl=True,
        verbose=True,
        auto_export_json=False,
        export_filename="optimization_results.json",
        random_state=42,
        acq_func="LCB",
        kappa=1.96,
        n_initial_points=5,
    ):
        self._reset_search_state()

        self._last_search_method = "bayesian_optimization"
        self._last_random_state = random_state
        self._last_acq_func = acq_func
        self._last_kappa = float(kappa) if kappa is not None else None
        self._last_n_calls = int(n_calls)
        self._last_n_initial_points = int(n_initial_points)

        def _safe_crystals(items):
            out = []
            for c in items:
                if isinstance(c, np.ndarray):
                    c = c.tolist()
                if isinstance(c, (list, tuple)):
                    c = "_".join(str(x) for x in c)
                if isinstance(c, np.generic):
                    c = c.item()
                out.append(str(c))
            return list(dict.fromkeys(out))

        def _hkl_to_str(h):
            if isinstance(h, np.ndarray):
                h = h.tolist()
            if isinstance(h, str):
                s = h.replace(" ", ",")
                parts = [p.strip() for p in s.split(",") if p.strip() != ""]
                if len(parts) != 3:
                    raise ValueError(f"Invalid HKL string: {h!r}")
                hh = [int(p) for p in parts]
                return f"{hh[0]},{hh[1]},{hh[2]}"
            if not isinstance(h, (list, tuple)) or len(h) != 3:
                raise ValueError(f"Invalid HKL entry: {h!r} (type={type(h)})")
            hh = []
            for x in h:
                if isinstance(x, np.generic):
                    x = x.item()
                if isinstance(x, np.ndarray):
                    x = np.asarray(x).flatten()[0].item()
                hh.append(int(x))
            return f"{hh[0]},{hh[1]},{hh[2]}"

        def _hkl_str_to_list(s):
            parts = [p.strip() for p in str(s).split(",") if p.strip() != ""]
            if len(parts) != 3:
                raise ValueError(f"Bad HKL category string: {s!r}")
            return [int(parts[0]), int(parts[1]), int(parts[2])]

        crystals_safe = _safe_crystals(self.crystals)
        hkls_safe_str = list(dict.fromkeys(_hkl_to_str(h) for h in self.hkls))

        use_pairs = len(self.crystal_hkl_pairs) > 0

        if verbose:
            print("[search] method:", self._last_search_method, flush=True)
            print("[search] random_state:", random_state, flush=True)
            print("[search] acq_func:", acq_func, flush=True)
            print("[search] kappa:", kappa, flush=True)
            print("[search] n_calls:", n_calls, flush=True)
            print("[search] n_initial_points:", n_initial_points, flush=True)
            print("[search] mode:", "paired crystal/hkl" if use_pairs else "independent crystal + hkl", flush=True)
            if use_pairs:
                print("[search] pairs:", [self._pair_to_str(p) for p in self.crystal_hkl_pairs], flush=True)
            else:
                print("[search] crystals:", crystals_safe, flush=True)
                print("[search] hkls:", hkls_safe_str, flush=True)
            print("[energies] sim:", self.sim_energies.tolist(), flush=True)
            print("[energies] target:", self.target_energies.tolist(), flush=True)
            print("[mapping] target idx in sim:", self._target_indices_in_sim, flush=True)

        space = [Real(self.distance_bounds[0], self.distance_bounds[-1], name="distance")]
        if use_pairs:
            pair_space = [self._pair_to_str(p) for p in self.crystal_hkl_pairs]
            space.append(Categorical(pair_space, name="crystal_hkl_pair"))
        else:
            if include_crystal:
                space.append(Categorical(crystals_safe, name="crystal"))
            if include_hkl:
                space.append(Categorical(hkls_safe_str, name="hkl"))

        def objective(params):
            try:
                distance = float(params[0])

                if use_pairs:
                    crystal, hkl = self._pair_str_to_tuple(params[1])
                else:
                    if include_crystal and include_hkl:
                        crystal = params[1]
                        hkl = _hkl_str_to_list(params[2])
                    elif include_crystal:
                        crystal = params[1]
                        hkl = _hkl_str_to_list(hkls_safe_str[0])
                    elif include_hkl:
                        crystal = crystals_safe[0]
                        hkl = _hkl_str_to_list(params[1])
                    else:
                        crystal = crystals_safe[0]
                        hkl = _hkl_str_to_list(hkls_safe_str[0])

                obj, payload = self.run_experiment(distance, crystal, hkl, allow_plot=False)

                iter_record = self._make_iteration_record(
                    iteration_number=len(self.all_history) + 1,
                    obj=obj,
                    distance=distance,
                    crystal=crystal,
                    hkl=hkl,
                    payload=payload,
                )
                self.all_history.append(iter_record)

                if payload is not None and obj < self.best_obj:
                    self.best_obj = obj
                    self.best_payload = payload

                    best_record = {
                        "iter": len(self.all_history),
                        "obj": float(obj),
                        "score": float(payload["debug"]["score"]) if payload.get("debug") else None,
                        "distance": float(payload["distance"]),
                        "crystal": payload.get("crystal"),
                        "hkl": payload.get("hkl"),
                        "chosen_peaks": payload.get("chosen_peaks").tolist() if payload.get("chosen_peaks") is not None else None,
                        "coverage": float(payload.get("coverage", 0.0)),
                        "pixel_diff": float(payload["metrics"]["pixel_diff"]) if payload.get("metrics") else None,
                        "deltaX": float(payload["metrics"]["deltaX"]) if payload.get("metrics") else None,
                    }
                    self.history.append(best_record)
                    self.best_history.append(best_record)

                    if self._best_update_callback is not None and self.best_payload is not None:
                        try:
                            self._best_update_callback(self.best_payload)
                        except Exception as e:
                            print("[best_update_callback] failed:", e, flush=True)

                    if self.enable_best_plots:
                        self._plot_payload(payload)

                if verbose and payload is not None and payload.get("metrics") is not None:
                    m = payload["metrics"]
                    d = payload["debug"]
                    print("\n=== Bayesian Optimization Iteration ===", flush=True)
                    print(f"Iteration    : {len(self.all_history)}", flush=True)
                    print(f"Distance     : {payload['distance']}", flush=True)
                    print(f"Crystal      : {payload['crystal']}", flush=True)
                    print(f"hkl          : {payload['hkl']}", flush=True)
                    print(f"Visible peaks: {payload['visible_peaks'].tolist()} (coverage={payload['coverage']:.2f})", flush=True)
                    print(f"Chosen peaks : {payload['chosen_peaks'].tolist()}", flush=True)
                    print(f"deltaX(px)   : {m['deltaX']:.3f} | pixel_diff(eV/px): {m['pixel_diff']:.6f}", flush=True)
                    print(f"peak_score   : {d['peak_score']:.4f} | dist_pen: {d['dist_pen']:.4f}", flush=True)
                    print(f"score        : {d['score']:.4f} | objective: {obj:.6f}", flush=True)

                return float(obj)

            except Exception as e:
                print("Experiment failed:", e, flush=True)
                return 1e6

        res = gp_minimize(
            objective,
            space,
            n_calls=n_calls,
            n_initial_points=n_initial_points,
            random_state=random_state,
            callback=[self._on_iter],
            acq_func=acq_func,
            kappa=kappa,
        )

        print("\n=== Bayesian Optimization Results ===", flush=True)
        idx = 0
        print(f"Best Distance : {res.x[idx]:.3f}", flush=True)
        idx += 1

        if use_pairs:
            best_crystal, best_hkl = self._pair_str_to_tuple(res.x[idx])
            print(f"Best Crystal  : {best_crystal}", flush=True)
            print(f"Best hkl      : {best_hkl}", flush=True)
        else:
            if include_crystal:
                print(f"Best Crystal  : {res.x[idx]}", flush=True)
                idx += 1
            if include_hkl:
                print(f"Best hkl      : {res.x[idx]}", flush=True)

        print(f"Best objective: {res.fun:.6f}", flush=True)

        if self.best_payload is not None and self.best_payload.get("metrics") is not None:
            d = self.best_payload["debug"]
            m = self.best_payload["metrics"]
            print(
                f"Best score    : {d['score']:.6f} "
                f"(peak_score={d['peak_score']:.6f}, dist_pen={d['dist_pen']:.6f})",
                flush=True
            )
            print(f"Best deltaX   : {m['deltaX']:.3f} px", flush=True)
            print(f"Best coverage : {self.best_payload.get('coverage', 0.0):.2f}", flush=True)

        if auto_export_json:
            self.export_results_to_json(export_filename)

        return {
            "res": res,
            "best_obj": self.best_obj,
            "best_payload": self.best_payload,
            "all_history": self.all_history,
            "best_history": self.best_history,
            "random_state": random_state,
            "acq_func": acq_func,
            "kappa": kappa,
            "n_calls": n_calls,
            "n_initial_points": n_initial_points,
        }

    # ------------------------------------------------------------------
    # random search baseline
    # ------------------------------------------------------------------
    def random_search(
        self,
        n_calls=15,
        verbose=True,
        auto_export_json=True,
        export_filename="random_search_results.json",
        random_state=42,
    ):
        self._reset_search_state()

        self._last_search_method = "random_search"
        self._last_random_state = random_state
        self._last_acq_func = None
        self._last_kappa = None
        self._last_n_calls = int(n_calls)
        self._last_n_initial_points = None

        rng = np.random.default_rng(random_state)
        use_pairs = len(self.crystal_hkl_pairs) > 0

        if verbose:
            print("[search] method:", self._last_search_method, flush=True)
            print("[search] random_state:", random_state, flush=True)
            print("[search] n_calls:", n_calls, flush=True)

        for i in range(n_calls):
            distance = float(rng.uniform(self.distance_bounds[0], self.distance_bounds[-1]))

            if use_pairs:
                crystal, hkl = self.crystal_hkl_pairs[int(rng.integers(0, len(self.crystal_hkl_pairs)))]
                hkl = list(hkl)
            else:
                if len(self.crystals) == 0 or len(self.hkls) == 0:
                    raise ValueError("Random search needs either crystal_hkl_pairs or non-empty crystals and hkls.")
                crystal = self.crystals[int(rng.integers(0, len(self.crystals)))]
                hkl = list(self.hkls[int(rng.integers(0, len(self.hkls)))])

            try:
                obj, payload = self.run_experiment(distance, crystal, hkl, allow_plot=False)

                iter_record = self._make_iteration_record(
                    iteration_number=i + 1,
                    obj=obj,
                    distance=distance,
                    crystal=crystal,
                    hkl=hkl,
                    payload=payload,
                )
                self.all_history.append(iter_record)

                if payload is not None and obj < self.best_obj:
                    self.best_obj = obj
                    self.best_payload = payload

                    best_record = {
                        "iter": i + 1,
                        "obj": float(obj),
                        "score": float(payload["debug"]["score"]) if payload.get("debug") else None,
                        "distance": float(payload["distance"]),
                        "crystal": payload.get("crystal"),
                        "hkl": payload.get("hkl"),
                        "chosen_peaks": payload.get("chosen_peaks").tolist() if payload.get("chosen_peaks") is not None else None,
                        "coverage": float(payload.get("coverage", 0.0)),
                        "pixel_diff": float(payload["metrics"]["pixel_diff"]) if payload.get("metrics") else None,
                        "deltaX": float(payload["metrics"]["deltaX"]) if payload.get("metrics") else None,
                    }
                    self.history.append(best_record)
                    self.best_history.append(best_record)

                    if self._best_update_callback is not None and self.best_payload is not None:
                        try:
                            self._best_update_callback(self.best_payload)
                        except Exception as e:
                            print("[best_update_callback] failed:", e, flush=True)

                    if self.enable_best_plots:
                        self._plot_payload(payload)

                if verbose and payload is not None and payload.get("metrics") is not None:
                    m = payload["metrics"]
                    d = payload["debug"]
                    print("\n=== Random Search Iteration ===", flush=True)
                    print(f"Iteration    : {i + 1}", flush=True)
                    print(f"Distance     : {payload['distance']}", flush=True)
                    print(f"Crystal      : {payload['crystal']}", flush=True)
                    print(f"hkl          : {payload['hkl']}", flush=True)
                    print(f"Visible peaks: {payload['visible_peaks'].tolist()} (coverage={payload['coverage']:.2f})", flush=True)
                    print(f"Chosen peaks : {payload['chosen_peaks'].tolist()}", flush=True)
                    print(f"deltaX(px)   : {m['deltaX']:.3f} | pixel_diff(eV/px): {m['pixel_diff']:.6f}", flush=True)
                    print(f"peak_score   : {d['peak_score']:.4f} | dist_pen: {d['dist_pen']:.4f}", flush=True)
                    print(f"score        : {d['score']:.4f} | objective: {obj:.6f}", flush=True)

            except Exception as e:
                failed_record = {
                    "iter": i + 1,
                    "objective": 1e6,
                    "distance": float(distance),
                    "crystal": str(crystal),
                    "hkl": [int(x) for x in hkl],
                    "valid_payload": False,
                    "error": str(e),
                }
                self.all_history.append(self._to_json_friendly(failed_record))
                if verbose:
                    print("[random_search] failed:", e, flush=True)

        if auto_export_json:
            self.export_results_to_json(export_filename)

        print("\n=== Random Search Results ===", flush=True)
        if self.best_payload is not None:
            print(f"Best Distance : {self.best_payload['distance']:.3f}", flush=True)
            print(f"Best Crystal  : {self.best_payload['crystal']}", flush=True)
            print(f"Best hkl      : {self.best_payload['hkl']}", flush=True)
            print(f"Best objective: {self.best_obj:.6f}", flush=True)

        return {
            "best_obj": self.best_obj,
            "best_payload": self.best_payload,
            "all_history": self.all_history,
            "best_history": self.best_history,
            "random_state": random_state,
            "n_calls": n_calls,
        }

    # ------------------------------------------------------------------
    # grid search baseline
    # ------------------------------------------------------------------
    def grid_search(
        self,
        step_mm=1.0,
        verbose=True,
        auto_export_json=True,
        export_filename="grid_search_results.json",
    ):
        """
        Exhaustive grid search over:
          - all paired crystal/HKL candidates (preferred)
          - or all independent crystal x HKL combinations
          - distance parameter sampled with fixed step size

        Returns:
            {
                "best_obj": ...,
                "best_payload": ...,
                "all_history": ...,
                "best_history": ...
            }
        """
        self._reset_search_state()

        self._last_search_method = "grid_search"
        self._last_random_state = None
        self._last_acq_func = None
        self._last_kappa = None
        self._last_n_calls = None
        self._last_n_initial_points = None

        use_pairs = len(self.crystal_hkl_pairs) > 0

        # distance grid (inclusive of upper bound if it lands on the step)
        d_start = float(self.distance_bounds[0])
        d_stop = float(self.distance_bounds[-1])

        if step_mm <= 0:
            raise ValueError("step_mm must be > 0")

        distances = np.arange(d_start, d_stop + 0.5 * step_mm, step_mm, dtype=float)

        # build candidate list
        candidates = []
        if use_pairs:
            for crystal, hkl in self.crystal_hkl_pairs:
                candidates.append((crystal, list(hkl)))
        else:
            if len(self.crystals) == 0 or len(self.hkls) == 0:
                raise ValueError("Grid search needs either crystal_hkl_pairs or non-empty crystals and hkls.")
            for crystal in self.crystals:
                for hkl in self.hkls:
                    candidates.append((crystal, list(hkl)))

        iter_counter = 0

        for crystal, hkl in candidates:
            for distance in distances:
                iter_counter += 1

                try:
                    obj, payload = self.run_experiment(distance, crystal, hkl, allow_plot=False)

                    iter_record = self._make_iteration_record(
                        iteration_number=iter_counter,
                        obj=obj,
                        distance=distance,
                        crystal=crystal,
                        hkl=hkl,
                        payload=payload,
                    )
                    self.all_history.append(iter_record)

                    if payload is not None and obj < self.best_obj:
                        self.best_obj = obj
                        self.best_payload = payload

                        best_record = {
                            "iter": iter_counter,
                            "obj": float(obj),
                            "score": float(payload["debug"]["score"]) if payload.get("debug") else None,
                            "distance": float(payload["distance"]),
                            "crystal": payload.get("crystal"),
                            "hkl": payload.get("hkl"),
                            "chosen_peaks": payload.get("chosen_peaks").tolist() if payload.get("chosen_peaks") is not None else None,
                            "coverage": float(payload.get("coverage", 0.0)),
                            "pixel_diff": float(payload["metrics"]["pixel_diff"]) if payload.get("metrics") else None,
                            "deltaX": float(payload["metrics"]["deltaX"]) if payload.get("metrics") else None,
                        }
                        self.history.append(best_record)
                        self.best_history.append(best_record)

                        if self._best_update_callback is not None and self.best_payload is not None:
                            try:
                                self._best_update_callback(self.best_payload)
                            except Exception as e:
                                print("[best_update_callback] failed:", e, flush=True)

                        if self.enable_best_plots:
                            self._plot_payload(payload)

                    if verbose and payload is not None and payload.get("metrics") is not None:
                        m = payload["metrics"]
                        d = payload["debug"]
                        print("\n=== Grid Search Iteration ===", flush=True)
                        print(f"Iteration    : {iter_counter}", flush=True)
                        print(f"Distance     : {payload['distance']}", flush=True)
                        print(f"Crystal      : {payload['crystal']}", flush=True)
                        print(f"hkl          : {payload['hkl']}", flush=True)
                        print(f"Visible peaks: {payload['visible_peaks'].tolist()} (coverage={payload['coverage']:.2f})", flush=True)
                        print(f"Chosen peaks : {payload['chosen_peaks'].tolist()}", flush=True)
                        print(f"deltaX(px)   : {m['deltaX']:.3f} | pixel_diff(eV/px): {m['pixel_diff']:.6f}", flush=True)
                        print(f"peak_score   : {d['peak_score']:.4f} | dist_pen: {d['dist_pen']:.4f}", flush=True)
                        print(f"score        : {d['score']:.4f} | objective: {obj:.6f}", flush=True)

                except Exception as e:
                    failed_record = {
                        "iter": iter_counter,
                        "objective": 1e6,
                        "distance": float(distance),
                        "crystal": str(crystal),
                        "hkl": [int(x) for x in hkl],
                        "valid_payload": False,
                        "error": str(e),
                    }
                    self.all_history.append(self._to_json_friendly(failed_record))
                    if verbose:
                        print("[grid_search] failed:", e, flush=True)

        if auto_export_json:
            self.export_results_to_json(export_filename)

        print("\n=== Grid Search Results ===", flush=True)
        if self.best_payload is not None:
            print(f"Best Distance : {self.best_payload['distance']:.3f}", flush=True)
            print(f"Best Crystal  : {self.best_payload['crystal']}", flush=True)
            print(f"Best hkl      : {self.best_payload['hkl']}", flush=True)
            print(f"Best objective: {self.best_obj:.6f}", flush=True)

        return {
            "best_obj": self.best_obj,
            "best_payload": self.best_payload,
            "all_history": self.all_history,
            "best_history": self.best_history,
        }

    # ------------------------------------------------------------------
    # export
    # ------------------------------------------------------------------
    def export_results_to_json(self, filename=None):
        final_best = None
        if self.best_payload is not None:
            bp = self.best_payload
            final_best = {
                "distance": float(bp["distance"]),
                "crystal": str(bp["crystal"]),
                "hkl": [int(x) for x in bp["hkl"]],
                "objective": float(self.best_obj),
                "score": float(bp["debug"]["score"]) if bp.get("debug") else None,
                "coverage": float(bp.get("coverage", 0.0)),
                "visible_peaks": self._to_json_friendly(bp.get("visible_peaks")),
                "chosen_peaks": self._to_json_friendly(bp.get("chosen_peaks")),
                "metrics": self._to_json_friendly(bp.get("metrics")),
                "debug": self._to_json_friendly(bp.get("debug")),
            }

        report = {
            "summary": {
                "search_method": self._last_search_method,
                "random_state": self._last_random_state,
                "acq_func": self._last_acq_func,
                "kappa": self._last_kappa,
                "n_calls": self._last_n_calls,
                "n_initial_points": self._last_n_initial_points,
                "total_iterations": len(self.all_history),
                "best_objective": float(self.best_obj) if self.best_obj != np.inf else None,
                "best_score": (
                    float(self.best_payload["debug"]["score"])
                    if self.best_payload is not None and self.best_payload.get("debug") is not None
                    else None
                ),
                "config": {
                    "sim_energies": self._to_json_friendly(self.sim_energies),
                    "target_energies": self._to_json_friendly(self.target_energies),
                    "distance_bounds": self._to_json_friendly(self.distance_bounds),
                    "crystals": self._to_json_friendly(self.crystals),
                    "hkls": self._to_json_friendly(self.hkls),
                    "crystal_hkl_pairs": self._to_json_friendly(self.crystal_hkl_pairs),
                    "repeats": int(self.repeats),
                    "smooth_sigma": float(self.smooth_sigma),
                    "halfmax_max_gap": int(self.halfmax_max_gap),
                    "halfmax_fracs": self._to_json_friendly(self.halfmax_fracs),
                    "prom_frac_fallback": float(self.prom_frac_fallback),
                    "prom_frac_fallback2": float(self.prom_frac_fallback2),
                    "w_sep": float(self.w_sep),
                    "w_dist": float(self.w_dist),
                    "dist_power": float(self.dist_power),
                    "expected_dx": self._to_json_friendly(self.expected_dx),
                    "expected_eff_dist": self._to_json_friendly(self.expected_eff_dist),
                },
            },
            "best_result": final_best,
            "all_iterations": self._to_json_friendly(self.all_history),
            "best_history": self._to_json_friendly(self.best_history),
        }

        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)

        return report