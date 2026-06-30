import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
import base64

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Productivity Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>

\&#x20;   .metric-card { background:#f8f9fa; border-radius:10px; padding:16px 20px;

\&#x20;                  border-left:4px solid #4f8bf9; margin-bottom:8px; }

\&#x20;   .alert-card  { background:#fff3cd; border-radius:8px; padding:12px 16px;

\&#x20;                  border-left:4px solid #ffc107; margin:4px 0; }

\&#x20;   .alert-name  { font-weight:600; color:#856404; }

\&#x20;   .alert-info  { font-size:12px; color:#856404; }


""", unsafe\_allow\_html=True)



\# ── Constants ─────────────────────────────────────────────────

SHEET\_ROLE\_MAP = {

&#x20;   "DC Productivity": "DC",

&#x20;   "QC Productivity": "QC",

&#x20;   "SE Productivity": "SE",

&#x20;   "PE Productivity": "PE",

}

RANGE\_COLOR = {

&#x20;   "Excellent": "#27ae60",

&#x20;   "Normal":    "#f39c12",

&#x20;   "Poor":      "#e74c3c",

&#x20;   "Achieved":  "#27ae60",

&#x20;   "Unknown":   "#95a5a6",

}

PERIOD\_ORDER = \["M-01", "M-02", "M-03", "M-04"]



\# ── Load Data ─────────────────────────────────────────────────

@st.cache\_data

def load\_data(file):

&#x20;   frames = \[]

&#x20;   xls = pd.ExcelFile(file)

&#x20;   for sheet, role in SHEET\_ROLE\_MAP.items():

&#x20;       if sheet not in xls.sheet\_names:

&#x20;           continue

&#x20;       df = pd.read\_excel(file, sheet\_name=sheet)

&#x20;       df = df.rename(columns=lambda c: str(c).strip())



&#x20;       score\_candidates = \["Total % Ach.", "Productivity", "Total Score", "Achievement", "Onsite Clock-In"]

&#x20;       df\["Score"] = 0.0

&#x20;       for col in score\_candidates:

&#x20;           if col in df.columns:

&#x20;               df\["Score"] = pd.to\_numeric(df\[col], errors="coerce").fillna(0)

&#x20;               break



&#x20;       if "Productivity Range" not in df.columns:

&#x20;           df\["Productivity Range"] = df.get("Productivity", "Unknown")

&#x20;       if "Region" not in df.columns:

&#x20;           df\["Region"] = "–"



&#x20;       df\["Role"]  = role

&#x20;       df\["Sheet"] = sheet

&#x20;       for c in \["Account", "Period", "Period Status", "Payment Coef.", "Name ID", "Uniq-ID"]:

&#x20;           if c not in df.columns:

&#x20;               df\[c] = None

&#x20;       frames.append(df)



&#x20;   all\_data = pd.concat(frames, ignore\_index=True)

&#x20;   all\_data\["Score"]              = pd.to\_numeric(all\_data\["Score"], errors="coerce").fillna(0)

&#x20;   all\_data\["Payment Coef."]      = pd.to\_numeric(all\_data\["Payment Coef."], errors="coerce")

&#x20;   all\_data\["Productivity Range"] = all\_data\["Productivity Range"].fillna("Unknown")

&#x20;   all\_data\["Period Status"]      = all\_data\["Period Status"].fillna("Unknown")

&#x20;   all\_data\["Account"]            = all\_data\["Account"].fillna("Unknown")

&#x20;   all\_data\["Region"]             = all\_data\["Region"].fillna("–")

&#x20;   all\_data\["Name Clean"]         = (all\_data\["Name ID"]

&#x20;                                       .astype(str)

&#x20;                                       .str.replace(r"\\s+wx\\d+", "", regex=True)

&#x20;                                       .str.strip())

&#x20;   return all\_data



def highlight\_range(val):

&#x20;   colors = {

&#x20;       "Excellent": "background-color:#d5f5e3; color:#1e8449",

&#x20;       "Normal":    "background-color:#fdebd0; color:#784212",

&#x20;       "Poor":      "background-color:#fadbd8; color:#922b21",

&#x20;       "Achieved":  "background-color:#d5f5e3; color:#1e8449",

&#x20;   }

&#x20;   return colors.get(val, "")



def highlight\_coef(val):

&#x20;   try:

&#x20;       v = float(val)



&#x20;       if v >= 1.5:

&#x20;           return "background-color:#d5f5e3; color:#1e8449; font-weight:600"



&#x20;       elif v >= 1.0:

&#x20;           return "background-color:#fdebd0; color:#784212"



&#x20;       elif v > 0:

&#x20;           return "background-color:#fadbd8; color:#922b21"



&#x20;   except:

&#x20;       pass



&#x20;   return ""





\# ══════════════════════════════════════════════

\# REPORT CARD HELPERS

\# ══════════════════════════════════════════════



def generate\_insight(df\_person):



&#x20;   scores=(

&#x20;       df\_person

&#x20;       .sort\_values("Period")\["Score"]

&#x20;       .reset\_index(drop=True)

&#x20;   )



&#x20;   if len(scores)<2:

&#x20;       return "📊 Data periode belum cukup"



&#x20;   first=scores.iloc\[0]

&#x20;   last=scores.iloc\[-1]



&#x20;   if first>0:

&#x20;       change=((last-first)/first)\*100

&#x20;   else:

&#x20;       change=0



&#x20;   if (

&#x20;       df\_person\["Productivity Range"]

&#x20;       .isin(\["Poor"])

&#x20;       .all()

&#x20;   ):

&#x20;       return "⚠️ Konsisten Poor di seluruh periode"



&#x20;   if change>=20:

&#x20;       return f"📈 Score meningkat {change:.0f}% sejak periode awal"



&#x20;   elif change<=-20:

&#x20;       return f"📉 Score turun {abs(change):.0f}% dari periode awal"



&#x20;   return "✓ Performa relatif stabil"





def get\_action(avg\_score,coef,status):



&#x20;   if status=="Poor":

&#x20;       return "🔴 Attention"



&#x20;   if avg\_score<1:

&#x20;       return "🔴 Attention"



&#x20;   if coef>=1.5:

&#x20;       return "🟢 Maintain"



&#x20;   if avg\_score>=2:

&#x20;       return "🔵 Improving"



&#x20;   return "🟡 Monitor"





def render\_report\_card(df\_person):



&#x20;   info=df\_person.iloc\[0]



&#x20;   uid=str(info\["Uniq-ID"])

&#x20;   name=info\["Name Clean"]



&#x20;   initials="".join(

&#x20;       \[x\[0].upper() for x in str(name).split()\[:2]]

&#x20;   )



&#x20;   avg\_score=df\_person\["Score"].mean()



&#x20;   max\_score=df\_person\["Score"].max()



&#x20;   periods=df\_person\["Period"].nunique()



&#x20;   coef\_data=(

&#x20;       df\_person\["Payment Coef."]

&#x20;       .dropna()

&#x20;   )



&#x20;   coef=(

&#x20;       coef\_data.iloc\[-1]

&#x20;       if len(coef\_data)>0

&#x20;       else 0

&#x20;   )



&#x20;   status\_mode=(

&#x20;       df\_person\["Productivity Range"]

&#x20;       .mode()

&#x20;   )



&#x20;   status=(

&#x20;       status\_mode.iloc\[0]

&#x20;       if len(status\_mode)>0

&#x20;       else "Unknown"

&#x20;   )



&#x20;   insight=generate\_insight(df\_person)



&#x20;   action=get\_action(

&#x20;       avg\_score,

&#x20;       coef,

&#x20;       status

&#x20;   )



&#x20;   badge\_color={

&#x20;       "Excellent":"#27ae60",

&#x20;       "Normal":"#f39c12",

&#x20;       "Poor":"#e74c3c",

&#x20;       "Unknown":"#95a5a6"

&#x20;   }



&#x20;   badge=badge\_color.get(

&#x20;       status,

&#x20;       "#95a5a6"

&#x20;   )



&#x20;   st.markdown(

&#x20;       f"""

