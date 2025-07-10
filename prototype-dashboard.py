import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from sklearn.linear_model import LinearRegression
from fpdf import FPDF
import tempfile

# --- Page Configuration ---
st.set_page_config(page_title="Dashboard Nice Valley", layout="wide")
st.title("📊 Dashboard Communication & Animations — Nice Valley")

# --- Sidebar: Data Uploads ---
st.sidebar.header("Importer tes données")
followers_file = st.sidebar.file_uploader("CSV « Followers en plus »",    type=["csv"])
visites_file   = st.sidebar.file_uploader("CSV « Visites »",             type=["csv"])
vues_file      = st.sidebar.file_uploader("CSV « Vues »",                type=["csv"])
budget_file    = st.sidebar.file_uploader("Budget mensuel (CSV ou XLSX)", type=["csv","xlsx"])
traffic_file   = st.sidebar.file_uploader("CSV/Excel « myTraffic »",     type=["csv","xlsx"])
if not (followers_file and visites_file and vues_file and budget_file and traffic_file):
    st.sidebar.info("Upload tes 5 fichiers : followers, visites, vues, budget, myTraffic")
    st.stop()

# --- Data Loading Functions ---
@st.cache_data
def load_and_clean_csv(file, col_name):
    df = pd.read_csv(file, encoding='utf-16', sep=',', skiprows=2,
                     names=["Date", col_name], dtype=str, na_filter=False)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df[col_name] = df[col_name].str.extract(r"(\d+)").astype(int)
    df["Mois"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    return df

@st.cache_data
def load_budget(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file, sep=';', header=0, encoding='utf-8')
        df.columns = ["Mois", "Budget"]
        df["Mois"]   = pd.to_datetime(df["Mois"] + "-01", format="%Y-%m-%d")
        df["Budget"] = pd.to_numeric(df["Budget"], errors="coerce").fillna(0)
    else:
        df = pd.read_excel(file, header=2, engine='openpyxl', sheet_name=0, dtype=str)
        month_cols = {
            'JANVIER':1,'FÉVRIER':2,'MARS':3,'AVRIL':4,
            'MAI':5,'JUIN':6,'JUILLET':7,'AOUT':8,
            'SEPTEMBRE':9,'OCTOBRE':10,'NOVEMBRE':11,'DÉCEMBRE':12
        }
        mask = df.iloc[:,0].str.contains("total", case=False, na=False)
        if not mask.any():
            st.error("Ligne 'SS TOTAL' introuvable dans le budget Excel.")
            st.stop()
        row = df[mask].iloc[-1]
        months, budgets = [], []
        year = pd.Timestamp.now().year
        for col, num in month_cols.items():
            if col in row.index:
                try: b = float(str(row[col]).replace(" ", ""))
                except: b = 0.0
                months.append(pd.to_datetime(f"{year}-{num:02d}-01"))
                budgets.append(b)
        df = pd.DataFrame({"Mois": months, "Budget": budgets})
    return df

@st.cache_data
def load_traffic(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file, parse_dates=[0], dayfirst=True, encoding='utf-8')
        df.columns = ["Timestamp","Count"]
    else:
        df = pd.read_excel(file, engine='openpyxl', sheet_name=0, dtype=str)
        if "Period" in df.columns and "Centre commercial Nice Valley" in df.columns:
            df = df[df["Period"].str.match(r"\d{4}-W\d{2}", na=False)]
            df["Timestamp"] = pd.to_datetime(df["Period"]+"-1",
                                             format="%G-W%V-%u", errors="coerce")
            df["Count"] = pd.to_numeric(df["Centre commercial Nice Valley"], errors="coerce").fillna(0)
        else:
            df = df.rename(columns={df.columns[0]:"Timestamp", df.columns[1]:"Count"})
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
            df["Count"] = pd.to_numeric(df["Count"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Timestamp"])
    df["Mois"] = df["Timestamp"].dt.to_period("M").dt.to_timestamp()
    return df.groupby("Mois")["Count"].sum().reset_index().rename(columns={"Count":"Footfall"})

# --- Load all data ---
df_followers = load_and_clean_csv(followers_file, "Followers")
df_visites   = load_and_clean_csv(visites_file,   "Visites")
df_vues      = load_and_clean_csv(vues_file,      "Vues")
df_budget    = load_budget(budget_file)
df_traffic   = load_traffic(traffic_file)

# --- Monthly aggregation ---
agg_f = df_followers.groupby("Mois")["Followers"].sum()
agg_v = df_visites.groupby("Mois")["Visites"].sum()
agg_w = df_vues.groupby("Mois")["Vues"].sum()
df_monthly = pd.concat([agg_f, agg_v, agg_w], axis=1).reset_index()
df_monthly = df_monthly.merge(df_budget,  on="Mois", how="left")
df_monthly = df_monthly.merge(df_traffic, on="Mois", how="left").fillna({"Footfall":0})

# --- Period of study ---
start = df_monthly["Mois"].min().strftime("%b %Y")
end   = df_monthly["Mois"].max().strftime("%b %Y")
st.markdown(f"**Période d’étude :** {start} – {end}")

# --- KPI principaux with clear help texts ---
st.header("KPI principaux")
c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Total Followers",
    f"{int(agg_f.sum()):,}",
    help="Nombre total de nouveaux abonnés obtenus sur la période."
)
c2.metric(
    "Total Visites",
    f"{int(agg_v.sum()):,}",
    help="Nombre total de visites de profil Instagram générées sur la période."
)
c3.metric(
    "Total Vues",
    f"{int(agg_w.sum()):,}",
    help="Nombre total d’impressions (vues) de votre contenu Instagram."
)
c4.metric(
    "Coût moyen/follower (EUR)",
    f"{(df_monthly['Budget'].sum()/agg_f.sum()):.2f}",
    help="Budget total dépensé divisé par le nombre de nouveaux followers."
)

# --- KPI additionnels with clear help texts ---
total_f = agg_f.sum()
total_v = agg_v.sum()
total_w = agg_w.sum()
conv_f = (total_f/total_w*100) if total_w else 0
conv_v = (total_v/total_w*100) if total_w else 0
growth = df_monthly["Followers"].diff().fillna(0)
avg_growth = growth.mean()
idx = growth.idxmax()
peak = df_monthly.loc[idx,"Mois"].strftime("%b %Y") if not growth.empty else "-"
c5, c6, c7, c8 = st.columns(4)
c5.metric(
    "Conv. Followers/Vues",
    f"{conv_f:.2f}%",
    help="Pourcentage de vues de contenu ayant conduit à un nouvel abonné."
)
c6.metric(
    "Conv. Visites/Vues",
    f"{conv_v:.2f}%",
    help="Pourcentage de vues de contenu ayant généré une visite de profil."
)
c7.metric(
    "Croissance mensuelle",
    f"{avg_growth:.0f} foll/mois",
    help="Nombre moyen de nouveaux followers gagnés chaque mois."
)
c8.metric(
    "Mois de pic growth",
    peak,
    help="Mois où le gain de followers a été le plus élevé."
)

# --- KPI Footfall (full width) with help text ---
total_footfall = int(df_monthly["Footfall"].sum())
st.metric(
    "Total Footfall",
    f"{total_footfall:,}",
    help="Nombre total de passages physiques enregistrés au centre sur la période."
)


# --- Data table ---
st.subheader("Données consolidées")
df_disp = df_monthly.copy()
df_disp["Mois"] = df_disp["Mois"].dt.strftime("%b %Y")
st.dataframe(df_disp.style.format({
    "Followers":"{:,}", "Visites":"{:,}", "Vues":"{:,}",
    "Budget":"{:.0f}", "Footfall":"{:,}"
}), use_container_width=True)

# --- Plot helper ---
def plot_series(x, y, title, ylabel, color, sec_data=None, sec_label=None):
    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(x, y, marker="o", color=color)
    ax.set_ylabel(ylabel, color=color)
    if sec_data is not None:
        ax2 = ax.twinx()
        ax2.plot(x, sec_data, marker="s", linestyle="--", color="tab:red")
        ax2.set_ylabel(sec_label, color="tab:red")
    ax.set_xticks(x)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()
    st.subheader(title)
    return fig

# --- Graphs ---
st.pyplot(plot_series(df_monthly["Mois"], df_monthly["Followers"],
                      "Followers vs Budget", "Followers", "tab:blue",
                      sec_data=df_monthly["Budget"], sec_label="Budget (EUR)"))

st.pyplot(plot_series(df_monthly["Mois"], df_monthly["Visites"],
                      "Visites profil", "Visites", "tab:orange"))

st.pyplot(plot_series(df_monthly["Mois"], df_monthly["Vues"],
                      "Vues contenu", "Vues", "tab:green"))

st.pyplot(plot_series(df_monthly["Mois"], df_monthly["Footfall"],
                      "Footfall mensuel", "Footfall", "tab:gray"))


# --- Export PDF ---
st.header("5. Export PDF")
if st.button("📄 Générer le rapport PDF"):
    pdf = FPDF('P','mm','A4'); pdf.add_page()
    pdf.set_font('Arial','B',16)
    pdf.cell(0,10,f"Rapport Nice Valley ({start}–{end})",ln=True,align='C')
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    for title, fig in [
        ("Followers vs Budget",   plot_series(df_monthly["Mois"], df_monthly["Followers"], "","", "")),
        ("Visites profil",        plot_series(df_monthly["Mois"], df_monthly["Visites"],"","", "")),
        ("Vues contenu",          plot_series(df_monthly["Mois"], df_monthly["Vues"],   "","", "")),
        ("Footfall mensuel",      plot_series(df_monthly["Mois"], df_monthly["Footfall"],"","", "")),
    ]:
        pdf.set_font('Arial','B',12); pdf.cell(0,6,title,ln=True)
        fig.savefig(tmp.name, dpi=150, bbox_inches='tight')
        pdf.image(tmp.name, x=15, w=180); pdf.ln(5)
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    fname = f"rapport_nice_valley_{start.replace(' ','_')}-{end.replace(' ','_')}.pdf"
    st.download_button("⬇️ Télécharger PDF", pdf_bytes, file_name=fname, mime="application/pdf")

st.markdown("© Nice Valley Dashboard — Généré avec Streamlit")
