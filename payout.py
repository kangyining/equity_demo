import streamlit as st
import pandas as pd
import altair as alt

# ---------------------------- Core simulation logic ---------------------------- #

import yfinance as yf

ticker = yf.Ticker("HAPBF")

# --- 1) preferred: fast_info (fastest, hits Yahoo real-time endpoint) ----
price = ticker.fast_info["last_price"]      # float
print("fast_info price:", price)

MARKET_CAP_USD = 20.49 * 1_000_000   # 16.86 million USD
SHARES_OUT     = MARKET_CAP_USD//price         # ≈ shares derived earlier (const)
stock_price = price
def simulate(acquisitions: dict[int, int], price_monthly: float, device_revenue: float,
             valuation_multiple: float, vesting_dict: dict[int, float],retain_rate: float = 0.90,) -> pd.DataFrame:
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
        # --- NEW: cumulative active users with 90 % retention ---------------- #
    # RETAIN = 0.90                     # 90 % of last year’s users stay active
    active = 0                        # running total of still-paying users
    cum_list = []                     # to collect year-by-year results

    for y in df.index:                # iterate in chronological order
        active = df.at[y, "new_users"] + active * retain_rate
        print('active:',active)
        cum_list.append(active)
    print(cum_list)

    df["cum_users"] = cum_list        # replaces simple .cumsum()
    # -------------------------------------------------------------------- #

    df["arr"] = df["cum_users"] * price_monthly * 12
    # df["arr"] = df["new_users"] * price_monthly * 12
    df["value_added"] = df["arr"] * valuation_multiple + df["one_time_rev"]
    df["vested_pct"] = df.index.to_series().map(vesting_dict).fillna(0)
    df["equity_value"] = df["value_added"] * df["vested_pct"]
        # --- NEW: translate value-added into market-cap & share-price -----------
    df["cum_val_added"] = df["value_added"].cumsum()
    df["market_cap_usd"]   = MARKET_CAP_USD + df["cum_val_added"]
    df["share_price_usd"]  = df["market_cap_usd"] / SHARES_OUT
    print(df)
    return df

# ---------------------------- UI layout --------------------------------------- #

st.set_page_config(page_title="Equity Simulation Dashboard", page_icon="📈", layout="wide",initial_sidebar_state="expanded")   # <— keep sidebar open by default)
st.title("📈 Equity Simulation Dashboard")
# NEW ───────────────────────────────────────────────────────────────────────── #
show_shares = st.toggle(
    "Show share count labels",             # label
    value=True,                            # default ON
    key="show_shares_toggle",
)  # Readers can flip this before or after adjusting parameters
# ───────────────────────────────────────────────────────────────────────────── #
st.write("Adjust inputs and compare conservative, base, and aggressive growth scenarios.")

# Sidebar – global parameters
with st.sidebar:
    st.header("Global Parameters")

    # Existing numeric inputs (unchanged)
    price_monthly = st.number_input(
        "Subscription price ($/month)", min_value=0.0, value=15.0, step=1.0
    )
    device_revenue = st.number_input(
        "Device revenue (one-time $)", min_value=0.0, value=200.0, step=10.0
    )
    st.markdown("#### Current HAPBF price (Yahoo Finance)")
    st.metric("Last trade", f"${price:.4f}")      # shows, e.g., $0.0811

    # st.markdown("### Company stock price ($)")

    # stock_price = float(
    #     st.text_input(
    #         label="",                       # no label to keep it compact
    #         value=f"{price:.4f}",                   # default value as a string
    #         key="stock_price_text",
    #     )
    # )                            # docs: st.text_input :contentReference[oaicite:3]{index=3}

    # ── Valuation multiple ──────────────────────────────────────────────── #
    st.markdown("### Valuation multiple (× ARR)")

    col_vs, col_vt = st.columns([3, 1])
    with col_vs:
        st.slider(
            label=" ", min_value=1.0, max_value=15.0, value=8.0, step=0.1,
            key="val_mult_slider",
            on_change=lambda: st.session_state.update(
                val_mult_text=st.session_state.val_mult_slider
            ),
        )
    with col_vt:
        st.text_input(
            label="", key="val_mult_text",
            value=str(st.session_state.get("val_mult_slider", 8.0)),
            on_change=lambda: st.session_state.update(
                val_mult_slider=float(st.session_state.val_mult_text or 0)
            ),
        )

    valuation_multiple = float(st.session_state.val_mult_slider)

    st.markdown("### Annual retention rate (%)")

    col_rr_slider, col_rr_text = st.columns([3, 1])          # wider slider, narrow box

    with col_rr_slider:
        st.slider(
            " ", 0.0, 1.0, 0.90, 0.01,                       # min, max, default, step
            key="retention_slider",
            on_change=lambda: st.session_state.update(
                retention_text=st.session_state.retention_slider
            ),
        )

    with col_rr_text:
        st.text_input(
            label="",
            key="retention_text",
            value=str(st.session_state.get("retention_slider", 0.90)),
            on_change=lambda: st.session_state.update(
                retention_slider=float(st.session_state.retention_text or 0)
            ),
        )

    retain_rate = float(st.session_state.retention_slider)    # unified numeric value
    # ── Vesting schedule (% vested each year) ──────────────────────────── #
    st.subheader("Vesting schedule (% vested each year)")
    
    vesting = {}
    default_perc = {1: 50, 2: 25, 3: 15}

    for yr in (1, 2, 3):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.slider(
                f"Year {yr}", 0, 100, default_perc[yr], 1,
                key=f"vest{yr}_slider",
                on_change=lambda y=yr: st.session_state.update(
                    **{f"vest{y}_text": st.session_state[f"vest{y}_slider"]}
                ),
            )
        with c2:
            st.text_input(
                label="", key=f"vest{yr}_text",
                value=str(st.session_state.get(f"vest{yr}_slider", default_perc[yr])),
                on_change=lambda y=yr: st.session_state.update(
                    **{f"vest{y}_slider": float(st.session_state[f"vest{y}_text"] or 0)}
                ),
            )
        vesting[yr] = st.session_state[f"vest{yr}_slider"] / 100

    # ── Scenario inputs (leave these as text areas) ─────────────────────── #
    st.header("New-user acquisitions per scenario")
    st.caption("Enter comma-separated year:user pairs (e.g. 1:1200,2:3000)")
    cons_txt = st.text_area("Conservative", "1:25000,2:37500,3:50000")
    base_txt = st.text_area("Base", "1:50000,2:75000,3:100000")
    aggr_txt = st.text_area("Aggressive", "1:100000,2:150000,3:200000")

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
    "Conservative": simulate(acq_cons, price_monthly, device_revenue,
                             valuation_multiple, vesting, retain_rate,
                             ),
    "Base":         simulate(acq_base, price_monthly, device_revenue,
                             valuation_multiple, vesting, retain_rate,
                             ),
    "Aggressive":   simulate(acq_aggr, price_monthly, device_revenue,
                             valuation_multiple, vesting, retain_rate,
                             )
}
proj_price_long = (
    pd.concat({name: df["share_price_usd"]
               for name, df in results.items()}, axis=1)      # stack side-by-side
      .reset_index()                                          # make Year a column
      .melt(id_vars="Year", var_name="Scenario",
            value_name="share_price_usd")                     # long form
)
# ---------------------------- Display ----------------------------------------- #

