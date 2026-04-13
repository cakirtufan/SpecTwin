# -*- coding: utf-8 -*-
"""
Created on Fri Oct 11 16:18:26 2024

@author: cakir
"""

from mp_api.client import MPRester
import os

class MPR:
    def __init__(self):
        self.API_KEY = "s0sfFNfYiGN0Wb9VdmQOoI0I0dNCAegh"
        self.mpids = []
        self.mpformulas = []
        
    def find_id_and_formulas(self, elements_included):
        """Find material IDs and formulas based on included and excluded elements."""
        with MPRester(self.API_KEY) as mpr:
            if elements_included:
                # Prepare search filters
                
                docs = mpr.summary.search(
                    elements=elements_included,                  
                    fields=["material_id", "formula_pretty"]
                    )

                # Collect material IDs and formulas from results
                self.mpformulas = [doc.formula_pretty for doc in docs]
                self.mpids = [doc.material_id for doc in docs]
                
                return self.mpformulas, self.mpids
            
            return [], []  # Return empty lists if no included elements

    def get_cif_data(self, mpid, selected_formula):
        """Retrieve the CIF file for a specific material by its material ID."""
        cwd = os.getcwd()
    
        # build absolute output directory
        outdir = os.path.join(
            cwd, "AutoFDMNES", "fdmnes_Win64", "Sim", "Test_stand", "in"
        )
    
        # make sure directory exists
        os.makedirs(outdir, exist_ok=True)
    
        file_name = f"{selected_formula}_{mpid}.cif"
        filepath = os.path.join(outdir, file_name)
    
        with MPRester(self.API_KEY) as mpr:
            structure = mpr.get_structure_by_material_id(mpid)
            structure.to(fmt="cif", filename=filepath)
    
        print(f"CIF data saved: {filepath}")
        return filepath
            
        