&#x20;       <div style="

&#x20;       background:white;

&#x20;       border-radius:16px;

&#x20;       padding:15px;

&#x20;       border:1px solid #ddd;

&#x20;       box-shadow:0px 2px 8px rgba(0,0,0,.08);

&#x20;       margin-bottom:10px;

&#x20;       ">



&#x20;       <div style="

&#x20;       display:flex;

&#x20;       align-items:center;

&#x20;       gap:10px;

&#x20;       ">



&#x20;       <div style="

&#x20;       width:45px;

&#x20;       height:45px;

&#x20;       border-radius:50%;

&#x20;       background:#4f8bf9;

&#x20;       color:white;

&#x20;       text-align:center;

&#x20;       line-height:45px;

&#x20;       font-weight:bold;

&#x20;       ">

&#x20;       {initials}

&#x20;       </div>



&#x20;       <div>



&#x20;       <div style="

&#x20;       font-weight:700;

&#x20;       font-size:15px;

&#x20;       ">

&#x20;       {name}

&#x20;       </div>



&#x20;       <span style="

&#x20;       background:{badge};

&#x20;       color:white;

&#x20;       border-radius:20px;

&#x20;       padding:4px 10px;

&#x20;       font-size:11px;

&#x20;       ">

&#x20;       {status}

&#x20;       </span>



&#x20;       </div>



&#x20;       </div>



&#x20;       <br>



&#x20;       <div style="

&#x20;       display:grid;

&#x20;       grid-template-columns:1fr 1fr;

&#x20;       gap:8px;

&#x20;       ">



&#x20;       <div style="background:#f8f9fa;padding:8px;border-radius:8px;text-align:center">

&#x20;       Avg<br>

&#x20;       **{avg\_score:.2f}**

&#x20;       </div>



&#x20;       <div style="background:#f8f9fa;padding:8px;border-radius:8px;text-align:center">

&#x20;       Max<br>

&#x20;       **{max\_score:.2f}**

&#x20;       </div>



&#x20;       <div style="background:#f8f9fa;padding:8px;border-radius:8px;text-align:center">

&#x20;       Coef<br>

&#x20;       **{coef:.1f}**

&#x20;       </div>



&#x20;       <div style="background:#f8f9fa;padding:8px;border-radius:8px;text-align:center">

&#x20;       Active<br>

&#x20;       **{periods}**

