#!/usr/bin/env python3

"""
Current features:
    (1) Extract Reference (SCF) energy
"""

import sys
import re

def get_reference(f):
    for line in f:
        if "REFERENCE ENERGY:     " in line:
            x = line.split()
            
    return x[2]
            
        

def main():
    if len(sys.argv) < 2:
        print("Usage: ./parse-gamess-output.py <gamess_output_file>")
        sys.exit(1)
        
    filename = sys.argv[1]
    
    with open(filename, 'r') as f:
        print("")
        print("==== GAMESS OUTPUT PARSING SCRIPT ====")
        print("")
        print("Parsing the " + filename + " file.")
        print("")
    
        # extract the reference energy
        ref_e = get_reference(f)
        print("REFERENCE ENERGY: "+ ref_e + " Hartree")
    
    
    
if __name__ == "__main__":
    main()
    
    