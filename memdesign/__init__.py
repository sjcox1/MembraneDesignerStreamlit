"""memdesign — membrane plant design calculation library.

Quick start
-----------
from memdesign import SystemConfig, PassConfig, StageConfig, simulate_system
from memdesign.membrane_db import GENERIC_BWRO_8

config = SystemConfig(
    passes=[
        PassConfig(
            feed_pressure_bar=10.0,
            stages=[
                StageConfig(n_vessels=6, n_elements=7, element=GENERIC_BWRO_8),
            ],
        )
    ],
    feed_flow_m3h=100.0,
    feed_tds=2000.0,
    temperature_c=25.0,
)

result = simulate_system(config)
print(f"Recovery: {result.overall_recovery:.1%}")
print(f"Permeate TDS: {result.net_permeate_tds:.0f} mg/L")
print(f"Salt rejection: {result.salt_rejection:.2%}")
"""

from .system import SystemConfig, PassConfig, simulate_system, SystemResult, PassResult
from .stage import StageConfig, StageResult
from .vessel import VesselResult
from .element import ElementResult
from .membrane_db import MembraneElement, MembraneType, MEMBRANE_LIBRARY
from .membrane_db import GENERIC_BWRO_8, GENERIC_SWRO_8, GENERIC_NF_8

__all__ = [
    "SystemConfig",
    "PassConfig",
    "StageConfig",
    "simulate_system",
    "SystemResult",
    "PassResult",
    "StageResult",
    "VesselResult",
    "ElementResult",
    "MembraneElement",
    "MembraneType",
    "MEMBRANE_LIBRARY",
    "GENERIC_BWRO_8",
    "GENERIC_SWRO_8",
    "GENERIC_NF_8",
]
