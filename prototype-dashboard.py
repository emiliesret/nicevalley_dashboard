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
followers_file = st.sidebar.file_uploader("CSV « Followers en plus »", type=["csv"])
visites_file   = st.sidebar.file_uploader("CSV « Visites »",        type=["csv"])
vues_file      = st.sidebar.file_uploader("CSV « Vues »",           type=["csv"])
budget_file    = st.sidebar.file_uploader("Budget mensuel (CSV/XLSX)", type=["csv","xlsx"])
traffic_file   = st.sidebar.file_uploader("CSV/Excel « myTraffic »",   type=["csv","xlsx"])
if not (followers_file and visites_file and vues_file and budget_file and traffic_file):
    st.sidebar.info("Upload tes 5 fichiers : followers, visites, vues, budget, myTraffic")
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
        df = pd.read_csv(file, sep=';', header=0, encoding='utf-8')
        df.columns = ["Mois", "Budget"]
        df["Mois"] = pd.to_datetime(df["Mois"] + "-01")
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

# --- Traffic Loader (CSV ou XLSX) ---
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
            df["Timestamp"] = pd.to_datetime(raw["Period"] + "-1",
                                             format="%G-W%V-%u", errors="coerce")
            df["Count"] = pd.to_numeric(raw["Centre commercial Nice Valley"], errors="coerce").fillna(0)
        else:
            df = raw.rename(columns={raw.columns[0]:"Timestamp", raw.columns[1]:"Count"})
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
            df["Count"] = pd.to_numeric(df["Count"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Timestamp"])
    df["Mois"] = df["Timestamp"].dt.to_period("M").dt.to_timestamp()
    return df.groupby("Mois")["Count"].sum().reset_index().rename(columns={"Count":"Footfall"})

# --- Load All Data ---
df_followers = load_and_clean_csv(followers_file, "Followers")
df_visites   = load_and_clean_csv(visites_file,   "Visites")
df_vues      = load_and_clean_csv(vues_file,      "Vues")
df_budget    = load_budget(budget_file)
df_traffic   = load_traffic(traffic_file)

# --- Monthly Aggregation ---
agg_f = df_followers.groupby("Mois")["Followers"].sum()
agg_v = df_visites.groupby("Mois")["Visites"].sum()
agg_w = df_vues.groupby("Mois")["Vues"].sum()
df_monthly = pd.concat([agg_f, agg_v, agg_w], axis=1).reset_index()
df_monthly = df_monthly.merge(df_budget,  on="Mois", how="left")
df_monthly = df_monthly.merge(df_traffic, on="Mois", how="left").fillna({"Footfall":0})

# --- Period of Study ---
start = df_monthly["Mois"].min().strftime("%b %Y")
end   = df_monthly["Mois"].max().strftime("%b %Y")
st.markdown(f"**Période d’étude :** {start} - {end}")

# --- KPI Principaux ---
st.header("KPI principaux")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Followers",     f"{int(agg_f.sum()):,}",                           help="Total des nouveaux abonnés sur la période.")
c2.metric("Total Visites",       f"{int(agg_v.sum()):,}",                           help="Total des visites de profil générées.")
c3.metric("Total Vues",          f"{int(agg_w.sum()):,}",                           help="Total des impressions de contenu.")
c4.metric("Coût moyen/follower", f"{(df_monthly['Budget'].sum()/agg_f.sum()):.2f}", help="Budget total divisé par le nombre de nouveaux abonnés.")

# --- KPI Additionnels ---
st.markdown("### KPI additionnels")
total_f    = agg_f.sum()
total_v    = agg_v.sum()
total_w    = agg_w.sum()
conv_f     = (total_f/total_w*100) if total_w else 0
conv_v     = (total_v/total_w*100) if total_w else 0
growth     = df_monthly["Followers"].diff().fillna(0)
avg_growth = growth.mean()
idx_peak   = growth.idxmax()
peak_month = df_monthly.loc[idx_peak,"Mois"].strftime("%b %Y") if not growth.empty else "-"
c5, c6, c7, c8 = st.columns(4)
c5.metric("Conv. Followers/Vues", f"{conv_f:.2f}%",   help="Pourcentage de vues menant à un nouvel abonné.")
c6.metric("Conv. Visites/Vues",   f"{conv_v:.2f}%",   help="Pourcentage de vues menant à une visite de profil.")
c7.metric("Croissance mensuelle", f"{avg_growth:.0f} foll/mois", help="Gain moyen de nouveaux abonnés par mois.")
c8.metric("Mois de pic growth",   peak_month,         help="Mois avec le plus fort gain d’abonnés.")

# --- KPI Footfall ---
st.markdown("### KPI Traffic physique")
total_footfall = int(df_monthly["Footfall"].sum())
st.metric("Total Footfall", f"{total_footfall:,}", help="Total des passages physiques au centre.")

# --- Data Table ---
st.subheader("Données consolidées")
df_disp = df_monthly.copy()
df_disp["Mois"] = df_disp["Mois"].dt.strftime("%b %Y")
st.dataframe(df_disp.style.format({
    "Followers":"{:,}", "Visites":"{:,}", "Vues":"{:,}",
    "Budget":"{:.0f}",    "Footfall":"{:,}"
}), use_container_width=True)

# --- Plot helper & Figures ---
def plot_series(x, y, title, ylabel, color, sec=None, sec_label=None):
    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(x, y, marker="o", color=color)
    ax.set_ylabel(ylabel)
    if sec is not None:
        ax2 = ax.twinx()
        ax2.plot(x, sec, marker="s", linestyle="--", color="tab:red")
        ax2.set_ylabel(sec_label)
    ax.set_xticks(x)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()
    return fig

# --- Create & Display Figures ---
fig1 = plot_series(df_monthly["Mois"], df_monthly["Followers"],
                   "Followers vs Budget", "Followers", "tab:blue",
                   sec=df_monthly["Budget"], sec_label="Budget (EUR)")
st.subheader("Followers vs Budget")
st.pyplot(fig1)

fig2 = plot_series(df_monthly["Mois"], df_monthly["Visites"],
                   "Visites profil", "Visites", "tab:orange")
st.subheader("Visites profil")
st.pyplot(fig2)

fig3 = plot_series(df_monthly["Mois"], df_monthly["Vues"],
                   "Vues contenu", "Vues", "tab:green")
st.subheader("Vues contenu")
st.pyplot(fig3)

fig4 = plot_series(df_monthly["Mois"], df_monthly["Footfall"],
                   "Footfall mensuel", "Footfall", "tab:gray")
st.subheader("Footfall mensuel")
st.pyplot(fig4)

# --- Export PDF ---
st.header("Export PDF")
if st.button("Générer le rapport PDF"):
    pdf = FPDF('P','mm','A4')
    pdf.add_page()

    # Titre
    pdf.set_font('Arial','B',16)
    pdf.cell(0,10,f"Rapport Nice Valley ({start} - {end})", ln=True, align='C')
    pdf.ln(5)

    # --- KPI Principaux ---
    pdf.set_font('Arial','B',14)
    pdf.cell(0,8,"KPI principaux", ln=True)
    pdf.set_font('Arial','',11)
    pdf.cell(0,6,f"Total Followers     : {int(agg_f.sum()):,}", ln=True)
    pdf.cell(0,6,f"Total Visites       : {int(agg_v.sum()):,}", ln=True)
    pdf.cell(0,6,f"Total Vues          : {int(agg_w.sum()):,}", ln=True)
    pdf.cell(0,6,f"Coût moyen/follower : {df_monthly['Budget'].sum()/agg_f.sum():.2f} EUR", ln=True)
    pdf.ln(5)

    # --- KPI Additionnels ---
    pdf.set_font('Arial','B',14)
    pdf.cell(0,8,"KPI additionnels", ln=True)
    pdf.set_font('Arial','',11)
    pdf.cell(0,6,f"Conv. Foll./Vues    : {conv_f:.2f} %", ln=True)
    pdf.cell(0,6,f"Conv. Vis./Vues     : {conv_v:.2f} %", ln=True)
    pdf.cell(0,6,f"Croiss. mensuelle   : {avg_growth:.0f} foll/mois", ln=True)
    pdf.cell(0,6,f"Mois de pic growth  : {peak_month}", ln=True)
    pdf.ln(5)

    # --- KPI Traffic Physique ---
    pdf.set_font('Arial','B',14)
    pdf.cell(0,8,"KPI Traffic physique", ln=True)
    pdf.set_font('Arial','',11)
    pdf.cell(0,6,f"Total Footfall      : {total_footfall:,}", ln=True)
    pdf.ln(5)

    # --- Figures ---
    def add_figure(title, fig):
        pdf.set_font('Arial','B',12)
        pdf.cell(0,6,title, ln=True)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        fig.savefig(tmp.name, dpi=150, bbox_inches='tight')
        pdf.image(tmp.name, x=15, w=180)
        pdf.ln(5)
        tmp.close()

    add_figure("Followers vs Budget", fig1)
    add_figure("Visites profil",      fig2)
    add_figure("Vues contenu",        fig3)
    add_figure("Footfall mensuel",    fig4)

    # --- Génère et propose le téléchargement ---
    pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
    fname = f"rapport_nice_valley_{start.replace(' ','_')}_{end.replace(' ','_')}.pdf"
    st.download_button("Télécharger le rapport PDF", pdf_bytes,
                       file_name=fname, mime="application/pdf")
    st.success("Rapport PDF généré avec succès !")
else:
    st.info("Clique le bouton pour générer le rapport PDF.")
    
# --- Footer ---
st.markdown("---")
st.markdown("**Développé par Nice Valley**")
