# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 09:43:31 2025

@author: cakir
"""

import xraydb

class XRFAnalyzer:
    """
    Class to analyze XRF data and find the corresponding emission line for a selected element.
    """
    def __init__(self, detector_channels=1024, gain_per_channel=26.5):
        self.detector_channels = detector_channels
        self.gain_per_channel = gain_per_channel
        self.xdb = xraydb.XrayDB()

    
    def find_emission_line(self, element, line): 
        """
        Finds the corresponding emission line based on X-ray fluorescence (XRF) energies.
        :param element: The element symbol as a string (e.g., "Fe").
        :param line: The emission line to retrieve (e.g., "Ka").
        :return: The emission energy in eV.
        """
        emission_energy = self.xdb.xray_lines(element)[line]

        
        if emission_energy is None:
            raise ValueError("Unsupported emission line or element not found.")
            
        return emission_energy
    
    def get_emission_lines(self, element):
        
        """
        Finds the corresponding emission lines based on selected element.
        :param element: The element symbol as a string (e.g., "Fe").
        :return: The emission lines.
        """
        
        return list(xraydb.xray_lines(element).keys())
            
    def find_channel(self, emission_energy):
                
        channel = emission_energy.energy / self.gain_per_channel
        return int(round(channel))
    
    def run_find_channel(self, element, line):

        """
        Runs the process to find the emission line energy and map it to a detector channel.
        :param element: The element symbol as a string (e.g., "Fe").
        :param line: The emission line to retrieve (e.g., "Ka").
        :return: The detector channel as an integer.
        """
        
        emission_energy = self.find_emission_line(element, line)
        
        return self.find_channel(emission_energy)