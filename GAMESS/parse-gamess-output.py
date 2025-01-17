#!/usr/bin/env python3

"""
Current features:
    (1) Reference (SCF) energy
    (2) CCSD energy
    (3) Point Group symmetry
"""

import sys
import re
import pandas as pd

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

def parse_eom_states(f):
    """
    Parse the EOM states (for DIP-EOM, DEA-EOM, IP-EOM, EA-EOM, etc.).
    Returns: a list of tuples (state_index, spin, ion_en, total_en).
    """
    re_eom_summary_begin = re.compile(r"SUMMARY\s+OF\s+.*EOMCC\s+CALCULATIONS", re.IGNORECASE)
    re_eom_state = re.compile(r"^\s*(\d+)\s+(\d+)\s+([-\d\.]+)\s+([-\d\.]+)\s+CONVERGED", re.IGNORECASE)

    eom_states = []
    in_eom_summary = False

    for line in f:
        # Detect EOM summary block
        if re_eom_summary_begin.search(line):
            in_eom_summary = True
            continue

        if in_eom_summary:
            m_eom = re_eom_state.match(line)
            if m_eom:
                st_idx = int(m_eom.group(1))
                sp_mult = int(m_eom.group(2))
                ion_en = float(m_eom.group(3))
                tot_en = float(m_eom.group(4))
                eom_states.append((st_idx, sp_mult, ion_en, tot_en))
            elif not line.strip():
                # blank line => maybe the summary ended
                in_eom_summary = False

    return eom_states

# get amplitudes
def get_amplitudes(f):
    matches = []
    # Regex pattern to match the specified line
    pattern = re.compile(r"NO\.\s+\d+\s+SELECTED STATE:\s+\d+\s+EIGENVALUE:", re.IGNORECASE)
    counter=0
    for idx, line in enumerate(f):
        if pattern.search(line):
            target_line_num = idx + 2  # Third line after the matched line
            counter += 1
            if target_line_num < len(f):
                extracted_info1 = f[target_line_num].split(':')
                extracted_info1.pop()
                extracted_info1 = list(extracted_info1)
                extracted_info2 = extracted_info1[0].split()
                amps=[]
                for element in extracted_info2:
                    # extracted_info.pop()
                    amps.append(int(element[:-1]))
                    
                matches.append((amps))  # (Matched Line Number, Extracted Info)
                # print(f"[DEBUG] Found match on line {idx + 1}. Extracted info from line {target_line_num + 1}: {amps}")
            else:
                print(f"[WARNING] Matched line {idx + 1} does not have two lines following it.")
    
    if not matches:
        print("No 'NO.   XX SELECTED STATE:    XX EIGENVALUE:' lines found.")
    
    return matches

def create_character_table(point_group_name, irreps, operations, characters):
    data = {op: chars for op, chars in zip(operations, zip(*characters))}
    df = pd.DataFrame(data, index=irreps)
    return df

