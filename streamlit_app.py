import streamlit as st
import pandas as pd
import random
import json
import os
from datetime import datetime

# ==========================
# CONSTANTES
# ==========================

INVENTAIRE_FILE = "inventaires.json"
HISTORIQUE_TIRAGES_FILE = "historique_tirages.json"
HISTORIQUE_DISTRIBUTIONS_FILE = "historique_distributions.json"

ADMIN_CREDENTIALS = {"admin": "Dreame12"}

# ==========================
# INITIALISATION SESSION
# ==========================

for key in [
    "joueur",
    "role",
    "inventaires",
    "last_tirage",
    "historique_tirages_admin",
    "historique_distributions_admin"
]:
    if key not in st.session_state:
        if key in ["inventaires"]:
            st.session_state[key] = {}
        elif key in ["historique_tirages_admin", "historique_distributions_admin"]:
            st.session_state[key] = []
        else:
            st.session_state[key] = None

# ==========================
# FONCTIONS JSON
# ==========================

def charger_json(file, default):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return default

def sauvegarder_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

# Chargement données persistantes
st.session_state.inventaires = charger_json(INVENTAIRE_FILE, {})
st.session_state.historique_tirages_admin = charger_json(HISTORIQUE_TIRAGES_FILE, [])
st.session_state.historique_distributions_admin = charger_json(HISTORIQUE_DISTRIBUTIONS_FILE, [])

# ==========================
# CHARGEMENT CSV
# ==========================

@st.cache_data
def charger_fichier(nom_fichier):
    try:
        df = pd.read_csv(nom_fichier, sep=";", encoding="cp1252", low_memory=False)
    except Exception as e:
        st.error(f"Erreur lecture {nom_fichier} : {e}")
        return pd.DataFrame()

    if len(df.columns) > 8:
        df = df.iloc[:, :8]

    df.columns = ["Nom","Usage","Habitat","Informations","Rarete","Debut","Fin","Proliferation"]

    df["Debut"] = pd.to_numeric(df["Debut"], errors="coerce").fillna(0).astype("Int64")
    df["Fin"] = pd.to_numeric(df["Fin"], errors="coerce").fillna(1000).astype("Int64")
    df["Rarete"] = pd.to_numeric(df["Rarete"], errors="coerce").fillna(0).astype("Int64")

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
# FONCTION TIRAGE
# ==========================

def tirer_plantes(df, nb):
    max_val = int(df["Fin"].max())
    tirage_total = pd.DataFrame()

    for _ in range(nb):
        tirage = random.randint(1, max_val)
        resultat = df[(df["Debut"] <= tirage) & (df["Fin"] >= tirage)]
        tirage_total = pd.concat([tirage_total, resultat], ignore_index=True)

    return tirage_total

# ==========================
# LOGIN
# ==========================

st.title("🌿 Mini-Jeu Botanique Multi-Joueurs")

if st.session_state.joueur is None:

    with st.form("login_form"):
        pseudo = st.text_input("Pseudo")
        mdp = st.text_input("Mot de passe (admin uniquement)", type="password")
        login = st.form_submit_button("Se connecter")
        signup = st.form_submit_button("Créer un compte")

        if login:
            if pseudo in ADMIN_CREDENTIALS and mdp == ADMIN_CREDENTIALS[pseudo]:
                st.session_state.joueur = pseudo
                st.session_state.role = "admin"
                st.success("Connexion administrateur réussie.")
            elif pseudo in st.session_state.inventaires:
                st.session_state.joueur = pseudo
                st.session_state.role = "joueur"
                st.success("Connexion joueur réussie.")
            else:
                st.warning("Pseudo inconnu.")

        if signup:
            if pseudo in st.session_state.inventaires or pseudo in ADMIN_CREDENTIALS:
                st.warning("Pseudo déjà utilisé.")
            else:
                st.session_state.inventaires[pseudo] = {}
                sauvegarder_json(INVENTAIRE_FILE, st.session_state.inventaires)
                st.success("Compte créé.")

else:
    st.write(f"Connecté : {st.session_state.joueur} ({st.session_state.role})")

# ==========================
# INTERFACE JOUEUR
# ==========================

