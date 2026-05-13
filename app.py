import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from memdesign import (
    SystemConfig, PassConfig, StageConfig, simulate_system,
    GENERIC_BWRO_8, GENERIC_SWRO_8, GENERIC_NF_8,
)
from memdesign.membrane_db import MembraneType
from memdesign.units import lmh_to_gfd, m3h_to_gpm

st.set_page_config(
    page_title="Membrane Designer",
    page_icon="💧",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ELEMENTS = {
    GENERIC_BWRO_8.name: GENERIC_BWRO_8,
    GENERIC_SWRO_8.name: GENERIC_SWRO_8,
    GENERIC_NF_8.name: GENERIC_NF_8,
}

DEFAULTS = {
    "BWRO": dict(
        feed_flow=100.0, feed_tds=2000, temperature=25,
        n_passes=1,
        p1_pressure=10.0, p1_n_stages=2,
        p1_s1_vessels=6, p1_s1_elements=7,
        p1_s2_vessels=3, p1_s2_elements=7, p1_s2_boost=1.5,
        p2_pressure=8.0, p2_s1_vessels=4, p2_s1_elements=7,
        element=GENERIC_BWRO_8.name,
    ),
    "SWRO": dict(
        feed_flow=100.0, feed_tds=35000, temperature=25,
        n_passes=1,
        p1_pressure=55.0, p1_n_stages=1,
        p1_s1_vessels=8, p1_s1_elements=7,
        p1_s2_vessels=4, p1_s2_elements=7, p1_s2_boost=2.0,
        p2_pressure=8.0, p2_s1_vessels=4, p2_s1_elements=7,
        element=GENERIC_SWRO_8.name,
    ),
    "NF": dict(
        feed_flow=50.0, feed_tds=800, temperature=20,
        n_passes=1,
        p1_pressure=6.0, p1_n_stages=1,
        p1_s1_vessels=4, p1_s1_elements=7,
        p1_s2_vessels=2, p1_s2_elements=7, p1_s2_boost=0.5,
        p2_pressure=5.0, p2_s1_vessels=2, p2_s1_elements=7,
        element=GENERIC_NF_8.name,
    ),
}


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def login():
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title("💧 Membrane Plant Designer")
        st.subheader("Please enter your name to continue")
        name_input = st.text_input("Your name", placeholder="e.g. Alice")
        if st.button("Login", type="primary", use_container_width=True):
            authorised = [n.lower() for n in st.secrets["users"]["names"]]
            if name_input.strip().lower() in authorised:
                st.session_state["user"] = name_input.strip().title()
                st.session_state["view"] = "setup"
                st.rerun()
            else:
                st.error("Name not recognised. Please check with your trainer.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _s(key, default=None):
    """Read a value from session_state with a fallback default."""
    return st.session_state.get(key, default)


def _apply_defaults(tech: str):
    for k, v in DEFAULTS[tech].items():
        st.session_state[k] = v


def _build_config() -> SystemConfig:
    d = DEFAULTS[_s("tech", "BWRO")]
    element = ELEMENTS[_s("element", d["element"])]

    p1_stages = [StageConfig(
        n_vessels=int(_s("p1_s1_vessels", d["p1_s1_vessels"])),
        n_elements=int(_s("p1_s1_elements", d["p1_s1_elements"])),
        element=element,
    )]
    if int(_s("p1_n_stages", d["p1_n_stages"])) == 2:
        p1_stages.append(StageConfig(
            n_vessels=int(_s("p1_s2_vessels", d["p1_s2_vessels"])),
            n_elements=int(_s("p1_s2_elements", d["p1_s2_elements"])),
            element=element,
            boost_pressure_bar=float(_s("p1_s2_boost", d["p1_s2_boost"])),
        ))

    passes = [PassConfig(
        stages=p1_stages,
        feed_pressure_bar=float(_s("p1_pressure", d["p1_pressure"])),
    )]

    if int(_s("n_passes", d["n_passes"])) == 2:
        passes.append(PassConfig(
            stages=[StageConfig(
                n_vessels=int(_s("p2_s1_vessels", d["p2_s1_vessels"])),
                n_elements=int(_s("p2_s1_elements", d["p2_s1_elements"])),
                element=element,
            )],
            feed_pressure_bar=float(_s("p2_pressure", d["p2_pressure"])),
        ))

    return SystemConfig(
        passes=passes,
        feed_flow_m3h=float(_s("feed_flow", d["feed_flow"])),
        feed_tds=float(_s("feed_tds", d["feed_tds"])),
        temperature_c=float(_s("temperature", d["temperature"])),
    )


# ---------------------------------------------------------------------------
# Setup page
# ---------------------------------------------------------------------------

def render_setup():
    with st.sidebar:
        st.markdown(f"Logged in as **{st.session_state['user']}**")
        if st.button("Logout"):
            del st.session_state["user"]
            st.rerun()

    st.title("💧 Membrane Plant Designer")
    st.caption("Work through each section below, then click **Run Simulation** when ready.")
    st.divider()

    # ── Step 1: Technology ──────────────────────────────────────────────────
    st.header("Step 1 — Select Technology")

    col_tech, col_btn = st.columns([2, 1], vertical_alignment="bottom")
    with col_tech:
        tech = st.selectbox(
            "Membrane technology",
            ["BWRO", "SWRO", "NF"],
            index=["BWRO", "SWRO", "NF"].index(_s("tech", "BWRO")),
            key="tech",
            help="BWRO: brackish water RO  |  SWRO: seawater RO  |  NF: nanofiltration",
        )
    with col_btn:
        if st.button(f"Load {tech} defaults", use_container_width=True):
            _apply_defaults(tech)
            st.rerun()

    d = DEFAULTS[tech]
    element_name = st.selectbox(
        "Membrane element",
        list(ELEMENTS.keys()),
        index=list(ELEMENTS.keys()).index(_s("element", d["element"])),
        key="element",
    )
    element = ELEMENTS[element_name]

    with st.expander("View element specification"):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Water permeability (A)", f"{element.a_coeff} L/(m²·h·bar)")
        c2.metric("Salt permeability (B)", f"{element.b_coeff} L/(m²·h)")
        c3.metric("Active area", f"{element.area_m2} m²")
        c4.metric(
            "Flux range",
            f"{element.min_flux_lmh}–{element.max_flux_lmh} LMH",
            f"{lmh_to_gfd(element.min_flux_lmh):.0f}–{lmh_to_gfd(element.max_flux_lmh):.0f} GFD",
        )

    st.divider()

    # ── Step 2: Feed Water ──────────────────────────────────────────────────
    st.header("Step 2 — Feed Water")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.number_input(
            "Feed flow rate (m³/h)",
            min_value=0.1, max_value=10000.0, step=10.0,
            value=float(_s("feed_flow", d["feed_flow"])),
            key="feed_flow",
            help=f"{m3h_to_gpm(float(_s('feed_flow', d['feed_flow']))):.0f} GPM",
        )
        st.caption(f"≈ {m3h_to_gpm(float(_s('feed_flow', d['feed_flow']))):.0f} GPM")
    with col2:
        st.number_input(
            "Feed TDS (mg/L)",
            min_value=1, max_value=50000, step=100,
            value=int(_s("feed_tds", d["feed_tds"])),
            key="feed_tds",
        )
    with col3:
        st.slider(
            "Temperature (°C)",
            min_value=5, max_value=45,
            value=int(_s("temperature", d["temperature"])),
            key="temperature",
        )

    st.divider()

    # ── Step 3: System Layout ───────────────────────────────────────────────
    st.header("Step 3 — System Layout")

    n_passes = st.radio(
        "Number of passes",
        [1, 2],
        index=[1, 2].index(int(_s("n_passes", d["n_passes"]))),
        horizontal=True,
        key="n_passes",
        help="Two-pass systems run the permeate from Pass 1 through a second membrane stage for higher purity.",
    )

    # Pass 1
    st.subheader("Pass 1")
    col_p1a, col_p1b = st.columns([1, 2])
    with col_p1a:
        st.number_input(
            "Feed pressure (bar)",
            min_value=0.5,
            max_value=float(element.max_feed_pressure_bar),
            step=0.5,
            value=float(_s("p1_pressure", d["p1_pressure"])),
            key="p1_pressure",
        )
    with col_p1b:
        p1_n_stages = st.radio(
            "Number of stages",
            [1, 2],
            index=[1, 2].index(int(_s("p1_n_stages", d["p1_n_stages"]))),
            horizontal=True,
            key="p1_n_stages",
            help="Two stages: concentrate from Stage 1 is fed to Stage 2 for higher recovery.",
        )

    col_s1a, col_s1b = st.columns(2)
    with col_s1a:
        st.markdown("**Stage 1**")
        sc1, sc2 = st.columns(2)
        sc1.number_input("Vessels", min_value=1, max_value=100,
                         value=int(_s("p1_s1_vessels", d["p1_s1_vessels"])),
                         key="p1_s1_vessels")
        sc2.number_input("Elements / vessel", min_value=1, max_value=8,
                         value=int(_s("p1_s1_elements", d["p1_s1_elements"])),
                         key="p1_s1_elements")

    if p1_n_stages == 2:
        with col_s1b:
            st.markdown("**Stage 2**")
            sc3, sc4 = st.columns(2)
            sc3.number_input("Vessels", min_value=1, max_value=100,
                             value=int(_s("p1_s2_vessels", d["p1_s2_vessels"])),
                             key="p1_s2_vessels")
            sc4.number_input("Elements / vessel", min_value=1, max_value=8,
                             value=int(_s("p1_s2_elements", d["p1_s2_elements"])),
                             key="p1_s2_elements")
            st.number_input(
                "Inter-stage boost pressure (bar)",
                min_value=0.0, max_value=10.0, step=0.5,
                value=float(_s("p1_s2_boost", d["p1_s2_boost"])),
                key="p1_s2_boost",
                help="Additional pressure added before Stage 2 by an inter-stage pump.",
            )

    # Pass 2 (optional)
    if n_passes == 2:
        st.subheader("Pass 2")
        st.caption("Pass 2 treats the permeate from Pass 1.")
        col_p2a, col_p2b = st.columns([1, 2])
        with col_p2a:
            st.number_input(
                "Feed pressure (bar)",
                min_value=0.5,
                max_value=float(element.max_feed_pressure_bar),
                step=0.5,
                value=float(_s("p2_pressure", d["p2_pressure"])),
                key="p2_pressure",
            )
        with col_p2b:
            st.markdown("**Stage 1**")
            sc5, sc6 = st.columns(2)
            sc5.number_input("Vessels", min_value=1, max_value=100,
                             value=int(_s("p2_s1_vessels", d["p2_s1_vessels"])),
                             key="p2_s1_vessels")
            sc6.number_input("Elements / vessel", min_value=1, max_value=8,
                             value=int(_s("p2_s1_elements", d["p2_s1_elements"])),
                             key="p2_s1_elements")

    st.divider()

    # ── Run ─────────────────────────────────────────────────────────────────
    st.header("Step 4 — Run Simulation")
    st.caption("Review your settings above, then click the button below to run the simulation.")

    if st.button("▶  Run Simulation", type="primary", use_container_width=True):
        try:
            config = _build_config()
            result = simulate_system(config)
            st.session_state["last_config"] = config
            st.session_state["last_result"] = result
            st.session_state["view"] = "results"
            st.rerun()
        except Exception as e:
            st.error(f"Simulation failed: {e}")
            st.info("Check that your feed pressure is high enough to overcome osmotic pressure.")


# ---------------------------------------------------------------------------
# Results page
# ---------------------------------------------------------------------------

def _element_profile_df(result) -> pd.DataFrame:
    rows = []
    pos = 1
    for p_idx, p_res in enumerate(result.pass_results):
        for s_idx, s_res in enumerate(p_res.stage_results):
            for e_idx, e_res in enumerate(s_res.vessel_result.element_results):
                rows.append({
                    "Position": pos,
                    "Pass": p_idx + 1,
                    "Stage": s_idx + 1,
                    "Element": e_idx + 1,
                    "Flux (LMH)": round(e_res.flux_lmh, 2),
                    "Flux (GFD)": round(lmh_to_gfd(e_res.flux_lmh), 2),
                    "NDP (bar)": round(e_res.ndp_bar, 2),
                    "Feed TDS (mg/L)": round(e_res.feed_tds, 1),
                    "Permeate TDS (mg/L)": round(e_res.permeate_tds, 1),
                    "CP Factor": round(e_res.cp_factor, 3),
                    "Element Recovery (%)": round(e_res.element_recovery * 100, 2),
                    "Feed Pressure (bar)": round(e_res.feed_pressure_bar, 2),
                    "Observed Rejection (%)": round(e_res.observed_rejection * 100, 2),
                })
                pos += 1
    return pd.DataFrame(rows)


def _design_warnings(result, element) -> list[str]:
    warnings = []
    df = _element_profile_df(result)
    if df.empty:
        return warnings
    over_flux = df[df["Flux (LMH)"] > element.max_flux_lmh]
    if not over_flux.empty:
        warnings.append(
            f"Flux exceeds maximum ({element.max_flux_lmh} LMH) "
            f"at element positions: {over_flux['Position'].tolist()}"
        )
    under_flux = df[df["Flux (LMH)"] < element.min_flux_lmh]
    if not under_flux.empty:
        warnings.append(
            f"Flux below minimum ({element.min_flux_lmh} LMH) "
            f"at element positions: {under_flux['Position'].tolist()} — scaling risk"
        )
    if df["NDP (bar)"].iloc[-1] < 0.5:
        warnings.append(
            f"Very low NDP ({df['NDP (bar)'].iloc[-1]:.2f} bar) on last element — "
            "system may be pressure-limited"
        )
    if result.concentrate_tds > 70000:
        warnings.append(
            f"Concentrate TDS {result.concentrate_tds:.0f} mg/L is very high — "
            "review scaling potential"
        )
    element_obj = ELEMENTS.get(_s("element", ""), None)
    if (element_obj and element_obj.type == MembraneType.BWRO
            and result.overall_recovery < 0.30):
        warnings.append("Recovery below 30% for BWRO — consider adding a second stage")
    return warnings


def _render_profiles(df: pd.DataFrame):
    if df.empty:
        st.info("No element data available.")
        return

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Flux along vessel (LMH)",
            "Net Driving Pressure (bar)",
            "Feed-side TDS (mg/L)",
            "Permeate TDS per element (mg/L)",
        ),
        vertical_spacing=0.15,
        horizontal_spacing=0.1,
    )

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    for idx, ((p, s), grp) in enumerate(df.groupby(["Pass", "Stage"])):
        col = colors[idx % len(colors)]
        name = f"P{p} S{s}"
        x = grp["Position"]
        shared = dict(line=dict(color=col), legendgroup=name, mode="lines+markers",
                      marker=dict(size=5))
        fig.add_trace(go.Scatter(x=x, y=grp["Flux (LMH)"], name=name,
                                  showlegend=True, **shared), row=1, col=1)
        fig.add_trace(go.Scatter(x=x, y=grp["NDP (bar)"], name=name,
                                  showlegend=False, **shared), row=1, col=2)
        fig.add_trace(go.Scatter(x=x, y=grp["Feed TDS (mg/L)"], name=name,
                                  showlegend=False, **shared), row=2, col=1)
        fig.add_trace(go.Scatter(x=x, y=grp["Permeate TDS (mg/L)"], name=name,
                                  showlegend=False, **shared), row=2, col=2)

    fig.update_xaxes(title_text="Element position")
    fig.update_layout(height=560, margin=dict(t=50, b=20), legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)


