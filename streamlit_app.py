# streamlit_botaniquerdd_final.py

import streamlit as st
import pandas as pd
import random
import json
import os

# ---------------------- Constants ----------------------
INVENTAIRE_FILE = "inventaires.json"
ADMIN_CREDENTIALS = {"admin": "Dreame12"}  # changer le mot de passe

# ---------------------- Session State ----------------------
for key in ["joueur", "role", "inventaires", "historique", "last_tirage"]:
    if key not in st.session_state:
        if key in ["inventaires", "historique"]:
            st.session_state[key] = {}
        else:
            st.session_state[key] = None

# ---------------------- Chargement JSON ----------------------
def charger_inventaires():
    if os.path.exists(INVENTAIRE_FILE):
        with open(INVENTAIRE_FILE, "r") as f:
            data = json.load(f)
            st.session_state.inventaires.update(data)
    else:
        st.session_state.inventaires = {}

def sauvegarder_inventaires():
    with open(INVENTAIRE_FILE, "w") as f:
        json.dump(st.session_state.inventaires, f)

charger_inventaires()

# ---------------------- Chargement CSV ----------------------
@st.cache_data
def charger_fichier(nom_fichier):
    try:
        df = pd.read_csv(nom_fichier, sep=";", encoding="utf-8-sig", low_memory=False)
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

# ---------------------- Fonctions utilitaires ----------------------
def get_color_stars(rarete_val):
    if rarete_val < -6:
        return "red", "★★★"
    elif -5 <= rarete_val <= -3:
        return "orange", "★★"
    else:
        return "green", "★"

def get_habitat_color_emoji(habitat):
    mapping = {
        "Collines": ("⛰️", "#C8FFC8"),
        "Forêts": ("🌳", "#B4FFB4"),
        "Plaines": ("🌾", "#FFFFC8"),
        "Montagnes": ("🏔️", "#DCDCDC"),
        "Marais": ("🐸", "#B4FFFF"),
        "Sous-sols": ("🕳️", "#C8C8C8"),
    }
    return mapping.get(habitat, ("🍀", "#F0F0F0"))

usage_emojis = {
    "alimentation": "🥗",
    "medicinale": "💊",
    "decorative": "🌸",
    "magique": "✨",
    "autre": "🍀"
}

def tirer_plantes(df, nb, env):
    habitat_emoji, habitat_color = get_habitat_color_emoji(env)
    resultat_html = ""
    max_val = int(df["Fin"].max())
    tirage_result_total = pd.DataFrame()

    for _ in range(nb):
        tirage = random.randint(1, max_val)
        tirage_result = df[(df["Debut"] <= tirage) & (df["Fin"] >= tirage)]
        tirage_result_total = pd.concat([tirage_result_total, tirage_result], ignore_index=True)
        resultat_html += f"<p>🎲 Tirage aléatoire : {tirage}</p>"

        if tirage_result.empty:
            resultat_html += "<p>❌ Aucune plante trouvée</p><hr>"
        else:
            for _, ligne in tirage_result.iterrows():
                rarete_color, stars = get_color_stars(ligne["Rarete"])
                usage = str(ligne["Usage"]).lower()
                emoji_usage = usage_emojis.get(usage, usage_emojis["autre"])
                texte_html = f"""
                <div style="
                    background-color:{habitat_color};
                    border:2px solid #888;
                    border-radius:10px;
                    padding:10px;
                    margin-bottom:10px;
                ">
                    <p style="color:{rarete_color}; font-weight:bold; font-size:16px;">
                    {stars} {emoji_usage} {habitat_emoji} Nom : {ligne['Nom']}</p>
                    <p><b>Usage :</b> {ligne['Usage']}</p>
                    <p><b>Infos :</b> {ligne['Informations']}</p>
                    <p><b>Prolifération :</b> {ligne['Proliferation']}</p>
                </div>
                """
                resultat_html += texte_html

    return resultat_html, tirage_result_total

# ---------------------- Login / Inscription ----------------------
st.title("🌱 Mini-Jeu de Plantes Multi-joueurs")

