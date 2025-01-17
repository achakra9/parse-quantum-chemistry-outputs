#!/usr/bin/env python3
"""
Parse a GAMESS output file and extract:
1) Reference (SCF) energy
2) CCSD total energy
"""

import sys
import re

def parse_gamess_output(filename):
    # Regex patterns to find energies
    # 1) Reference (ROHF or UHF) energy lines often look like:
    #       FINAL ROHF ENERGY IS     -148.7916464072 ...
    #    or sometimes:
    #       FINAL UHF ENERGY IS  ...
    #    or occasionally:
    #       REFERENCE ENERGY:  ...
    re_ref = re.compile(
        r"(?:FINAL\s+(?:ROHF|UHF)\s+ENERGY\s+IS\s+|\bREFERENCE ENERGY:\s+)([-\d\.]+)",
        re.IGNORECASE
    )

    # 2) CCSD total energy lines often look like:
    #       CCSD ENERGY:     -149.1437096354 ...
    #    or a line reading:
    #       SUMMARY OF CCSD RESULTS
    #       CCSD ENERGY: ...
    re_ccsd = re.compile(
        r"^\s*CCSD\s+ENERGY:\s+([-\d\.]+)",
        re.IGNORECASE
    )

    reference_energy = None
    ccsd_energy = None

    with open(filename, 'r') as f:
        for line in f:
            # Try matching the reference energy
            m_ref = re_ref.search(line)
            if m_ref:
                reference_energy = float(m_ref.group(1))

            # Try matching the CCSD total energy
            m_ccsd = re_ccsd.search(line)
            if m_ccsd:
                ccsd_energy = float(m_ccsd.group(1))

    return reference_energy, ccsd_energy

def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_gamess.py <gamess_output_file>")
        sys.exit(1)

    filename = sys.argv[1]
    ref, ccsd = parse_gamess_output(filename)

    print("=== GAMESS Energy Report ===")
    if ref is not None:
        print(f"Reference Energy (SCF):  {ref:.8f} Hartree")
    else:
        print("Reference energy not found.")

    if ccsd is not None:
        print(f"CCSD Energy:            {ccsd:.8f} Hartree")
    else:
        print("CCSD energy not found.")

if __name__ == "__main__":
    main()