&#x20;       </div>



&#x20;       </div>



&#x20;       </div>

&#x20;       """,

&#x20;       unsafe\_allow\_html=True

&#x20;   )



&#x20;   trend=(

&#x20;       df\_person

&#x20;       .groupby("Period")

&#x20;       .agg(

&#x20;           Score=("Score","max")

&#x20;       )

&#x20;       .reset\_index()

&#x20;       .sort\_values("Period")

&#x20;   )



&#x20;   fig=px.bar(

&#x20;       trend,

&#x20;       x="Period",

&#x20;       y="Score",

&#x20;       height=120

&#x20;   )



&#x20;   fig.update\_layout(

&#x20;       margin=dict(

&#x20;           l=0,

&#x20;           r=0,

&#x20;           t=0,

&#x20;           b=0

&#x20;       ),

&#x20;       xaxis\_title=None,

&#x20;       yaxis\_title=None,

&#x20;       showlegend=False

&#x20;   )



&#x20;   st.plotly\_chart(

&#x20;       fig,

&#x20;       use\_container\_width=True,

&#x20;       key=f"chart\_{uid}"

&#x20;   )



&#x20;   st.info(

&#x20;       f"{insight}\\n\\n🎯 {action}"

&#x20;   )



\# ══════════════════════════════════════════════════════════════

\#  MAIN APP

\# ══════════════════════════════════════════════════════════════

st.title("📊 Productivity Monitoring Dashboard")

st.caption("Upload file Excel, gunakan filter sidebar, dan eksplorasi data produktivitas tim.")



uploaded = st.file\_uploader(

&#x20;   "Upload Combined\_Data\_Productivity\_Report.xlsx",

&#x20;   type=\["xlsx"],

&#x20;   help="File harus punya sheet: DC Productivity, QC Productivity, SE Productivity, PE Productivity"

)

if uploaded is None:

&#x20;   st.info("👆 Upload file Excel untuk memulai.")

&#x20;   st.stop()



df\_all = load\_data(uploaded)



\# ── Sidebar Filters ───────────────────────────────────────────

with st.sidebar:

&#x20;   st.header("🔍 Filter")

&#x20;   sel\_role = st.multiselect("Role", options=\["DC","QC","SE","PE"], default=\["DC","QC","SE","PE"])

&#x20;   accounts\_avail = sorted(df\_all\[df\_all\["Role"].isin(sel\_role)]\["Account"].dropna().unique())

&#x20;   sel\_account = st.multiselect("Account / Client", options=accounts\_avail, default=accounts\_avail)

&#x20;   periods\_avail = sorted(df\_all\["Period"].dropna().unique())

&#x20;   sel\_period  = st.multiselect("Periode", options=periods\_avail, default=periods\_avail)

&#x20;   sel\_status  = st.multiselect("Status Periode",

&#x20;                                 options=\["Ended","Ongoing","Not Start","Unknown"],

&#x20;                                 default=\["Ended","Ongoing"])

&#x20;   name\_q = st.text\_input("🔎 Cari Nama", placeholder="ketik sebagian nama...")

&#x20;   regions\_avail = sorted(df\_all\[df\_all\["Role"].isin(sel\_role)]\["Region"].dropna().unique())

&#x20;   sel\_region = st.multiselect("Region", options=regions\_avail, default=regions\_avail)

&#x20;   st.divider()

&#x20;   st.caption("💡 Pilih lebih dari satu opsi dengan klik.")



\# ── Apply Filter ──────────────────────────────────────────────

mask = (

&#x20;   df\_all\["Role"].isin(sel\_role) \&

&#x20;   df\_all\["Account"].isin(sel\_account) \&

&#x20;   df\_all\["Period"].isin(sel\_period) \&

&#x20;   df\_all\["Period Status"].isin(sel\_status) \&

&#x20;   df\_all\["Region"].isin(sel\_region)

)

df = df\_all\[mask].copy()

if name\_q.strip():

&#x20;   df = df\[df\["Name Clean"].str.contains(name\_q.strip(), case=False, na=False)]



if df.empty:

&#x20;   st.warning("⚠️ Tidak ada data untuk kombinasi filter ini.")

&#x20;   st.stop()



\# ── Tabs ──────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(\[

&#x20;   "📊 Overview",

&#x20;   "⚠️ Perlu Perhatian",

&#x20;   "📅 Perbandingan Periode",

&#x20;   "👤 Detail Individu",

&#x20;   "💰 Koefisien Pembayaran",

&#x20;   "🪪 Report Cards",

])



\# ══════════════════════════════════════════════════════════════

\#  TAB 1 — OVERVIEW

\# ══════════════════════════════════════════════════════════════

with tab1:

&#x20;   per\_person = df.groupby("Uniq-ID").agg(

&#x20;       Score=("Score", "max"),

&#x20;       Prod\_Range=("Productivity Range", lambda x: x.mode()\[0] if not x.mode().empty else "Unknown"),

&#x20;   ).reset\_index()



&#x20;   total\_people = per\_person\["Uniq-ID"].nunique()

&#x20;   avg\_score    = per\_person\["Score"].mean()

&#x20;   cnt\_excel    = (per\_person\["Prod\_Range"] == "Excellent").sum()

