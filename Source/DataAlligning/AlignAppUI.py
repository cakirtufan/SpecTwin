# -*- coding: utf-8 -*-
"""
Created on Mon Apr 14 11:38:58 2025

@author: cakir
"""


import dearpygui.dearpygui as dpg
from scipy.optimize import curve_fit
from scipy.signal import find_peaks
from silx.math.fit import snip1d
from scipy.ndimage import gaussian_filter1d
import pandas as pd
import numpy as np
import os

import HDF5Reader  # Ensure this module is available
import BackgroundCorrectionAppUI


class AligningUI:
    def __init__(self, parent_tag, calibration_data):
        self.parent_tag = parent_tag
        self.calibration_data = calibration_data
        self.selected_file = []
        self.param_a = calibration_data.get('params_a')
        self.param_b = calibration_data.get('params_b')
        self.allign_peaks = calibration_data['allign_peaks']
        self.file_list = []
        self.file_names = []
        self.hdf5_readers = {}
        self.plotted_data = set()
        self.aligned_data = {}
        self.selected_widths = {}
        self.centroid_entries = []
        self.hdf5_reader = None
                
        self.file_dialog_tag = f"{self.parent_tag}_file_dialog"

        self._build_layout()
        self._execute_initial_ref_data()

    def _build_layout(self):
        with dpg.group(parent=self.parent_tag):
            with dpg.group(horizontal=True):  # Split left (files) and right (graph+table)
                
                # === Left column: File selection ===
                with dpg.child_window(width=300, height=-1):
                    dpg.add_text("H5 Files")
                    self.file_listbox = dpg.add_listbox(items=[], num_items=38, width=-1,
                                                        callback=self._on_file_select)
                    
                    with dpg.group(horizontal=True):
                    
                        dpg.add_button(label="Add File", callback=self._add_file)
                        dpg.add_button(label="Read & Process", callback=self._process_start)

                # === Right column: Graph + Table + Buttons ===
                with dpg.child_window(width=-1, height=-1):
                    # Graph area
                    with dpg.child_window(height=700, border=True):
                        with dpg.plot(label="Aligned Spectra", height=-1, width=-1, tag="align_plot"):
                            dpg.add_plot_axis(dpg.mvXAxis, label="Energy (eV)", tag="align_x_axis")
                            with dpg.plot_axis(dpg.mvYAxis, label="Intensity", tag="align_y_axis"):
                                self.series = dpg.add_line_series([], [], label="Data", tag="align_series")

                    # Table area
                    with dpg.child_window(height=200, border=True):
                        with dpg.table(header_row=True, resizable=True, borders_innerH=True,
                                       borders_innerV=True, borders_outerH=True, borders_outerV=True,
                                       row_background=True, tag="align_table"):
                            dpg.add_table_column(label="Sample")
                            dpg.add_table_column(label="Element")
                            dpg.add_table_column(label="Emission Line")
                            dpg.add_table_column(label="Centroid")

                    # Buttons row
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Background Correction", callback=self._bckg_correction, width=180)
                        dpg.add_button(label="Align All", callback=self._plot_alligned_spectra, width=100)
                        dpg.add_button(label="Save CSV", callback=self._save_csv, width=100)

            # === File dialog (created ONCE, hidden by default) ===
            with dpg.file_dialog(
                directory_selector=False, show=False,
                callback=self._file_selected,
                tag=self.file_dialog_tag,
                width=600, height=400
            ):
                dpg.add_file_extension(".h5", color=(150, 255, 150, 255))
                dpg.add_file_extension(".*")
                        
                        
                        

    # === File handling ===
    def _add_file(self):
        """Show the existing file dialog instead of recreating it."""
        if dpg.does_item_exist(self.file_dialog_tag):
            dpg.show_item(self.file_dialog_tag)
        else:
            print(f"⚠️ File dialog not found: {self.file_dialog_tag}")

    def _file_selected(self, sender, app_data):
        """Callback after user picks a file in the dialog."""
        file_path = app_data['file_path_name']
        if file_path not in self.file_list:
            self.file_names.append(file_path.split("\\")[-1].replace(".h5", ""))
            self.file_list.append(file_path)
            dpg.configure_item(self.file_listbox, items=self.file_names)
            # also store HDF5Reader
            self.hdf5_readers[file_path] = HDF5Reader.HDF5Reader(file_path)
            
            print("File list in file selection is: ", self.file_list)
            print("File names in file selection are: ", self.file_names)

    def _on_file_select(self, sender, app_data):
        """Triggered when user selects an item from the listbox."""
        self.selected_file = app_data
        print("Selected file:", self.selected_file)


    def _bckg_correction(self):
        print("Background correction clicked")
        
        self.open_bckg_correction_window()
        
    def _plot_alligned_spectra(self):
        """Plot all aligned spectra inside DearPyGui plot."""
        if not self.aligned_data:
            dpg.add_text("⚠️ No aligned data available", parent=self.parent_tag)
            return
    
        # --- Clear previous plot content (series, annotations, inf-lines) ---
        for axis in ("align_x_axis", "align_y_axis"):
            if dpg.does_item_exist(axis):
                children = dpg.get_item_children(axis, 1)  # slot 1 = items inside axis
                for child in children:
                    dpg.delete_item(child)
    
        # Also clear annotations (slot 2 of plot)
        if dpg.does_item_exist("align_plot"):
            annotations = dpg.get_item_children("align_plot", 2)  # slot 2 = annotations
            for ann in annotations:
                dpg.delete_item(ann)
    
        # --- Plot each aligned spectrum ---
        for file, values in self.aligned_data.items():
            aligned_x = values["Aligned_Energy"]
            intensity = values["Normalized_Intensity"]
    
            # Background correction
            bckg = snip1d(intensity, self.selected_widths.get(file, 10))
            bckg_corrected = gaussian_filter1d(intensity, 1) - bckg
            bckg_corrected = bckg_corrected / max(bckg_corrected)
    
            label = file.split("\\")[-1].replace(".h5", "")
            dpg.add_line_series(
                aligned_x.tolist(), bckg_corrected.tolist(),
                label=label, parent="align_y_axis"
            )
            
        dpg.set_value("centroid_label", default_value=([], []), label="")
    
        # Auto-fit axes
        dpg.fit_axis_data("align_x_axis")
        dpg.fit_axis_data("align_y_axis")
    
        print("✅ Aligned spectra plotted (previous content cleared).")
                 
    def _save_csv(self):
        """Open a save dialog to export aligned spectra as CSV."""
        if not self.aligned_data:
            print("⚠️ No aligned data to save.")
            return
    
        if hasattr(self, "save_dialog_id"):
            dpg.delete_item(self.save_dialog_id)
    
        with dpg.file_dialog(directory_selector=True, show=True,
                             callback=self._save_csv_callback,
                             tag="save_dialog_id",
                             width=600, height=400):
            dpg.add_file_extension(".*")

    def _save_csv_callback(self, sender, app_data):
        """Save aligned spectra to selected directory."""
        directory = app_data["file_path_name"]
        print(f"Saving CSV files to {directory}")
    
        for file, values in self.aligned_data.items():
            aligned_x = values["Aligned_Energy"]
            intensity = values["Normalized_Intensity"]
    
            bckg = snip1d(intensity, self.selected_widths.get(file, 10))
            bckg_corrected = gaussian_filter1d(intensity, 1) - bckg
            bckg_corrected = bckg_corrected / max(bckg_corrected)
    
            label = file.split("\\")[-1].replace(".h5", "")
            dict_data = {"Energy": aligned_x, "Intensity": bckg_corrected}
            pd.DataFrame(dict_data).to_csv(os.path.join(directory, f"{label}.csv"), index=False)
    
        print("✅ All CSV files saved.")



    def _execute_initial_ref_data(self):
        
        self.file_names.append(self.calibration_data.get("ref_data").split("\\")[-1].replace(".h5", ""))
        self.file_list.append(self.calibration_data.get("ref_data"))
        dpg.configure_item(self.file_listbox, items=self.file_names)
        self.selected_file.append(self.calibration_data.get("ref_data"))
        self.hdf5_readers[self.calibration_data.get("ref_data")] = HDF5Reader.HDF5Reader(self.calibration_data.get("ref_data")) 
        self._process_start()        
    
    def _read_data(self, file_path):
        """
        Read the dataset from the HDF5 file using calibration info.
    
        Returns
        -------
        data : np.ndarray
            The intensity array read from the HDF5 file.
        """
        if file_path not in self.hdf5_readers:
            return np.array([])
    
        channel_start = self.calibration_data.get("channel_start")
        channel_end   = self.calibration_data.get("channel_end")
        
        # The read_data method in HDF5Reader is assumed to return a 1D numpy array
        data = self.hdf5_readers[file_path].read_data(channel_start, channel_end)
        return data
        
            
    def _align_energy(self, a, b, pixel_indices):

        return a * pixel_indices + b  

    def _find_shifted_peak(self, ref_x, ref_y, real_x, real_y, x_range_expansion=20, y_tolerance=0.4):
        """
        Finds the shifted peak position in real data based on a reference peak position.
    
        Parameters:
        - ref_x (float): X position of the peak in reference data.
        - ref_y (float): Y position of the peak in reference data.
        - real_x (numpy array): X-axis values of the real data.
        - real_y (numpy array): Y-axis values of the real data.
        - x_range_expansion (int): Range expansion factor to search for the peak in real data.
        - y_tolerance (float): Allowed tolerance for y-value match.
    
        Returns:
        - tuple: (X position, Y position) of the detected shifted peak in real data, or None if not found.
        """
        
        # Define the search range in real data
        # search_x_min = ref_x - x_range_expansion
        # search_x_max = ref_x + x_range_expansion
        print("Height is: ", max(real_y) * 0.4)
        print("Max is : ", max(real_y) )
        # Find peaks in real data using intensity filtering
        # peaks, properties = find_peaks(real_y, height=ref_y - y_tolerance*ref_y)
        peaks, properties = find_peaks(real_y, height=max(real_y) * 0.4)
        
        
        print("Detected peaks indices:", peaks)
        
        # Filter peaks within the x search range
        # valid_peaks = [p for p in peaks if search_x_min <= real_x[p] <= search_x_max]
    
        # # Further filter peaks based on y intensity condition
        # adjusted_peaks = [p for p in valid_peaks if ((1 - y_tolerance) * ref_y) <= real_y[p] <= ((1 + y_tolerance) * ref_y)]
    
        # if not adjusted_peaks:
        #     return None  # No matching peak found
    
        # # If multiple peaks are found, return the one closest to the reference x
        # best_peak = min(adjusted_peaks, key=lambda p: abs(real_x[p] - ref_x))
        
        print("Best_peak at: ", [(float(real_x[peaks[0]]), float(real_y[peaks[0]])), (float(real_x[peaks[1]]), float(real_y[peaks[1]]))])
        
        return [[(float(real_x[peaks[0]]), float(real_y[peaks[0]]))], [(float(real_x[peaks[1]]), float(real_y[peaks[1]]))]]
    
    
    def open_bckg_correction_window(self):
        """Opens the Background Correction window (DPG)."""
    
        if not self.aligned_data:  # Ensure data is available
            self._align_spectra()
    
        if dpg.does_item_exist("bckg_window"):
            dpg.delete_item("bckg_window")
    
        with dpg.window(label="Background Correction", modal=True,
                        width=600, height=400, tag="bckg_window", on_close=lambda: dpg.delete_item("bckg_window")):
            # Here you can embed your BackgroundCorrectionApp as a DPG widget
            BackgroundCorrectionAppUI.BackgroundCorrectionApp(self)  
    
        print("Selected widths:", self.selected_widths)


    def _align_spectra(self):
        """Aligns spectra by shifting centroids relative to reference."""
    
        if not self.centroid_entries:
            print("⚠️ No centroid entries available to align.")
            return
    
        centroids = [entry[-1] for entry in self.centroid_entries]
        reference_centroid = centroids[0]
    
        for (file_name, centroid) in zip([e[0] for e in self.centroid_entries], centroids):
    
            # Get full file path (search in hdf5_readers keys)
            full_path = None
            for key in self.hdf5_readers:
                if file_name in key:
                    full_path = key
                    break
            if not full_path:
                continue
    
            data = self._read_data(full_path)
            if data is None or len(data) == 0:
                continue
    
            x_axis = np.arange(len(data))
    
            # Compute the shift needed to align the peak to the reference centroid
            shift = reference_centroid - centroid
            aligned_x_axis = x_axis + shift
    
            # Use calibration parameters if available
            if self.param_a is not None and self.param_b is not None:
                aligned_energy = self._align_energy(self.param_a, self.param_b, aligned_x_axis)
            else:
                aligned_energy = aligned_x_axis  # fallback: pixel axis
    
            # Store aligned data
            self.aligned_data[file_name] = {
                "Aligned_Energy": aligned_energy,
                "Normalized_Intensity": data
            }
        
        
    
        print("✅ Spectra aligned:", list(self.aligned_data.keys()))

    
    def _fit_gaussian(self, x_data, y_data, allign_peaks):
        """
        Fit a single Gaussian function to the provided x_data, y_data,
        using the provided align_peaks as initial guess for the center.
    
        Parameters
        ----------
        x_data : np.ndarray
            Array of channel indices (or pixel numbers).
        y_data : np.ndarray
            Intensity values.
        allign_peaks : list of tuples
            e.g. [(24.0, 6915.8)] where 24 is the channel center.
    
        Returns
        -------
        popt : list or None
            The optimized parameters [a, mu, sigma].
            Returns None if the fit fails.
        """
        if len(allign_peaks) < 1:
            dpg.add_text(
                "Insufficient Peak Info",
                "Need at least one peak center in allign_peaks to perform a fit.", 
                parent=self.parent_tag
            )
            return None
    
        # Extract channel center from allign_peaks
        peak_center = allign_peaks[0][0]  # e.g. 24.0
    
        # Provide an initial guess for amplitude
        guess_a = self._local_max(y_data, peak_center)
        guess_sigma = 1 # Assumed initial sigma value
    
        p0 = [guess_a, peak_center, guess_sigma]
    
        try:
            popt, _ = curve_fit(self._gaussian, x_data, y_data, p0=p0)
            return popt
        except RuntimeError:
            dpg.add_text("Fit Error", "Single Gaussian fit failed.",
                         parent=self.parent_tag)
            return None


    def _fit_double_gaussian(self, x_data, y_data, allign_peaks):
        """
        Fit a double Gaussian function to the provided x_data, y_data,
        using the provided align_peaks as initial guesses for centers.
    
        Parameters
        ----------
        x_data : np.ndarray
            Array of channel indices (or pixel numbers).
        y_data : np.ndarray
            Intensity values.
        allign_peaks : list of tuples
            e.g. [(24.0, 6915.8), (28.0, 6930.9)] where 24 and 28 are channel centers.
    
        Returns
        -------
        popt : list or None
            The optimized parameters [a1, mu1, sigma1, a2, mu2, sigma2].
            Returns None if the fit fails or if there aren't two peaks.
        """
        # if len(allign_peaks) < 2:
        #     messagebox.showwarning(
        #         "Insufficient Peak Info",
        #         "Need at least two peak centers in allign_peaks to perform a double fit."
        #     )
        #     return None
        
        print("align_peaks_in_double_fit: ", allign_peaks)
        
        # Extract channel centers from allign_peaks
        peak1_center = allign_peaks[0][0][0][0]  # e.g. 24.0
        peak2_center = allign_peaks[0][1][0][0]  # e.g. 28.0
    
        # Provide initial guesses for amplitudes (a1, a2) by sampling intensities near those centers
        guess_a1 = self._local_max(y_data, peak1_center)
        guess_a2 = self._local_max(y_data, peak2_center)
    
        # Provide initial guesses for sigmas
        guess_sigma1 = 2
        guess_sigma2 = 2
    
        p0 = [
            guess_a1, peak1_center, guess_sigma1,
            guess_a2, peak2_center, guess_sigma2
        ]
    
        try:
            popt, _ = curve_fit(self._double_gaussian, x_data, y_data, p0=p0)
            return popt
        except RuntimeError:
            dpg.add_text("Fit Error", "Double Gaussian fit failed.",
                         parent=self.parent_tag)
            return None
    
    def _local_max(self, y_data, center, window=2):
        """
        A simple helper function to estimate the amplitude near a peak center
        by looking for the local max in a small window around 'center'.
    
        Parameters
        ----------
        y_data : np.ndarray
            1D intensity array.
        center : float
            Peak center in channel units.
        window : int
            Half-window size around 'center' to search for a local max.
    
        Returns
        -------
        amplitude_guess : float
            An estimated amplitude near that center.
        """
        center = int(round(center))
        lower = max(0, center - window)
        upper = min(len(y_data), center + window + 1)
        return float(np.max(y_data[lower:upper]))
    
    
    @staticmethod
    def _gaussian(x, a, mu, sigma):
        """
        Single Gaussian function.
        """
        return a * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
    
    def _double_gaussian(self, x, a1, mu1, sigma1, a2, mu2, sigma2):
        """
        Double Gaussian = G1 + G2
        """
        return (self._gaussian(x, a1, mu1, sigma1)
                + self._gaussian(x, a2, mu2, sigma2))
        
    def _process_start(self):
        
        print("Len allign_peaks: ", len(self.allign_peaks))

        if len(self.allign_peaks) >= 2:
            
            # self.allign_peaks = self.allign_peaks[:2]
            
            self._process_data()
            
        elif len(self.allign_peaks) == 1:

            self._process_single_data()
            
            
    def _process_single_data(self):
        """
        Process the selected file in DearPyGui:
        1. Retrieve the selected file from listbox.
        2. Read the data from that file (based on calibration).
        3. Fit the data (single Gaussian) using peak centers from allign_peaks.
        4. Plot the result in the DPG plot and update the table.
        """
    
        # If no file selected, fall back to first in list
        if not self.selected_file and self.file_list:
            self.selected_file = self.file_list[0]
    
        if not self.selected_file:
            dpg.add_text("⚠️ No file selected!", parent=self.parent_tag)
            return
    
        file_path = self.selected_file
        element = self.calibration_data.get("selected_element", "Unknown")
    
        plot_key = (file_path, element)
        if not hasattr(self, "plotted_data"):
            self.plotted_data = set()
        if plot_key in self.plotted_data:
            return  # Already plotted this file+element combo
    
        # === Step 1: Read the data ===
        data = self._read_data(file_path)
        x_data = np.arange(len(data))
        y_data = data.copy()
    
        # === Step 2: Peak fitting ===
        allign_peaks_all = self.calibration_data.get("allign_peaks", [])
        next_data_peaks = []
    
        if allign_peaks_all:
            peak_1 = self._find_shifted_peak(
                allign_peaks_all[0][0],  # ref_x
                allign_peaks_all[0][1],  # ref_y
                x_data, y_data,
                x_range_expansion=20,
                y_tolerance=0.4
            )
            peak_1_emission_line = allign_peaks_all[0][2]
            next_data_peaks.append(peak_1)
        else:
            dpg.add_text("⚠️ No calibration peaks available", parent=self.parent_tag)
            return
    
        allign_peaks = [(x, y) for x, y, _ in allign_peaks_all]
    
        if next_data_peaks == allign_peaks:
            print("next_data_peaks == allign_peaks")
            popt = self._fit_gaussian(x_data, y_data, allign_peaks)
        else:
            print("next_data_peaks != allign_peaks")
            popt = self._fit_gaussian(x_data, y_data, next_data_peaks)
    
        # === Step 3: Plot in DearPyGui ===
        if popt is not None:
            dpg.set_value("align_series", [x_data.tolist(), y_data.tolist()])
    
            # Add a vertical line for centroid (optional)
            centroid = popt[1]
            
            dpg.add_plot_annotation(label=f"Centroid {centroid:.2f}", default_value=(centroid, max(y_data)), tag = "centroid_label")
                
    
            # === Step 4: Update table ===
            sample_name = file_path.split("/")[-1].replace(".h5", "")
            if not hasattr(self, "centroid_entries"):
                self.centroid_entries = []
    
            self.centroid_entries.append((sample_name, element, peak_1_emission_line, centroid))
    
            # Clear old rows and repopulate
            dpg.delete_item("align_table", children_only=True, slot=1)
            for entry in self.centroid_entries:
                with dpg.table_row(parent="align_table"):
                    dpg.add_text(entry[0])  # Sample
                    dpg.add_text(entry[1])  # Element
                    dpg.add_text(entry[2])  # Emission Line
                    dpg.add_text(f"{entry[3]:.2f}")  # Centroid
    
            self.plotted_data.add(plot_key)

    def _process_data(self):
        """
        Process the selected file in DearPyGui:
        1. Retrieve the selected file path.
        2. Read the data from that file (based on calibration).
        3. Fit the data (two Gaussians) using peak centers from allign_peaks.
        4. Plot the result in the DPG plot and update the table.
        """
    
        # If no file selected, fall back to first in list
        if not self.selected_file and self.file_list:
            self.selected_file = self.file_list
    
        if not self.selected_file:
            dpg.add_text("⚠️ No file selected!", parent=self.parent_tag)
            return
    
        file_path = self.selected_file[-1]
        element = self.calibration_data.get("selected_element", "Unknown")
    
        if not hasattr(self, "plotted_data"):
            self.plotted_data = set()
        plot_key = (file_path, element)
    
        if plot_key in self.plotted_data:
            return  # Already plotted
    
        print("Current file list is: ", self.file_list)
        print("Selected files path are: ", self.selected_file)
        print("Current file path is: ", file_path)
    
        # === Step 1: Read the data ===
        data = self._read_data(self.file_list[-1])
        x_data = np.arange(len(data))
        y_data = data.copy()
    
        # === Step 2: Prepare peaks ===
        allign_peaks_all = self.calibration_data.get("allign_peaks", [])
        if len(allign_peaks_all) < 2:
            dpg.add_text("⚠️ Need at least 2 peaks in calibration to fit double Gaussian",
                         parent=self.parent_tag)
            return
    
        print("Allign_peaks_all:", allign_peaks_all)
    
        peak_1 = self._find_shifted_peak(
            allign_peaks_all[0][0],
            allign_peaks_all[0][1],
            x_data, y_data,
            x_range_expansion=20,
            y_tolerance=0.5
        )
    
        peak_1_emission_line = allign_peaks_all[0][2]
        peak_2_emission_line = allign_peaks_all[1][2]
    
        print("peak_1 emission line:", peak_1_emission_line,
              "peak_2 emission line:", peak_2_emission_line)
    
        next_data_peaks = [peak_1]
    
        # === Step 3: Fit double Gaussian ===
        popt = self._fit_double_gaussian(x_data, y_data, next_data_peaks)
    
        if popt is not None:
            fwhm_2 = 2.355 * popt[5]  # sigma2 → FWHM
            centroid_2 = popt[4]      # mu2
    
            # === Step 4: Add a new series (instead of overwriting old one) ===
            sample_name = self.file_list[-1].split("\\")[-1].replace(".h5", "")
            series_tag = f"series_{sample_name}"
    
            dpg.add_line_series(
                x_data.tolist(), y_data.tolist(),
                label=sample_name,
                parent="align_y_axis",
                tag=series_tag
            )
    
            # Annotate centroid + FWHM
            dpg.add_plot_annotation(label=f"Centroid {centroid_2:.2f}",
                                    default_value=(centroid_2, max(y_data)),
                                    parent="align_plot")
    
            left_fwhm = centroid_2 - fwhm_2 / 2
            right_fwhm = centroid_2 + fwhm_2 / 2
    
            dpg.add_inf_line_series(centroid_2, label="Centroid", parent="align_x_axis")
            dpg.add_inf_line_series(left_fwhm, label="FWHM Left", parent="align_x_axis")
            dpg.add_inf_line_series(right_fwhm, label="FWHM Right", parent="align_x_axis")
    
            # === Step 5: Update table ===
            if not hasattr(self, "centroid_entries"):
                self.centroid_entries = []
    
            self.centroid_entries.append((sample_name, element, peak_2_emission_line, centroid_2))
    
            dpg.delete_item("align_table", children_only=True, slot=1)
            for entry in self.centroid_entries:
                with dpg.table_row(parent="align_table"):
                    dpg.add_text(entry[0])                # Sample
                    dpg.add_text(entry[1])                # Element
                    dpg.add_text(entry[2])                # Emission Line
                    dpg.add_text(f"{entry[3]:.2f}")       # Centroid
    
            self.plotted_data.add(plot_key)
    
        
                
