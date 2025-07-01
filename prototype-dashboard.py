import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

st.set_page_config(page_title="Dashboard Nice Valley", layout="wide")
st.title("📊 Dashboard Communication & Animations — Nice Valley")

# ------------- Sidebar : uploads & inputs -------------
st.sidebar.header("1. Importer tes données")
followers_file  = st.sidebar.file_uploader("CSV « Followers en plus »", type=["csv"])
visites_file    = st.sidebar.file_uploader("CSV « Visites »",        type=["csv"])
vues_file       = st.sidebar.file_uploader("CSV « Vues »",           type=["csv"])
budget_file     = st.sidebar.file_uploader("Excel « Budget mensuel »", type=["xlsx"])

if not (followers_file and visites_file and vues_file and budget_file):
    st.sidebar.info("Upload tes 4 fichiers : followers, visites, vues, budget")
    st.stop()

value_per_follower = st.sidebar.number_input(
    "Valeur estimée par follower (€)",
    min_value=0.0, value=0.50, step=0.01,
    help="Coût moyen d'acquisition ou valeur marketing d'un follower"
)

# ------------- Lecture & nettoyage générique CSV -------------
@st.cache_data
def load_and_clean_csv(file, col_name):
    df = pd.read_csv(
        file,
        encoding='utf-16',
        sep=',',
        skiprows=2,
        names=["Date", col_name],
        dtype=str,
        na_filter=False
    )
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df[col_name] = df[col_name].str.extract(r"(\d+)").astype(int)
    df["Mois"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    return df

# ------------- Lecture & détection automatique Budget Excel -------------
@st.cache_data
def load_budget_excel(file):
    # On lit la feuille principale en sautant 2 lignes pour arriver à l'en-tête mois
    df = pd.read_excel(file, header=2, engine='openpyxl', sheet_name=0, dtype=str)
    # Colonnes des mois en français (sans accents pour fiabilité)
    month_cols = {
        'JANVIER':1,'FÉVRIER':2,'MARS':3,'AVRIL':4,'MAI':5,'JUIN':6,
        'JUILLET':7,'AOUT':8,'SEPTEMBRE':9,'OCTOBRE':10,'NOVEMBRE':11,'DÉCEMBRE':12
    }
    # On repère la ligne agrégée SS TOTAL (ou contenant "total")
    mask = df.iloc[:,0].str.contains("total", case=False, na=False)
    if not mask.any():
        st.error("Impossible de trouver la ligne ‘SS TOTAL’ dans le budget Excel.")
        st.stop()
    # On prend la dernière occurrence (cumul général)
    row = df[mask].iloc[-1]
    # On construit les listes Mois/Budget
    mois_list = []
    budget_list = []
    for col, num in month_cols.items():
        if col in row.index:
            val = row[col]
            try:
                b = float(str(val).replace(" ","").replace(" ",""))
            except:
                b = 0.0
            date = pd.to_datetime(f"2025-{num:02d}-01")  # On place en année 2025
            mois_list.append(date)
            budget_list.append(b)
    return pd.DataFrame({"Mois": mois_list, "Budget": budget_list})

# ------------- Chargement des données -------------
df_followers = load_and_clean_csv(followers_file, "Followers")
df_visites   = load_and_clean_csv(visites_file,   "Visites")
df_vues      = load_and_clean_csv(vues_file,      "Vues")
df_budget    = load_budget_excel(budget_file)

# ------------- Agrégation mensuelle -------------
agg_f = df_followers.groupby("Mois")["Followers"].sum()
agg_v = df_visites.groupby("Mois")["Visites"].sum()
agg_w = df_vues.groupby("Mois")["Vues"].sum()

df_monthly = pd.concat([agg_f, agg_v, agg_w], axis=1).reset_index()
df_monthly = df_monthly.merge(df_budget, on="Mois", how="left")

# ------------- Calculs ROI & Coûts -------------
df_monthly["Valeur Followers"] = df_monthly["Followers"] * value_per_follower
df_monthly["ROI (%)"] = ((df_monthly["Valeur Followers"] - df_monthly["Budget"]) 
                         / df_monthly["Budget"]) * 100
df_monthly["Coût/Follower (€)"] = df_monthly["Budget"] / df_monthly["Followers"]

# ------------- KPI clés -------------
st.header("2. KPI & ROI")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Followers",       f"{int(agg_f.sum()):,}")
c2.metric("Total Budget (€)",      f"{int(df_monthly['Budget'].sum()):,}")
c3.metric("ROI moyen (%)",         f"{df_monthly['ROI (%)'].mean():.1f}")
c4.metric("Coût moyen/follower (€)", f"{df_monthly['Coût/Follower (€)'].mean():.2f}")

# ------------- Tableau de données -------------
st.subheader("Données consolidées & ROI")
df_disp = df_monthly.copy()
df_disp["Mois"] = df_disp["Mois"].dt.strftime("%b %Y")
st.dataframe(df_disp.style.format({
    "Followers":"{:,}",
    "Visites":  "{:,}",
    "Vues":     "{:,}",
    "Budget":   "{:.0f}",
    "ROI (%)":  "{:+.1f}",
    "Coût/Follower (€)":"{:.2f}"
}), use_container_width=True)

# ------------- Graphiques -------------
st.header("3. Graphiques")

# Followers vs Budget
st.subheader("Followers vs Budget")
fig1, ax1 = plt.subplots()
ax1.plot(df_monthly["Mois"], df_monthly["Followers"], marker="o", label="Followers", color="tab:blue")
ax1.set_ylabel("Followers", color="tab:blue")
ax1.tick_params(axis='y', labelcolor="tab:blue")
ax2 = ax1.twinx()
ax2.plot(df_monthly["Mois"], df_monthly["Budget"], marker="s", linestyle="--", label="Budget", color="tab:red")
ax2.set_ylabel("Budget (€)", color="tab:red")
for ax in (ax1, ax2):
    ax.set_xticks(df_monthly["Mois"])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig1.autofmt_xdate()
st.pyplot(fig1)

# ROI mensuel
st.subheader("ROI mensuel (%)")
fig2, ax2 = plt.subplots()
ax2.bar(df_monthly["Mois"], df_monthly["ROI (%)"], color="tab:purple")
ax2.axhline(0, color='black', linewidth=0.8)
ax2.set_ylabel("ROI (%)")
ax2.set_xticks(df_monthly["Mois"])
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig2.autofmt_xdate()
st.pyplot(fig2)

# Visites
st.subheader("Évolution des visites profil")
fig3, ax3 = plt.subplots()
ax3.plot(df_monthly["Mois"], df_monthly["Visites"], marker="o", linestyle="-", color="tab:orange")
ax3.set_ylabel("Visites")
ax3.set_xticks(df_monthly["Mois"])
ax3.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig3.autofmt_xdate()
st.pyplot(fig3)

# Vues
st.subheader("Évolution des vues contenu")
fig4, ax4 = plt.subplots()
ax4.plot(df_monthly["Mois"], df_monthly["Vues"], marker="o", linestyle="-", color="tab:green")
ax4.set_ylabel("Vues")
ax4.set_xticks(df_monthly["Mois"])
ax4.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig4.autofmt_xdate()
st.pyplot(fig4)

st.markdown("---")
st.markdown("© Nice Valley Dashboard — Généré avec Streamlit")