if st.session_state.joueur is None:
    with st.form("login_form"):
        pseudo = st.text_input("Pseudo")
        mdp = st.text_input("Mot de passe (pour admin)", type="password")
        bouton_login = st.form_submit_button("Se connecter")
        bouton_signup = st.form_submit_button("Créer un compte")

        if bouton_login:
            if pseudo in ADMIN_CREDENTIALS and mdp == ADMIN_CREDENTIALS[pseudo]:
                st.session_state.joueur = pseudo
                st.session_state.role = "admin"
                st.success("Connecté en tant qu'administrateur")
            elif pseudo in st.session_state.inventaires:
                st.session_state.joueur = pseudo
                st.session_state.role = "joueur"
                st.success(f"Connecté en tant que joueur : {pseudo}")
            else:
                st.warning("Pseudo non trouvé, veuillez créer un compte")
            
            st.session_state.inventaires.setdefault(st.session_state.joueur, {})
            st.session_state.historique.setdefault(st.session_state.joueur, [])

        if bouton_signup:
            if pseudo in st.session_state.inventaires or pseudo in ADMIN_CREDENTIALS:
                st.warning("Pseudo déjà existant, choisissez-en un autre")
            else:
                st.session_state.joueur = pseudo
                st.session_state.role = "joueur"
                st.session_state.inventaires[pseudo] = {}
                st.session_state.historique[pseudo] = []
                sauvegarder_inventaires()
                st.success(f"Compte créé et connecté en tant que : {pseudo}")

else:
    st.write(f"🎮 Connecté : {st.session_state.joueur} ({st.session_state.role})")

# ---------------------- Interface ----------------------
if st.session_state.joueur:

    # --------- Joueurs uniquement ---------
    if st.session_state.role == "joueur":
        st.subheader("📜 Votre inventaire")
        inventaire = st.session_state.inventaires.get(st.session_state.joueur, {})
        historique = st.session_state.historique.get(st.session_state.joueur, [])
        
        if inventaire:
            st.table(pd.DataFrame(list(inventaire.items()), columns=["Plante", "Quantité"]))
        if historique:
            with st.expander("📂 Historique des plantes reçues"):
                for plante in historique:
                    st.markdown(f"- {plante}")

    # --------- Admin uniquement ---------
    elif st.session_state.role == "admin":
        st.subheader("🧑‍🌾 Administration")
        joueurs = list(st.session_state.inventaires.keys())
        
        # Tirage
        env = st.selectbox("Choisissez un environnement :", list(fichiers.keys()))
        df = fichiers.get(env)
        col1, col2, col3 = st.columns(3)
        nb_plantes = 0
        if col1.button("Tirer 1 plante"):
            nb_plantes = 1
        if col2.button("Tirer 3 plantes"):
            nb_plantes = 3
        if col3.button("Tirer 5 plantes"):
            nb_plantes = 5

        if nb_plantes > 0 and not df.empty:
            resultat_html, tirage_result = tirer_plantes(df, nb_plantes, env)
            st.markdown(resultat_html, unsafe_allow_html=True)
            st.session_state.last_tirage = tirage_result

        # Distribution sécurisée
        if ("last_tirage" in st.session_state and
            st.session_state.last_tirage is not None and
            not st.session_state.last_tirage.empty and
            "Nom" in st.session_state.last_tirage.columns):

            joueur_choisi = st.selectbox("Attribuer à quel joueur ?", joueurs)
            plantes_disponibles = st.session_state.last_tirage["Nom"].tolist()
            plante_choisie = st.selectbox("Plante à distribuer", plantes_disponibles)
            quantite = st.number_input("Quantité à donner", min_value=1, max_value=10, value=1)
            
            if st.button("Distribuer"):
                st.session_state.inventaires.setdefault(joueur_choisi, {})
                st.session_state.historique.setdefault(joueur_choisi, [])
                inventaire = st.session_state.inventaires[joueur_choisi]
                inventaire[plante_choisie] = inventaire.get(plante_choisie, 0) + quantite
                st.session_state.historique[joueur_choisi].extend([plante_choisie]*quantite)
                sauvegarder_inventaires()
                st.success(f"{quantite}x {plante_choisie} donnée(s) à {joueur_choisi} !")
        else:
            st.info("Aucun tirage disponible. Tirer des plantes pour pouvoir les distribuer.")
