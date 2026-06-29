import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
import base64
import hmac

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Productivity Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Password Protection ───────────────────────────────────────
def check_password():
    if st.session_state.get("authenticated"):
        return True

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🔐 Login")
        st.caption("Masukkan password untuk mengakses dashboard.")
        with st.form("login_form"):
            password = st.text_input("Password", type="password", placeholder="Masukkan password...")
            submitted = st.form_submit_button("Masuk", use_container_width=True)
        if submitted:
            correct = st.secrets.get("APP_PASSWORD", "")
            if correct and hmac.compare_digest(password, correct):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ Password salah. Coba lagi.")
    return False

if not check_password():
    st.stop()



st.markdown("""
<style>
    .metric-card { background:#f8f9fa; border-radius:10px; padding:16px 20px;
                   border-left:4px solid #4f8bf9; margin-bottom:8px; }
    .alert-card  { background:#fff3cd; border-radius:8px; padding:12px 16px;
                   border-left:4px solid #ffc107; margin:4px 0; }
    .alert-name  { font-weight:600; color:#856404; }
    .alert-info  { font-size:12px; color:#856404; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────
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

# ── Load Data ─────────────────────────────────────────────────
@st.cache_data
def load_data(file):
    frames = []
    xls = pd.ExcelFile(file)
    for sheet, role in SHEET_ROLE_MAP.items():
        if sheet not in xls.sheet_names:
            continue
        df = pd.read_excel(file, sheet_name=sheet)
        df = df.rename(columns=lambda c: str(c).strip())

        score_candidates = ["Total % Ach.", "Productivity", "Total Score", "Achievement", "Onsite Clock-In"]
        df["Score"] = 0.0
        for col in score_candidates:
            if col in df.columns:
                df["Score"] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                break

        if "Productivity Range" not in df.columns:
            df["Productivity Range"] = df.get("Productivity", "Unknown")
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

def highlight_range(val):
    colors = {
        "Excellent": "background-color:#d5f5e3; color:#1e8449",
        "Normal":    "background-color:#fdebd0; color:#784212",
        "Poor":      "background-color:#fadbd8; color:#922b21",
        "Achieved":  "background-color:#d5f5e3; color:#1e8449",
    }
    return colors.get(val, "")

def highlight_coef(val):
    try:
        v = float(val)
        if v >= 1.5:   return "background-color:#d5f5e3; color:#1e8449; font-weight:600"
        elif v >= 1.0: return "background-color:#fdebd0; color:#784212"
        elif v > 0:    return "background-color:#fadbd8; color:#922b21"
    except:
        pass
    return ""

# ══════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════
st.title("📊 Productivity Monitoring Dashboard")
st.caption("Upload file Excel, gunakan filter sidebar, dan eksplorasi data produktivitas tim.")

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
    sel_role = st.multiselect("Role", options=["DC","QC","SE","PE"], default=["DC","QC","SE","PE"])
    accounts_avail = sorted(df_all[df_all["Role"].isin(sel_role)]["Account"].dropna().unique())
    sel_account = st.multiselect("Account / Client", options=accounts_avail, default=accounts_avail)
    periods_avail = sorted(df_all["Period"].dropna().unique())
    sel_period  = st.multiselect("Periode", options=periods_avail, default=periods_avail)
    sel_status  = st.multiselect("Status Periode",
                                  options=["Ended","Ongoing","Not Start","Unknown"],
                                  default=["Ended","Ongoing"])
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
    st.warning("⚠️ Tidak ada data untuk kombinasi filter ini.")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview",
    "⚠️ Perlu Perhatian",
    "📅 Perbandingan Periode",
    "👤 Detail Individu",
    "💰 Koefisien Pembayaran",
])

# ══════════════════════════════════════════════════════════════
#  TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════
with tab1:
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
    k1.metric("👥 Total Individu",  f"{total_people:,}")
    k2.metric("📈 Avg Score",       f"{avg_score:.2f}")
    k3.metric("🏆 Excellent",       f"{cnt_excel}  ({pct_excel:.0f}%)")
    k4.metric("⚠️ Poor",            f"{cnt_poor}")
    st.divider()

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
        trend = (df.groupby(["Period","Role"])["Score"].mean().reset_index().sort_values("Period"))
        fig2 = px.line(trend, x="Period", y="Score", color="Role",
                       markers=True, category_orders={"Period": PERIOD_ORDER})
        fig2.update_layout(height=360, margin=dict(t=20))
        st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("🏆 Top 20 Individu — Score Tertinggi")
        top = (df.groupby(["Uniq-ID","Name Clean","Role","Account"])["Score"]
                 .max().reset_index().sort_values("Score", ascending=False).head(20))
        fig3 = px.bar(top, x="Score", y="Name Clean", orientation="h",
                      color="Role", text=top["Score"].round(2), hover_data=["Account","Role"])
        fig3.update_traces(texttemplate="%{text}", textposition="outside")
        fig3.update_layout(height=500, yaxis={"categoryorder":"total ascending"}, margin=dict(t=20))
        st.plotly_chart(fig3, use_container_width=True)

    with c4:
        st.subheader("🏢 Rata-rata Score per Account")
        acct = (df.groupby("Account")["Score"].mean().reset_index().sort_values("Score", ascending=False))
        fig4 = px.bar(acct, x="Account", y="Score", color="Score",
                      color_continuous_scale="RdYlGn", text=acct["Score"].round(2))
        fig4.update_traces(textposition="outside")
        fig4.update_layout(height=500, margin=dict(t=20))
        st.plotly_chart(fig4, use_container_width=True)

    c5, c6 = st.columns(2)
    with c5:
        st.subheader("⏱️ Status Periode")
        stat = (df.drop_duplicates(subset=["Uniq-ID","Period"])
                  .groupby("Period Status").size().reset_index(name="Jumlah"))
        fig5 = px.pie(stat, names="Period Status", values="Jumlah", color="Period Status",
                      color_discrete_map={"Ended":"#27ae60","Ongoing":"#f39c12",
                                          "Not Start":"#95a5a6","Unknown":"#bdc3c7"})
        fig5.update_layout(height=360, margin=dict(t=20))
        st.plotly_chart(fig5, use_container_width=True)

    with c6:
        st.subheader("🗺️ Sebaran per Region")
        if df["Region"].nunique() > 1:
            reg = (df.drop_duplicates(subset=["Uniq-ID","Period"])
                     .groupby(["Region","Productivity Range"]).size().reset_index(name="Jumlah"))
            fig6 = px.bar(reg, x="Region", y="Jumlah", color="Productivity Range",
                          color_discrete_map=RANGE_COLOR, barmode="stack", text="Jumlah")
            fig6.update_traces(textposition="inside")
            fig6.update_layout(height=360, margin=dict(t=20))
            st.plotly_chart(fig6, use_container_width=True)
        else:
            st.info("Data Region hanya tersedia untuk role QC, SE, dan PE.")

# ══════════════════════════════════════════════════════════════
#  TAB 2 — PERLU PERHATIAN
# ══════════════════════════════════════════════════════════════
with tab2:
    st.subheader("⚠️ Individu yang Perlu Perhatian")
    st.caption("Berdasarkan periode aktif (Ended/Ongoing) dengan score rendah atau konsisten Poor.")

    # Ambil periode aktif saja
    df_active = df[df["Period Status"].isin(["Ended","Ongoing"])].copy()

    # Score rendah: semua periode = Poor atau score 0 terus
    summary = df_active.groupby(["Uniq-ID","Name Clean","Role","Account"]).agg(
        Avg_Score=("Score", "mean"),
        Max_Score=("Score", "max"),
        All_Poor=("Productivity Range", lambda x: (x.isin(["Poor","Unknown"])).all()),
        Latest_Coef=("Payment Coef.", "last"),
        Periods=("Period", "nunique"),
    ).reset_index()

    at_risk = summary[
        (summary["All_Poor"] == True) |
        (summary["Max_Score"] == 0) |
        (summary["Avg_Score"] < 0.5)
    ].sort_values("Avg_Score")

    consistent_poor = summary[
        (summary["All_Poor"] == True) & (summary["Periods"] >= 2)
    ]

    zero_score = summary[summary["Max_Score"] == 0]

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("🔴 Total At-Risk",        len(at_risk))
    col_b.metric("📉 Konsisten Poor (≥2P)", len(consistent_poor))
    col_c.metric("⭕ Score 0 Semua Periode", len(zero_score))
    st.divider()

    if not at_risk.empty:
        # Chart distribusi at-risk per Role
        risk_role = at_risk.groupby("Role").size().reset_index(name="Jumlah")
        fig_risk = px.bar(risk_role, x="Role", y="Jumlah", color="Role",
                          title="At-Risk per Role", text="Jumlah", height=280)
        fig_risk.update_traces(textposition="outside")
        fig_risk.update_layout(showlegend=False, margin=dict(t=40,b=20))
        st.plotly_chart(fig_risk, use_container_width=True)

        st.subheader("📋 Daftar Individu At-Risk")
        tbl_risk = at_risk[["Name Clean","Role","Account","Avg_Score","Max_Score","Latest_Coef","Periods"]].copy()
        tbl_risk.columns = ["Nama","Role","Account","Avg Score","Max Score","Koef Terakhir","Jumlah Periode"]
        tbl_risk = tbl_risk.reset_index(drop=True)

        def highlight_avg_score(val):
            try:
                v = float(val)
                if v >= 3:   return "background-color:#d5f5e3; color:#1e8449; font-weight:600"
                elif v >= 1: return "background-color:#fdebd0; color:#784212"
                else:        return "background-color:#fadbd8; color:#922b21"
            except:
                return ""

        st.dataframe(
            tbl_risk.style
                .map(highlight_avg_score, subset=["Avg Score"])
                .format({"Avg Score":"{:.2f}", "Max Score":"{:.2f}",
                         "Koef Terakhir": lambda x: f"{x:.1f}" if pd.notna(x) else "–"}),
            use_container_width=True, height=400
        )

        csv_risk = tbl_risk.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Daftar At-Risk (CSV)", data=csv_risk,
                           file_name="at_risk.csv", mime="text/csv")
    else:
        st.success("✅ Tidak ada individu at-risk dengan filter saat ini!")

# ══════════════════════════════════════════════════════════════
#  TAB 3 — PERBANDINGAN PERIODE
# ══════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📅 Perbandingan Antar Periode")

    periods_available = sorted(df["Period"].dropna().unique())
    if len(periods_available) < 2:
        st.info("Butuh minimal 2 periode untuk perbandingan.")
    else:
        col_p1, col_p2 = st.columns(2)
        p1 = col_p1.selectbox("Periode A", options=periods_available, index=0)
        p2 = col_p2.selectbox("Periode B", options=periods_available,
                               index=min(1, len(periods_available)-1))

        df_p1 = df[df["Period"] == p1].groupby("Uniq-ID").agg(
            Score_A=("Score","max"), Range_A=("Productivity Range", lambda x: x.mode()[0] if not x.mode().empty else "Unknown"),
            Name=("Name Clean","first"), Role=("Role","first"), Account=("Account","first")
        ).reset_index()

        df_p2 = df[df["Period"] == p2].groupby("Uniq-ID").agg(
            Score_B=("Score","max"), Range_B=("Productivity Range", lambda x: x.mode()[0] if not x.mode().empty else "Unknown")
        ).reset_index()

        comp = df_p1.merge(df_p2, on="Uniq-ID", how="outer")
        comp["Score_A"] = comp["Score_A"].fillna(0)
        comp["Score_B"] = comp["Score_B"].fillna(0)
        comp["Delta"]   = comp["Score_B"] - comp["Score_A"]
        comp["Trend"]   = comp["Delta"].apply(lambda x: "📈 Naik" if x > 0 else ("📉 Turun" if x < 0 else "➡️ Sama"))

        st.divider()
        col_m1, col_m2, col_m3 = st.columns(3)
        naik  = (comp["Delta"] > 0).sum()
        turun = (comp["Delta"] < 0).sum()
        sama  = (comp["Delta"] == 0).sum()
        col_m1.metric("📈 Naik",  naik)
        col_m2.metric("📉 Turun", turun)
        col_m3.metric("➡️ Sama",  sama)

        # Scatter plot perbandingan
        fig_comp = px.scatter(
            comp.dropna(subset=["Name"]), x="Score_A", y="Score_B",
            color="Trend", hover_name="Name",
            hover_data=["Role","Account","Delta"],
            labels={"Score_A": f"Score {p1}", "Score_B": f"Score {p2}"},
            title=f"Perbandingan Score: {p1} vs {p2}",
            color_discrete_map={"📈 Naik":"#27ae60","📉 Turun":"#e74c3c","➡️ Sama":"#95a5a6"},
            height=420
        )
        # Garis diagonal (sama persis)
        max_val = max(comp["Score_A"].max(), comp["Score_B"].max()) * 1.05
        fig_comp.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                           line=dict(dash="dot", color="gray", width=1))
        fig_comp.update_layout(margin=dict(t=40))
        st.plotly_chart(fig_comp, use_container_width=True)

        # Top mover
        c_up, c_down = st.columns(2)
        with c_up:
            st.markdown("**🚀 Top 10 Paling Naik**")
            top_up = comp.nlargest(10, "Delta")[["Name","Role","Score_A","Score_B","Delta"]].reset_index(drop=True)
            top_up.columns = ["Nama","Role",f"Score {p1}",f"Score {p2}","Delta"]
            st.dataframe(top_up.style.format({f"Score {p1}":"{:.2f}",f"Score {p2}":"{:.2f}","Delta":"{:+.2f}"}),
                         use_container_width=True, height=300)
        with c_down:
            st.markdown("**📉 Top 10 Paling Turun**")
            top_down = comp.nsmallest(10, "Delta")[["Name","Role","Score_A","Score_B","Delta"]].reset_index(drop=True)
            top_down.columns = ["Nama","Role",f"Score {p1}",f"Score {p2}","Delta"]
            st.dataframe(top_down.style.format({f"Score {p1}":"{:.2f}",f"Score {p2}":"{:.2f}","Delta":"{:+.2f}"}),
                         use_container_width=True, height=300)

# ══════════════════════════════════════════════════════════════
#  TAB 4 — DETAIL INDIVIDU
# ══════════════════════════════════════════════════════════════
with tab4:
    st.subheader("👤 Detail per Individu")

    names_avail = sorted(df["Name Clean"].dropna().unique())
    sel_name = st.selectbox("Pilih individu:", options=names_avail)

    df_ind = df[df["Name Clean"] == sel_name].copy()

    if df_ind.empty:
        st.warning("Data tidak ditemukan.")
    else:
        info = df_ind.iloc[0]

        period_data = (df_ind.groupby("Period").agg(
            Score=("Score","max"),
            Status=("Period Status","first"),
            Range=("Productivity Range", lambda x: x.mode()[0] if not x.mode().empty else "Unknown"),
            Coef=("Payment Coef.","first"),
        ).reset_index().sort_values("Period"))

        avg_score    = period_data["Score"].mean()
        max_score    = period_data["Score"].max()
        best_period  = period_data.loc[period_data["Score"].idxmax(), "Period"] if not period_data.empty else "–"
        last_coef    = period_data["Coef"].dropna().iloc[-1] if period_data["Coef"].notna().any() else None
        n_periods    = len(period_data)
        overall_range = period_data["Range"].mode()[0] if not period_data["Range"].mode().empty else "Unknown"

        if len(period_data) >= 2:
            delta = period_data["Score"].iloc[-1] - period_data["Score"].iloc[-2]
            if delta > 0.5:    tren_text = f"naik {delta:.1f} poin dari periode sebelumnya"
            elif delta < -0.5: tren_text = f"turun {abs(delta):.1f} poin dari periode sebelumnya"
            else:              tren_text = "stabil dibanding periode sebelumnya"
        else:
            tren_text = "baru 1 periode aktif"

        coef_vals = period_data["Coef"].dropna()
        if len(coef_vals) >= 2:
            coef_delta = coef_vals.iloc[-1] - coef_vals.iloc[-2]
            coef_note = f"Koefisien {'naik' if coef_delta > 0 else 'turun' if coef_delta < 0 else 'stabil'} ke {coef_vals.iloc[-1]:.1f} di periode terakhir."
        elif len(coef_vals) == 1:
            coef_note = f"Koefisien tercatat {coef_vals.iloc[0]:.1f}."
        else:
            coef_note = "Data koefisien belum tersedia."

        badge_colors = {
            "Excellent": ("#d5f5e3","#1e8449"),
            "Normal":    ("#fdebd0","#784212"),
            "Poor":      ("#fadbd8","#922b21"),
            "Achieved":  ("#d5f5e3","#1e8449"),
            "Unknown":   ("#f0f0f0","#555"),
        }
        badge_bg, badge_fg = badge_colors.get(overall_range, ("#f0f0f0","#555"))

        parts    = sel_name.split()
        initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()

        if overall_range == "Excellent":
            narasi_icon = "✅"
            narasi = f"Performa terbaik di {best_period} (score {max_score:.1f}). {coef_note} Score {tren_text}."
        elif overall_range == "Poor":
            narasi_icon = "⚠️"
            narasi = f"Perlu perhatian — score tertinggi hanya {max_score:.1f} di {best_period}. {coef_note} Score {tren_text}."
        else:
            narasi_icon = "📊"
            narasi = f"Score terbaik {max_score:.1f} di {best_period}. {coef_note} Score {tren_text}."

        narasi_colors = {
            "Excellent": ("#eaf7f0","#1e8449","#27ae60"),
            "Normal":    ("#fef9ec","#784212","#f39c12"),
            "Poor":      ("#fdf3f2","#922b21","#e74c3c"),
            "Achieved":  ("#eaf7f0","#1e8449","#27ae60"),
            "Unknown":   ("#f5f5f5","#555","#aaa"),
        }
        n_bg, n_fg, n_border = narasi_colors.get(overall_range, ("#f5f5f5","#555","#aaa"))

        coef_display = f"{last_coef:.1f}" if last_coef is not None else "–"
        coef_color   = "#1e8449" if last_coef and last_coef >= 1.5 else ("#784212" if last_coef and last_coef >= 1.0 else "#922b21")

        st.markdown(f"""
        <div style="background:var(--surface-2); border:0.5px solid var(--border); border-radius:12px; padding:1.25rem; margin-bottom:16px;">
          <div style="display:flex; align-items:center; gap:14px; margin-bottom:16px;">
            <div style="width:52px; height:52px; border-radius:50%; background:{badge_bg};
                        display:flex; align-items:center; justify-content:center;
                        font-weight:500; font-size:16px; color:{badge_fg}; flex-shrink:0;">
              {initials}
            </div>
            <div style="flex:1;">
              <p style="font-weight:500; font-size:16px; margin:0; color:var(--text-primary);">{sel_name}</p>
              <p style="font-size:13px; color:var(--text-muted); margin:2px 0 0;">
                {info.get("Role","–")} &middot; {info.get("Account","–")} &middot; {info.get("Region","–")}
              </p>
            </div>
            <div style="background:{badge_bg}; border-radius:20px; padding:4px 14px;
                        font-size:12px; font-weight:500; color:{badge_fg}; white-space:nowrap;">
              {overall_range}
            </div>
          </div>
          <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:14px;">
            <div style="background:var(--surface-1); border-radius:8px; padding:10px 12px;">
              <p style="font-size:11px; color:var(--text-muted); margin:0 0 4px;">Avg Score</p>
              <p style="font-size:22px; font-weight:500; margin:0; color:var(--text-primary);">{avg_score:.1f}</p>
            </div>
            <div style="background:var(--surface-1); border-radius:8px; padding:10px 12px;">
              <p style="font-size:11px; color:var(--text-muted); margin:0 0 4px;">Max Score</p>
              <p style="font-size:22px; font-weight:500; margin:0; color:var(--text-primary);">{max_score:.1f}</p>
            </div>
            <div style="background:var(--surface-1); border-radius:8px; padding:10px 12px;">
              <p style="font-size:11px; color:var(--text-muted); margin:0 0 4px;">Koefisien</p>
              <p style="font-size:22px; font-weight:500; margin:0; color:{coef_color};">{coef_display}</p>
            </div>
            <div style="background:var(--surface-1); border-radius:8px; padding:10px 12px;">
              <p style="font-size:11px; color:var(--text-muted); margin:0 0 4px;">Periode Aktif</p>
              <p style="font-size:22px; font-weight:500; margin:0; color:var(--text-primary);">{n_periods}</p>
            </div>
          </div>
          <div style="background:{n_bg}; border-radius:8px; padding:10px 14px; border-left:3px solid {n_border};">
            <p style="font-size:13px; color:{n_fg}; margin:0; line-height:1.6;">{narasi_icon} {narasi}</p>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        col_chart, col_tbl = st.columns([3,2])
        with col_chart:
            fig_ind = go.Figure()
            fig_ind.add_trace(go.Bar(
                x=period_data["Period"], y=period_data["Score"],
                marker_color=[RANGE_COLOR.get(r,"#95a5a6") for r in period_data["Range"]],
                text=period_data["Score"].round(2), textposition="outside",
                name="Score"
            ))
            fig_ind.update_layout(title=f"Score per Periode — {sel_name}",
                                   height=320, margin=dict(t=40,b=20),
                                   xaxis_title="Periode", yaxis_title="Score")
            st.plotly_chart(fig_ind, use_container_width=True)

        with col_tbl:
            st.markdown("**Ringkasan per Periode**")
            disp = period_data[["Period","Status","Range","Score","Coef"]].copy()
            disp.columns = ["Periode","Status","Range","Score","Koef"]
            st.dataframe(
                disp.style
                    .map(highlight_range, subset=["Range"])
                    .map(highlight_coef,  subset=["Koef"])
                    .format({"Score":"{:.2f}", "Koef": lambda x: f"{x:.1f}" if pd.notna(x) else "–"}),
                use_container_width=True, height=260
            )

        if period_data["Coef"].notna().any():
            fig_coef = px.line(period_data, x="Period", y="Coef",
                               markers=True, title="Tren Koefisien Pembayaran",
                               color_discrete_sequence=["#4f8bf9"], height=260)
            fig_coef.add_hline(y=1.0, line_dash="dot", line_color="orange", annotation_text="Batas Normal")
            fig_coef.add_hline(y=1.5, line_dash="dot", line_color="green",  annotation_text="Excellent")
            fig_coef.update_layout(margin=dict(t=40,b=20))
            st.plotly_chart(fig_coef, use_container_width=True)

        # Kolom detail per role
        ROLE_DETAIL_COLS = {
            "DC": ["Document Category","Document Type","Source Data","Baseline/Cycle","Total Doc.","% Achievement"],
            "QC": ["QEHS Inspection (ONSITE)","Compliance Check (TL)","Training (Class)","Baseline","Achievement"],
            "SE": ["Onsite Clock-In","M-06 Integrated"],
            "PE": ["M-04 MOS   (20%)","M-05 Installation   (30%)","On Air   (20%)","ATP Submit   (20%)","ATP Approve   (20%)","Total Score"],
        }

        role = info.get("Role","")
        detail_cols = [c for c in ROLE_DETAIL_COLS.get(role, []) if c in df_ind.columns]

        if detail_cols:
            st.markdown("**Detail per Periode**")
            detail_tbl = (df_ind[["Period","Period Status"] + detail_cols]
                            .sort_values("Period")
                            .reset_index(drop=True))
            # Format angka
            num_cols = [c for c in detail_cols if pd.api.types.is_numeric_dtype(detail_tbl[c])]
            fmt = {c: "{:.0f}" for c in num_cols}
            st.dataframe(
                detail_tbl.style.format(fmt, na_rep="–"),
                use_container_width=True,
                height=200,
            )
        else:
            st.info("Tidak ada data detail tambahan untuk individu ini.")


# ══════════════════════════════════════════════════════════════
#  TAB 5 — KOEFISIEN PEMBAYARAN
# ══════════════════════════════════════════════════════════════
with tab5:
    st.subheader("💰 Analisis Koefisien Pembayaran")
    st.caption("Koefisien: 1.5 = Excellent · 1.0 = Normal · 0.9 = Poor · 0.5 = Very Poor")

    df_coef = df[df["Payment Coef."].notna()].copy()

    if df_coef.empty:
        st.info("Tidak ada data koefisien untuk filter ini.")
    else:
        # KPI
        avg_coef  = df_coef.groupby("Uniq-ID")["Payment Coef."].last().mean()
        cnt_15    = (df_coef.groupby("Uniq-ID")["Payment Coef."].last() >= 1.5).sum()
        cnt_low   = (df_coef.groupby("Uniq-ID")["Payment Coef."].last() < 1.0).sum()

        ck1, ck2, ck3 = st.columns(3)
        ck1.metric("📊 Avg Koefisien",      f"{avg_coef:.2f}")
        ck2.metric("🟢 Koef ≥ 1.5 (Excellent)", cnt_15)
        ck3.metric("🔴 Koef < 1.0 (Poor)",  cnt_low)
        st.divider()

        cc1, cc2 = st.columns(2)
        with cc1:
            # Distribusi koefisien
            coef_dist = (df_coef.groupby(["Role","Payment Coef."])
                           .size().reset_index(name="Jumlah"))
            coef_dist["Koef"] = coef_dist["Payment Coef."].astype(str)
            fig_c1 = px.bar(coef_dist, x="Koef", y="Jumlah", color="Role",
                            barmode="group", title="Distribusi Koefisien per Role",
                            text="Jumlah", height=340)
            fig_c1.update_traces(textposition="outside")
            fig_c1.update_layout(margin=dict(t=40))
            st.plotly_chart(fig_c1, use_container_width=True)

        with cc2:
            # Avg koefisien per account
            coef_acct = (df_coef.groupby("Account")["Payment Coef."]
                           .mean().reset_index()
                           .sort_values("Payment Coef.", ascending=False))
            fig_c2 = px.bar(coef_acct, x="Account", y="Payment Coef.",
                            color="Payment Coef.", color_continuous_scale="RdYlGn",
                            title="Rata-rata Koefisien per Account",
                            text=coef_acct["Payment Coef."].round(2), height=340)
            fig_c2.update_traces(textposition="outside")
            fig_c2.update_layout(margin=dict(t=40))
            st.plotly_chart(fig_c2, use_container_width=True)

        # Tren koefisien per periode
        coef_trend = (df_coef.groupby(["Period","Role"])["Payment Coef."]
                        .mean().reset_index().sort_values("Period"))
        fig_ct = px.line(coef_trend, x="Period", y="Payment Coef.", color="Role",
                         markers=True, title="Tren Koefisien per Periode",
                         category_orders={"Period": PERIOD_ORDER}, height=320)
        fig_ct.add_hline(y=1.0, line_dash="dot", line_color="orange", annotation_text="Normal (1.0)")
        fig_ct.add_hline(y=1.5, line_dash="dot", line_color="green",  annotation_text="Excellent (1.5)")
        fig_ct.update_layout(margin=dict(t=40))
        st.plotly_chart(fig_ct, use_container_width=True)

        # Tabel lengkap koefisien
        st.markdown("**📋 Tabel Koefisien per Individu**")
        coef_tbl = (df_coef.groupby(["Uniq-ID","Name Clean","Role","Account","Period"])
                      .agg(Score=("Score","max"), Coef=("Payment Coef.","first"),
                           Range=("Productivity Range", lambda x: x.mode()[0] if not x.mode().empty else "Unknown"))
                      .reset_index()
                      .sort_values(["Role","Coef"], ascending=[True,False]))

        st.dataframe(
            coef_tbl.rename(columns={"Name Clean":"Nama","Payment Coef.":"Koef",
                                      "Productivity Range":"Range"})
                    .style
                    .map(highlight_range, subset=["Range"])
                    .map(highlight_coef,  subset=["Coef"])
                    .format({"Score":"{:.2f}", "Coef": lambda x: f"{x:.1f}" if pd.notna(x) else "–"}),
            use_container_width=True, height=400
        )

        csv_coef = coef_tbl.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Tabel Koefisien (CSV)", data=csv_coef,
                           file_name="koefisien.csv", mime="text/csv")

# ── Footer ────────────────────────────────────────────────────
st.divider()
st.caption("📊 Productivity Dashboard · Data diproses langsung dari file Excel yang diupload")
