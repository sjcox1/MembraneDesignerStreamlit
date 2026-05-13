"""Membrane element specifications and library.

A coefficient (water permeability): L/(m²·h·bar)  — how easily water passes
B coefficient (salt permeability): L/(m²·h)        — how easily salt passes
Higher A → more productive. Lower B → better rejection.

Generic elements are representative of each technology class using published
ranges from FilmTec, Hydranautics, and Toray datasheets. Actual manufacturer
elements can be added to MEMBRANE_LIBRARY using the same dataclass.
"""
from dataclasses import dataclass, field
from enum import Enum


class MembraneType(str, Enum):
    BWRO = "BWRO"
    SWRO = "SWRO"
    NF = "NF"


@dataclass(frozen=True)
class MembraneElement:
    name: str
    type: MembraneType

    # Transport coefficients at 25°C
    a_coeff: float          # Water permeability, L/(m²·h·bar)
    b_coeff: float          # Salt permeability, L/(m²·h)

    # Physical dimensions
    area_m2: float          # Active membrane area, m²

    # Operating limits
    max_flux_lmh: float     # Maximum permeate flux
    min_flux_lmh: float     # Minimum flux (scaling/fouling control)
    max_feed_pressure_bar: float

    # Pressure drop at reference feed flow (used to scale ΔP with actual flow)
    ref_pressure_drop_bar: float
    ref_feed_flow_m3h: float

    # Film theory mass transfer coefficient for CP calculation
    mass_transfer_coeff_lmh: float = 120.0


# ---------------------------------------------------------------------------
# Generic 8" × 40" elements (standard 37.2 m² / 400 ft² active area)
# ---------------------------------------------------------------------------

GENERIC_BWRO_8 = MembraneElement(
    name='Generic BWRO 8"',
    type=MembraneType.BWRO,
    # A = 5.5 gives ~20 LMH at NDP ≈ 3.6 bar (typical BWRO design)
    a_coeff=5.5,
    # B = 0.13 gives ~99.5% rejection at design flux/NDP
    b_coeff=0.13,
    area_m2=37.2,
    max_flux_lmh=34.0,
    min_flux_lmh=8.5,
    max_feed_pressure_bar=41.0,
    ref_pressure_drop_bar=0.35,
    ref_feed_flow_m3h=12.3,
    mass_transfer_coeff_lmh=120.0,
)

GENERIC_SWRO_8 = MembraneElement(
    name='Generic SWRO 8"',
    type=MembraneType.SWRO,
    # A = 1.0 gives ~18 LMH at NDP ≈ 18 bar (55 bar applied − 37 bar net osmotic)
    a_coeff=1.0,
    # B = 0.036 gives ~99.8% rejection at design conditions
    b_coeff=0.036,
    area_m2=37.2,
    max_flux_lmh=20.0,
    min_flux_lmh=6.8,
    max_feed_pressure_bar=83.0,
    ref_pressure_drop_bar=0.28,
    ref_feed_flow_m3h=10.2,
    mass_transfer_coeff_lmh=100.0,
)

GENERIC_NF_8 = MembraneElement(
    name='Generic NF 8"',
    type=MembraneType.NF,
    # A = 8.0 gives ~32 LMH at NDP ≈ 4 bar (typical NF design)
    a_coeff=8.0,
    # B = 5.0 gives ~60–75% TDS rejection at design flux (NF varies by salt species)
    b_coeff=5.0,
    area_m2=37.2,
    max_flux_lmh=51.0,
    min_flux_lmh=8.5,
    max_feed_pressure_bar=41.0,
    ref_pressure_drop_bar=0.35,
    ref_feed_flow_m3h=12.3,
    mass_transfer_coeff_lmh=140.0,
)


MEMBRANE_LIBRARY: dict[str, MembraneElement] = {
    m.name: m for m in [GENERIC_BWRO_8, GENERIC_SWRO_8, GENERIC_NF_8]
}
