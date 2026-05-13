"""Full system simulation — one or two passes, each with one or more stages.

Topology
--------
Pass 1: Feed → [Stage 1] → concentrate → [Stage 2 (optional)] → concentrate out
                ↓ permeate              ↓ permeate
                └────────────── combined permeate (pass 1 product)

Pass 2 (optional):  Pass 1 permeate → [Stage 1] → permeate out (final product)

Inter-stage: concentrate from stage N feeds stage N+1.
             Pressure = concentrate pressure from previous stage + boost (if any).

Inter-pass:  Pass 2 feed = pass 1 permeate combined flow and TDS.
"""
from dataclasses import dataclass, field

from .membrane_db import MembraneElement, GENERIC_BWRO_8
from .stage import StageConfig, StageResult, simulate_stage


@dataclass
class PassConfig:
    """Configuration for one pass (one or more stages)."""
    stages: list[StageConfig]
    feed_pressure_bar: float


@dataclass
class SystemConfig:
    """Full system configuration."""
    passes: list[PassConfig]
    feed_flow_m3h: float
    feed_tds: float
    temperature_c: float = 25.0
    permeate_pressure_bar: float = 0.0


@dataclass
class PassResult:
    feed_flow_m3h: float
    feed_tds: float

    permeate_flow_m3h: float
    permeate_tds: float

    concentrate_flow_m3h: float
    concentrate_tds: float
    concentrate_pressure_bar: float

    recovery: float
    stage_results: list[StageResult] = field(default_factory=list)


@dataclass
class SystemResult:
    feed_flow_m3h: float
    feed_tds: float

    net_permeate_flow_m3h: float
    net_permeate_tds: float

    concentrate_flow_m3h: float
    concentrate_tds: float

    overall_recovery: float
    pass_results: list[PassResult] = field(default_factory=list)

    @property
    def salt_rejection(self) -> float:
        """Observed salt rejection based on feed and product TDS."""
        return 1.0 - self.net_permeate_tds / self.feed_tds if self.feed_tds > 0 else 0.0

    @property
    def concentration_factor(self) -> float:
        """Ratio of concentrate TDS to feed TDS."""
        return self.concentrate_tds / self.feed_tds if self.feed_tds > 0 else 0.0

    @property
    def specific_recovery(self) -> float:
        """Alias for overall_recovery, as a percentage."""
        return self.overall_recovery * 100.0


def _simulate_pass(
    feed_flow_m3h: float,
    feed_tds: float,
    pass_config: PassConfig,
    temperature_c: float,
    permeate_pressure_bar: float,
) -> PassResult:
    """Run all stages in a single pass sequentially."""
    stage_results: list[StageResult] = []

    current_flow = feed_flow_m3h
    current_tds = feed_tds
    current_pressure = pass_config.feed_pressure_bar

    total_permeate_flow = 0.0
    total_permeate_tds_x_flow = 0.0

    for stage_cfg in pass_config.stages:
        # Apply inter-stage boost pump pressure (0 for first stage)
        stage_pressure = current_pressure + stage_cfg.boost_pressure_bar

        result = simulate_stage(
            feed_flow_m3h=current_flow,
            feed_tds=current_tds,
            feed_pressure_bar=stage_pressure,
            config=stage_cfg,
            temperature_c=temperature_c,
            permeate_pressure_bar=permeate_pressure_bar,
        )
        stage_results.append(result)

        total_permeate_flow += result.permeate_flow_m3h
        total_permeate_tds_x_flow += result.permeate_flow_m3h * result.permeate_tds

        # Concentrate becomes feed to next stage
        current_flow = result.concentrate_flow_m3h
        current_tds = result.concentrate_tds
        current_pressure = result.concentrate_pressure_bar

    avg_permeate_tds = (
        total_permeate_tds_x_flow / total_permeate_flow
        if total_permeate_flow > 0 else 0.0
    )

    return PassResult(
        feed_flow_m3h=feed_flow_m3h,
        feed_tds=feed_tds,
        permeate_flow_m3h=total_permeate_flow,
        permeate_tds=avg_permeate_tds,
        concentrate_flow_m3h=current_flow,
        concentrate_tds=current_tds,
        concentrate_pressure_bar=current_pressure,
        recovery=total_permeate_flow / feed_flow_m3h,
        stage_results=stage_results,
    )


def simulate_system(config: SystemConfig) -> SystemResult:
    """Simulate a full membrane system.

    Pass 1 concentrate is discharged. Pass 2 (if configured) treats pass 1 permeate.
    Final product is pass 2 permeate (two-pass) or pass 1 permeate (single-pass).
    """
    if not config.passes:
        raise ValueError("SystemConfig must contain at least one pass.")

    pass_results: list[PassResult] = []

    # Pass 1 always receives the raw feed
    pass1 = _simulate_pass(
        feed_flow_m3h=config.feed_flow_m3h,
        feed_tds=config.feed_tds,
        pass_config=config.passes[0],
        temperature_c=config.temperature_c,
        permeate_pressure_bar=config.permeate_pressure_bar,
    )
    pass_results.append(pass1)

    if len(config.passes) == 1:
        return SystemResult(
            feed_flow_m3h=config.feed_flow_m3h,
            feed_tds=config.feed_tds,
            net_permeate_flow_m3h=pass1.permeate_flow_m3h,
            net_permeate_tds=pass1.permeate_tds,
            concentrate_flow_m3h=pass1.concentrate_flow_m3h,
            concentrate_tds=pass1.concentrate_tds,
            overall_recovery=pass1.recovery,
            pass_results=pass_results,
        )

    # Pass 2 treats pass 1 permeate
    pass2 = _simulate_pass(
        feed_flow_m3h=pass1.permeate_flow_m3h,
        feed_tds=pass1.permeate_tds,
        pass_config=config.passes[1],
        temperature_c=config.temperature_c,
        permeate_pressure_bar=config.permeate_pressure_bar,
    )
    pass_results.append(pass2)

    overall_recovery = pass2.permeate_flow_m3h / config.feed_flow_m3h

    return SystemResult(
        feed_flow_m3h=config.feed_flow_m3h,
        feed_tds=config.feed_tds,
        net_permeate_flow_m3h=pass2.permeate_flow_m3h,
        net_permeate_tds=pass2.permeate_tds,
        concentrate_flow_m3h=pass1.concentrate_flow_m3h,
        concentrate_tds=pass1.concentrate_tds,
        overall_recovery=overall_recovery,
        pass_results=pass_results,
    )