def render_results():
    result = st.session_state["last_result"]
    config = st.session_state["last_config"]
    element = ELEMENTS.get(_s("element", ""), GENERIC_BWRO_8)
    df = _element_profile_df(result)
    warnings = _design_warnings(result, element)

    with st.sidebar:
        st.markdown(f"Logged in as **{st.session_state['user']}**")
        st.divider()
        if st.button("← Modify Design", use_container_width=True):
            st.session_state["view"] = "setup"
            st.rerun()
        st.divider()
        st.markdown("**Feed water**")
        st.markdown(f"Flow: {config.feed_flow_m3h:.1f} m³/h")
        st.markdown(f"TDS: {config.feed_tds:.0f} mg/L")
        st.markdown(f"Temp: {config.temperature_c:.0f} °C")
        st.divider()
        st.markdown("**Results summary**")
        st.markdown(f"Recovery: **{result.overall_recovery:.1%}**")
        st.markdown(f"Permeate TDS: **{result.net_permeate_tds:.0f} mg/L**")
        st.markdown(f"Salt rejection: **{result.salt_rejection:.2%}**")
        if st.button("Logout"):
            del st.session_state["user"]
            st.rerun()

    st.title("💧 Simulation Results")

    # Warnings banner
    if warnings:
        with st.expander(f"⚠️ {len(warnings)} design warning(s) — click to review", expanded=True):
            for w in warnings:
                st.warning(w)

    # Headline metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Overall Recovery", f"{result.overall_recovery:.1%}")
    col2.metric(
        "Permeate Flow",
        f"{result.net_permeate_flow_m3h:.1f} m³/h",
        f"{m3h_to_gpm(result.net_permeate_flow_m3h):.0f} GPM",
    )
    col3.metric("Permeate TDS", f"{result.net_permeate_tds:.0f} mg/L")
    col4.metric("Salt Rejection", f"{result.salt_rejection:.2%}")
    col5.metric("Concentration Factor", f"{result.concentration_factor:.2f}×")

    st.divider()

    tab_summary, tab_profiles, tab_table = st.tabs([
        "System Summary", "Element Profiles", "Full Data Table",
    ])

    with tab_summary:
        for p_idx, p_res in enumerate(result.pass_results):
            st.subheader(f"Pass {p_idx + 1}")
            cols = st.columns(len(p_res.stage_results))
            for s_idx, s_res in enumerate(p_res.stage_results):
                with cols[s_idx]:
                    st.markdown(f"**Stage {s_idx + 1}**")
                    rows = {
                        "Vessels": s_res.n_vessels,
                        "Elements / vessel": s_res.n_elements,
                        "Total elements": s_res.n_vessels * s_res.n_elements,
                        "Feed flow (m³/h)": f"{s_res.feed_flow_m3h:.1f}",
                        "Feed TDS (mg/L)": f"{s_res.feed_tds:.0f}",
                        "Feed pressure (bar)": f"{s_res.feed_pressure_bar:.1f}",
                        "Permeate flow (m³/h)": f"{s_res.permeate_flow_m3h:.1f}",
                        "Permeate TDS (mg/L)": f"{s_res.permeate_tds:.1f}",
                        "Concentrate TDS (mg/L)": f"{s_res.concentrate_tds:.0f}",
                        "Stage recovery": f"{s_res.recovery:.1%}",
                        "Vessel ΔP (bar)": f"{s_res.vessel_result.pressure_drop_bar:.2f}",
                    }
                    st.table(pd.DataFrame(rows.items(), columns=["Parameter", "Value"]))
            st.divider()

    with tab_profiles:
        _render_profiles(df)

    with tab_table:
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode()
        st.download_button(
            "Download CSV",
            csv,
            file_name="membrane_element_profile.csv",
            mime="text/csv",
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if "user" not in st.session_state:
    login()
elif st.session_state.get("view", "setup") == "results":
    render_results()
else:
    render_setup()
