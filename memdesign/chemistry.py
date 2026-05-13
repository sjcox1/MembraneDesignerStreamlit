"""Feed water chemistry calculations for RO/NF/UF design.

Simplified TDS-only model (full ionic analysis to be added later).
Osmotic pressure derived from van't Hoff assuming NaCl-equivalent TDS:
    π = 2 × (TDS/58440) × R × T  →  π ≈ 8.48×10⁻⁴ × TDS  bar at 25°C
"""
import math

# Derived from van't Hoff for NaCl: 2 × R / 58.44 (g/mol) in bar·L/mg units
_PI_COEFF_BAR_PER_MGL = 8.48e-4

# Arrhenius activation energy parameter for membrane water permeability (Kelvin)
_TCF_ACTIVATION_ENERGY_K = 2640.0


def osmotic_pressure(tds_mg_l: float, temperature_c: float = 25.0) -> float:
    """Osmotic pressure in bar. NaCl-equivalent TDS, ideal van't Hoff.

    Temperature correction scales linearly with absolute temperature (π ∝ T).
    """
    if tds_mg_l < 0:
        raise ValueError(f"TDS must be non-negative, got {tds_mg_l}")
    pi_25 = tds_mg_l * _PI_COEFF_BAR_PER_MGL
    return pi_25 * (temperature_c + 273.15) / 298.15


def temperature_correction_factor(temperature_c: float) -> float:
    """Arrhenius TCF for membrane water permeability, normalised to 25°C.

    A_effective = A_25 × TCF(T)
    """
    return math.exp(
        _TCF_ACTIVATION_ENERGY_K * (1.0 / 298.15 - 1.0 / (temperature_c + 273.15))
    )
