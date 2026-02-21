# multi_player_botaniquerdd.py

import streamlit as st
import pandas as pd
import random
import json
import os

# ----------- Session State -----------
if "joueur" not in st.session_state:
    st.session_state.joueur = None

if "inventaires" not in st.session_state:
    st.session_state.inventaires = {}

if "historique" not in st.session_state:
    st.session_state.historique = {}

if "compteur" not in st.session_state:
    st.session_state.compteur = 0

# ----------- Chargement des fichiers -----------
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

# ----------- Chargement CSV -----------
fichiers = {
    "Collines": charger_fichier("Collines.csv"),
    "Forêts": charger_fichier("Forets.csv"),
    "Plaines": charger_fichier("Plaines.csv"),
    "Montagnes": charger_fichier("Montagnes.csv"),
    "Marais": charger_fichier("Marais.csv"),
    "Sous-sols": charger_fichier("Sous-sols.csv"),
}

# ----------- Utilitaires -----------

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

# ----------- Gestion JSON pour inventaire persistant -----------

INVENTAIRE_FILE = "inventaires.json"

def charger_inventaires():
    if os.path.exists(INVENTAIRE_FILE):
        with open(INVENTAIRE_FILE, "r") as f:
            st.session_state.inventaires = json.load(f)
    else:
        st.session_state.inventaires = {}

def sauvegarder_inventaires():
    with open(INVENTAIRE_FILE, "w") as f:
        json.dump(st.session_state.inventaires, f)

# ----------- Connexion joueur -----------
st.title("🌱 Mini-Jeu de Plantes Multi-joueurs")

charger_inventaires()

if st.session_state.joueur is None:
    pseudo = st.text_input("Entrez votre pseudo :")
    if st.button("Se connecter"):
        st.session_state.joueur = pseudo
        if pseudo not in st.session_state.inventaires:
            st.session_state.inventaires[pseudo] = {}
        if pseudo not in st.session_state.historique:
            st.session_state.historique[pseudo] = []
        st.experimental_rerun()
else:
    st.write(f"🎮 Connecté en tant que : **{st.session_state.joueur}**")

# ----------- Tirage et distribution -----------

def tirer_plantes(df, nb, env):
    habitat_emoji, habitat_color = get_habitat_color_emoji(env)
    resultat_html = ""
    max_val = int(df["Fin"].max())

    for _ in range(nb):
        tirage = random.randint(1, max_val)
        tirage_result = df[(df["Debut"] <= tirage) & (df["Fin"] >= tirage)]
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

    return resultat_html, tirage_result

# ----------- Interface tirages -----------

env = st.selectbox("Choisissez un environnement :", list(fichiers.keys()))
df = fichiers.get(env)

col1, col2, col3 = st.columns(3)
nb_plantes = 0
tirage_result = pd.DataFrame()

if col1.button("Tirer 1 plante"):
    nb_plantes = 1
if col2.button("Tirer 3 plantes"):
    nb_plantes = 3
if col3.button("Tirer 5 plantes"):
    nb_plantes = 5

if nb_plantes > 0 and not df.empty:
    resultat_html, tirage_result = tirer_plantes(df, nb_plantes, env)
    st.markdown(resultat_html, unsafe_allow_html=True)
    st.session_state.last_tirage = tirage_result  # dernier tirage pour distribution

# ----------- Distribution admin -----------

st.divider()
st.subheader("🧑‍🌾 Distribution manuelle")

joueurs = list(st.session_state.inventaires.keys())
if joueurs and "last_tirage" in st.session_state:
    joueur_choisi = st.selectbox("À quel joueur donner la plante ?", joueurs)
    plantes_disponibles = st.session_state.last_tirage["Nom"].tolist()
    plante_choisie = st.selectbox("Plante à distribuer", plantes_disponibles)

    if st.button("Distribuer"):
        inventaire = st.session_state.inventaires[joueur_choisi]
        inventaire[plante_choisie] = inventaire.get(plante_choisie, 0) + 1
        st.session_state.historique[joueur_choisi].append(plante_choisie)
        sauvegarder_inventaires()
        st.success(f"{plante_choisie} donnée à {joueur_choisi} !")

# ----------- Historique et inventaire -----------

st.divider()
st.subheader(f"📜 Historique et inventaire de {st.session_state.joueur}")

# Inventaire
inventaire = st.session_state.inventaires[st.session_state.joueur]
if inventaire:
    st.table(pd.DataFrame(list(inventaire.items()), columns=["Plante", "Quantité"]))

# Historique
hist = st.session_state.historique[st.session_state.joueur]
if hist:
    with st.expander("📂 Historique des plantes reçues"):
        for p in hist:
            st.markdown(f"- {p}")

# Boutons gestion
colA, colB = st.columns(2)
if colA.button("🗑️ Vider inventaire et historique"):
    st.session_state.inventaires[st.session_state.joueur] = {}
    st.session_state.historique[st.session_state.joueur] = []
    sauvegarder_inventaires()
    st.experimental_rerun()

if colB.button("📥 Télécharger inventaire CSV"):
    df_inv = pd.DataFrame(list(st.session_state.inventaires[st.session_state.joueur].items()),
                          columns=["Plante", "Quantité"])
    st.download_button(
        "Télécharger",
        df_inv.to_csv(index=False, sep=";"),
        file_name=f"inventaire_{st.session_state.joueur}.csv",
        mime="text/csv"
    )
