import streamlit as st
import pandas as pd
import random
import json
import os
import hashlib
from datetime import datetime

# ==========================
# CONFIG
# ==========================

INVENTAIRE_FILE = "inventaires.json"
HISTORIQUE_TIRAGES_FILE = "historique_tirages.json"
HISTORIQUE_DISTRIBUTIONS_FILE = "historique_distributions.json"

ADMIN_USER = "admin"
ADMIN_HASH = "3a5763614660da0211b90045a806e2105a528a06a4dc9694299484092dd74d3e"

# ==========================
# STYLE CARTES
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
.card h3 {
    color: #7CFC00;
}
.card p {
    color: #f0f0f0;
}
</style>
""", unsafe_allow_html=True)

# ==========================
# INIT SESSION
# ==========================

for key in ["joueur","role","inventaires","last_tirage",
            "historique_tirages_admin","historique_distributions_admin"]:
    if key not in st.session_state:
        if key == "inventaires":
            st.session_state[key] = {}
        elif "historique" in key:
            st.session_state[key] = []
        else:
            st.session_state[key] = None

# ==========================
# JSON
# ==========================

def charger_json(file, default):
    if os.path.exists(file):
        with open(file,"r") as f:
            return json.load(f)
    return default

def sauvegarder_json(file,data):
    with open(file,"w") as f:
        json.dump(data,f)

st.session_state.inventaires = charger_json(INVENTAIRE_FILE,{})
st.session_state.historique_tirages_admin = charger_json(HISTORIQUE_TIRAGES_FILE,[])
st.session_state.historique_distributions_admin = charger_json(HISTORIQUE_DISTRIBUTIONS_FILE,[])

# ==========================
# CSV
# ==========================

@st.cache_data
def charger_fichier(nom):
    try:
        df = pd.read_csv(nom,sep=";",encoding="cp1252")
    except:
        return pd.DataFrame()
    df = df.iloc[:, :8]
    df.columns = ["Nom","Usage","Habitat","Informations","Rarete","Debut","Fin","Proliferation"]
    df["Debut"] = pd.to_numeric(df["Debut"], errors="coerce").fillna(0)
    df["Fin"] = pd.to_numeric(df["Fin"], errors="coerce").fillna(1000)
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

st.title("🌿 Mini-Jeu Botanique Avancé")

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
                sauvegarder_json(INVENTAIRE_FILE, st.session_state.inventaires)
                st.success("Compte créé")

else:
    st.write(f"Connecté : {st.session_state.joueur}")

# ==========================
# JOUEUR
# ==========================

if st.session_state.role == "joueur":

    inv = st.session_state.inventaires.get(st.session_state.joueur,{})
    st.subheader("📦 Inventaire")

    for plante,qt in inv.items():
        st.markdown(f"""
        <div class="card">
        <h3>{plante}</h3>
        <p>Quantité : {qt}</p>
        </div>
        """, unsafe_allow_html=True)

# ==========================
# ADMIN
# ==========================

elif st.session_state.role == "admin":

    col_left, col_right = st.columns(2)

    # ===== COLONNE GAUCHE =====
    with col_left:
        st.subheader("🎲 Tirage")

        env = st.selectbox("Environnement", list(fichiers.keys()))

        c1,c2,c3 = st.columns(3)
        nb = 0

        if c1.button("1"): nb=1
        if c2.button("3"): nb=3
        if c3.button("5"): nb=5

        if nb>0:
            tirage = tirer_plantes(fichiers[env],nb)
            st.session_state.last_tirage = tirage

            for _,row in tirage.iterrows():
                st.markdown(f"""
                <div class="card">
                <h3>{row['Nom']}</h3>
                <p><b>Habitat :</b> {row['Habitat']}</p>
                <p><b>Usage :</b> {row['Usage']}</p>
                <p><b>Rareté :</b> {row['Rarete']}</p>
                </div>
                """, unsafe_allow_html=True)

                st.session_state.historique_tirages_admin.append({
                    "Date":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Env":env,
                    "Plante":row["Nom"]
                })

            sauvegarder_json(HISTORIQUE_TIRAGES_FILE,
                             st.session_state.historique_tirages_admin)

    # ===== COLONNE DROITE =====
    with col_right:
        st.subheader("🎁 Distribution")

        if isinstance(st.session_state.last_tirage,pd.DataFrame):
            joueur = st.selectbox("Joueur",
                                  list(st.session_state.inventaires.keys()))
            plante = st.selectbox("Plante",
                                  st.session_state.last_tirage["Nom"].tolist())
            qte = st.number_input("Quantité",1,10,1)

            if st.button("Distribuer"):
                inv = st.session_state.inventaires[joueur]
                inv[plante] = inv.get(plante,0)+qte
                sauvegarder_json(INVENTAIRE_FILE,
                                 st.session_state.inventaires)

                st.session_state.historique_distributions_admin.append({
                    "Date":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Joueur":joueur,
                    "Plante":plante,
                    "Quantité":qte
                })

                sauvegarder_json(HISTORIQUE_DISTRIBUTIONS_FILE,
                                 st.session_state.historique_distributions_admin)

                st.success("Distribué")

        st.subheader("📊 Stats")
        if st.session_state.historique_distributions_admin:
            df = pd.DataFrame(st.session_state.historique_distributions_admin)
            st.bar_chart(df["Joueur"].value_counts())

