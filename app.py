import streamlit as st
import matplotlib.pyplot as plt
import io

# -------------------------------
# App Config
# -------------------------------
st.set_page_config(page_title="Hotel GST Impact Calculator (India)", layout="wide")

# -------------------------------
# Constants (GST)
# -------------------------------
OLD_OUTPUT_GST = 0.12   # 12% (with ITC)
NEW_OUTPUT_GST = 0.05   # 5% (no ITC)

# Guest-bill break-even (percentage points out of the 12% slab)
GUEST_BREAK_EVEN_PP = (1 + OLD_OUTPUT_GST) / (1 + NEW_OUTPUT_GST) - 1  # ≈ 0.066666...
GUEST_BREAK_EVEN_PP *= 100  # to percentage points

# -------------------------------
# Page Title / Intro
# -------------------------------
st.title("🏨 Hotel GST Impact Calculator (India)")
st.caption("Simple view for room tariffs ≤ ₹7,500/night — input **ITC claimed out of the 12% slab** (old regime).")

# Prominent break-even callout
st.info(f"🔎 **Guest-bill break-even:** If your ITC claimed earlier was about **{GUEST_BREAK_EVEN_PP:.1f} percentage points** "
        "out of the 12% slab, then the guest would pay roughly the **same** under the new regime at margin-neutral ADR. "
        "Below that, guests can pay **less** even if you hold margin; above that, guests may pay **more** at margin-neutral ADR.")

# -------------------------------
# Sidebar: Inputs
# -------------------------------
with st.sidebar:
    st.header("🔧 Inputs")

    base_adr = st.number_input(
        "Base ADR (₹) – pre-GST room rate",
        min_value=300.0, value=6000.0, step=100.0,
        help="Average daily rate before GST."
    )

    itc_claim_pp = st.slider(
        "ITC claimed out of 12% (old regime) – percentage points",
        min_value=0, max_value=12, value=3, step=1,
        help="How much of the 12% output GST was effectively offset by ITC (e.g., 3 means ~3% of base)."
    )

    absorb_rupees = st.number_input(
        "Hotel absorption (+) / capture (−) per night (₹)",
        min_value=-5000, max_value=5000, value=0, step=100,
        help="Positive = absorb some margin (lower guest bill). Negative = capture more profit."
    )

    st.markdown("---")
    st.subheader("Assumptions")
    st.write("""
    • Old output GST = **12%** (with ITC)  
    • New output GST = **5%** (without ITC)  
    • Simple model ignores channel/OTA costs to isolate pure GST/ITC effects.  
    • Profit proxy = **Base ADR** (old: plus ITC credit; new: equals base ADR).
    """)

# -------------------------------
# Core Formulas
# -------------------------------
def guest_pay_old(base):
    return base * (1 + OLD_OUTPUT_GST)

def guest_pay_new(base):
    return base * (1 + NEW_OUTPUT_GST)

def profit_old(base, itc_claim_points):
    return base + base * (itc_claim_points / 100.0)

def profit_new(base_new):
    return base_new

def neutral_adr(base_old, itc_claim_points):
    return base_old * (1 + itc_claim_points / 100.0)

# -------------------------------
# Calculation
# -------------------------------
old_profit = profit_old(base_adr, itc_claim_pp)
neutral_base = neutral_adr(base_adr, itc_claim_pp)

# Apply absorption/capture policy
# Profit_new = chosen_base (simple model), so chosen_base = old_profit - absorb
chosen_base = max(0.0, old_profit - absorb_rupees)
new_profit_chosen = profit_new(chosen_base)

guest_old = guest_pay_old(base_adr)
guest_new_chosen = guest_pay_new(chosen_base)
guest_delta_chosen = guest_new_chosen - guest_old

adr_uplift_pct_neutral = (neutral_base / base_adr - 1) * 100
adr_uplift_pct_chosen = (chosen_base / base_adr - 1) * 100

# -------------------------------
# KPI Tiles
# -------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Guest Payable (Old)", f"₹{guest_old:,.0f}")
    st.metric("Guest Payable (New @Chosen ADR)", f"₹{guest_new_chosen:,.0f}",
              delta=f"{guest_delta_chosen:+,.0f}")

with col2:
    st.metric("Profit (Old Regime)", f"₹{old_profit:,.0f}")
    st.metric("Profit (New Regime @Chosen ADR)", f"₹{new_profit_chosen:,.0f}",
              delta=f"{(new_profit_chosen - old_profit):+,.0f}")

with col3:
    st.metric("Neutral ADR (keeps profit same)", f"₹{neutral_base:,.0f}",
              delta=f"{adr_uplift_pct_neutral:,.1f}%")
    st.metric("Chosen ADR (after absorption/capture)", f"₹{chosen_base:,.0f}",
              delta=f"{adr_uplift_pct_chosen:,.1f}%")

st.caption(
    "Tip: Set **absorption** positive (e.g., +₹200) to pass savings to guests; set **negative** (e.g., −₹200) to capture more profit. "
    "Neutral ADR is when absorption = ₹0."
)

st.markdown("---")

# -------------------------------
# Chart: Guest Payable vs ITC claimed + Download
# -------------------------------
st.subheader("Guest Payable (New @Chosen ADR) vs ITC claimed (pp of 12%)")

slabs = list(range(0, 13))  # 0..12 inclusive
y_vals = [guest_pay_new(max(0.0, profit_old(base_adr, pp) - absorb_rupees)) for pp in slabs]

fig = plt.figure()
plt.plot(slabs, y_vals, label="Guest Pay (New @Chosen ADR)")
plt.axhline(guest_old, linestyle="--", label="Guest Pay (Old)")
plt.scatter([itc_claim_pp], [guest_new_chosen], s=60, zorder=5, label="Current selection")
plt.xlabel("ITC claimed (pp out of 12%)")
plt.ylabel("Guest Payable (₹)")
plt.legend()

# Save figure to buffer for download
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
buf.seek(0)

st.pyplot(fig)

st.download_button(
    label="⬇️ Download chart (PNG)",
    data=buf,
    file_name="guest_pay_vs_itc_claim.png",
    mime="image/png",
    help="Download the current chart as a PNG image."
)

# -------------------------------
# Recommendation
# -------------------------------
st.subheader("Recommendation")

if absorb_rupees > 0:
    st.info(
        f"You are absorbing ₹{absorb_rupees:,.0f}/night. Guest pays ₹{guest_new_chosen:,.0f} "
        f"(Δ {guest_delta_chosen:+,.0f} vs old). This helps competitiveness; monitor occupancy uplift."
    )
elif absorb_rupees < 0:
    st.warning(
        f"You are capturing {abs(absorb_rupees):,.0f}/night more profit. Guest pays ₹{guest_new_chosen:,.0f} "
        f"(Δ {guest_delta_chosen:+,.0f} vs old). Validate demand at this ADR and bundle value if needed."
    )
else:
    st.success(
        "Neutral posture: profit held constant. If competitors drop guest price, consider small positive absorption to defend share."
    )
