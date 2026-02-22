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
ADMIN_HASH = "COLLER_LE_HASH_ICI"  # Hash SHA256 du mot de passe admin

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
# AUTO REFRESH (Joueur)
# ==========================
if st.session_state.role=="joueur":
    # Rafraîchissement automatique toutes les 5 secondes
    count = st_autorefresh(interval=5000, limit=None, key="joueur_autorefresh")

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
                # Récupération type
                type_plante = "Inconnu"
                for df in fichiers.values():
                    res = df[df["Nom"] == plante]
                    if not res.empty:
                        type_plante = res.iloc[0]["Usage"]
                        break
                # Icône par usage exact
                icones_dict = {
                    "soin": "❤️","médic": "❤️","guér": "❤️","curatif": "❤️",
                    "tox": "☠️","poison": "☠️","aliment": "🍽️","arom": "🌿",
                    "mag": "✨","bois": "🪵","résine": "🪵"
                }
                icone = "🌱"
                usage_lower = type_plante.lower()
                for key in icones_dict:
                    if key in usage_lower:
                        icone = icones_dict[key]
                        break
                data_inv.append({"Plante": f"{icone} {plante}","Type": type_plante,"Quantité": qt})

            df_inv = pd.DataFrame(data_inv)
            st.dataframe(df_inv,use_container_width=True,hide_index=True)

        else:
            st.info("Inventaire vide.")

    with tabs_joueur[1]:
        st.subheader("📜 Journal personnel")
        journal = st.session_state.journal_usages.get(joueur, [])
        if journal:
            df_journal = pd.DataFrame(journal)
            st.dataframe(df_journal,use_container_width=True,hide_index=True)
        else:
            st.info("Aucune utilisation enregistrée.")

# ==========================
# INTERFACE ADMIN
# ==========================
elif st.session_state.role=="admin":
    tabs = st.tabs(["🎮 Gestion","📜 Historique"])
    with tabs[0]:
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("🎲 Tirage")
            env = st.selectbox("Environnement", list(fichiers.keys()))
            c1,c2,c3 = st.columns(3)
            nb = 0
            if c1.button("1"): nb=1
            if c2.button("3"): nb=3
            if c3.button("5"): nb=5

            if nb>0:
                tirage = tirer_plantes(fichiers[env], nb)
                st.session_state.last_tirage = tirage
                for _,row in tirage.iterrows():
                    st.markdown(f"<div class='card'><h3>{row['Nom']}</h3><p><b>Usage :</b> {row['Usage']}</p><p><b>Habitat :</b> {row['Habitat']}</p></div>", unsafe_allow_html=True)
                    st.session_state.historique_tirages_admin.append({"Date":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"Env":env,"Plante":row["Nom"]})

        with col_right:
            st.subheader("🎁 Distribution")
            if isinstance(st.session_state.last_tirage,pd.DataFrame) and not st.session_state.last_tirage.empty:
                joueur = st.selectbox("Joueur", list(st.session_state.inventaires.keys()))
                plante = st.selectbox("Plante", st.session_state.last_tirage["Nom"].tolist())
                qte = st.number_input("Quantité",1,10,1)
                if st.button("Distribuer"):
                    inv = st.session_state.inventaires[joueur]
                    inv[plante] = inv.get(plante,0)+qte
                    sauvegarder_json(INVENTAIRE_FILE, st.session_state.inventaires)
                    st.success("Distribution effectuée")

    with tabs[1]:
        st.subheader("📜 Historique des tirages")
        if st.session_state.historique_tirages_admin:
            st.dataframe(pd.DataFrame(st.session_state.historique_tirages_admin), use_container_width=True)
        else:
            st.info("Aucun tirage enregistré.")
