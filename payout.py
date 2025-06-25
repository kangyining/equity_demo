import streamlit as st
import pandas as pd
import altair as alt

# ---------------------------- Core simulation logic ---------------------------- #

def simulate(acquisitions: dict[int, int], price_monthly: float, device_revenue: float,
             valuation_multiple: float, vesting_dict: dict[int, float]) -> pd.DataFrame:
    """Return a DataFrame with revenue, value-add, and vested equity for each year."""
    df = (
        pd.DataFrame({
            "Year": acquisitions.keys(),
            "new_users": acquisitions.values(),
        })
        .set_index("Year")
        .sort_index()
    )

    df["one_time_rev"] = df["new_users"] * device_revenue
    df["arr"] = df["new_users"] * price_monthly * 12
    df["value_added"] = df["arr"] * valuation_multiple
    df["vested_pct"] = df.index.to_series().map(vesting_dict).fillna(0)
    df["equity_value"] = df["value_added"] * df["vested_pct"]

    return df

# ---------------------------- UI layout --------------------------------------- #

st.set_page_config(
    page_title="Equity Simulation Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"  # 👉 keeps sidebar open by default
)

st.title("📈 Equity Simulation Dashboard")
st.write("Adjust inputs and compare conservative, base, and aggressive growth scenarios.")

# Sidebar – global parameters
with st.sidebar:
    st.header("Global Parameters")
    price_monthly = st.number_input("Subscription price ($/month)", min_value=0.0, value=20.0, step=1.0)
    device_revenue = st.number_input("Device revenue (one-time $)", min_value=0.0, value=100.0, step=10.0)
    valuation_multiple = st.slider("Valuation multiple (× ARR)", 1.0, 15.0, value=8.0)

    # Vesting schedule
    st.subheader("Vesting schedule (% vested each year)")
    v1 = st.slider("Year 1", 0.0, 100.0, 50.0) / 100
    v2 = st.slider("Year 2", 0.0, 100.0, 25.0) / 100
    v3 = st.slider("Year 3", 0.0, 100.0, 15.0) / 100
    vesting = {1: v1, 2: v2, 3: v3}

    # Scenario inputs
    st.header("New-user acquisitions per scenario")
    st.caption("Enter comma-separated year:user pairs (e.g. 1:1200,2:3000)")
    base_txt = st.text_area("Base", "1:1200,2:3000,3:5000")
    cons_txt = st.text_area("Conservative", "1:800,2:2000,3:3500")
    aggr_txt = st.text_area("Aggressive", "1:1600,2:4500,3:8000")

# Helper to parse acquisitions safely
def parse_pairs(s: str) -> dict[int, int]:
    try:
        return {
            int(item.split(":")[0].strip()): int(item.split(":")[1].strip())
            for item in s.split(",") if ":" in item
        }
    except Exception:
        st.error("❌ Invalid format – use year:users pairs like 1:1200,2:3000")
        st.stop()

acq_base = parse_pairs(base_txt)
acq_cons = parse_pairs(cons_txt)
acq_aggr = parse_pairs(aggr_txt)

# Run simulations
results = {
    "Conservative": simulate(acq_cons, price_monthly, device_revenue, valuation_multiple, vesting),
    "Base": simulate(acq_base, price_monthly, device_revenue, valuation_multiple, vesting),
    "Aggressive": simulate(acq_aggr, price_monthly, device_revenue, valuation_multiple, vesting),
}

# ---------------------------- Display ----------------------------------------- #

# 1️⃣  Combined EQUITY line chart with labels
combined_equity = pd.concat({k: v["equity_value"] for k, v in results.items()}, axis=1).reset_index().melt(id_vars="Year", var_name="Scenario", value_name="Equity")

line_equity = alt.Chart(combined_equity).mark_line(point=True).encode(
    x=alt.X("Year:O", axis=alt.Axis(title="Year", tickMinStep=1)),
    y=alt.Y("Equity:Q", axis=alt.Axis(title="Equity Value ($)", format="$,.0f")),
    color="Scenario:N",
    tooltip=["Scenario", "Year", alt.Tooltip("Equity", format="$,.0f")],
)
labels_equity = line_equity.mark_text(dy=-15, fontWeight="bold").encode(
    text=alt.Text("Equity:Q", format="$,.0f")
)

st.header("📈 Equity Value Comparison Across Scenarios")
st.altair_chart((line_equity + labels_equity).properties(width=800, height=350), use_container_width=True)

# 2️⃣ Combined VALUE-ADDED line chart with labels
combined_va = pd.concat({k: v["value_added"] for k, v in results.items()}, axis=1).reset_index().melt(id_vars="Year", var_name="Scenario", value_name="ValueAdded")

line_va = alt.Chart(combined_va).mark_line(point=True).encode(
    x=alt.X("Year:O", axis=alt.Axis(title="Year", tickMinStep=1)),
    y=alt.Y("ValueAdded:Q", axis=alt.Axis(title="Valuation Added ($)", format="$,.0f")),
    color="Scenario:N",
    tooltip=["Scenario", "Year", alt.Tooltip("ValueAdded", format="$,.0f")],
)
labels_va = line_va.mark_text(dy=-15, fontWeight="bold").encode(
    text=alt.Text("ValueAdded:Q", format="$,.0f")
)

st.header("🏷️ Valuation Added Across Scenarios")
st.altair_chart((line_va + labels_va).properties(width=800, height=350), use_container_width=True)

# 3️⃣  Scenario tables
fmt = {
    "one_time_rev": "${:,.0f}",
    "arr": "${:,.0f}",
    "value_added": "${:,.0f}",
    "vested_pct": "{:.0%}",
    "equity_value": "${:,.0f}",
}

for name in ["Conservative", "Base", "Aggressive"]:
    st.subheader(f"🧮 {name} scenario – yearly results")
    st.dataframe(results[name].style.format(fmt))
