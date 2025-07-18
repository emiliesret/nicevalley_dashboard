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
st.sidebar.header("1. Importer tes données")
followers_file  = st.sidebar.file_uploader("CSV « Followers en plus »",     type=["csv"])
visites_file    = st.sidebar.file_uploader("CSV « Visites »",              type=["csv"])
vues_file       = st.sidebar.file_uploader("CSV « Vues »",                 type=["csv"])
budget_file     = st.sidebar.file_uploader("Budget mensuel (CSV/XLSX)",     type=["csv","xlsx"])
traffic_file    = st.sidebar.file_uploader("CSV/Excel « myTraffic »",      type=["csv","xlsx"])
animations_file = st.sidebar.file_uploader("Animations 2025 (CSV)",         type=["csv"])

if not (followers_file and visites_file and vues_file and budget_file and traffic_file):
    st.sidebar.info("Merci d’uploader : followers, visites, vues, budget, myTraffic")
    st.stop()

# --- CSV Loader & Cleaner ---
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

# --- Budget Loader (CSV ou XLSX) ---
@st.cache_data
def load_budget(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file, sep=';', encoding='utf-8')
        df.columns = ["Mois", "Budget"]
        df["Mois"]   = pd.to_datetime(df["Mois"] + "-01", format="%Y-%m-%d")
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
                try:    b = float(str(row[col]).replace(" ", ""))
                except: b = 0.0
                months.append(pd.to_datetime(f"{year}-{num:02d}-01"))
                budgets.append(b)
        df = pd.DataFrame({"Mois": months, "Budget": budgets})
    return df

