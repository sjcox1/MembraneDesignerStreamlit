"""Pressure vessel simulation — a series chain of membrane elements.

Each element's concentrate becomes the next element's feed.
Permeate from all elements is collected and flow-weighted averaged for TDS.
"""
from dataclasses import dataclass, field

from .element import ElementResult, simulate_element
from .membrane_db import MembraneElement


@dataclass
class VesselResult:
    feed_flow_m3h: float
    feed_tds: float
    feed_pressure_bar: float

    permeate_flow_m3h: float
    permeate_tds: float

    concentrate_flow_m3h: float
    concentrate_tds: float
    concentrate_pressure_bar: float

    recovery: float
    pressure_drop_bar: float

    element_results: list[ElementResult] = field(default_factory=list)


def simulate_vessel(
    feed_flow_m3h: float,
    feed_tds: float,
    feed_pressure_bar: float,
    n_elements: int,
    element: MembraneElement,
    temperature_c: float = 25.0,
    permeate_pressure_bar: float = 0.0,
) -> VesselResult:
    """Simulate a pressure vessel containing n_elements in series."""
    element_results: list[ElementResult] = []

    current_flow = feed_flow_m3h
    current_tds = feed_tds
    current_pressure = feed_pressure_bar
    total_permeate_flow = 0.0
    total_permeate_tds_x_flow = 0.0

    for _ in range(n_elements):
        result = simulate_element(
            feed_flow_m3h=current_flow,
            feed_tds=current_tds,
            feed_pressure_bar=current_pressure,
            element=element,
            temperature_c=temperature_c,
            permeate_pressure_bar=permeate_pressure_bar,
        )
        element_results.append(result)

        total_permeate_flow += result.permeate_flow_m3h
        total_permeate_tds_x_flow += result.permeate_flow_m3h * result.permeate_tds

        current_flow = result.concentrate_flow_m3h
        current_tds = result.concentrate_tds
        current_pressure = result.concentrate_pressure_bar

    avg_permeate_tds = (
        total_permeate_tds_x_flow / total_permeate_flow
        if total_permeate_flow > 0 else 0.0
    )

    return VesselResult(
        feed_flow_m3h=feed_flow_m3h,
        feed_tds=feed_tds,
        feed_pressure_bar=feed_pressure_bar,
        permeate_flow_m3h=total_permeate_flow,
        permeate_tds=avg_permeate_tds,
        concentrate_flow_m3h=current_flow,
        concentrate_tds=current_tds,
        concentrate_pressure_bar=current_pressure,
        recovery=total_permeate_flow / feed_flow_m3h,
        pressure_drop_bar=feed_pressure_bar - current_pressure,
        element_results=element_results,
    )
