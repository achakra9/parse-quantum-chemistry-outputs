#!/usr/bin/env python3
"""
Parse a GAMESS output file and extract:
1) Reference (SCF) energy
2) CCSD total energy
3) MO energies and irreps from the MO block,
   labeled as "EIGENVECTOR(S)" or "MOLECULAR ORBITALS"
   or something similar.

Modifications made:
- We look for any line containing "EIGENVECTOR" or "MOLECULAR ORBITALS"
  (case-insensitive).
- We DO NOT immediately exit the block upon seeing lines with "-----".
- We allow a more flexible irreps regex pattern for lines like B2U(1).
"""

import sys
import re

def parse_gamess_output(filename):
    # -------------------------------------------------------------------
    # 1) Regex patterns for SCF and CCSD energies
    # -------------------------------------------------------------------
    re_ref = re.compile(
        r"(?:FINAL\s+(?:ROHF|UHF|HF)\s+ENERGY\s+IS\s+|\bREFERENCE ENERGY:\s+)([-\d\.]+)",
        re.IGNORECASE
    )
    re_ccsd = re.compile(
        r"^\s*CCSD\s+ENERGY:\s+([-\d\.]+)",
        re.IGNORECASE
    )

    reference_energy = None
    ccsd_energy = None

    # -------------------------------------------------------------------
    # 2) Collect MO energies & irreps
    # -------------------------------------------------------------------
    mo_energies = []
    mo_irreps   = []

    in_mo_block     = False
    energies_buffer = None

    # Let's allow scientific notation, e.g. -2.01E+01, etc.
    def parse_float_line(line):
        tokens = line.split()
        floats = []
        for t in tokens:
            # We'll try a broader approach
            # e.g. -1.2345e+01
            try:
                val = float(t.replace('D','E'))  # if there's a D for exponent
                floats.append(val)
            except ValueError:
                return None
        return floats

    # We expand the irreps pattern to handle variations like "B1U", "B2g(2)"
    # Rough pattern: starts with A or B, optional digit, then g/u, plus optional (digit).
    # e.g. AG, B1U, B2g, B2U(1), B2G(3), etc.
    irreps_pattern = re.compile(r"^[AB]\d?[g-uG-U](?:\(\d+\))?$")

    def line_is_irrep_list(line):
        tokens = line.strip().split()
        if not tokens:
            return False
        for tok in tokens:
            if not irreps_pattern.match(tok):
                return False
        return True

    # -------------------------------------------------------------------
    # 3) File reading
    # -------------------------------------------------------------------
    with open(filename, 'r') as f:
        for line in f:
            # a) Check reference energy
            match_ref = re_ref.search(line)
            if match_ref:
                reference_energy = float(match_ref.group(1))

            # b) Check CCSD energy
            match_ccsd = re_ccsd.search(line)
            if match_ccsd:
                ccsd_energy = float(match_ccsd.group(1))

            # c) Check if line starts the MO block
            #    e.g. "EIGENVECTOR", "EIGENVECTORS", or "MOLECULAR ORBITALS" in uppercase
            upper_line = line.upper()
            if ("EIGENVECTOR" in upper_line) or ("MOLECULAR ORBITALS" in upper_line):
                in_mo_block     = True
                energies_buffer = None
                continue

            # d) If we are in the MO block, parse lines
            if in_mo_block:
                raw = line.strip()
                # If blank, skip
                if not raw:
                    continue

                # Attempt floats
                float_vals = parse_float_line(raw)
                if float_vals is not None and len(float_vals) > 0:
                    # This is an energies line
                    energies_buffer = float_vals
                    continue

                # Possibly irreps line
                if line_is_irrep_list(raw):
                    tokens = raw.split()
                    # Pair with energies
                    if energies_buffer and len(tokens) == len(energies_buffer):
                        mo_energies.extend(energies_buffer)
                        mo_irreps.extend(tokens)
                        energies_buffer = None
                    continue

                # If line is something else (maybe "Occupied Orbitals" or "Vectors"?),
                # we do nothing. We do NOT break out. Because in many outputs,
                # dashed lines occur or there's more content after.
                # If you'd like to break at some prompt, you can add logic here.

    return reference_energy, ccsd_energy, mo_energies, mo_irreps

def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_gamess.py <gamess_output_file>")
        sys.exit(1)

    filename = sys.argv[1]
    ref_energy, ccsd_energy, energies, irreps = parse_gamess_output(filename)

    print("=== GAMESS Energy & MO Report ===\n")

    # 1) Print the reference (SCF) energy
    if ref_energy is not None:
        print(f"Hartree-Fock (SCF) Energy: {ref_energy:.8f} Hartree")
    else:
        print("Hartree-Fock (SCF) energy not found.")

    # 2) Print CCSD energy
    if ccsd_energy is not None:
        print(f"CCSD Energy:              {ccsd_energy:.8f} Hartree")
    else:
        print("CCSD energy not found.")

    # 3) Print MO energies & irreps
    print("\nMolecular Orbitals (energy + irrep):")
    n = min(len(energies), len(irreps))
    if n == 0:
        print("No MO data found (or recognized) in the output.")
    else:
        for i in range(n):
            print(f" MO #{i+1:2d}:  Energy = {energies[i]:11.5f}  Irrep = {irreps[i]}")

if __name__ == "__main__":
    main()