if st.session_state.role == "joueur":

    st.subheader("📦 Votre inventaire")

    inventaire = st.session_state.inventaires.get(st.session_state.joueur, {})

    if inventaire:
        df_inv = pd.DataFrame(list(inventaire.items()), columns=["Plante", "Quantité"])
        st.table(df_inv)
    else:
        st.info("Inventaire vide.")

# ==========================
# INTERFACE ADMIN
# ==========================

elif st.session_state.role == "admin":

    st.subheader("🎲 Tirage des plantes")

    env = st.selectbox("Choisir environnement", list(fichiers.keys()))

    col1, col2, col3 = st.columns(3)

    tirage_effectue = False
    nb_tirage = 0

    with col1:
        if st.button("🎲 Tirer 1"):
            nb_tirage = 1
            tirage_effectue = True

    with col2:
        if st.button("🎲 Tirer 3"):
            nb_tirage = 3
            tirage_effectue = True

    with col3:
        if st.button("🎲 Tirer 5"):
            nb_tirage = 5
            tirage_effectue = True

    if tirage_effectue:
        df = fichiers[env]
        tirage = tirer_plantes(df, nb_tirage)
        st.session_state.last_tirage = tirage

        if not tirage.empty:
            st.write(f"### 🌿 Résultat du tirage ({nb_tirage})")
            st.dataframe(tirage, use_container_width=True)

            for nom in tirage["Nom"].tolist():
                entree = {
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Environnement": env,
                    "Plante": nom
                }
                st.session_state.historique_tirages_admin.append(entree)

            sauvegarder_json(HISTORIQUE_TIRAGES_FILE, st.session_state.historique_tirages_admin)

    # ======================
    # DISTRIBUTION
    # ======================

    if isinstance(st.session_state.last_tirage, pd.DataFrame) and not st.session_state.last_tirage.empty:

        st.subheader("🎁 Distribution")

        joueur = st.selectbox("Choisir joueur", list(st.session_state.inventaires.keys()))
        plante = st.selectbox("Choisir plante", st.session_state.last_tirage["Nom"].tolist())
        quantite = st.number_input("Quantité", 1, 10, 1)

        if st.button("Distribuer"):
            inv = st.session_state.inventaires[joueur]
            inv[plante] = inv.get(plante, 0) + quantite
            sauvegarder_json(INVENTAIRE_FILE, st.session_state.inventaires)

            distribution_entry = {
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Joueur": joueur,
                "Plante": plante,
                "Quantité": quantite
            }

            st.session_state.historique_distributions_admin.append(distribution_entry)
            sauvegarder_json(HISTORIQUE_DISTRIBUTIONS_FILE, st.session_state.historique_distributions_admin)

            st.success("Distribution effectuée.")

    # ======================
    # HISTORIQUES
    # ======================

    st.subheader("📜 Historique des tirages")

    if st.session_state.historique_tirages_admin:
        st.dataframe(pd.DataFrame(st.session_state.historique_tirages_admin))
        if st.button("Effacer historique tirages"):
            st.session_state.historique_tirages_admin = []
            sauvegarder_json(HISTORIQUE_TIRAGES_FILE, [])
            st.success("Historique tirages effacé.")

    st.subheader("📦 Journal des distributions")

    if st.session_state.historique_distributions_admin:
        st.dataframe(pd.DataFrame(st.session_state.historique_distributions_admin))
        if st.button("Effacer journal distributions"):
            st.session_state.historique_distributions_admin = []
            sauvegarder_json(HISTORIQUE_DISTRIBUTIONS_FILE, [])
            st.success("Journal distributions effacé.")

    # ======================
    # STATISTIQUES
    # ======================

    st.subheader("📊 Statistiques")

    if st.session_state.historique_tirages_admin:
        df_stats = pd.DataFrame(st.session_state.historique_tirages_admin)
        st.write("Tirages par environnement")
        st.bar_chart(df_stats["Environnement"].value_counts())

    if st.session_state.historique_distributions_admin:
        df_stats_dist = pd.DataFrame(st.session_state.historique_distributions_admin)
        st.write("Distributions par joueur")
        st.bar_chart(df_stats_dist["Joueur"].value_counts())