&#x20;   cnt\_poor     = (per\_person\["Prod\_Range"] == "Poor").sum()

&#x20;   pct\_excel    = cnt\_excel / total\_people \* 100 if total\_people else 0



&#x20;   k1, k2, k3, k4 = st.columns(4)

&#x20;   k1.metric("👥 Total Individu",  f"{total\_people:,}")

&#x20;   k2.metric("📈 Avg Score",       f"{avg\_score:.2f}")

&#x20;   k3.metric("🏆 Excellent",       f"{cnt\_excel}  ({pct\_excel:.0f}%)")

&#x20;   k4.metric("⚠️ Poor",            f"{cnt\_poor}")

&#x20;   st.divider()



&#x20;   c1, c2 = st.columns(2)

&#x20;   with c1:

&#x20;       st.subheader("Distribusi Productivity Range per Role")

&#x20;       dist = (df.drop\_duplicates(subset=\["Uniq-ID","Period"])

&#x20;                 .groupby(\["Role","Productivity Range"])

&#x20;                 .size().reset\_index(name="Jumlah"))

&#x20;       fig = px.bar(dist, x="Role", y="Jumlah", color="Productivity Range",

&#x20;                    color\_discrete\_map=RANGE\_COLOR, barmode="stack", text="Jumlah")

&#x20;       fig.update\_traces(textposition="inside")

&#x20;       fig.update\_layout(height=360, legend\_title="Range", margin=dict(t=20))

&#x20;       st.plotly\_chart(fig, use\_container\_width=True)



&#x20;   with c2:

&#x20;       st.subheader("Tren Rata-rata Score per Periode")

&#x20;       trend = (df.groupby(\["Period","Role"])\["Score"].mean().reset\_index().sort\_values("Period"))

&#x20;       fig2 = px.line(trend, x="Period", y="Score", color="Role",

&#x20;                      markers=True, category\_orders={"Period": PERIOD\_ORDER})

&#x20;       fig2.update\_layout(height=360, margin=dict(t=20))

&#x20;       st.plotly\_chart(fig2, use\_container\_width=True)



&#x20;   c3, c4 = st.columns(2)

&#x20;   with c3:

&#x20;       st.subheader("🏆 Top 20 Individu — Score Tertinggi")

&#x20;       top = (df.groupby(\["Uniq-ID","Name Clean","Role","Account"])\["Score"]

&#x20;                .max().reset\_index().sort\_values("Score", ascending=False).head(20))

&#x20;       fig3 = px.bar(top, x="Score", y="Name Clean", orientation="h",

&#x20;                     color="Role", text=top\["Score"].round(2), hover\_data=\["Account","Role"])

&#x20;       fig3.update\_traces(texttemplate="%{text}", textposition="outside")

&#x20;       fig3.update\_layout(height=500, yaxis={"categoryorder":"total ascending"}, margin=dict(t=20))

&#x20;       st.plotly\_chart(fig3, use\_container\_width=True)



&#x20;   with c4:

&#x20;       st.subheader("🏢 Rata-rata Score per Account")

&#x20;       acct = (df.groupby("Account")\["Score"].mean().reset\_index().sort\_values("Score", ascending=False))

&#x20;       fig4 = px.bar(acct, x="Account", y="Score", color="Score",

&#x20;                     color\_continuous\_scale="RdYlGn", text=acct\["Score"].round(2))

&#x20;       fig4.update\_traces(textposition="outside")

&#x20;       fig4.update\_layout(height=500, margin=dict(t=20))

&#x20;       st.plotly\_chart(fig4, use\_container\_width=True)



&#x20;   c5, c6 = st.columns(2)

&#x20;   with c5:

&#x20;       st.subheader("⏱️ Status Periode")

&#x20;       stat = (df.drop\_duplicates(subset=\["Uniq-ID","Period"])

&#x20;                 .groupby("Period Status").size().reset\_index(name="Jumlah"))

&#x20;       fig5 = px.pie(stat, names="Period Status", values="Jumlah", color="Period Status",

&#x20;                     color\_discrete\_map={"Ended":"#27ae60","Ongoing":"#f39c12",

&#x20;                                         "Not Start":"#95a5a6","Unknown":"#bdc3c7"})

&#x20;       fig5.update\_layout(height=360, margin=dict(t=20))

&#x20;       st.plotly\_chart(fig5, use\_container\_width=True)



&#x20;   with c6:

&#x20;       st.subheader("🗺️ Sebaran per Region")

&#x20;       if df\["Region"].nunique() > 1:

&#x20;           reg = (df.drop\_duplicates(subset=\["Uniq-ID","Period"])

&#x20;                    .groupby(\["Region","Productivity Range"]).size().reset\_index(name="Jumlah"))

&#x20;           fig6 = px.bar(reg, x="Region", y="Jumlah", color="Productivity Range",

&#x20;                         color\_discrete\_map=RANGE\_COLOR, barmode="stack", text="Jumlah")

&#x20;           fig6.update\_traces(textposition="inside")

&#x20;           fig6.update\_layout(height=360, margin=dict(t=20))

&#x20;           st.plotly\_chart(fig6, use\_container\_width=True)

&#x20;       else:

&#x20;           st.info("Data Region hanya tersedia untuk role QC, SE, dan PE.")



