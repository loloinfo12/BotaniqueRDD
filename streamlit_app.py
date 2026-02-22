import streamlit as st
import pandas as pd
import random
import json
import os
import hashlib
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ==========================
# CONFIGURATION
# ==========================
INVENTAIRE_FILE = "inventaires.json"
HISTORIQUE_TIRAGES_FILE = "historique_tirages.json"
HISTORIQUE_DISTRIBUTIONS_FILE = "historique_distributions.json"
JOURNAL_FILE = "journal_usages.json"

ADMIN_USER = "admin"
ADMIN_HASH = "3a5763614660da0211b90045a806e2105a528a06a4dc9694299484092dd74d3e"

# ==========================
# STYLE
# ==========================
st.markdown("""
<style>
.card {
    background-color: #1e1e1e;
    padding: 20px;
    border-radius: 15px;
    margin-bottom: 15px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.4);
}
.card h3 { color: #7CFC00; margin-bottom:5px; }
.card p { color: #f0f0f0; margin:2px 0; }
.card.champignon { border-left: 5px solid #ff6600; }
.card.herbe { border-left: 5px solid #32cd32; }
</style>
""", unsafe_allow_html=True)

# ==========================
# SESSION INIT
# ==========================
for key in ["joueur","role","inventaires","last_tirage",
            "historique_tirages_admin","historique_distributions_admin","journal_usages"]:
    if key not in st.session_state:
        if key in ["inventaires","journal_usages"]:
            st.session_state[key] = {}
        elif "historique" in key:
            st.session_state[key] = []
        else:
            st.session_state[key] = None

# ==========================
# JSON FUNCTIONS
# ==========================
def charger_json(file, default):
    if os.path.exists(file):
        with open(file,"r") as f:
            return json.load(f)
    return default

def sauvegarder_json(file, data):
    with open(file,"w") as f:
        json.dump(data,f)

st.session_state.inventaires = charger_json(INVENTAIRE_FILE,{})
st.session_state.historique_tirages_admin = charger_json(HISTORIQUE_TIRAGES_FILE,[])
st.session_state.historique_distributions_admin = charger_json(HISTORIQUE_DISTRIBUTIONS_FILE,[])
st.session_state.journal_usages = charger_json(JOURNAL_FILE,{})

# ==========================
# LOAD CSV
# ==========================
@st.cache_data
def charger_fichier(nom):
    try:
        df = pd.read_csv(nom, sep=";", encoding="cp1252")
    except:
        return pd.DataFrame()

    df = df.iloc[:, :8]
    df.columns = ["Nom","Usage","Habitat","Informations",
                  "Rarete","Debut","Fin","Proliferation"]

    df["Debut"] = pd.to_numeric(df["Debut"], errors="coerce").fillna(0)
    df["Fin"] = pd.to_numeric(df["Fin"], errors="coerce").fillna(1000)
    df["Rarete"] = pd.to_numeric(df["Rarete"], errors="coerce").fillna(0)

    return df

fichiers = {
    "Collines": charger_fichier("Collines.csv"),
    "Forêts": charger_fichier("Forets.csv"),
    "Plaines": charger_fichier("Plaines.csv"),
    "Montagnes": charger_fichier("Montagnes.csv"),
    "Marais": charger_fichier("Marais.csv"),
    "Sous-sols": charger_fichier("Sous-sols.csv"),
}

# ==========================
# TIRAGE
# ==========================
def tirer_plantes(df, nb):
    if df.empty:
        return pd.DataFrame()
    max_val = int(df["Fin"].max())
    tirage_total = pd.DataFrame()
    for _ in range(nb):
        val = random.randint(1,max_val)
        res = df[(df["Debut"]<=val)&(df["Fin"]>=val)]
        tirage_total = pd.concat([tirage_total,res])
    return tirage_total

# ==========================
# LOGIN
# ==========================
st.title("🌿 Mini-Jeu Botanique")

if st.session_state.joueur is None:
    with st.form("login"):
        pseudo = st.text_input("Pseudo")
        mdp = st.text_input("Mot de passe admin", type="password")
        login = st.form_submit_button("Connexion")
        signup = st.form_submit_button("Créer compte")

        if login:
            hash_input = hashlib.sha256(mdp.encode()).hexdigest()
            if pseudo == ADMIN_USER and hash_input == ADMIN_HASH:
                st.session_state.joueur = pseudo
                st.session_state.role = "admin"
            elif pseudo in st.session_state.inventaires:
                st.session_state.joueur = pseudo
                st.session_state.role = "joueur"
            else:
                st.warning("Identifiants invalides")

        if signup:
            if pseudo in st.session_state.inventaires:
                st.warning("Pseudo existant")
            else:
                st.session_state.inventaires[pseudo] = {}
                sauvegarder_json(INVENTAIRE_FILE,st.session_state.inventaires)
                st.success("Compte créé")

# ==========================
# INTERFACE JOUEUR
# ==========================
if st.session_state.role == "joueur":

    st_autorefresh(interval=5000, key="raffraichissement_auto")

    joueur = st.session_state.joueur
    inventaire = st.session_state.inventaires.get(joueur, {})

    if joueur not in st.session_state.journal_usages:
        st.session_state.journal_usages[joueur] = []

    tabs_joueur = st.tabs(["📦 Inventaire", "📜 Journal"])

    with tabs_joueur[0]:
        st.subheader("📦 Mon Inventaire")

        if inventaire:
            data_inv = []
            for plante, qt in inventaire.items():
                type_plante = "Inconnu"
                for df in fichiers.values():
                    res = df[df["Nom"] == plante]
                    if not res.empty:
                        type_plante = res.iloc[0]["Usage"]
                        break

                usage_lower = type_plante.lower()

                if any(m in usage_lower for m in ["soin","médic","guér","curatif"]): icone="❤️"
                elif any(m in usage_lower for m in ["tox","poison"]): icone="☠️"
                elif "aliment" in usage_lower: icone="🍽️"
                elif "arom" in usage_lower: icone="🌿"
                elif "mag" in usage_lower: icone="✨"
                elif "bois" in usage_lower or "résine" in usage_lower: icone="🪵"
                else: icone="🌱"

                data_inv.append({
                    "Plante": f"{icone} {plante}",
                    "Type": type_plante,
                    "Quantité": qt
                })

            st.dataframe(pd.DataFrame(data_inv), use_container_width=True, hide_index=True)

        else:
            st.info("Inventaire vide.")

    with tabs_joueur[1]:
        st.subheader("📜 Journal personnel")
        journal = st.session_state.journal_usages.get(joueur, [])
        if journal:
            st.dataframe(pd.DataFrame(journal), use_container_width=True, hide_index=True)
        else:
            st.info("Aucune utilisation enregistrée.")
