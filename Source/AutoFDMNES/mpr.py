# -*- coding: utf-8 -*-
"""
Created on Fri Oct 11 16:18:26 2024

@author: cakir
"""

from mp_api.client import MPRester
import os
from pathlib import Path

class MPR:
    def __init__(self):
        self.API_KEY = os.environ.get("MP_API_KEY")
        self.mpids = []
        self.mpformulas = []

    def _get_api_key(self):
        if not self.API_KEY:
            raise RuntimeError("Materials Project API key is missing. Set MP_API_KEY in your environment.")
        return self.API_KEY
        
    def find_id_and_formulas(self, elements_included):
        """Find material IDs and formulas based on included and excluded elements."""
        with MPRester(self._get_api_key()) as mpr:
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
        auto_root = Path(__file__).resolve().parent
    
        # build absolute output directory
        outdir = auto_root / "fdmnes_Win64" / "Sim" / "Test_stand" / "in"
    
        # make sure directory exists
        outdir.mkdir(parents=True, exist_ok=True)
    
        file_name = f"{selected_formula}_{mpid}.cif"
        filepath = outdir / file_name
    
        with MPRester(self._get_api_key()) as mpr:
            structure = mpr.get_structure_by_material_id(mpid)
            structure.to(fmt="cif", filename=str(filepath))
    
        print(f"CIF data saved: {filepath}")
        return filepath
            
        