\# ══════════════════════════════════════════════════════════════

\#  TAB 2 — PERLU PERHATIAN

\# ══════════════════════════════════════════════════════════════

with tab2:

&#x20;   st.subheader("⚠️ Individu yang Perlu Perhatian")

&#x20;   st.caption("Berdasarkan periode aktif (Ended/Ongoing) dengan score rendah atau konsisten Poor.")



&#x20;   # Ambil periode aktif saja

&#x20;   df\_active = df\[df\["Period Status"].isin(\["Ended","Ongoing"])].copy()



&#x20;   # Score rendah: semua periode = Poor atau score 0 terus

&#x20;   summary = df\_active.groupby(\["Uniq-ID","Name Clean","Role","Account"]).agg(

&#x20;       Avg\_Score=("Score", "mean"),

&#x20;       Max\_Score=("Score", "max"),

&#x20;       All\_Poor=("Productivity Range", lambda x: (x.isin(\["Poor","Unknown"])).all()),

&#x20;       Latest\_Coef=("Payment Coef.", "last"),

&#x20;       Periods=("Period", "nunique"),

&#x20;   ).reset\_index()



&#x20;   at\_risk = summary\[

&#x20;       (summary\["All\_Poor"] == True) |

&#x20;       (summary\["Max\_Score"] == 0) |

&#x20;       (summary\["Avg\_Score"] < 0.5)

&#x20;   ].sort\_values("Avg\_Score")



&#x20;   consistent\_poor = summary\[

&#x20;       (summary\["All\_Poor"] == True) \& (summary\["Periods"] >= 2)

&#x20;   ]



&#x20;   zero\_score = summary\[summary\["Max\_Score"] == 0]



&#x20;   col\_a, col\_b, col\_c = st.columns(3)

&#x20;   col\_a.metric("🔴 Total At-Risk",        len(at\_risk))

&#x20;   col\_b.metric("📉 Konsisten Poor (≥2P)", len(consistent\_poor))

&#x20;   col\_c.metric("⭕ Score 0 Semua Periode", len(zero\_score))

&#x20;   st.divider()



&#x20;   if not at\_risk.empty:

&#x20;       # Chart distribusi at-risk per Role

&#x20;       risk\_role = at\_risk.groupby("Role").size().reset\_index(name="Jumlah")

&#x20;       fig\_risk = px.bar(risk\_role, x="Role", y="Jumlah", color="Role",

&#x20;                         title="At-Risk per Role", text="Jumlah", height=280)

&#x20;       fig\_risk.update\_traces(textposition="outside")

&#x20;       fig\_risk.update\_layout(showlegend=False, margin=dict(t=40,b=20))

&#x20;       st.plotly\_chart(fig\_risk, use\_container\_width=True)



&#x20;       st.subheader("📋 Daftar Individu At-Risk")

&#x20;       tbl\_risk = at\_risk\[\["Name Clean","Role","Account","Avg\_Score","Max\_Score","Latest\_Coef","Periods"]].copy()

&#x20;       tbl\_risk.columns = \["Nama","Role","Account","Avg Score","Max Score","Koef Terakhir","Jumlah Periode"]

&#x20;       tbl\_risk = tbl\_risk.reset\_index(drop=True)



&#x20;       def highlight\_avg\_score(val):

&#x20;           try:

&#x20;               v = float(val)

&#x20;               if v >= 3:   return "background-color:#d5f5e3; color:#1e8449; font-weight:600"

&#x20;               elif v >= 1: return "background-color:#fdebd0; color:#784212"

&#x20;               else:        return "background-color:#fadbd8; color:#922b21"

&#x20;           except:

&#x20;               return ""



&#x20;       st.dataframe(

&#x20;           tbl\_risk.style

&#x20;               .map(highlight\_avg\_score, subset=\["Avg Score"])

&#x20;               .format({"Avg Score":"{:.2f}", "Max Score":"{:.2f}",

&#x20;                        "Koef Terakhir": lambda x: f"{x:.1f}" if pd.notna(x) else "–"}),

&#x20;           use\_container\_width=True, height=400

&#x20;       )



&#x20;       csv\_risk = tbl\_risk.to\_csv(index=False).encode("utf-8")

&#x20;       st.download\_button("⬇️ Download Daftar At-Risk (CSV)", data=csv\_risk,

&#x20;                          file\_name="at\_risk.csv", mime="text/csv")

&#x20;   else:

&#x20;       st.success("✅ Tidak ada individu at-risk dengan filter saat ini!")



\# ══════════════════════════════════════════════════════════════

\#  TAB 3 — PERBANDINGAN PERIODE

\# ══════════════════════════════════════════════════════════════

with tab3:

&#x20;   st.subheader("📅 Perbandingan Antar Periode")



&#x20;   periods\_available = sorted(df\["Period"].dropna().unique())

&#x20;   if len(periods\_available) < 2:

&#x20;       st.info("Butuh minimal 2 periode untuk perbandingan.")

&#x20;   else:

&#x20;       col\_p1, col\_p2 = st.columns(2)

&#x20;       p1 = col\_p1.selectbox("Periode A", options=periods\_available, index=0)

&#x20;       p2 = col\_p2.selectbox("Periode B", options=periods\_available,

