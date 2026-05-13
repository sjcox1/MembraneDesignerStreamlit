"""Unit conversion helpers. All internal calculations use SI-friendly units:
    flow: m³/h, pressure: bar, TDS: mg/L, flux: L/(m²·h), area: m², temp: °C
"""


def bar_to_psi(bar: float) -> float:
    return bar * 14.5038

def psi_to_bar(psi: float) -> float:
    return psi / 14.5038

def lmh_to_gfd(lmh: float) -> float:
    """L/(m²·h) → US gallons/(ft²·day)"""
    return lmh * 0.5886

def gfd_to_lmh(gfd: float) -> float:
    return gfd / 0.5886

def m3h_to_gpm(m3h: float) -> float:
    return m3h * 4.4029

def gpm_to_m3h(gpm: float) -> float:
    return gpm / 4.4029

def m3h_to_lpd(m3h: float) -> float:
    return m3h * 24_000.0

def lpd_to_m3h(lpd: float) -> float:
    return lpd / 24_000.0
