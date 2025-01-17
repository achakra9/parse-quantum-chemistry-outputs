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

def parse_mo_data(f):
    """
    Parse the MO energies and irreps from the EIGENVECTOR or MOLECULAR ORBITALS block.
    Returns: (mo_energies, mo_irreps), where each is a list.
    """
    # Regex helpers
    irreps_pattern = re.compile(r"^[AB]\d?[g-uG-U](?:\(\d+\))?$")

    def parse_float_line(line):
        """Try parsing a line of floats (replacing D with E for exponents)."""
        tokens = line.split()
        floats = []
        for t in tokens:
            t_for_exp = t.replace('D', 'E')
            try:
                val = float(t_for_exp)
                floats.append(val)
            except ValueError:
                return None
        return floats

    def line_is_irrep_list(line):
        tokens = line.strip().split()
        if not tokens:
            return False
        for tok in tokens:
            if not irreps_pattern.match(tok):
                return False
        return True

    mo_energies = []
    mo_irreps = []

    in_mo_block = False
    energies_buffer = None

    for line in f:
        upper_line = line.upper()

        # Detect beginning of MO block
        if ("EIGENVECTOR" in upper_line) or ("MOLECULAR ORBITALS" in upper_line):
            in_mo_block = True
            energies_buffer = None
            continue

        if in_mo_block:
            raw = line.strip()
            if not raw:
                # blank line => skip
                continue

            # Try to parse a line of floats
            float_vals = parse_float_line(raw)
            if float_vals is not None and len(float_vals) > 0:
                energies_buffer = float_vals
                continue

            # If line looks like a list of irreps
            if line_is_irrep_list(raw):
                tokens = raw.split()
                # Only extend if energies_buffer and irreps have the same length
                if energies_buffer and len(tokens) == len(energies_buffer):
                    mo_energies.extend(energies_buffer)
                    mo_irreps.extend(tokens)
                energies_buffer = None
                continue

    return mo_energies, mo_irreps

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
    # extract point group symmetry
    pg = get_pointgroup(f) 
    print(f"POINT GROUP SYMMETRY: {pg}")
    #
    # Print MO energies & irreps
    energies, irreps = parse_mo_data(f)
    print("\nMolecular Orbitals (energy + irrep):")
    n = min(len(energies), len(irreps))
    if n == 0:
        print("No MO data found (or recognized) in the output.")
    else:
        for i in range(n):
            print(f" MO #{i+1:2d}:  Energy = {energies[i]:10.5f}  Irrep = {irreps[i]}")
    #
    # extract CCSD energy
    ccsd_e, ccsd_corr = get_ccsd(f)
    print(f"CCSD ENERGY:        {ccsd_e} Hartree  CORR. E: {ccsd_corr} Hartree")
    
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
    
    