&#x20;                              index=min(1, len(periods\_available)-1))



&#x20;       df\_p1 = df\[df\["Period"] == p1].groupby("Uniq-ID").agg(

&#x20;           Score\_A=("Score","max"), Range\_A=("Productivity Range", lambda x: x.mode()\[0] if not x.mode().empty else "Unknown"),

&#x20;           Name=("Name Clean","first"), Role=("Role","first"), Account=("Account","first")

&#x20;       ).reset\_index()



&#x20;       df\_p2 = df\[df\["Period"] == p2].groupby("Uniq-ID").agg(

&#x20;           Score\_B=("Score","max"), Range\_B=("Productivity Range", lambda x: x.mode()\[0] if not x.mode().empty else "Unknown")

&#x20;       ).reset\_index()



&#x20;       comp = df\_p1.merge(df\_p2, on="Uniq-ID", how="outer")

&#x20;       comp\["Score\_A"] = comp\["Score\_A"].fillna(0)

&#x20;       comp\["Score\_B"] = comp\["Score\_B"].fillna(0)

&#x20;       comp\["Delta"]   = comp\["Score\_B"] - comp\["Score\_A"]

&#x20;       comp\["Trend"]   = comp\["Delta"].apply(lambda x: "📈 Naik" if x > 0 else ("📉 Turun" if x < 0 else "➡️ Sama"))



&#x20;       st.divider()

&#x20;       col\_m1, col\_m2, col\_m3 = st.columns(3)

&#x20;       naik  = (comp\["Delta"] > 0).sum()

&#x20;       turun = (comp\["Delta"] < 0).sum()

&#x20;       sama  = (comp\["Delta"] == 0).sum()

&#x20;       col\_m1.metric("📈 Naik",  naik)

&#x20;       col\_m2.metric("📉 Turun", turun)

&#x20;       col\_m3.metric("➡️ Sama",  sama)



&#x20;       # Scatter plot perbandingan

&#x20;       fig\_comp = px.scatter(

&#x20;           comp.dropna(subset=\["Name"]), x="Score\_A", y="Score\_B",

&#x20;           color="Trend", hover\_name="Name",

&#x20;           hover\_data=\["Role","Account","Delta"],

&#x20;           labels={"Score\_A": f"Score {p1}", "Score\_B": f"Score {p2}"},

&#x20;           title=f"Perbandingan Score: {p1} vs {p2}",

&#x20;           color\_discrete\_map={"📈 Naik":"#27ae60","📉 Turun":"#e74c3c","➡️ Sama":"#95a5a6"},

&#x20;           height=420

&#x20;       )

&#x20;       # Garis diagonal (sama persis)

&#x20;       max\_val = max(comp\["Score\_A"].max(), comp\["Score\_B"].max()) \* 1.05

&#x20;       fig\_comp.add\_shape(type="line", x0=0, y0=0, x1=max\_val, y1=max\_val,

&#x20;                          line=dict(dash="dot", color="gray", width=1))

&#x20;       fig\_comp.update\_layout(margin=dict(t=40))

&#x20;       st.plotly\_chart(fig\_comp, use\_container\_width=True)



&#x20;       # Top mover

&#x20;       c\_up, c\_down = st.columns(2)

&#x20;       with c\_up:

&#x20;           st.markdown("\*\*🚀 Top 10 Paling Naik\*\*")

&#x20;           top\_up = comp.nlargest(10, "Delta")\[\["Name","Role","Score\_A","Score\_B","Delta"]].reset\_index(drop=True)

&#x20;           top\_up.columns = \["Nama","Role",f"Score {p1}",f"Score {p2}","Delta"]

&#x20;           st.dataframe(top\_up.style.format({f"Score {p1}":"{:.2f}",f"Score {p2}":"{:.2f}","Delta":"{:+.2f}"}),

&#x20;                        use\_container\_width=True, height=300)

&#x20;       with c\_down:

&#x20;           st.markdown("\*\*📉 Top 10 Paling Turun\*\*")

&#x20;           top\_down = comp.nsmallest(10, "Delta")\[\["Name","Role","Score\_A","Score\_B","Delta"]].reset\_index(drop=True)

&#x20;           top\_down.columns = \["Nama","Role",f"Score {p1}",f"Score {p2}","Delta"]

&#x20;           st.dataframe(top\_down.style.format({f"Score {p1}":"{:.2f}",f"Score {p2}":"{:.2f}","Delta":"{:+.2f}"}),

&#x20;                        use\_container\_width=True, height=300)



\# ══════════════════════════════════════════════════════════════

\#  TAB 4 — DETAIL INDIVIDU

\# ══════════════════════════════════════════════════════════════

with tab4:

&#x20;   st.subheader("👤 Detail per Individu")



&#x20;   names\_avail = sorted(df\["Name Clean"].dropna().unique())

&#x20;   sel\_name = st.selectbox("Pilih individu:", options=names\_avail)



&#x20;   df\_ind = df\[df\["Name Clean"] == sel\_name].copy()



&#x20;   if df\_ind.empty:

&#x20;       st.warning("Data tidak ditemukan.")

&#x20;   else:

&#x20;       info = df\_ind.iloc\[0]

&#x20;       i1, i2, i3, i4 = st.columns(4)

