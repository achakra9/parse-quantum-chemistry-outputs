#!/usr/bin/env python3
"""
Parse a GAMESS output file for:
  (1) Reference (SCF) energy
  (2) CCSD total energy
  (3) Point group
  (4) Order of principal axis, and replace 'N' in the point group with this number
  (5) MO energies + irreps from EIGENVECTOR or MOLECULAR ORBITALS block
  (6) EOM states from DIP-EOM, DEA-EOM, IP-EOM, or EA-EOM summary
"""

import sys
import re

def parse_gamess_output(filename):
    # -------------------------------------------------------------------
    # Regex patterns
    # -------------------------------------------------------------------
    # 1) Reference (SCF) energy
    re_ref = re.compile(
        r"(?:FINAL\s+(?:ROHF|UHF|HF)\s+ENERGY\s+IS\s+|\bREFERENCE ENERGY:\s+)([-\d\.]+)",
        re.IGNORECASE
    )

    # 2) CCSD total energy
    re_ccsd = re.compile(
        r"^\s*CCSD\s+ENERGY:\s+([-\d\.]+)",
        re.IGNORECASE
    )

    # 3) Point group
    re_pg = re.compile(
        r"THE\s+POINT\s+GROUP\s+OF\s+THE\s+MOLECULE\s+IS\s+(\S+)",
        re.IGNORECASE
    )

    # 4) Order of principal axis
    re_axis_order = re.compile(
        r"THE\s+ORDER\s+OF\s+THE\s+PRINCIPAL\s+AXIS\s+IS\s+(\d+)",
        re.IGNORECASE
    )

    # 5) EOM states (generic format):
    #    STATE  SPIN   IONIZATION/EA/...  TOTAL ...  CONVERGED
    #
    re_eom_state = re.compile(
        r"^\s*(\d+)\s+(\d+)\s+([-\d\.]+)\s+([-\d\.]+)\s+CONVERGED",
        re.IGNORECASE
    )

    # We'll detect *any* line containing "SUMMARY OF ... EOMCC CALCULATIONS"
    # That way it doesn't matter if it's DIP-EOMCC, DEA-EOMCC, IP-EOMCC, etc.
    re_eom_summary_begin = re.compile(
        r"SUMMARY\s+OF\s+.*EOMCC\s+CALCULATIONS",
        re.IGNORECASE
    )

    # -------------------------------------------------------------------
    # Data containers
    # -------------------------------------------------------------------
    reference_energy = None
    ccsd_energy      = None
    point_group      = None
    axis_order_str   = None

    mo_energies = []
    mo_irreps   = []

    eom_states  = []  # to store (state_index, spin, ion_en, total_en)

    # Flags to detect blocks
    in_mo_block       = False
    in_eom_summary    = False
    energies_buffer   = None

    # -------------------------------------------------------------------
    # Helper functions
    # -------------------------------------------------------------------
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

    # This pattern matches something like "AG", "B1U", "B2G", etc.
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
    # Reading the file
    # -------------------------------------------------------------------
    with open(filename, 'r') as f:
        for line in f:
            # 1) Check reference energy
            m_ref = re_ref.search(line)
            if m_ref:
                reference_energy = float(m_ref.group(1))

            # 2) Check CCSD energy
            m_ccsd = re_ccsd.search(line)
            if m_ccsd:
                ccsd_energy = float(m_ccsd.group(1))

            # 3) Check for point group
            m_pg = re_pg.search(line)
            if m_pg:
                point_group = m_pg.group(1).upper().strip()

            # 4) Check for order of principal axis
            m_ax = re_axis_order.search(line)
            if m_ax:
                axis_order_str = m_ax.group(1).strip()

            # 5) Detect beginning of the MO block
            upper_line = line.upper()
            if ("EIGENVECTOR" in upper_line) or ("MOLECULAR ORBITALS" in upper_line):
                in_mo_block = True
                energies_buffer = None
                continue

            # If inside MO block, parse lines for energies/irreps
            if in_mo_block:
                raw = line.strip()
                if not raw:
                    continue

                float_vals = parse_float_line(raw)
                if float_vals is not None and len(float_vals) > 0:
                    energies_buffer = float_vals
                    continue

                if line_is_irrep_list(raw):
                    tokens = raw.split()
                    if energies_buffer and len(tokens) == len(energies_buffer):
                        mo_energies.extend(energies_buffer)
                        mo_irreps.extend(tokens)
                    energies_buffer = None
                    continue
                # If the line doesn't match energies or irreps, we ignore.

            # 6) Detect start of EOM summary block
            #    e.g. "---- SUMMARY OF DIP-EOMCC CALCULATIONS ----"
            #    or    "---- SUMMARY OF DEA-EOMCC CALCULATIONS ----", etc.
            if re_eom_summary_begin.search(line):
                in_eom_summary = True
                continue

            # If we are in an EOM summary block, look for lines describing states
            if in_eom_summary:
                m_eom = re_eom_state.match(line)
                if m_eom:
                    st_idx  = int(m_eom.group(1))
                    sp_mult = int(m_eom.group(2))
                    ion_en  = float(m_eom.group(3))
                    tot_en  = float(m_eom.group(4))
                    eom_states.append((st_idx, sp_mult, ion_en, tot_en))
                elif not line.strip():
                    # blank line => maybe the summary ended
                    in_eom_summary = False

    # -------------------------------------------------------------------
    # If there's an axis order, and the point_group has "N", replace it
    # -------------------------------------------------------------------
    if point_group and axis_order_str and "N" in point_group:
        point_group = point_group.replace("N", axis_order_str)

    return reference_energy, ccsd_energy, point_group, mo_energies, mo_irreps, eom_states

def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_gamess.py <gamess_output_file>")
        sys.exit(1)

    filename = sys.argv[1]
    (ref_energy, ccsd_energy, point_group,
     energies, irreps, eom_states) = parse_gamess_output(filename)

    print("=== GAMESS Energy & MO Report ===\n")
    # 1) Reference (SCF) energy
    if ref_energy is not None:
        print(f"Hartree-Fock (SCF) Energy:   {ref_energy:.8f} Hartree")
    else:
        print("Hartree-Fock (SCF) energy not found.")

    # 2) CCSD total energy
    if ccsd_energy is not None:
        print(f"CCSD Energy:                {ccsd_energy:.8f} Hartree")
    else:
        print("CCSD energy not found.")

    # 3) Print point group
    if point_group:
        print(f"Point Group Used:           {point_group}")
    else:
        print("Point group not found in output.")

    # 4) Print MO energies & irreps
    print("\nMolecular Orbitals (energy + irrep):")
    n = min(len(energies), len(irreps))
    if n == 0:
        print("No MO data found (or recognized) in the output.")
    else:
        for i in range(n):
            print(f" MO #{i+1:2d}:  Energy = {energies[i]:10.5f}  Irrep = {irreps[i]}")

    # 5) Print EOM states
    print("\n=== EOM States (for DIP, DEA, IP, EA, etc.) ===")
    if not eom_states:
        print("No EOM states found in output.")
    else:
        print(f"{'State':>5s}  {'Spin':>4s}  {'Ion_En (Ha)':>12s}  {'Total_E (Ha)':>14s}")
        for st_idx, sp_mult, ion_en, tot_en in eom_states:
            print(f"{st_idx:5d}  {sp_mult:4d}  {ion_en:12.6f}  {tot_en:14.6f}")

if __name__ == "__main__":
    main()
