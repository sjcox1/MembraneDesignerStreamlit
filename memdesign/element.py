"""Single membrane element simulation using the solution-diffusion model.

Model summary
-------------
Water flux:   Jw = A_eff × NDP
              NDP = P_feed_avg − P_permeate − (π_membrane − π_permeate)

Salt flux:    Js = B × (Cm − Cp)
              Cp = B × Cm / (Jw + B)   [analytical solution]

Concentration polarisation:
              Cm = Cb × exp(Jw / k)
              where Cb = arithmetic mean of inlet/outlet bulk concentration

Pressure drop:
              ΔP = ΔP_ref × (Q_feed / Q_ref) ^ 1.7
"""
import math
from dataclasses import dataclass

from .chemistry import osmotic_pressure, temperature_correction_factor
from .membrane_db import MembraneElement

_DP_EXPONENT = 1.7      # Empirical exponent for feed-spacer pressure drop
_MAX_ITER = 60
_CONVERGENCE_TOL = 1e-7
_DAMPING = 0.35         # Under-relaxation factor for iteration stability


@dataclass
class ElementResult:
    feed_flow_m3h: float
    feed_tds: float
    feed_pressure_bar: float

    permeate_flow_m3h: float
    permeate_tds: float

    concentrate_flow_m3h: float
    concentrate_tds: float
    concentrate_pressure_bar: float

    flux_lmh: float
    ndp_bar: float
    cp_factor: float
    element_recovery: float
    observed_rejection: float


def _pressure_drop(feed_flow_m3h: float, element: MembraneElement) -> float:
    """Feed-side pressure drop across one element (bar)."""
    ratio = feed_flow_m3h / element.ref_feed_flow_m3h
    return element.ref_pressure_drop_bar * (ratio ** _DP_EXPONENT)


def simulate_element(
    feed_flow_m3h: float,
    feed_tds: float,
    feed_pressure_bar: float,
    element: MembraneElement,
    temperature_c: float = 25.0,
    permeate_pressure_bar: float = 0.0,
) -> ElementResult:
    """Simulate one membrane element.

    Parameters
    ----------
    feed_flow_m3h : Feed flow rate, m³/h
    feed_tds : Feed TDS, mg/L
    feed_pressure_bar : Feed-side inlet pressure, bar (gauge)
    element : Membrane element specification
    temperature_c : Feed temperature, °C
    permeate_pressure_bar : Permeate backpressure, bar (gauge)

    Returns
    -------
    ElementResult
    """
    area = element.area_m2
    A_eff = element.a_coeff * temperature_correction_factor(temperature_c)
    B = element.b_coeff
    k = element.mass_transfer_coeff_lmh

    dp = _pressure_drop(feed_flow_m3h, element)
    p_avg = feed_pressure_bar - dp / 2.0

    # Iterative solution: converge on element recovery (r)
    r = 0.10  # initial guess

    for _ in range(_MAX_ITER):
        Qp = feed_flow_m3h * r
        Qc = feed_flow_m3h - Qp

        Cc = feed_tds * feed_flow_m3h / Qc
        Cb = (feed_tds + Cc) / 2.0

        Jw = Qp * 1000.0 / area  # LMH

        # Concentration polarisation — cap exponent to avoid overflow
        CF = math.exp(min(Jw / k, 1.5))
        Cm = Cb * CF

        # Analytical permeate concentration from Cp = B·Cm / (Jw + B)
        Cp = (B * Cm / (Jw + B)) if Jw > 0 else Cm

        pi_m = osmotic_pressure(Cm, temperature_c)
        pi_p = osmotic_pressure(Cp, temperature_c)
        NDP = max(p_avg - permeate_pressure_bar - (pi_m - pi_p), 0.0)

        Jw_calc = min(A_eff * NDP, element.max_flux_lmh)
        Qp_new = min(Jw_calc * area / 1000.0, feed_flow_m3h * 0.99)
        r_new = Qp_new / feed_flow_m3h

        if abs(r_new - r) < _CONVERGENCE_TOL:
            r = r_new
            break

        r = r + _DAMPING * (r_new - r)

    # Final state from converged r
    Qp = feed_flow_m3h * r
    Qc = feed_flow_m3h - Qp
    Cc = feed_tds * feed_flow_m3h / Qc
    Cb = (feed_tds + Cc) / 2.0
    Jw = Qp * 1000.0 / area
    CF = math.exp(min(Jw / k, 1.5))
    Cm = Cb * CF
    Cp = (B * Cm / (Jw + B)) if Jw > 0 else Cm
    pi_m = osmotic_pressure(Cm, temperature_c)
    pi_p = osmotic_pressure(Cp, temperature_c)
    NDP = max(p_avg - permeate_pressure_bar - (pi_m - pi_p), 0.0)

    return ElementResult(
        feed_flow_m3h=feed_flow_m3h,
        feed_tds=feed_tds,
        feed_pressure_bar=feed_pressure_bar,
        permeate_flow_m3h=Qp,
        permeate_tds=Cp,
        concentrate_flow_m3h=Qc,
        concentrate_tds=Cc,
        concentrate_pressure_bar=feed_pressure_bar - dp,
        flux_lmh=Jw,
        ndp_bar=NDP,
        cp_factor=CF,
        element_recovery=r,
        observed_rejection=1.0 - Cp / Cm if Cm > 0 else 0.0,
    )
