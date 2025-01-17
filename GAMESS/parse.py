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

def parse_reference_energy(lines):
    """
    Parse the reference (SCF) energy from the file lines.
    Returns: float or None
    """
    re_ref = re.compile(
        r"(?:FINAL\s+(?:ROHF|UHF|HF)\s+ENERGY\s+IS\s+|\bREFERENCE ENERGY:\s+)([-\d\.]+)",
        re.IGNORECASE
    )
    reference_energy = None

    for line in lines:
        m_ref = re_ref.search(line)
        if m_ref:
            reference_energy = float(m_ref.group(1))
            break  # Stop after first match

    return reference_energy

def parse_ccsd_energy(lines):
    """
    Parse the CCSD total energy from the file lines.
    Returns: float or None
    """
    re_ccsd = re.compile(r"^\s*CCSD\s+ENERGY:\s+([-\d\.]+)", re.IGNORECASE)
    ccsd_energy = None

    for line in lines:
        m_ccsd = re_ccsd.search(line)
        if m_ccsd:
            ccsd_energy = float(m_ccsd.group(1))
            break  # Stop after first match

    return ccsd_energy

def parse_point_group(lines):
    """
    Parse the point group and the order of the principal axis (for 'N').
    Returns: point_group (str or None), axis_order_str (str or None)
    """
    re_pg = re.compile(
        r"THE\s+POINT\s+GROUP\s+OF\s+THE\s+MOLECULE\s+IS\s+(\S+)",
        re.IGNORECASE
    )
    re_axis_order = re.compile(
        r"THE\s+ORDER\s+OF\s+THE\s+PRINCIPAL\s+AXIS\s+IS\s+(\d+)",
        re.IGNORECASE
    )

    point_group = None
    axis_order_str = None

    for line in lines:
        m_pg = re_pg.search(line)
        if m_pg:
            point_group = m_pg.group(1).upper().strip()

        m_ax = re_axis_order.search(line)
        if m_ax:
            axis_order_str = m_ax.group(1).strip()

    # If there's an axis order, and the point_group has "N", replace it
    if point_group and axis_order_str and "N" in point_group:
        point_group = point_group.replace("N", axis_order_str)

    return point_group

def parse_mo_data(lines):
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

    for line in lines:
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

def parse_eom_states(lines):
    """
    Parse the EOM states (for DIP-EOM, DEA-EOM, IP-EOM, EA-EOM, etc.).
    Returns: a list of tuples (state_index, spin, ion_en, total_en).
    """
    re_eom_summary_begin = re.compile(r"SUMMARY\s+OF\s+.*EOMCC\s+CALCULATIONS", re.IGNORECASE)
    re_eom_state = re.compile(r"^\s*(\d+)\s+(\d+)\s+([-\d\.]+)\s+([-\d\.]+)\s+CONVERGED", re.IGNORECASE)

    eom_states = []
    in_eom_summary = False

    for line in lines:
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

def parse_gamess_output(filename):
    """
    Orchestrates all parsing tasks and returns a tuple containing:
        reference_energy, ccsd_energy, point_group,
        mo_energies, mo_irreps, eom_states
    """

    # Read all lines
    with open(filename, 'r') as f:
        lines = f.readlines()

    ref_energy = parse_reference_energy(lines)
    ccsd_energy = parse_ccsd_energy(lines)
    point_group = parse_point_group(lines)
    mo_energies, mo_irreps = parse_mo_data(lines)
    eom_states = parse_eom_states(lines)

    return ref_energy, ccsd_energy, point_group, mo_energies, mo_irreps, eom_states

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
