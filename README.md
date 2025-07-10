# Dashboard Nice Valley

Un outil **Streamlit** interactif pour visualiser et analyser :  

- Les performances Instagram *(followers, visites, vues)*  
- Le trafic physique du centre *(footfall)*  
- L’impact des animations *(régression linéaire)*  
- Un rapport PDF complet  

---

## Prérequis

- Python **3.8+**
- `pip`
- Système : **Windows**, **macOS** ou **Linux**

---

## Installation

1. **Cloner le dépôt**  
   ```bash
   git clone https://github.com/ton-compte/stage_nice_valley.git
   cd stage_nice_valley
   ```

2. **Créer et activer un environnement virtuel**  
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

3. **Installer les dépendances**  
   ```bash
   pip install streamlit pandas matplotlib scikit-learn fpdf openpyxl
   ```

4. **Lancer l’application**  
   ```bash
   streamlit run app.py
   ```

   Ouvrir ensuite le navigateur à l’adresse indiquée *(généralement http://localhost:8501)*.

---

## Préparation des données

L’application attend **5 fichiers** à importer depuis la barre latérale :  

1. **Followers en plus** *(CSV UTF-16)*  
   - 2 lignes d’en-tête  
   - Colonne 1 : Date *(YYYY-MM-DD HH:MM:SS)*  
   - Colonne 2 : nombre de nouveaux followers

2. **Visites** *(CSV UTF-16)*  
   - Même format que pour les followers

3. **Vues** *(CSV UTF-16)*  
   - Même format que pour les followers

4. **Budget mensuel**

   **Option CSV** :  
     ```csv
     Mois;Budget
     2025-01;1200
     2025-02;1500
     ...
     ```

5. **myTraffic** *(CSV ou XLSX)*  
   - Colonne 1 : date ou période *(2025-01-01 ou 2025-W01)*  
   - Colonne 2 : nombre de passages

---

## Utilisation

Uploader les **5 fichiers** dans la barre latérale.  

L’application calcule automatiquement :  

- **Période d’étude** *(mois début/fin)*  
- **KPI principaux** : total followers, total visites, total vues, coût moyen par follower  
- **KPI additionnels** : taux de conversion *(vues → followers, vues → visites)*, croissance mensuelle, mois record  
- **KPI trafic physique** : footfall total

Consulter les **graphiques** :  
- Followers vs budget  
- Visites de profil  
- Vues de contenu  
- Footfall mensuel

Générer un **rapport PDF complet** d’un clic.

---

## Bonnes pratiques

- Vérifier que les exports **Meta** soient UTF-16 et contiennent **2 lignes d’en-tête**.
- Pour le budget Excel, conserver les mois en **majuscules** et la ligne *“SS TOTAL”*.

---

## Personnalisation

- Ajouter un filtre de période : `st.date_input`
- Permettre la sélection des KPI/graphes : `st.multiselect`
