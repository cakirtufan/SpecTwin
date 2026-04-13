# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 09:58:06 2025

@author: cakir
"""

import h5py
import numpy as np

class HDF5Reader:
    """
    Class to read HDF5 files and extract relevant data.
    """
    def __init__(self, h5_file):
        self.h5_file = h5_file
    
    def read_data(self, channel_start, channel_end):
        """
        Reads HDF5 data, extracting a specific region around the given channel.
        :param find_channel: The detected channel from XRF analysis.
        :return: The extracted NumPy array.
        """
        with h5py.File(self.h5_file, 'r') as file:
            np_raw_data = np.array(file.get("Raw"))[35:-35, 10:-10, channel_start:channel_end]
        return np.sum(np.sum(np_raw_data, 2), 0)
    
    def read_2d_data(self, channel_start, channel_end):
          
        if channel_start and channel_end:
        
            with h5py.File(self.h5_file, 'r') as file:
                
                np_raw_data= np.array(file.get("Raw"))[:,:,channel_start:channel_end]
                
            return np.sum(np_raw_data,2)
        
        else:
            
            print("Hoppalaaa")
            
    def read_raw(self):
        
        with h5py.File(self.h5_file) as file:
            
            return np.array(file.get("Raw"))
        
    def save_h5(self, sum_data):
        
        with h5py.File(self.h5_file, "w") as f:
            
            f.create_dataset("Raw", data = sum_data)
            
            