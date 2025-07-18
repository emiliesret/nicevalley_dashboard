import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from fpdf import FPDF
import tempfile

# --- Page Configuration ---
st.set_page_config(page_title="Dashboard Nice Valley", layout="wide")
st.title("Dashboard Communication & Animations — Nice Valley")

# --- Sidebar: Data Uploads ---
st.sidebar.header("Importer tes données")
followers_file  = st.sidebar.file_uploader("CSV « Followers en plus »",       type=["csv"])
visites_file    = st.sidebar.file_uploader("CSV « Visites »",                 type=["csv"])
vues_file       = st.sidebar.file_uploader("CSV « Vues »",                    type=["csv"])
budget_file     = st.sidebar.file_uploader("Budget mensuel (CSV/XLSX)",       type=["csv","xlsx"])
traffic_file    = st.sidebar.file_uploader("CSV/Excel « myTraffic »",         type=["csv","xlsx"])
animations_file = st.sidebar.file_uploader("CSV « Animations 2025 »",         type=["csv"])
if not (followers_file and visites_file and vues_file and budget_file and traffic_file and animations_file):
    st.sidebar.info("Upload tes 6 fichiers : followers, visites, vues, budget, myTraffic, animations")
    st.stop()

# --- CSV Loader & Cleaner ---
@st.cache_data
def load_and_clean_csv(file, col_name):
    df = pd.read_csv(file, encoding='utf-16', sep=',', skiprows=2,
                     names=["Date", col_name], dtype=str, na_filter=False)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df[col_name] = df[col_name].str.extract(r"(\d+)").astype(int)
    df["Mois"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    return df

# --- Budget Loader (CSV ou XLSX) ---
@st.cache_data
def load_budget(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file, sep=';', encoding='utf-8', header=0)
        df.columns = ["Mois", "Budget"]
        df["Mois"]   = pd.to_datetime(df["Mois"] + "-01")
        df["Budget"] = pd.to_numeric(df["Budget"], errors="coerce").fillna(0)
    else:
        raw = pd.read_excel(file, header=2, engine='openpyxl', dtype=str)
        month_cols = {
            'JANVIER':1,'FÉVRIER':2,'MARS':3,'AVRIL':4,
            'MAI':5,'JUIN':6,'JUILLET':7,'AOUT':8,
            'SEPTEMBRE':9,'OCTOBRE':10,'NOVEMBRE':11,'DÉCEMBRE':12
        }
        mask = raw.iloc[:,0].str.contains("total", case=False, na=False)
        row = raw[mask].iloc[-1]
        months, budgets = [], []
        year = pd.Timestamp.now().year
        for col, num in month_cols.items():
            if col in row:
                try:
                    b = float(str(row[col]).replace(" ", ""))
                except:
                    b = 0.0
                months.append(pd.to_datetime(f"{year}-{num:02d}-01"))
                budgets.append(b)
        df = pd.DataFrame({"Mois": months, "Budget": budgets})
    return df

# --- Traffic Loader ---
@st.cache_data
def load_traffic(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file, parse_dates=[0], dayfirst=True, encoding='utf-8')
        df.columns = ["Timestamp", "Count"]
    else:
        raw = pd.read_excel(file, engine='openpyxl', dtype=str)
        if "Period" in raw.columns and "Centre commercial Nice Valley" in raw.columns:
            df = raw[raw["Period"].str.match(r"\d{4}-W\d{2}", na=False)]
            df["Timestamp"] = pd.to_datetime(df["Period"] + "-1",
                                             format="%G-W%V-%u", errors="coerce")
            df["Count"] = pd.to_numeric(raw["Centre commercial Nice Valley"], errors="coerce").fillna(0)
        else:
            df = raw.rename(columns={raw.columns[0]:"Timestamp", raw.columns[1]:"Count"})
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
            df["Count"] = pd.to_numeric(df["Count"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Timestamp"])
    df["Mois"] = df["Timestamp"].dt.to_period("M").dt.to_timestamp()
    return df.groupby("Mois")["Count"].sum().reset_index().rename(columns={"Count":"Footfall"})

# --- Animations Loader ---
@st.cache_data
def load_animations(file):
    df = pd.read_csv(file, parse_dates=["Date"])
    df["Budget"] = pd.to_numeric(df["Budget"], errors="coerce").fillna(0)
    df["Mois"]   = df["Date"].dt.to_period("M").dt.to_timestamp()
    return df

# --- Load All Data ---
df_followers = load_and_clean_csv(followers_file, "Followers")
df_visites   = load_and_clean_csv(visites_file,   "Visites")
df_vues      = load_and_clean_csv(vues_file,      "Vues")
df_budget    = load_budget(budget_file)
df_traffic   = load_traffic(traffic_file)
df_anim      = load_animations(animations_file)

# --- Monthly Aggregation ---
agg_f = df_followers.groupby("Mois")["Followers"].sum()
agg_v = df_visites.groupby("Mois")["Visites"].sum()
agg_w = df_vues.groupby("Mois")["Vues"].sum()
agg_bud = df_budget.set_index("Mois")["Budget"]
agg_t = df_traffic.set_index("Mois")["Footfall"]
# nouvel : budget animations mensuel
agg_a = df_anim.groupby("Mois")["Budget"].sum()

df_monthly = (
    pd.concat([agg_f, agg_v, agg_w, agg_bud, agg_t, agg_a], axis=1)
      .rename(columns={"Budget":"Budget_Marketing", "Footfall":"Footfall", "Budget":"Budget_Anim"})
      .fillna(0)
      .reset_index()
)
df_monthly.columns = ["Mois","Followers","Visites","Vues",
                      "Budget_Marketing","Footfall","Budget_Anim"]

# --- Period of Study ---
start = df_monthly["Mois"].min().strftime("%b %Y")
end   = df_monthly["Mois"].max().strftime("%b %Y")
st.markdown(f"**Période d’étude :** {start} – {end}")

# --- KPI Principaux ---
st.header("1. KPI principaux")
c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Followers",      f"{int(agg_f.sum()):,}",
          help="Total des nouveaux abonnés sur la période.")
c2.metric("Total Visites",        f"{int(agg_v.sum()):,}",
          help="Total des visites de profil générées.")
c3.metric("Total Vues",           f"{int(agg_w.sum()):,}",
          help="Total des impressions de contenu.")
c4.metric("Total Budget Anim.",   f"{int(agg_a.sum()):,} €",
          help="Budget total consommé par les animations.")

# --- Tableau des animations ---
st.header("2. Détail des animations 2025")
st.dataframe(
    df_anim[["Date","Animation","Budget"]]
      .sort_values("Date")
      .assign(Date=lambda d: d["Date"].dt.strftime("%d/%m/%Y")),
    use_container_width=True
)

# --- Graphiques ---
st.header("3. Graphiques")
# 3.1 Followers vs Marketing & Anim
fig1, ax1 = plt.subplots(figsize=(10,4))
ax1.plot(df_monthly["Mois"], df_monthly["Followers"], "o-", label="Followers")
ax1.set_ylabel("Followers")
ax2 = ax1.twinx()
ax2.bar(df_monthly["Mois"], df_monthly["Budget_Marketing"], width=20, alpha=0.3, label="Budget Comm.")
ax2.bar(df_monthly["Mois"], df_monthly["Budget_Anim"],      width=10, alpha=0.6, label="Budget Anim.")
ax2.set_ylabel("Budget (€)")
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig1.autofmt_xdate()
ax1.legend(loc="upper left")
ax2.legend(loc="upper right")
st.pyplot(fig1)

# 3.2 Footfall
fig2, ax = plt.subplots(figsize=(10,4))
ax.plot(df_monthly["Mois"], df_monthly["Footfall"], "s-", color="tab:gray")
ax.set_ylabel("Footfall")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig2.autofmt_xdate()
st.pyplot(fig2)

# --- Export PDF ---
st.header("4. Export PDF")
if st.button("Générer le rapport PDF"):
    pdf = FPDF('P','mm','A4'); pdf.add_page()
    pdf.set_font('Arial','B',16)
    pdf.cell(0,10,f"Rapport Nice Valley ({start} – {end})",ln=True,align='C')
    pdf.ln(4)
    # KPIs
    pdf.set_font('Arial','B',12)
    pdf.cell(0,6,"KPI principaux",ln=True)
    pdf.set_font('Arial','',11)
    pdf.cell(0,5,f"New Followers   : {int(agg_f.sum()):,}",ln=True)
    pdf.cell(0,5,f"New Visits      : {int(agg_v.sum()):,}",ln=True)
    pdf.cell(0,5,f"Content Views   : {int(agg_w.sum()):,}",ln=True)
    pdf.cell(0,5,f"Budget Anim.    : {int(agg_a.sum()):,} €",ln=True)
    pdf.ln(4)
    # Figures helper
    def add_fig(title, fig):
        pdf.set_font('Arial','B',12); pdf.cell(0,5,title,ln=True)
        tmp=tempfile.NamedTemporaryFile(suffix=".png",delete=False)
        fig.savefig(tmp.name,dpi=100,bbox_inches='tight')
        pdf.image(tmp.name,x=15,w=180); pdf.ln(5); tmp.close()
    add_fig("Followers vs Budgets", fig1)
    add_fig("Footfall mensuel",       fig2)
    pdf_bytes = pdf.output(dest='S').encode('latin-1','ignore')
    st.download_button("⬇ Télécharger PDF", pdf_bytes,
                       file_name=f"rapport_{start.replace(' ','_')}_{end.replace(' ','_')}.pdf",
                       mime="application/pdf")
# --- Footer ---
st.markdown("---")
st.markdown("**© 2025 Nice Valley** - Dashboard de suivi des performances marketing")
