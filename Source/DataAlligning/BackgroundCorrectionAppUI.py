import dearpygui.dearpygui as dpg
from silx.math.fit import snip1d
import numpy as np


class BackgroundCorrectionApp:
    def __init__(self, parent):
        self.parent = parent
        self.files = list(self.parent.aligned_data.keys())  # Get file list
        self.current_index = 0  # Start with the first file
        self.width = 8  # Default width

        # Build modal window
        if dpg.does_item_exist("bckg_window"):
            dpg.delete_item("bckg_window")

        with dpg.window(label="Background Correction - Step by Step",
                        modal=True, tag="bckg_window",
                        width=800, height=600,
                        on_close=lambda: dpg.delete_item("bckg_window")):

            # Plot area
            with dpg.plot(label="Background Correction Plot", height=400, width=-1,
                          tag="bckg_plot"):
                dpg.add_plot_axis(dpg.mvXAxis, label="Pixel", tag="bckg_x_axis")
                with dpg.plot_axis(dpg.mvYAxis, label="Intensity", tag="bckg_y_axis"):
                    self.raw_series = dpg.add_line_series([], [], label="Raw Data", parent="bckg_y_axis")
                    self.bkg_series = dpg.add_line_series([], [], label="Background", parent="bckg_y_axis")

            # Controls row
            with dpg.group(horizontal=True):
                dpg.add_button(label="Next", callback=self.next_file, width=100)

                dpg.add_slider_int(label="Width", min_value=1, max_value=15,
                                   default_value=self.width, width=300,
                                   callback=self.update_plot, tag="width_slider")

        # First plot
        self._bckg_correction(self.width)

    def _bckg_correction(self, width):
        """Applies background correction to the current file and updates the plot."""
        if self.current_index >= len(self.files):
            dpg.delete_item("bckg_window")
            return

        file = self.files[self.current_index]
        values = self.parent.aligned_data[file]

        aligned_x = np.array(values["Aligned_Energy"])
        intensity = np.array(values["Normalized_Intensity"])
        bckg = snip1d(intensity, width)
        bckg_corrected = intensity - bckg
        if np.max(bckg_corrected) > 0:
            bckg_corrected /= np.max(bckg_corrected)

        # Update DPG plot
        dpg.set_value(self.raw_series, [aligned_x.tolist(), intensity.tolist()])
        dpg.set_value(self.bkg_series, [aligned_x.tolist(), bckg.tolist()])

        dpg.set_item_label("bckg_plot", f"File: {file.split('/')[-1]}")
        dpg.configure_item("bckg_x_axis", label="Energy (eV)")
        dpg.configure_item("bckg_y_axis", label="Intensity")

    def update_plot(self, sender, app_data):
        """Updates the plot when the slider is moved."""
        self.width = int(app_data)
        self._bckg_correction(self.width)

    def next_file(self):
        """Stores selected width and moves to the next file."""
        file = self.files[self.current_index]
        self.parent.selected_widths[file] = self.width  # Save width

        self.current_index += 1

        if self.current_index < len(self.files):
            reset_value = 8
            dpg.set_value("width_slider", reset_value)  # Reset slider
            self.width = reset_value
            self._bckg_correction(self.width)
        else:
            print("All files processed:", self.parent.selected_widths)
            dpg.delete_item("bckg_window")  # Close when finished
