# -*- coding: utf-8 -*-
"""
Created on Fri Jun 14 14:17:55 2024

@author: cakir
"""

import numpy as np
from CrystalSelector import CrystalSelector

class BraggCalculator:
    
    def __init__(self, energy, distance, crystal,hkl):
        self.energy = energy
        self.distance = distance
        self.crystal = crystal
        self.hkl = hkl
    
    def find_wavelength(self):
        """
        Convert energy in electron volts (eV) to wavelength in angstroms.
        """
        wavelength = 1239.8 / self.energy  # Wavelength in nanometers
        return wavelength * 10  # Convert to angstroms

    def calculate_angle(self, wavelength, two_d):
        """
        Calculate the Bragg angle (theta) in radians given the wavelength and 2d.
        """
        sin_theta = wavelength / two_d
        if sin_theta > 1 or sin_theta < -1:
            raise ValueError("Invalid sine value for theta.")
        return np.arcsin(sin_theta)
    
    def find_lengths(self, theta):
        """
        Calculate the length c based on the angle theta and distance d.
        """
        return self.distance * np.tan(theta)  # Calculate c
    
    def run_calculations(self, two_d):
        wavelength = self.find_wavelength()
        theta = self.calculate_angle(wavelength, two_d)
        c = self.find_lengths(theta)
        
        print(f"Wavelength: {wavelength} Å, Theta: {np.degrees(theta)} degrees, Length c: {c} mm")
        return theta, c, self.distance

    def main(self):
        # Retrieve crystal data
        crystal_data = CrystalSelector().get_crystal_method(self.crystal, hkl=self.hkl)
        print(crystal_data)
        
        if crystal_data:
            _d = crystal_data.d  # Assuming it returns an object with attribute 'd'
            print(f"Lattice spacing of {self.crystal}: {_d}")
            two_d = _d * 2
            
            # Use retrieved _d in calculations
            theta, c, _ = self.run_calculations(two_d)
            return theta, c
        else:
            print(f"Crystal '{self.crystal}' not found or does not have the '_d' attribute.")
            return None, None, None