&#x20;       i1.metric("🆔 ID",      info.get("Uniq-ID","–"))

&#x20;       i2.metric("🏢 Account", info.get("Account","–"))

&#x20;       i3.metric("👔 Role",    info.get("Role","–"))

&#x20;       i4.metric("🗺️ Region",  info.get("Region","–"))

&#x20;       st.divider()



&#x20;       # Score per periode

&#x20;       period\_data = (df\_ind.groupby("Period").agg(

&#x20;           Score=("Score","max"),

&#x20;           Status=("Period Status","first"),

&#x20;           Range=("Productivity Range", lambda x: x.mode()\[0] if not x.mode().empty else "Unknown"),

&#x20;           Coef=("Payment Coef.","first"),

&#x20;       ).reset\_index().sort\_values("Period"))



&#x20;       col\_chart, col\_tbl = st.columns(\[3,2])

&#x20;       with col\_chart:

&#x20;           fig\_ind = go.Figure()

&#x20;           fig\_ind.add\_trace(go.Bar(

&#x20;               x=period\_data\["Period"], y=period\_data\["Score"],

&#x20;               marker\_color=\[RANGE\_COLOR.get(r,"#95a5a6") for r in period\_data\["Range"]],

&#x20;               text=period\_data\["Score"].round(2), textposition="outside",

&#x20;               name="Score"

&#x20;           ))

&#x20;           fig\_ind.update\_layout(title=f"Score per Periode — {sel\_name}",

&#x20;                                  height=320, margin=dict(t=40,b=20),

&#x20;                                  xaxis\_title="Periode", yaxis\_title="Score")

&#x20;           st.plotly\_chart(fig\_ind, use\_container\_width=True)



&#x20;       with col\_tbl:

&#x20;           st.markdown("\*\*Ringkasan per Periode\*\*")

&#x20;           disp = period\_data\[\["Period","Status","Range","Score","Coef"]].copy()

&#x20;           disp.columns = \["Periode","Status","Range","Score","Koef"]

&#x20;           st.dataframe(

&#x20;               disp.style

&#x20;                   .map(highlight\_range, subset=\["Range"])

&#x20;                   .map(highlight\_coef, subset=\["Koef"])

&#x20;                   .format({"Score":"{:.2f}", "Koef": lambda x: f"{x:.1f}" if pd.notna(x) else "–"}),

&#x20;               use\_container\_width=True, height=260

&#x20;           )



&#x20;       # Tren koefisien

&#x20;       if period\_data\["Coef"].notna().any():

&#x20;           fig\_coef = px.line(period\_data, x="Period", y="Coef",

&#x20;                              markers=True, title="Tren Koefisien Pembayaran",

&#x20;                              color\_discrete\_sequence=\["#4f8bf9"], height=260)

&#x20;           fig\_coef.add\_hline(y=1.0, line\_dash="dot", line\_color="orange", annotation\_text="Batas Normal")

&#x20;           fig\_coef.add\_hline(y=1.5, line\_dash="dot", line\_color="green",  annotation\_text="Excellent")

&#x20;           fig\_coef.update\_layout(margin=dict(t=40,b=20))

&#x20;           st.plotly\_chart(fig\_coef, use\_container\_width=True)



&#x20;       # Detail dokumen (kalau ada)

&#x20;       doc\_cols = \[c for c in df\_ind.columns if c in

&#x20;                   \["Document Category","Document Type","Total Doc.","% Achievement","Source Data","Baseline/Cycle"]]

&#x20;       if doc\_cols:

&#x20;           st.markdown("\*\*Detail Dokumen\*\*")

&#x20;           doc\_tbl = df\_ind\[\["Period"] + doc\_cols].dropna(subset=doc\_cols\[:1]).reset\_index(drop=True)

&#x20;           st.dataframe(doc\_tbl, use\_container\_width=True, height=200)



\# ══════════════════════════════════════════════════════════════

\#  TAB 5 — KOEFISIEN PEMBAYARAN

\# ══════════════════════════════════════════════════════════════

with tab5:

&#x20;   st.subheader("💰 Analisis Koefisien Pembayaran")

&#x20;   st.caption("Koefisien: 1.5 = Excellent · 1.0 = Normal · 0.9 = Poor · 0.5 = Very Poor")



&#x20;   df\_coef = df\[df\["Payment Coef."].notna()].copy()



&#x20;   if df\_coef.empty:

&#x20;       st.info("Tidak ada data koefisien untuk filter ini.")

&#x20;   else:

&#x20;       # KPI

&#x20;       avg\_coef  = df\_coef.groupby("Uniq-ID")\["Payment Coef."].last().mean()

&#x20;       cnt\_15    = (df\_coef.groupby("Uniq-ID")\["Payment Coef."].last() >= 1.5).sum()

&#x20;       cnt\_low   = (df\_coef.groupby("Uniq-ID")\["Payment Coef."].last() < 1.0).sum()



&#x20;       ck1, ck2, ck3 = st.columns(3)

&#x20;       ck1.metric("📊 Avg Koefisien",      f"{avg\_coef:.2f}")

&#x20;       ck2.metric("🟢 Koef ≥ 1.5 (Excellent)", cnt\_15)

&#x20;       ck3.metric("🔴 Koef < 1.0 (Poor)",  cnt\_low)

