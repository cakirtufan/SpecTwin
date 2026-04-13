# -*- coding: utf-8 -*-
"""
Created on Mon Oct 14 17:26:48 2024

@author: cakir
"""

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

class PlotClass:
    def __init__(self, tab3, file1_path, file2_path):
        self.tab3 = tab3
        self.file1_path = file1_path
        self.file2_path = file2_path
        self.create_widgets()

    def read_file1(self):
        
        with open(self.file1_path, 'r') as file:
            lines = file.readlines()
    
        # Find the start of the data section
        data_start = None
        for i, line in enumerate(lines):
            if 'Energy' in line and '<xes>' in line:
                data_start = i + 1
                break
    
        # If the section is found, read the data
        if data_start:
            data = []
            for line in lines[data_start:]:
                # Split the line into energy and xes values
                try:
                    parts = line.strip().split()
                    energy = float(parts[0])
                    xes = float(parts[1])
                    data.append([energy, xes])
                except (ValueError, IndexError):
                    continue
    
            # Create a DataFrame with the extracted data
            df = pd.DataFrame(data, columns=['Energy', 'XES'])
            
            print("first _ df is: ", df)
            
            return df
        else:
            raise ValueError("Energy and XES data not found in the file")

    def read_file2(self):
        
        with open(self.file2_path, 'r') as file:
            lines = file.readlines()
        
        # Find the start of the data section
        data_start = None
        for i, line in enumerate(lines):
            if 'Energy' in line and '<xanes>' in line:
                data_start = i + 1
                break
        
        # If the section is found, read the data
        if data_start:
            data = []
            for line in lines[data_start:]:
                # Split the line into energy and xanes values
                try:
                    parts = line.strip().split()
                    energy = float(parts[0])
                    xanes = float(parts[1])
                    data.append([energy, xanes])
                except (ValueError, IndexError):
                    continue
        
            # Create a DataFrame with the extracted data
            df = pd.DataFrame(data, columns=['Energy', 'XANES'])
            print("second _ df is: ", df)
            return df
        else:
            raise ValueError("Energy and XANES data not found in the file")

    def create_widgets(self):
        # Create the plot
        self.fig, self.ax = plt.subplots(figsize=(8, 6))

        # Read data from files
        data1 = self.read_file1()
        data2 = self.read_file2()

        if not data1.empty and not data2.empty:
            # Plot data from the two files
            # self.ax.plot(data1["Energy"], data1["XES"], label="Bi2O3photon_conv_calc <xes>")
            self.ax.plot(data2["Energy"], data2["XANES"], label="Bi2O3_calc_2 <xanes>")

            # Add title and labels
            self.ax.set_title('Bi2O3 Data')
            self.ax.set_xlabel('Energy')
            self.ax.set_ylabel('Values')
            self.ax.legend()
        else:
            self.ax.text(0.5, 0.5, 'Error: Data could not be plotted.', horizontalalignment='center', verticalalignment='center')

        # Display the plot in the tkinter tab
        canvas = FigureCanvasTkAgg(self.fig, master=self.tab3)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        


