# -*- coding: utf-8 -*-
"""
Created on Fri Oct 11 16:17:44 2024

@author: cakir
"""

import xraydb

class XrayDBHandler:
    def __init__(self):
        self.xdb = xraydb.XrayDB()

    def get_elements(self):
        return sorted(self.xdb.atomic_symbols)
    
    def get_atomic_numbers(self, element): 
        return self.xdb.atomic_number(element)

    def get_lines_by_element(self, element):
        return self.xdb.xray_lines(element)

    def get_line_energy(self, element, line):
        return self.xdb.xray_lines(element)[line].energy
    def get_edges(self, element):
        # Fetch available X-ray edges for the given element
        return self.xdb.xray_edges(element).keys()
    def get_edge_energy(self, element, edge):
        return self.xdb.xray_edges(element)[edge].energy