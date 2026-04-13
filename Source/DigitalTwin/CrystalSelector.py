# -*- coding: utf-8 -*-
"""
Created on Fri Jul 12 10:07:17 2024

@author: cakir
"""

import xrt.backends.raycing.materials_crystals as rmatscr

class CrystalSelector:
    def __init__(self):
        # Initialize with a predefined list of crystals
        self.crystals = ['Si', 'Ge', 'Diamond', 'GaAs', 'GaSb', 'GaP',
                          'InAs', 'InP', 'InSb', 'SiC', 'NaCl', 'CsF', 'LiF', 'KCl', 'CsCl',
                          'Be', 'Graphite', 'PET', 'Beryl', 'KAP', 'RbAP', 'TlAP',
                          'Muscovite', 'AlphaQuartz', 'Copper', 'LiNbO3', 'Platinum',
                          'Gold', 'Sapphire', 'LaB6', 'LaB6NIST', 'KTP', 'AlphaAlumina',
                          'Aluminum', 'Iron', 'Titanium']
        
        

    def get_crystal_method(self, crystal_name, hkl):
        # Check if the crystal is in the list and the function exists in the module
        if crystal_name in self.crystals:
            try:
                # Dynamically call the function from rmatscr that matches the crystal_name
                crystal_function = getattr(rmatscr, crystal_name)
                return crystal_function(hkl=hkl)
            except AttributeError:
                return f"Error: No method corresponds to the crystal '{crystal_name}' in the rmatscr module."
        else:
            return "Error: Crystal not found in the list."



