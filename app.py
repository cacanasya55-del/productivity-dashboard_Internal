import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Productivity Dashboard",
    page_icon="📊",
    layout="wide",
)

# ── Styling ──────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 16px 20px;
        border-left: 4px solid #4f8bf9;
        margin-bottom: 8px;
    }
    .metric-val { font-size: 2rem; font-weight: 700; color: #1a1a2e; }
    .metric-lbl { font-size: 0.8rem; color: #6c757d; margin-top: 2px; }
    .excellent  { color: #27ae60; font-weight: 600; }
    .normal     { color: #f39c12; font-weight: 600; }
    .poor       { color: #e74c3c; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── Constants ────────────────────────────────────────────────
SHEET_ROLE_MAP = {
    "DC Productivity": "DC",
    "QC Productivity": "QC",
    "SE Productivity": "SE",
    "PE Productivity": "PE",
}
RANGE_COLOR = {
    "Excellent": "#27ae60",
    "Normal":    "#f39c12",
    "Poor":      "#e74c3c",
    "Achieved":  "#27ae60",
    "Unknown":   "#95a5a6",
}
PERIOD_ORDER = ["M-01", "M-02", "M-03", "M-04"]

# ── Load Data ────────────────────────────────────────────────
@st.cache_data
def load_data(file):
    frames = []
    xls = pd.ExcelFile(file)

    for sheet, role in SHEET_ROLE_MAP.items():
        if sheet not in xls.sheet_names:
            continue
        df = pd.read_excel(file, sheet_name=sheet)
        df = df.rename(columns=lambda c: str(c).strip())

        # Score → normalise ke satu kolom
        score_candidates = ["Total % Ach.", "Productivity", "Total Score", "Achievement", "Onsite Clock-In"]
        df["Score"] = 0.0
        for col in score_candidates:
            if col in df.columns:
                df["Score"] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                break

        # Productivity Range
        if "Productivity Range" not in df.columns:
            if "Productivity" in df.columns:
                df["Productivity Range"] = df["Productivity"]
            else:
                df["Productivity Range"] = "Unknown"

        # Region
        if "Region" not in df.columns:
            df["Region"] = "–"

        df["Role"]  = role
        df["Sheet"] = sheet

        for c in ["Account", "Period", "Period Status", "Payment Coef.", "Name ID", "Uniq-ID"]:
            if c not in df.columns:
                df[c] = None

        frames.append(df)

    all_data = pd.concat(frames, ignore_index=True)

    all_data["Score"]              = pd.to_numeric(all_data["Score"], errors="coerce").fillna(0)
    all_data["Payment Coef."]      = pd.to_numeric(all_data["Payment Coef."], errors="coerce")
    all_data["Productivity Range"] = all_data["Productivity Range"].fillna("Unknown")
    all_data["Period Status"]      = all_data["Period Status"].fillna("Unknown")
    all_data["Account"]            = all_data["Account"].fillna("Unknown")
    all_data["Region"]             = all_data["Region"].fillna("–")
    all_data["Name Clean"]         = (all_data["Name ID"]
                                        .astype(str)
                                        .str.replace(r"\s+wx\d+", "", regex=True)
                                        .str.strip())
    return all_data


# ══════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════
st.title("📊 Productivity Monitoring Dashboard")
st.caption("Upload file Excel kamu, lalu gunakan filter di sidebar untuk eksplorasi data.")

# ── Upload ────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Upload Combined_Data_Productivity_Report.xlsx",
    type=["xlsx"],
    help="File harus punya sheet: DC Productivity, QC Productivity, SE Productivity, PE Productivity"
)

if uploaded is None:
    st.info("👆 Upload file Excel untuk memulai.")
    st.stop()

df_all = load_data(uploaded)

# ── Sidebar Filters ───────────────────────────────────────────
with st.sidebar:
    st.header("🔍 Filter")

    sel_role = st.multiselect(
        "Role", options=["DC","QC","SE","PE"],
        default=["DC","QC","SE","PE"]
    )

    accounts_avail = sorted(df_all[df_all["Role"].isin(sel_role)]["Account"].dropna().unique())
    sel_account = st.multiselect(
        "Account / Client", options=accounts_avail,
        default=accounts_avail
    )

    periods_avail = sorted(df_all["Period"].dropna().unique())
    sel_period = st.multiselect(
        "Periode", options=periods_avail,
        default=periods_avail
    )

    sel_status = st.multiselect(
        "Status Periode",
        options=["Ended","Ongoing","Not Start","Unknown"],
        default=["Ended","Ongoing"]
    )

    name_q = st.text_input("🔎 Cari Nama", placeholder="ketik sebagian nama...")

    regions_avail = sorted(df_all[df_all["Role"].isin(sel_role)]["Region"].dropna().unique())
    sel_region = st.multiselect("Region", options=regions_avail, default=regions_avail)

    st.divider()
    st.caption("💡 Pilih lebih dari satu opsi dengan klik.")

# ── Apply Filter ──────────────────────────────────────────────
mask = (
    df_all["Role"].isin(sel_role) &
    df_all["Account"].isin(sel_account) &
    df_all["Period"].isin(sel_period) &
    df_all["Period Status"].isin(sel_status) &
    df_all["Region"].isin(sel_region)
)
df = df_all[mask].copy()

if name_q.strip():
    df = df[df["Name Clean"].str.contains(name_q.strip(), case=False, na=False)]

if df.empty:
    st.warning("⚠️ Tidak ada data untuk kombinasi filter ini. Coba ubah filter.")
    st.stop()

# ══════════════════════════════════════════════════════════════
#  KPI CARDS
# ══════════════════════════════════════════════════════════════
per_person = df.groupby("Uniq-ID").agg(
    Score=("Score", "max"),
    Prod_Range=("Productivity Range", lambda x: x.mode()[0] if not x.mode().empty else "Unknown"),
).reset_index()

total_people = per_person["Uniq-ID"].nunique()
avg_score    = per_person["Score"].mean()
cnt_excel    = (per_person["Prod_Range"] == "Excellent").sum()
cnt_poor     = (per_person["Prod_Range"] == "Poor").sum()
pct_excel    = cnt_excel / total_people * 100 if total_people else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("👥 Total Individu",    f"{total_people:,}")
k2.metric("📈 Avg Score",         f"{avg_score:.2f}")
k3.metric("🏆 Excellent",         f"{cnt_excel}  ({pct_excel:.0f}%)")
k4.metric("⚠️ Poor",              f"{cnt_poor}")

st.divider()

# ══════════════════════════════════════════════════════════════
#  CHARTS — ROW 1
# ══════════════════════════════════════════════════════════════
c1, c2 = st.columns(2)

with c1:
    st.subheader("Distribusi Productivity Range per Role")
    dist = (df.drop_duplicates(subset=["Uniq-ID","Period"])
              .groupby(["Role","Productivity Range"])
              .size().reset_index(name="Jumlah"))
    fig = px.bar(dist, x="Role", y="Jumlah", color="Productivity Range",
                 color_discrete_map=RANGE_COLOR, barmode="stack", text="Jumlah")
    fig.update_traces(textposition="inside")
    fig.update_layout(height=360, legend_title="Range", margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Tren Rata-rata Score per Periode")
    trend = (df.groupby(["Period","Role"])["Score"]
               .mean().reset_index()
               .sort_values("Period"))
    fig2 = px.line(trend, x="Period", y="Score", color="Role",
                   markers=True,
                   category_orders={"Period": PERIOD_ORDER})
    fig2.update_layout(height=360, margin=dict(t=20))
    st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════════
#  CHARTS — ROW 2
# ══════════════════════════════════════════════════════════════
c3, c4 = st.columns(2)

with c3:
    st.subheader("🏆 Top 20 Individu — Score Tertinggi")
    top = (df.groupby(["Uniq-ID","Name Clean","Role","Account"])["Score"]
             .max().reset_index()
             .sort_values("Score", ascending=False)
             .head(20))
    fig3 = px.bar(top, x="Score", y="Name Clean", orientation="h",
                  color="Role", text=top["Score"].round(2),
                  hover_data=["Account","Role"])
    fig3.update_traces(texttemplate="%{text}", textposition="outside")
    fig3.update_layout(height=500, yaxis={"categoryorder":"total ascending"}, margin=dict(t=20))
    st.plotly_chart(fig3, use_container_width=True)

with c4:
    st.subheader("🏢 Rata-rata Score per Account")
    acct = (df.groupby("Account")["Score"]
              .mean().reset_index()
              .sort_values("Score", ascending=False))
    fig4 = px.bar(acct, x="Account", y="Score",
                  color="Score", color_continuous_scale="RdYlGn",
                  text=acct["Score"].round(2))
    fig4.update_traces(textposition="outside")
    fig4.update_layout(height=500, margin=dict(t=20))
    st.plotly_chart(fig4, use_container_width=True)

# ══════════════════════════════════════════════════════════════
#  CHARTS — ROW 3
# ══════════════════════════════════════════════════════════════
c5, c6 = st.columns(2)

with c5:
    st.subheader("⏱️ Status Periode")
    stat = (df.drop_duplicates(subset=["Uniq-ID","Period"])
              .groupby("Period Status").size()
              .reset_index(name="Jumlah"))
    fig5 = px.pie(stat, names="Period Status", values="Jumlah",
                  color="Period Status",
                  color_discrete_map={
                      "Ended":"#27ae60","Ongoing":"#f39c12",
                      "Not Start":"#95a5a6","Unknown":"#bdc3c7"
                  })
    fig5.update_layout(height=360, margin=dict(t=20))
    st.plotly_chart(fig5, use_container_width=True)

with c6:
    st.subheader("🗺️ Sebaran per Region")
    if df["Region"].nunique() > 1:
        reg = (df.drop_duplicates(subset=["Uniq-ID","Period"])
                 .groupby(["Region","Productivity Range"])
                 .size().reset_index(name="Jumlah"))
        fig6 = px.bar(reg, x="Region", y="Jumlah", color="Productivity Range",
                      color_discrete_map=RANGE_COLOR, barmode="stack", text="Jumlah")
        fig6.update_traces(textposition="inside")
        fig6.update_layout(height=360, margin=dict(t=20))
        st.plotly_chart(fig6, use_container_width=True)
    else:
        st.info("Data Region hanya tersedia untuk role QC, SE, dan PE.")

# ══════════════════════════════════════════════════════════════
#  TABEL DETAIL
# ══════════════════════════════════════════════════════════════
st.divider()
st.subheader("📋 Tabel Detail")

cols_show = ["Uniq-ID","Name Clean","Role","Account","Region",
             "Period","Period Status","Productivity Range","Score","Payment Coef."]
cols_show = [c for c in cols_show if c in df.columns]

tbl = (df[cols_show]
       .drop_duplicates(subset=["Uniq-ID","Period"])
       .sort_values(["Role","Score"], ascending=[True, False])
       .reset_index(drop=True))

def highlight_range(val):
    colors = {
        "Excellent": "background-color:#d5f5e3; color:#1e8449",
        "Normal":    "background-color:#fdebd0; color:#784212",
        "Poor":      "background-color:#fadbd8; color:#922b21",
        "Achieved":  "background-color:#d5f5e3; color:#1e8449",
    }
    return colors.get(val, "")

st.dataframe(
    tbl.style
       .map(highlight_range, subset=["Productivity Range"])
       .format({"Score": "{:.2f}", "Payment Coef.": lambda x: f"{x:.1f}" if pd.notna(x) else "–"}),
    use_container_width=True,
    height=400,
)

# Download tabel
csv = tbl.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download Tabel sebagai CSV",
    data=csv,
    file_name="productivity_filtered.csv",
    mime="text/csv",
)