# 1️⃣  Combined EQUITY line chart with labels
# combined_equity = pd.concat({k: v["equity_value"] for k, v in results.items()}, axis=1).reset_index().melt(id_vars="Year", var_name="Scenario", value_name="Equity")
combined_equity = (
    pd.concat({k: v["equity_value"] for k, v in results.items()}, axis=1)
      .reset_index()
      .melt(id_vars="Year", var_name="Scenario", value_name="Equity")
      .merge(proj_price_long, on=["Year", "Scenario"])            # ← NEW merge
)
combined_equity["Shares"] = (
    combined_equity["Equity"] / combined_equity["share_price_usd"]
)
combined_equity["SharesLabel"] = combined_equity["Shares"].apply(
    lambda s: f"[{s:,.0f}]"
)

# # --- shares = equity / stock_price -------------------------------------- #
# combined_equity["Shares"] = combined_equity["Equity"] / stock_price           # numeric
# combined_equity["SharesLabel"] = combined_equity["Shares"].apply(             # "[123,456]"
#     lambda s: f"[{s:,.0f}]"
# )
line_equity = alt.Chart(combined_equity).mark_line(point=True).encode(
    x=alt.X("Year:O", axis=alt.Axis(title="Year", tickMinStep=1,labelAngle=0)),
    y=alt.Y("Equity:Q", axis=alt.Axis(title="Equity Value ($)", format="$,.0f")),
    color="Scenario:N",
    tooltip=["Scenario", "Year", alt.Tooltip("Equity", format="$,.0f")],
)
labels_equity = line_equity.mark_text(dy=-15, fontWeight="bold").encode(
    text=alt.Text("Equity:Q", format="$,.0f")
)
shares_labels = (
    alt.Chart(combined_equity)
    .mark_text(dy=15, fontWeight="bold")                                       # 15 px below the point
    .encode(
        x="Year:O",
        y="Equity:Q",
        color="Scenario:N",
        text="SharesLabel:N",
    )
)

base_layers = line_equity + labels_equity          # always visible
if show_shares:                                    # add only if switch ON
    equity_chart = base_layers + shares_labels
else:
    equity_chart = base_layers

st.header("📈 Equity Value Comparison Across Scenarios")
st.altair_chart(
    equity_chart.properties(width=800, height=350),
    use_container_width=True,
)
# 2️⃣ Combined VALUE‑ADDED line chart with labels
combined_va = pd.concat({k: v["value_added"] for k, v in results.items()}, axis=1).reset_index().melt(id_vars="Year", var_name="Scenario", value_name="ValueAdded")

line_va = alt.Chart(combined_va).mark_line(point=True).encode(
    x=alt.X("Year:O", axis=alt.Axis(title="Year", tickMinStep=1,labelAngle=0)),
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


proj_price_df = pd.concat(
    {name: df["share_price_usd"] for name, df in results.items()},
    axis=1
).reset_index().rename_axis(None, axis=1)
st.subheader("💵 Projected Share Price (USD)")
st.dataframe(proj_price_df.style.format({"Conservative":"${:,.3f}",
                                   "Base":"${:,.3f}",
                                   "Aggressive":"${:,.3f}"}))