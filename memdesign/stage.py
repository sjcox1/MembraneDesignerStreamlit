"""Stage simulation — parallel array of identical pressure vessels.

All vessels in a stage receive an equal share of the stage feed flow.
Results are scaled up from a single representative vessel.
"""
from dataclasses import dataclass, field

from .membrane_db import MembraneElement
from .vessel import VesselResult, simulate_vessel


@dataclass
class StageConfig:
    n_vessels: int
    n_elements: int = 7
    element: MembraneElement = None  # set by caller

    boost_pressure_bar: float = 0.0  # inter-stage boost pump (added to inlet pressure)


@dataclass
class StageResult:
    feed_flow_m3h: float
    feed_tds: float
    feed_pressure_bar: float

    permeate_flow_m3h: float
    permeate_tds: float

    concentrate_flow_m3h: float
    concentrate_tds: float
    concentrate_pressure_bar: float

    recovery: float
    n_vessels: int
    n_elements: int

    vessel_result: VesselResult = None  # representative single-vessel result


def simulate_stage(
    feed_flow_m3h: float,
    feed_tds: float,
    feed_pressure_bar: float,
    config: StageConfig,
    temperature_c: float = 25.0,
    permeate_pressure_bar: float = 0.0,
) -> StageResult:
    """Simulate one stage.

    All vessels are assumed identical — one vessel is simulated and results
    scaled by n_vessels.
    """
    vessel_feed_flow = feed_flow_m3h / config.n_vessels

    vessel_result = simulate_vessel(
        feed_flow_m3h=vessel_feed_flow,
        feed_tds=feed_tds,
        feed_pressure_bar=feed_pressure_bar,
        n_elements=config.n_elements,
        element=config.element,
        temperature_c=temperature_c,
        permeate_pressure_bar=permeate_pressure_bar,
    )

    n = config.n_vessels
    return StageResult(
        feed_flow_m3h=feed_flow_m3h,
        feed_tds=feed_tds,
        feed_pressure_bar=feed_pressure_bar,
        permeate_flow_m3h=vessel_result.permeate_flow_m3h * n,
        permeate_tds=vessel_result.permeate_tds,
        concentrate_flow_m3h=vessel_result.concentrate_flow_m3h * n,
        concentrate_tds=vessel_result.concentrate_tds,
        concentrate_pressure_bar=vessel_result.concentrate_pressure_bar,
        recovery=vessel_result.recovery,
        n_vessels=n,
        n_elements=config.n_elements,
        vessel_result=vessel_result,
    )