def get_product(point_group, irrep1, irrep2):
    # Define character tables
    character_tables = {}

    # C1
    C1_irr = ['A']
    C1_ops = ['E']
    C1_chars = [
        [1]  # Characters for A
    ]
    C1 = create_character_table('C1', C1_irr, C1_ops, C1_chars)
    character_tables['C1'] = C1

    # C2
    C2_irr = ['A', 'B']
    C2_ops = ['E', 'C2']
    C2_chars = [
        [1, 1],  # Characters for A
        [1, -1]  # Characters for B
    ]
    C2 = create_character_table('C2', C2_irr, C2_ops, C2_chars)
    character_tables['C2'] = C2

    # Ci
    Ci_irr = ['AG', 'AU']
    Ci_ops = ['E', 'I']
    Ci_chars = [
        [1, 1],   # Characters for A_g
        [1, -1]   # Characters for A_u
    ]
    Ci = create_character_table('CI', Ci_irr, Ci_ops, Ci_chars)
    character_tables['CI'] = Ci

    # Cs
    Cs_irr = ["A'", "A''"]
    Cs_ops = ['E', 'S']
    Cs_chars = [
        [1, 1],   # Characters for A'
        [1, -1]   # Characters for A''
    ]
    Cs = create_character_table('CS', Cs_irr, Cs_ops, Cs_chars)
    character_tables['CS'] = Cs

    # C2v
    C2v_irr = ['A1', 'A2', 'B1', 'B2']
    C2v_ops = ['E', 'C2', 'SV', "SPV"]
    C2v_chars = [
        [1, 1, 1, 1],    # Characters for A1
        [1, 1, -1, -1],  # Characters for A2
        [1, -1, 1, -1],  # Characters for B1
        [1, -1, -1, 1]    # Characters for B2
    ]
    C2v = create_character_table('C2V', C2v_irr, C2v_ops, C2v_chars)
    character_tables['C2V'] = C2v

    # C2h
    C2h_irr = ['AG', 'BG', 'AU', 'BU']
    C2h_ops = ['E', 'C2', 'I', 'SH']
    C2h_chars = [
        [1, 1, 1, 1],    # Characters for A_g
        [1, -1, 1, -1],  # Characters for B_g
        [1, 1, -1, -1],  # Characters for A_u
        [1, -1, -1, 1]    # Characters for B_u
    ]
    C2h = create_character_table('C2H', C2h_irr, C2h_ops, C2h_chars)
    character_tables['C2H'] = C2h

    # D2
    D2_irr = ['A', 'B1', 'B2', 'B3']
    D2_ops = ['E', 'C2(z)', 'C2(y)', 'C2(x)']
    D2_chars = [
        [1, 1, 1, 1],      # Characters for A
        [1, -1, 1, -1],    # Characters for B1
        [1, 1, -1, -1],    # Characters for B2
        [1, -1, -1, 1]      # Characters for B3
    ]
    D2 = create_character_table('D2', D2_irr, D2_ops, D2_chars)
    character_tables['D2'] = D2

    # D2h
    D2h_irr = ['AG', 'B1G', 'B2G', 'B3G', 'AU', 'B1U', 'B2U', 'B3U']
    D2h_ops = ['E', 'C2(z)', 'C2(y)', 'C2(x)', 'I', 'SH', 'SD', "SPD"]
    D2h_chars = [
        [1, 1, 1, 1, 1, 1, 1, 1],      # Characters for A_g
        [1, -1, 1, -1, -1, -1, 1, -1],# Characters for B1_g
        [1, 1, -1, -1, 1, 1, -1, 1],  # Characters for B2_g
        [1, -1, -1, 1, -1, -1, 1, -1],# Characters for B3_g
        [1, 1, 1, 1, -1, -1, -1, 1],  # Characters for A_u
        [1, -1, 1, -1, 1, 1, -1, -1], # Characters for B1_u
        [1, 1, -1, -1, -1, -1, 1, 1], # Characters for B2_u
        [1, -1, -1, 1, 1, 1, 1, -1]    # Characters for B3_u
    ]
    D2h = create_character_table('D2H', D2h_irr, D2h_ops, D2h_chars)
    character_tables['D2H'] = D2h
    if point_group not in character_tables:
        print(f"Point group '{point_group}' not found.")
        return None
    
    table = character_tables[point_group]
    
    if irrep1 not in table.index or irrep2 not in table.index:
        print(f"One or both irreps '{irrep1}', '{irrep2}' not found in point group '{point_group}'.")
        return None
    
    # Get characters for both irreps
    chars1 = table.loc[irrep1]
    chars2 = table.loc[irrep2]
    
    # Multiply characters element-wise
    product_chars = chars1 * chars2
    
    # Decompose the product into irreps
    decomposition = {}
    for irrep in table.index:
        # Calculate the inner product (sum of products divided by group order)
        inner_product = sum(product_chars * table.loc[irrep]) / len(product_chars)
        if inner_product > 0:
            decomposition[irrep] = int(inner_product)
    
    return decomposition
        
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
    
    # Print EOM states
    eom_states=parse_eom_states(f)
    amps = get_amplitudes(f)
    print("*****************************")
    st = get_product(pg,'B1U','B3G')
    print(st)

    # print(eom_states)
    print(f"=== {calc} States (for DIP, DEA, IP, EA, etc.) ===")
    cols=['State', 'mult', 'omega (H)', 'Total E (H)']
    df_eom=pd.DataFrame(eom_states, columns=cols)
    # print(df_eom)
    df_eom['amplitudes']=amps
    # print(df_eom)
                 
         
if __name__ == "__main__":
    main()
    
    