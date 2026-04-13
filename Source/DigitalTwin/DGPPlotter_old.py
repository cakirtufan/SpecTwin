# -*- coding: utf-8 -*-
"""
Created on Tue Apr 22 10:23:08 2025

@author: cakir
"""

import dearpygui.dearpygui as dpg
import numpy as np

class DPGPlotter:
    def __init__(self, image2D, image1Dx, image1Dz, total1DEnergy, total1DEnergy_limits, histo1Dx):
        self.image2D = image2D
        self.image1Dx = image1Dx
        self.image1Dz = image1Dz
        self.total1DEnergy = total1DEnergy
        self.total1DEnergy_limits = total1DEnergy_limits
        self.histo1Dx = histo1Dx
        
        
        print(f"Shapes -> image2D: {np.shape(image2D)}, image1Dx: {np.shape(image1Dx)}, "
      f"image1Dz: {np.shape(image1Dz)}, total1DEnergy: {np.shape(total1DEnergy)}, "
      f"total1DEnergy_limits: {total1DEnergy_limits}")

    def normalize_image(self, image):
        norm_image = (image / np.max(image) * 255).astype(np.uint8)
        # Convert RGB to RGBA by adding an alpha channel
        if norm_image.shape[-1] == 3:
            alpha_channel = np.full((*norm_image.shape[:-1], 1), 255, dtype=np.float32)
            norm_image = np.concatenate([norm_image, alpha_channel], axis=-1)
        return norm_image


    def setup_textures(self):
        try:
            if not dpg.does_item_exist("texture_reg"):
                with dpg.texture_registry(tag="texture_reg"):
                    pass
            else:
                dpg.delete_item("texture_reg", children_only=True)
    
            # Main image
            img2D_norm = self.normalize_image(self.image2D).reshape((264, 264, 4))
            dpg.add_static_texture(264, 264, img2D_norm.flatten() / 255.0, parent="texture_reg", tag="texture_main")
    
            # Top RGB bar
            rgb_x_norm = self.normalize_image(self.image1Dx).reshape((-1, 1, 4))
            top_bar = np.tile(rgb_x_norm, (1, 264, 1))
            top_bar = np.swapaxes(top_bar, 0, 1)
            dpg.add_static_texture(top_bar.shape[1], top_bar.shape[0],
                                   top_bar.flatten() / 255.0, parent="texture_reg", tag="texture_top")
            
            print(top_bar.shape)
            
            # Right RGB bar
            rgb_z_norm = self.normalize_image(self.image1Dz).reshape((-1, 1, 4))
            right_bar = np.tile(rgb_z_norm, (1, 264, 1))
            dpg.add_static_texture(right_bar.shape[1], right_bar.shape[0],
                                   right_bar.flatten() / 255.0, parent="texture_reg", tag="texture_right")
    
            # Energy Bar
            energy_norm = self.normalize_image(self.total1DEnergy).reshape((-1, 1, 4))
            energy_bar = np.tile(energy_norm, (1, 128, 1))
            print(energy_bar.shape)
            dpg.add_static_texture(energy_bar.shape[1], energy_bar.shape[0],
                                   energy_bar.flatten() / 255.0, parent="texture_reg", tag="texture_energy")
    
        except Exception as e:
            print(f"[setup_textures ERROR]: {e}")
            
            
    def save_csv_callback(self, sender, app_data):
            """Saves the histo1Dx data to a CSV file."""
            try:
                # Create an array where Col 1 is Index (Pixel) and Col 2 is Value (Intensity)
                indices = np.arange(len(self.histo1Dx))
                data_to_save = np.column_stack((indices, self.histo1Dx))
                
                filename = "histogram_1dx_output.csv"
                
                # Save using numpy (fast and clean)
                np.savetxt(filename, data_to_save, delimiter=",", 
                           header="Pixel,Intensity", comments="")
                
                print(f"Successfully saved to {filename}")
            except Exception as e:
                print(f"Error saving CSV: {e}")


    def render_ui(self, parent):
    
        dpg.delete_item(parent, children_only=True)

        self.setup_textures()
        
        # --- Added Export Button ---
        # Placing it at the top of the UI for easy access
        dpg.add_button(label="Export Histogram to CSV", 
                       callback=self.save_csv_callback, 
                       parent=parent)
        dpg.add_separator(parent=parent)

        # 4) Main row: plot + right bar + energy bar
        main_row = dpg.add_group(horizontal=True, parent=parent)
        
        left_col = dpg.add_group(parent=main_row) 

        # 4a) Plot
        plot_overlay = dpg.add_plot(label="Overlay Plot", width=500, height=500, parent=left_col)
        x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="X (pixel)", parent=plot_overlay)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Y (pixel)", parent=plot_overlay)

        # set limits
        dpg.set_axis_limits(x_axis, 0, self.image2D.shape[1] - 1)
        dpg.set_axis_limits(y_axis, 0, self.image2D.shape[1] - 1)

        # background image
        dpg.add_image_series(
            texture_tag="texture_main",
            bounds_min=[0, 0],
            bounds_max=[self.image2D.shape[1] - 1, self.image2D.shape[1] - 1],
            parent=x_axis
        )


        # # dpg.add_image("texture_top", width=528, height=60, parent=parent) 
        # # Top bar
        
        histogram_1dx = dpg.add_plot(label="Histogram 1Dx",
                            width=500, height=120,
                            parent=left_col)
        
        ax_x_dx = dpg.add_plot_axis(dpg.mvXAxis
                          , parent=histogram_1dx)
        
        ax_y_dx = dpg.add_plot_axis(dpg.mvYAxis, label="Poisiton (X)",
                                parent=histogram_1dx)
        
        dpg.set_axis_limits(ax_x_dx, 0, 263)
        dpg.set_axis_limits(ax_y_dx, 0, 263)
        
        
        dpg.add_image_series(texture_tag="texture_top",
                      bounds_min=[0, 0],
                      bounds_max=[263, 263],
                      parent=ax_y_dx)
        
        right_col = dpg.add_group(parent=main_row, horizontal = True)


        histogram_1dz = dpg.add_plot(label="  ",
                            width=150, height=500,
                            parent=right_col)
        
        ax_x_dz = dpg.add_plot_axis(dpg.mvXAxis, label="Poisiton (Y)"
                          , parent=histogram_1dz)
        
        ax_y_dz = dpg.add_plot_axis(dpg.mvYAxis, label="Histogram 1Dz",
                                parent=histogram_1dz)
        
        
        dpg.add_image_series(texture_tag="texture_right",
                      bounds_min=[0, 0],
                      bounds_max=[263, 263],
                      parent=ax_y_dz)
        
        
        minE, maxE = self.total1DEnergy_limits[0], self.total1DEnergy_limits[1]
        
        print(minE, maxE)
        
        energy = dpg.add_plot(label="  ",
                            width=150, height=500,
                            parent=right_col)
        
        ax_x_energy = dpg.add_plot_axis(dpg.mvXAxis, label="  "
                          , parent=energy)
        
        ax_y_energy = dpg.add_plot_axis(dpg.mvYAxis, label="Energy (eV)",
                                parent=energy)
        
        
        dpg.add_image_series(texture_tag="texture_energy",
                      bounds_min=[0, maxE],
                      bounds_max=[127, minE],
                      parent=ax_y_energy)
        
        dpg.set_axis_limits(ax_y_energy, maxE, minE)
        
        dpg.add_spacer(width = 25, parent= right_col)
        
        # sum_histo_plot = dpg.add_group(horizontal=True, parent=parent)
        
        histo1Dx_plot = dpg.add_plot(label = "Sum of Histogram 1Dx", width = 750, height=500, parent = right_col)
        
        ax_x_histo1Dx = dpg.add_plot_axis(dpg.mvXAxis, label=" Pixel "
                          , parent=histo1Dx_plot)
        ax_y_histo1Dx = dpg.add_plot_axis(dpg.mvYAxis, label="Intensity (a.u.)",
                                parent=histo1Dx_plot)
        
        dpg.add_line_series(list(range(len(self.histo1Dx))), self.histo1Dx, parent = ax_y_histo1Dx )
        
        dpg.fit_axis_data(ax_x_histo1Dx)
        dpg.fit_axis_data(ax_y_histo1Dx)
        
            
    def plot(self, parent):
        self.setup_textures()
        self.render_ui(parent)
