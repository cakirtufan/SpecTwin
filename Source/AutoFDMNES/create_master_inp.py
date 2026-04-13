# -*- coding: utf-8 -*-
"""
Created on Fri Oct 11 16:20:19 2024

@author: cakir
"""

class create_master_inp:

    def __init__(self, input_):
        self.input_ = input_

    def modify_master_inp(self, input_file):
        # Normalize path a bit (FDMNES Windows'ta da forward slash ile çalışıyor)
        inp = str(self.input_).replace("\\", "/")

        with open(input_file, 'w', encoding="utf-8") as file:
            input_count = 1
            file.write(f' {input_count}\n')
            file.write(f'{inp}\n')

        print(f"File '{input_file}' has been overwritten with new inputs.")
