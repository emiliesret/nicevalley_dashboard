import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from fpdf import FPDF
import tempfile

# Page config
st.set_page_config(page_title="Dashboard Nice Valley", layout="wide")
st.title("📊 Dashboard Communication & Animations — Nice Valley")

# Sidebar uploads and inputs
st.sidebar.header("1. Importer tes données")
followers_file = st.sidebar.file_uploader("CSV « Followers en plus »", type=["csv"])
visites_file   = st.sidebar.file_uploader("CSV « Visites »",         type=["csv"])
vues_file      = st.sidebar.file_uploader("CSV « Vues »",            type=["csv"])
budget_file    = st.sidebar.file_uploader("Budget mensuel (CSV ou XLSX)", type=["csv","xlsx"])

if not (followers_file and visites_file and vues_file and budget_file):
    st.sidebar.info("Upload tes 4 fichiers : followers, visites, vues, budget")
    st.stop()

value_per_follower = st.sidebar.number_input(
    "Valeur estimée par follower (EUR)",
    min_value=0.0, value=0.50, step=0.01,
    help="Valeur unitaire pour calculer le coût par follower"
)

# Generic CSV loader and cleaner
@st.cache_data
def load_and_clean_csv(file, col_name):
    df = pd.read_csv(
        file, encoding='utf-16', sep=',', skiprows=2,
        names=["Date", col_name], dtype=str, na_filter=False
    )
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df[col_name] = df[col_name].str.extract(r"(\d+)").astype(int)
    df["Mois"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    return df

# Budget loader supporting CSV or XLSX
@st.cache_data
def load_budget(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file, sep=';', header=0, encoding='utf-8')
        df.columns = ["Mois", "Budget"]
        df["Mois"] = pd.to_datetime(df["Mois"] + "-01", format="%Y-%m-%d")
        df["Budget"] = pd.to_numeric(df["Budget"], errors="coerce").fillna(0)
        return df
    else:
        df = pd.read_excel(file, header=2, engine='openpyxl', sheet_name=0, dtype=str)
        month_cols = {
            'JANVIER':1,'FÉVRIER':2,'MARS':3,'AVRIL':4,'MAI':5,'JUIN':6,
            'JUILLET':7,'AOUT':8,'SEPTEMBRE':9,'OCTOBRE':10,'NOVEMBRE':11,'DÉCEMBRE':12
        }
        mask = df.iloc[:,0].str.contains("total", case=False, na=False)
        if not mask.any():
            st.error("Ligne 'SS TOTAL' introuvable dans le budget Excel.")
            st.stop()
        row = df[mask].iloc[-1]
        mois_list, budget_list = [], []
        current_year = pd.Timestamp.now().year
        for col, num in month_cols.items():
            if col in row.index:
                try:
                    b = float(str(row[col]).replace(" ", ""))
                except:
                    b = 0.0
                mois_list.append(pd.to_datetime(f"{current_year}-{num:02d}-01"))
                budget_list.append(b)
        return pd.DataFrame({"Mois": mois_list, "Budget": budget_list})

# Load data
df_followers = load_and_clean_csv(followers_file, "Followers")
df_visites   = load_and_clean_csv(visites_file,   "Visites")
df_vues      = load_and_clean_csv(vues_file,      "Vues")
df_budget    = load_budget(budget_file)

# Monthly aggregation
agg_f = df_followers.groupby("Mois")["Followers"].sum()
agg_v = df_visites.groupby("Mois")["Visites"].sum()
agg_w = df_vues.groupby("Mois")["Vues"].sum()
df_monthly = pd.concat([agg_f, agg_v, agg_w], axis=1).reset_index()
df_monthly = df_monthly.merge(df_budget, on="Mois", how="left")

# Compute cost per follower
df_monthly["Coût/Follower (EUR)"] = df_monthly["Budget"] / df_monthly["Followers"]

# Period of study
start = df_monthly["Mois"].min().strftime("%b %Y")
end   = df_monthly["Mois"].max().strftime("%b %Y")
st.markdown(f"**Période d’étude :** {start} - {end}")

# KPI principaux
st.header("2. KPI principaux")
c1, c2, c3, c4 = st.columns(4)
c1.metric(
    label="Total Followers",
    value=f"{int(agg_f.sum()):,}",
    help="Nombre total de nouveaux abonnés gagnés sur la période sélectionnée."
)
c2.metric(
    label="Total Visites",
    value=f"{int(agg_v.sum()):,}",
    help="Nombre total de visites de profil Instagram générées."
)
c3.metric(
    label="Total Vues",
    value=f"{int(agg_w.sum()):,}",
    help="Nombre total d'impressions/vues de votre contenu Instagram."
)
c4.metric(
    label="Coût moyen/follower (EUR)",
    value=f"{df_monthly['Coût/Follower (EUR)'].mean():.2f}",
    help="Budget moyen dépensé pour acquérir un nouveau follower."
)

# KPI additionnels
st.markdown("### KPI additionnels")
total_followers   = agg_f.sum()
total_visites     = agg_v.sum()
total_vues        = agg_w.sum()
conv_foll_rate    = (total_followers / total_vues * 100) if total_vues else 0
conv_vis_rate     = (total_visites   / total_vues * 100) if total_vues else 0
monthly_growth    = df_monthly["Followers"].diff().fillna(0)
avg_monthly_growth = monthly_growth.mean()
idx_peak          = monthly_growth.idxmax()
peak_month        = df_monthly.loc[idx_peak, "Mois"].strftime("%b %Y") if not monthly_growth.empty else "-"

c5, c6, c7, c8 = st.columns(4)
c5.metric(
    label="Conv. Followers/Vues",
    value=f"{conv_foll_rate:.2f}%",
    help="Pourcentage de vues de contenu qui ont abouti à un nouvel abonné."
)
c6.metric(
    label="Conv. Visites/Vues",
    value=f"{conv_vis_rate:.2f}%",
    help="Pourcentage de vues de contenu qui ont généré une visite de profil."
)
c7.metric(
    label="Croiss. mensuelle (moy.)",
    value=f"{avg_monthly_growth:.0f} foll/mois",
    help="Nombre moyen de nouveaux followers gagnés par mois."
)
c8.metric(
    label="Mois de pic growth",
    value=f"{peak_month}",
    help="Mois où le nombre de nouveaux followers a été le plus élevé."
)

# Data table
st.subheader("Données consolidées")
df_disp = df_monthly.copy()
df_disp["Mois"] = df_disp["Mois"].dt.strftime("%b %Y")
st.dataframe(
    df_disp.style.format({
        "Followers":"{:,}",
        "Visites":"{:,}",
        "Vues":"{:,}",
        "Budget":"{:.0f}",
        "Coût/Follower (EUR)":"{:.2f}"
    }),
    use_container_width=True
)

# Graphs
st.header("3. Graphiques")

fig1, ax1 = plt.subplots(figsize=(10, 4))
ax1.plot(df_monthly["Mois"], df_monthly["Followers"], marker="o", color="tab:blue")
ax1.set_ylabel("Followers", color="tab:blue")
ax2 = ax1.twinx()
ax2.plot(df_monthly["Mois"], df_monthly["Budget"], marker="s", linestyle="--", color="tab:red")
ax2.set_ylabel("Budget (EUR)", color="tab:red")
ax1.set_xticks(df_monthly["Mois"])
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig1.autofmt_xdate()
st.subheader("Followers vs Budget")
st.pyplot(fig1)

fig2, ax2 = plt.subplots(figsize=(10, 4))
ax2.plot(df_monthly["Mois"], df_monthly["Coût/Follower (EUR)"], marker="o", color="tab:purple")
ax2.set_ylabel("Coût/Follower (EUR)")
ax2.set_xticks(df_monthly["Mois"])
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig2.autofmt_xdate()
st.subheader("Coût par follower")
st.pyplot(fig2)

fig3, ax3 = plt.subplots(figsize=(10, 4))
ax3.plot(df_monthly["Mois"], df_monthly["Visites"], marker="o", color="tab:orange")
ax3.set_ylabel("Visites")
ax3.set_xticks(df_monthly["Mois"])
ax3.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig3.autofmt_xdate()
st.subheader("Visites profil")
st.pyplot(fig3)

fig4, ax4 = plt.subplots(figsize=(10, 4))
ax4.plot(df_monthly["Mois"], df_monthly["Vues"], marker="o", color="tab:green")
ax4.set_ylabel("Vues")
ax4.set_xticks(df_monthly["Mois"])
ax4.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig4.autofmt_xdate()
st.subheader("Vues contenu")
st.pyplot(fig4)

st.markdown("---")

# ------------- Export PDF -------------
st.header("4. Export PDF")
if st.button("📄 Générer le rapport PDF"):
    pdf = FPDF('P', 'mm', 'A4')
    pdf.add_page()
    # Titre du rapport avec période
    pdf.set_font('Arial', 'B', 16)
    title = f"Rapport Nice Valley ({start} - {end})"
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(5)

    # KPI principaux
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 8, 'KPI principaux', ln=True)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 6, f"Total Followers : {int(agg_f.sum()):,}", ln=True)
    pdf.cell(0, 6, f"Total Visites   : {int(agg_v.sum()):,}", ln=True)
    pdf.cell(0, 6, f"Total Vues      : {int(agg_w.sum()):,}", ln=True)
    pdf.cell(0, 6, f"Coût/Follower   : {df_monthly['Coût/Follower (EUR)'].mean():.2f} EUR", ln=True)
    pdf.ln(5)

    # KPI additionnels
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 8, 'KPI additionnels', ln=True)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 6, f"Conv. Followers/Vues    : {conv_foll_rate:.2f} %", ln=True)
    pdf.cell(0, 6, f"Conv. Visites/Vues      : {conv_vis_rate:.2f} %", ln=True)
    pdf.cell(0, 6, f"Croiss. mensuelle (moy.) : {avg_monthly_growth:.0f} foll/mois", ln=True)
    pdf.cell(0, 6, f"Mois de pic growth      : {peak_month}", ln=True)
    pdf.ln(5)

    # Fonction pour ajouter un graphique avec titre
    def add_titled_figure(title, fig):
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 6, title, ln=True)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        fig.savefig(tmp.name, dpi=150, bbox_inches='tight')
        pdf.image(tmp.name, x=15, w=180)
        pdf.ln(5)
        tmp.close()

    # Insertion des graphiques avec titre
    add_titled_figure("Followers vs Budget", fig1)
    add_titled_figure("Coût par follower (EUR) mensuel", fig2)
    add_titled_figure("Évolution des visites profil", fig3)
    add_titled_figure("Évolution des vues contenu", fig4)

    # Génération et téléchargement
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    fname = f"rapport_nice_valley_{start.replace(' ', '_')}-{end.replace(' ', '_')}.pdf"
    st.download_button(
        label="⬇️ Télécharger le rapport PDF",
        data=pdf_bytes,
        file_name=fname,
        mime="application/pdf"
    )

st.markdown("© Nice Valley Dashboard — Généré avec Streamlit")
