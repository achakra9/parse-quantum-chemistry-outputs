#!/usr/bin/env python3

"""
Current features:
    (1) Reference (SCF) energy
    (2) CCSD energy
    (3) Point Group symmetry
"""

import sys
import re

# Reference
def get_reference(f):
    for line in f:
        if "REFERENCE ENERGY:     " in line:
            x = line.split()
            break
            
    return x[2]

# CCSD
def get_ccsd(f):
    for line in f:
        if "CCSD ENERGY:" in line:
            x = line.split()
            break
            
    return x[2],x[5]

# Point Group
def get_pointgroup(f):
    for line in f:
        if "THE POINT GROUP OF THE MOLECULE IS " in line:
            x = line.split()
        elif "THE ORDER OF THE PRINCIPAL AXIS IS " in line:
            y = line.split()
            break
    
    pg = x[7]
    pg = pg.replace("N",y[7])
     
    return pg

# further parsing
def proceed_further(f):
    for line in f:
        if 'eominp' or 'EOMINP' in line:
            return True
    else:
        return False   
    
# Type of Calculation
def get_calc(f):
    pattern = re.compile(r"BEGINNING\s+(.*?)\s+ITERATIONS\s+FOR\s+STATE\s+(\d+)", re.IGNORECASE)
    for line in f:
        match=pattern.search(line)
        if match:
            info=match.group(1)
            break
               
    return info
        
def main():
    if len(sys.argv) < 2:
        print("Usage: ./parse-gamess-output.py <gamess_output_file>")
        sys.exit(1)
        
    filename = sys.argv[1]
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            f = file.readlines()
    except FileNotFoundError:
        print(f"Error: File not found - {filename}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        sys.exit(1)
    
    print("")
    print("==== GAMESS OUTPUT PARSING SCRIPT ====")
    print("")
    print(f"Parsing the {filename} file.")
    print("")
    #  
    # extract the reference energy
    ref_e = get_reference(f)
    print(f"REFERENCE ENERGY:  {ref_e} Hartree")
    # 
    # extract CCSD energy
    ccsd_e, ccsd_corr = get_ccsd(f)
    print(f"CCSD ENERGY:        {ccsd_e} Hartree  CORR. E: {ccsd_corr} Hartree")
    #
    # extract point group symmetry
    pg = get_pointgroup(f) 
    print(f"POINT GROUP SYMMETRY: {pg}")
    
    # Check if further parsing is needed
    stat = proceed_further(f)
    if stat:
        print("EXCITED STATE CALCULATION WAS PERFORMED")
    else:
        print("DONE WITH ALL PARSING")
        sys.exit(0)
        
    print("proceeding with further extractions.")
    calc = get_calc(f)
    print(f"{calc} calculation performed")
         
         
if __name__ == "__main__":
    main()
    
    