&#x20;       st.divider()



&#x20;       cc1, cc2 = st.columns(2)

&#x20;       with cc1:

&#x20;           # Distribusi koefisien

&#x20;           coef\_dist = (df\_coef.groupby(\["Role","Payment Coef."])

&#x20;                          .size().reset\_index(name="Jumlah"))

&#x20;           coef\_dist\["Koef"] = coef\_dist\["Payment Coef."].astype(str)

&#x20;           fig\_c1 = px.bar(coef\_dist, x="Koef", y="Jumlah", color="Role",

&#x20;                           barmode="group", title="Distribusi Koefisien per Role",

&#x20;                           text="Jumlah", height=340)

&#x20;           fig\_c1.update\_traces(textposition="outside")

&#x20;           fig\_c1.update\_layout(margin=dict(t=40))

&#x20;           st.plotly\_chart(fig\_c1, use\_container\_width=True)



&#x20;       with cc2:

&#x20;           # Avg koefisien per account

&#x20;           coef\_acct = (df\_coef.groupby("Account")\["Payment Coef."]

&#x20;                          .mean().reset\_index()

&#x20;                          .sort\_values("Payment Coef.", ascending=False))

&#x20;           fig\_c2 = px.bar(coef\_acct, x="Account", y="Payment Coef.",

&#x20;                           color="Payment Coef.", color\_continuous\_scale="RdYlGn",

&#x20;                           title="Rata-rata Koefisien per Account",

&#x20;                           text=coef\_acct\["Payment Coef."].round(2), height=340)

&#x20;           fig\_c2.update\_traces(textposition="outside")

&#x20;           fig\_c2.update\_layout(margin=dict(t=40))

&#x20;           st.plotly\_chart(fig\_c2, use\_container\_width=True)



&#x20;       # Tren koefisien per periode

&#x20;       coef\_trend = (df\_coef.groupby(\["Period","Role"])\["Payment Coef."]

&#x20;                       .mean().reset\_index().sort\_values("Period"))

&#x20;       fig\_ct = px.line(coef\_trend, x="Period", y="Payment Coef.", color="Role",

&#x20;                        markers=True, title="Tren Koefisien per Periode",

&#x20;                        category\_orders={"Period": PERIOD\_ORDER}, height=320)

&#x20;       fig\_ct.add\_hline(y=1.0, line\_dash="dot", line\_color="orange", annotation\_text="Normal (1.0)")

&#x20;       fig\_ct.add\_hline(y=1.5, line\_dash="dot", line\_color="green",  annotation\_text="Excellent (1.5)")

&#x20;       fig\_ct.update\_layout(margin=dict(t=40))

&#x20;       st.plotly\_chart(fig\_ct, use\_container\_width=True)



&#x20;       # Tabel lengkap koefisien

&#x20;       st.markdown("\*\*📋 Tabel Koefisien per Individu\*\*")

&#x20;       coef\_tbl = (df\_coef.groupby(\["Uniq-ID","Name Clean","Role","Account","Period"])

&#x20;                     .agg(Score=("Score","max"), Coef=("Payment Coef.","first"),

&#x20;                          Range=("Productivity Range", lambda x: x.mode()\[0] if not x.mode().empty else "Unknown"))

&#x20;                     .reset\_index()

&#x20;                     .sort\_values(\["Role","Coef"], ascending=\[True,False]))



&#x20;       st.dataframe(

&#x20;           coef\_tbl.rename(columns={"Name Clean":"Nama","Payment Coef.":"Koef",

&#x20;                                     "Productivity Range":"Range"})

&#x20;                   .style

&#x20;                   .map(highlight\_range, subset=\["Range"])

&#x20;                   .map(highlight\_coef,  subset=\["Coef"])

&#x20;                   .format({"Score":"{:.2f}", "Coef": lambda x: f"{x:.1f}" if pd.notna(x) else "–"}),

&#x20;           use\_container\_width=True, height=400

&#x20;       )



&#x20;       csv\_coef = coef\_tbl.to\_csv(index=False).encode("utf-8")

&#x20;       st.download\_button("⬇️ Download Tabel Koefisien (CSV)", data=csv\_coef,

&#x20;                          file\_name="koefisien.csv", mime="text/csv")

\# ══════════════════════════════════════════════

\# TAB 6 — REPORT CARDS

\# ══════════════════════════════════════════════



with tab6:



&#x20;   st.subheader(

&#x20;       "🪪 Individual Report Cards"

&#x20;   )



&#x20;   st.caption(

&#x20;       "Scan cepat performa seluruh individu"

&#x20;   )



&#x20;   people = sorted(

&#x20;       df\["Name Clean"]

&#x20;       .dropna()

&#x20;       .unique()

&#x20;   )



&#x20;   cols = st.columns(3)



&#x20;   for i,name in enumerate(people):



&#x20;       person\_df = df\[

&#x20;           df\["Name Clean"]==name

&#x20;       ]



&#x20;       with cols\[i%3]:



&#x20;           render\_report\_card(

&#x20;               person\_df

&#x20;           )

\# ── Footer ────────────────────────────────────────────────────

st.divider()

st.caption("📊 Productivity Dashboard · Data diproses langsung dari file Excel yang diupload")