# --- myTraffic Loader (CSV ou XLSX) ---
@st.cache_data
def load_traffic(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file, parse_dates=[0], dayfirst=True, encoding='utf-8')
        df.columns = ["Timestamp", "Count"]
    else:
        raw = pd.read_excel(file, engine='openpyxl', dtype=str)
        if "Period" in raw.columns and "Centre commercial Nice Valley" in raw.columns:
            df = raw[raw["Period"].str.match(r"\d{4}-W\d{2}", na=False)].copy()
            df["Timestamp"] = pd.to_datetime(df["Period"] + "-1", format="%G-W%V-%u", errors="coerce")
            df["Count"]     = pd.to_numeric(df["Centre commercial Nice Valley"], errors="coerce").fillna(0)
        else:
            df = raw.rename(columns={raw.columns[0]:"Timestamp", raw.columns[1]:"Count"})
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
            df["Count"]     = pd.to_numeric(df["Count"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Timestamp"])
    df["Mois"] = df["Timestamp"].dt.to_period("M").dt.to_timestamp()
    return df.groupby("Mois")["Count"].sum().reset_index().rename(columns={"Count":"Footfall"})

# --- Animations Loader (CSV) ---
@st.cache_data
def load_animations(file):
    # on détecte automatiquement le séparateur (',', ';', '\t', ...)
    df = pd.read_csv(
        file,
        sep=None,
        engine='python',
        dtype=str,
        on_bad_lines='skip'  # pour sauter les lignes mal formées
    )
    # on supprime les colonnes complètement vides
    df = df.dropna(axis=1, how='all')
    if df.shape[1] < 2:
        st.error("Le fichier animations doit contenir au moins deux colonnes.")
        return pd.DataFrame(columns=["Date","Animation"])
    # on ne garde que les 2 premières colonnes
    df = df.iloc[:, :2].copy()
    df.columns = ["Date", "Animation"]
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date","Animation"])
    return df.reset_index(drop=True)

# --- Load data ---
df_followers = load_and_clean_csv(followers_file, "Followers")
df_visites   = load_and_clean_csv(visites_file,   "Visites")
df_vues      = load_and_clean_csv(vues_file,      "Vues")
df_budget    = load_budget(budget_file)
df_traffic   = load_traffic(traffic_file)
df_anim      = load_animations(animations_file) if animations_file else pd.DataFrame(columns=["Date","Animation"])

# --- Monthly aggregation ---
agg_f = df_followers.groupby("Mois")["Followers"].sum()
agg_v = df_visites.groupby("Mois")["Visites"].sum()
agg_w = df_vues.groupby("Mois")["Vues"].sum()
df_monthly = (
    pd.concat([agg_f, agg_v, agg_w], axis=1)
      .reset_index()
      .merge(df_budget,  on="Mois", how="left")
      .merge(df_traffic, on="Mois", how="left")
      .fillna(0)
)

# --- Période d’étude ---
start = df_monthly["Mois"].min().strftime("%b %Y")
end   = df_monthly["Mois"].max().strftime("%b %Y")
st.markdown(f"**Période d’étude :** {start} – {end}")

# --- KPI principaux ---
st.header("2. KPI principaux")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Followers",  f"{int(agg_f.sum()):,}")
c2.metric("Total Visites",    f"{int(agg_v.sum()):,}")
c3.metric("Total Vues",       f"{int(agg_w.sum()):,}")
c4.metric("Budget total (€)", f"{int(df_monthly['Budget'].sum()):,}")
c5.metric("Total Footfall",   f"{int(df_monthly['Footfall'].sum()):,}")

# --- Données mensuelles ---
st.subheader("3. Données mensuelles consolidées")
df_disp = df_monthly.copy()
df_disp["Mois"] = df_disp["Mois"].dt.strftime("%b %Y")
st.dataframe(df_disp.style.format({
    "Followers":"{:,}", "Visites":"{:,}", "Vues":"{:,}",
    "Budget":"{:.0f}",   "Footfall":"{:,}"
}), use_container_width=True)

# --- Graph mensuel avec annotations animations ---
def plot_monthly(x, y, title, ylabel, color, sec=None, sec_label=None):
    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(x, y, color=color, lw=2)
    ax.set_ylabel(ylabel, color=color)
    if sec is not None:
        ax2 = ax.twinx()
        ax2.plot(x, sec, color="tab:red", lw=2, ls="--")
        ax2.set_ylabel(sec_label, color="tab:red")
    for _, r in df_anim.iterrows():
        m = r["Date"].to_period("M").to_timestamp()
        ax.axvline(m, color="gray", ls=":", lw=1)
        ax.text(m, ax.get_ylim()[1],
                r["Animation"], rotation=90, va="bottom",
                ha="center", fontsize=8, backgroundcolor="white",
                clip_on=True)
    ax.margins(x=0.05)
    ax.set_xticks(x)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.tight_layout()
    st.subheader(title)
    return fig

fig1 = plot_monthly(df_monthly["Mois"], df_monthly["Followers"],
                    "Followers vs Budget", "Followers", "tab:blue",
                    sec=df_monthly["Budget"], sec_label="Budget (€)")
st.pyplot(fig1)

fig2 = plot_monthly(df_monthly["Mois"], df_monthly["Visites"],
                    "Visites profil", "Visites", "tab:orange")
st.pyplot(fig2)

fig3 = plot_monthly(df_monthly["Mois"], df_monthly["Vues"],
                    "Vues de contenu", "Vues", "tab:green")
st.pyplot(fig3)

fig4 = plot_monthly(df_monthly["Mois"], df_monthly["Footfall"],
                    "Footfall mensuel", "Passages", "tab:gray")
st.pyplot(fig4)

# --- Courbe journalière des Followers avec animations ---
st.subheader("4. Courbe journalière des Followers")
fig5, ax5 = plt.subplots(figsize=(12,4))
ax5.plot(df_followers["Date"], df_followers["Followers"], color="tab:blue", lw=1.5)
ax5.set_xlabel("Date"); ax5.set_ylabel("Followers")
for _, r in df_anim.iterrows():
    d = r["Date"]
    nearest = df_followers.iloc[(df_followers["Date"] - d).abs().argsort()[:1]]
    y = nearest["Followers"].iat[0]
    ax5.scatter(d, y, color="tab:red", s=70, zorder=5)
    ax5.text(d, y, r["Animation"], rotation=45,
             ha="right", va="bottom", fontsize=8,
             backgroundcolor="white", clip_on=True)
fig5.autofmt_xdate(); fig5.tight_layout(); st.pyplot(fig5)

# --- Export PDF ---
st.header("5. Export PDF")
if st.button("Générer le rapport PDF"):
    pdf = FPDF('P','mm','A4'); pdf.add_page()
    pdf.set_font('Arial','B',16)
    pdf.cell(0,10,f"Rapport Nice Valley ({start}–{end})", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font('Arial','B',14); pdf.cell(0,8,"KPI principaux", ln=True)
    pdf.set_font('Arial','',11)
    pdf.cell(0,6,f"Total Followers  : {int(agg_f.sum()):,}", ln=True)
    pdf.cell(0,6,f"Total Visites    : {int(agg_v.sum()):,}", ln=True)
    pdf.cell(0,6,f"Total Vues       : {int(agg_w.sum()):,}", ln=True)
    pdf.cell(0,6,f"Budget total (€) : {int(df_monthly['Budget'].sum()):,}", ln=True)
    pdf.cell(0,6,f"Total Footfall   : {int(df_monthly['Footfall'].sum()):,}", ln=True)
    pdf.ln(5)
    def add_fig(title, fig):
        pdf.set_font('Arial','B',12); pdf.cell(0,6,title, ln=True)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        fig.savefig(tmp.name, dpi=150, bbox_inches='tight')
        pdf.image(tmp.name, x=15, w=180); pdf.ln(5); tmp.close()
    for t,f in [("Monthly Followers vs Budget",fig1),
                ("Visites profil",fig2),
                ("Vues de contenu",fig3),
                ("Footfall mensuel",fig4),
                ("Courbe journalière",fig5)]:
        add_fig(t,f)
    pdf_bytes = pdf.output(dest='S').encode('latin-1','ignore')
    fname = f"rapport_nice_valley_{start.replace(' ','_')}_{end.replace(' ','_')}.pdf"
    st.download_button("Télécharger le PDF", pdf_bytes, file_name=fname, mime="application/pdf")
    st.success("✅ PDF généré !")
else:
    st.info("Clique pour générer le PDF")

st.markdown("---")
st.markdown("**Développé par Nice Valley**")
