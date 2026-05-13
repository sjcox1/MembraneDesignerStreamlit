import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from memdesign import (
    SystemConfig, PassConfig, StageConfig, simulate_system,
    GENERIC_BWRO_8, GENERIC_SWRO_8, GENERIC_NF_8,
)
from memdesign.membrane_db import MembraneType
from memdesign.units import bar_to_psi, lmh_to_gfd, m3h_to_gpm

st.set_page_config(
    page_title="Membrane Designer",
    page_icon="💧",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def login():
    st.title("Membrane Plant Designer")
    st.subheader("Please enter your name to continue")
    name_input = st.text_input("Your name", placeholder="e.g. Alice")
    if st.button("Login", type="primary"):
        authorised = [n.lower() for n in st.secrets["users"]["names"]]
        if name_input.strip().lower() in authorised:
            st.session_state["user"] = name_input.strip().title()
            st.rerun()
        else:
            st.error("Name not recognised. Please check with your trainer.")


# ---------------------------------------------------------------------------
# Membrane element library
# ---------------------------------------------------------------------------

ELEMENTS = {
    GENERIC_BWRO_8.name: GENERIC_BWRO_8,
    GENERIC_SWRO_8.name: GENERIC_SWRO_8,
    GENERIC_NF_8.name: GENERIC_NF_8,
}

# Sensible defaults per technology
DEFAULTS = {
    "BWRO": dict(
        feed_flow=100.0, feed_tds=2000, temperature=25.0,
        n_passes=1,
        p1_pressure=10.0, p1_n_stages=2,
        p1_s1_vessels=6, p1_s1_elements=7,
        p1_s2_vessels=3, p1_s2_elements=7, p1_s2_boost=1.5,
        p2_pressure=8.0, p2_n_stages=1,
        p2_s1_vessels=4, p2_s1_elements=7,
        element=GENERIC_BWRO_8.name,
    ),
    "SWRO": dict(
        feed_flow=100.0, feed_tds=35000, temperature=25.0,
        n_passes=1,
        p1_pressure=55.0, p1_n_stages=1,
        p1_s1_vessels=8, p1_s1_elements=7,
        p1_s2_vessels=4, p1_s2_elements=7, p1_s2_boost=2.0,
        p2_pressure=8.0, p2_n_stages=1,
        p2_s1_vessels=4, p2_s1_elements=7,
        element=GENERIC_SWRO_8.name,
    ),
    "NF": dict(
        feed_flow=50.0, feed_tds=800, temperature=20.0,
        n_passes=1,
        p1_pressure=6.0, p1_n_stages=1,
        p1_s1_vessels=4, p1_s1_elements=7,
        p1_s2_vessels=2, p1_s2_elements=7, p1_s2_boost=0.5,
        p2_pressure=5.0, p2_n_stages=1,
        p2_s1_vessels=2, p2_s1_elements=7,
        element=GENERIC_NF_8.name,
    ),
}


# ---------------------------------------------------------------------------
# Sidebar — inputs
# ---------------------------------------------------------------------------

def render_sidebar():
    with st.sidebar:
        st.markdown(f"Logged in as **{st.session_state['user']}**")
        if st.button("Logout"):
            del st.session_state["user"]
            st.rerun()

        st.divider()

        # Technology preset
        st.header("Technology")
        tech = st.selectbox("Membrane type", ["BWRO", "SWRO", "NF"], key="tech")
        d = DEFAULTS[tech]

        # Load defaults button
        if st.button("Load defaults for " + tech):
            for k, v in d.items():
                st.session_state[k] = v
            st.rerun()

        st.divider()

        # Feed water
        st.header("Feed Water")
        feed_flow = st.number_input(
            "Feed flow rate (m³/h)", min_value=0.1, max_value=10000.0,
            value=float(st.session_state.get("feed_flow", d["feed_flow"])),
            step=10.0, key="feed_flow",
        )
        feed_tds = st.number_input(
            "Feed TDS (mg/L)", min_value=1, max_value=50000,
            value=int(st.session_state.get("feed_tds", d["feed_tds"])),
            step=100, key="feed_tds",
        )
        temperature = st.slider(
            "Temperature (°C)", min_value=5, max_value=45,
            value=int(st.session_state.get("temperature", d["temperature"])),
            key="temperature",
        )

        st.divider()

        # Membrane element
        st.header("Membrane Element")
        element_name = st.selectbox(
            "Element", list(ELEMENTS.keys()),
            index=list(ELEMENTS.keys()).index(
                st.session_state.get("element", d["element"])
            ),
            key="element",
        )
        element = ELEMENTS[element_name]
        with st.expander("Element specification"):
            st.markdown(f"**Type:** {element.type.value}")
            st.markdown(f"**A (water perm.):** {element.a_coeff} L/(m²·h·bar)")
            st.markdown(f"**B (salt perm.):** {element.b_coeff} L/(m²·h)")
            st.markdown(f"**Active area:** {element.area_m2} m²")
            st.markdown(
                f"**Flux range:** {element.min_flux_lmh}–{element.max_flux_lmh} LMH"
                f"  ({lmh_to_gfd(element.min_flux_lmh):.1f}–{lmh_to_gfd(element.max_flux_lmh):.1f} GFD)"
            )
            st.markdown(f"**Max pressure:** {element.max_feed_pressure_bar} bar")

        st.divider()

        # System layout
        st.header("System Layout")
        n_passes = st.radio(
            "Passes", [1, 2],
            index=[1, 2].index(int(st.session_state.get("n_passes", d["n_passes"]))),
            horizontal=True, key="n_passes",
        )

        # Pass 1
        with st.expander("Pass 1", expanded=True):
            p1_pressure = st.number_input(
                "Feed pressure (bar)", min_value=0.5, max_value=float(element.max_feed_pressure_bar),
                value=float(st.session_state.get("p1_pressure", d["p1_pressure"])),
                step=0.5, key="p1_pressure",
            )
            p1_n_stages = st.radio(
                "Stages", [1, 2], horizontal=True,
                index=[1, 2].index(int(st.session_state.get("p1_n_stages", d["p1_n_stages"]))),
                key="p1_n_stages",
            )
            st.markdown("**Stage 1**")
            c1, c2 = st.columns(2)
            p1_s1_vessels = c1.number_input(
                "Vessels", min_value=1, max_value=50,
                value=int(st.session_state.get("p1_s1_vessels", d["p1_s1_vessels"])),
                key="p1_s1_vessels",
            )
            p1_s1_elements = c2.number_input(
                "Elements/vessel", min_value=1, max_value=8,
                value=int(st.session_state.get("p1_s1_elements", d["p1_s1_elements"])),
                key="p1_s1_elements",
            )

            if p1_n_stages == 2:
                st.markdown("**Stage 2**")
                c3, c4 = st.columns(2)
                p1_s2_vessels = c3.number_input(
                    "Vessels", min_value=1, max_value=50,
                    value=int(st.session_state.get("p1_s2_vessels", d["p1_s2_vessels"])),
                    key="p1_s2_vessels",
                )
                p1_s2_elements = c4.number_input(
                    "Elements/vessel", min_value=1, max_value=8,
                    value=int(st.session_state.get("p1_s2_elements", d["p1_s2_elements"])),
                    key="p1_s2_elements",
                )
                p1_s2_boost = st.number_input(
                    "Inter-stage boost pressure (bar)", min_value=0.0, max_value=10.0,
                    value=float(st.session_state.get("p1_s2_boost", d["p1_s2_boost"])),
                    step=0.5, key="p1_s2_boost",
                )

        # Pass 2 (optional)
        if n_passes == 2:
            with st.expander("Pass 2", expanded=True):
                p2_pressure = st.number_input(
                    "Feed pressure (bar)", min_value=0.5, max_value=float(element.max_feed_pressure_bar),
                    value=float(st.session_state.get("p2_pressure", d["p2_pressure"])),
                    step=0.5, key="p2_pressure",
                )
                st.markdown("**Stage 1**")
                c5, c6 = st.columns(2)
                p2_s1_vessels = c5.number_input(
                    "Vessels", min_value=1, max_value=50,
                    value=int(st.session_state.get("p2_s1_vessels", d["p2_s1_vessels"])),
                    key="p2_s1_vessels",
                )
                p2_s1_elements = c6.number_input(
                    "Elements/vessel", min_value=1, max_value=8,
                    value=int(st.session_state.get("p2_s1_elements", d["p2_s1_elements"])),
                    key="p2_s1_elements",
                )

    # Build SystemConfig from sidebar values
    p1_stages = [
        StageConfig(
            n_vessels=int(st.session_state.get("p1_s1_vessels", d["p1_s1_vessels"])),
            n_elements=int(st.session_state.get("p1_s1_elements", d["p1_s1_elements"])),
            element=element,
        )
    ]
    if int(st.session_state.get("p1_n_stages", d["p1_n_stages"])) == 2:
        p1_stages.append(StageConfig(
            n_vessels=int(st.session_state.get("p1_s2_vessels", d["p1_s2_vessels"])),
            n_elements=int(st.session_state.get("p1_s2_elements", d["p1_s2_elements"])),
            element=element,
            boost_pressure_bar=float(st.session_state.get("p1_s2_boost", d["p1_s2_boost"])),
        ))

    passes = [PassConfig(
        stages=p1_stages,
        feed_pressure_bar=float(st.session_state.get("p1_pressure", d["p1_pressure"])),
    )]

    if int(st.session_state.get("n_passes", d["n_passes"])) == 2:
        passes.append(PassConfig(
            stages=[StageConfig(
                n_vessels=int(st.session_state.get("p2_s1_vessels", d["p2_s1_vessels"])),
                n_elements=int(st.session_state.get("p2_s1_elements", d["p2_s1_elements"])),
                element=element,
            )],
            feed_pressure_bar=float(st.session_state.get("p2_pressure", d["p2_pressure"])),
        ))

    return SystemConfig(
        passes=passes,
        feed_flow_m3h=float(st.session_state.get("feed_flow", d["feed_flow"])),
        feed_tds=float(st.session_state.get("feed_tds", d["feed_tds"])),
        temperature_c=float(st.session_state.get("temperature", d["temperature"])),
    )


# ---------------------------------------------------------------------------
# Results rendering
# ---------------------------------------------------------------------------

def _element_profile_df(result) -> pd.DataFrame:
    """Flatten all element results across all passes and stages into a DataFrame."""
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
                    "Recovery (%)": round(e_res.element_recovery * 100, 2),
                    "Feed Pressure (bar)": round(e_res.feed_pressure_bar, 2),
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
        positions = over_flux["Position"].tolist()
        warnings.append(
            f"Flux exceeds maximum ({element.max_flux_lmh} LMH) at element positions: {positions}"
        )

    under_flux = df[df["Flux (LMH)"] < element.min_flux_lmh]
    if not under_flux.empty:
        positions = under_flux["Position"].tolist()
        warnings.append(
            f"Flux below minimum ({element.min_flux_lmh} LMH) at element positions: {positions} — scaling risk"
        )

    last_ndp = df["NDP (bar)"].iloc[-1]
    if last_ndp < 0.5:
        warnings.append(
            f"Very low net driving pressure ({last_ndp:.2f} bar) on last element — system may be pressure-limited"
        )

    if result.concentrate_tds > 70000:
        warnings.append(
            f"Concentrate TDS {result.concentrate_tds:.0f} mg/L is very high — check scaling potential"
        )

    if result.overall_recovery < 0.30 and element.type == MembraneType.BWRO:
        warnings.append("Recovery below 30% for BWRO — consider adding a second stage")

    return warnings


def render_results(result, element):
    df = _element_profile_df(result)
    warnings = _design_warnings(result, element)

    # Key metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Overall Recovery", f"{result.overall_recovery:.1%}")
    col2.metric("Permeate Flow", f"{result.net_permeate_flow_m3h:.1f} m³/h",
                f"{m3h_to_gpm(result.net_permeate_flow_m3h):.0f} GPM")
    col3.metric("Permeate TDS", f"{result.net_permeate_tds:.0f} mg/L")
    col4.metric("Salt Rejection", f"{result.salt_rejection:.2%}")
    col5.metric("Concentration Factor", f"{result.concentration_factor:.2f}×")

    if warnings:
        for w in warnings:
            st.warning(w)

    st.divider()

    tab_summary, tab_profiles, tab_table = st.tabs(
        ["System Summary", "Element Profiles", "Element Data Table"]
    )

    with tab_summary:
        _render_summary(result)

    with tab_profiles:
        _render_profiles(df)

    with tab_table:
        st.dataframe(df, use_container_width=True, hide_index=True)


def _render_summary(result):
    for p_idx, p_res in enumerate(result.pass_results):
        st.subheader(f"Pass {p_idx + 1}")
        cols = st.columns(len(p_res.stage_results))
        for s_idx, s_res in enumerate(p_res.stage_results):
            with cols[s_idx]:
                st.markdown(f"**Stage {s_idx + 1}**")
                st.markdown(f"Vessels: {s_res.n_vessels}")
                st.markdown(f"Elements/vessel: {s_res.n_elements}")
                st.markdown(f"Feed flow: {s_res.feed_flow_m3h:.1f} m³/h")
                st.markdown(f"Feed TDS: {s_res.feed_tds:.0f} mg/L")
                st.markdown(f"Feed pressure: {s_res.feed_pressure_bar:.1f} bar")
                st.markdown(f"Permeate flow: {s_res.permeate_flow_m3h:.1f} m³/h")
                st.markdown(f"Permeate TDS: {s_res.permeate_tds:.1f} mg/L")
                st.markdown(f"Concentrate TDS: {s_res.concentrate_tds:.0f} mg/L")
                st.markdown(f"Stage recovery: {s_res.recovery:.1%}")
                st.markdown(
                    f"Pressure drop: "
                    f"{s_res.vessel_result.pressure_drop_bar:.2f} bar"
                )

        st.markdown(
            f"**Pass {p_idx + 1} overall:** "
            f"{p_res.permeate_flow_m3h:.1f} m³/h permeate at "
            f"{p_res.permeate_tds:.1f} mg/L TDS — "
            f"{p_res.recovery:.1%} recovery"
        )
        st.divider()


def _render_profiles(df: pd.DataFrame):
    if df.empty:
        st.info("No element data to display.")
        return

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Flux profile (LMH)",
            "Net Driving Pressure (bar)",
            "Feed-side TDS (mg/L)",
            "Permeate TDS per element (mg/L)",
        ),
    )

    # Stage boundary shading
    stage_groups = df.groupby(["Pass", "Stage"])

    def stage_label(p, s):
        return f"P{p} S{s}"

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    color_idx = 0
    for (p, s), grp in stage_groups:
        col = colors[color_idx % len(colors)]
        name = stage_label(p, s)
        x = grp["Position"]

        fig.add_trace(go.Scatter(x=x, y=grp["Flux (LMH)"], name=name,
                                  line=dict(color=col), legendgroup=name,
                                  showlegend=True), row=1, col=1)
        fig.add_trace(go.Scatter(x=x, y=grp["NDP (bar)"], name=name,
                                  line=dict(color=col), legendgroup=name,
                                  showlegend=False), row=1, col=2)
        fig.add_trace(go.Scatter(x=x, y=grp["Feed TDS (mg/L)"], name=name,
                                  line=dict(color=col), legendgroup=name,
                                  showlegend=False), row=2, col=1)
        fig.add_trace(go.Scatter(x=x, y=grp["Permeate TDS (mg/L)"], name=name,
                                  line=dict(color=col), legendgroup=name,
                                  showlegend=False), row=2, col=2)
        color_idx += 1

    fig.update_xaxes(title_text="Element position")
    fig.update_layout(height=550, margin=dict(t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.title("Membrane Plant Designer")

    config = render_sidebar()
    element = ELEMENTS[st.session_state.get("element", "Generic BWRO 8\"")]

    try:
        result = simulate_system(config)
        render_results(result, element)
    except Exception as e:
        st.error(f"Simulation error: {e}")
        st.info("Check that your feed pressure is sufficient to overcome osmotic pressure.")


if "user" not in st.session_state:
    login()
else:
    main()
