# streamlit_app.py

import streamlit as st
import pandas as pd
import random

# ----------- Session State -----------
if "historique" not in st.session_state:
    st.session_state.historique = {}

if "compteur" not in st.session_state:
    st.session_state.compteur = 0

# ----------- Chargement des fichiers -----------
@st.cache_data
def charger_fichier(nom_fichier):
    try:
        df = pd.read_csv(nom_fichier, sep=";", encoding="cp1252")
    except Exception as e:
        st.error(f"Erreur lecture {nom_fichier} : {e}")
        return pd.DataFrame()

    if len(df.columns) > 8:
        df = df.iloc[:, :8]

    df.columns = [
        "Nom","Usage","Habitat","Informations",
        "Rarete","Debut","Fin","Proliferation"
    ]

    df["Debut"] = pd.to_numeric(df["Debut"], errors="coerce").fillna(0).astype("Int64")
    df["Fin"] = pd.to_numeric(df["Fin"], errors="coerce").fillna(1000).astype("Int64")
    df["Rarete"] = pd.to_numeric(df["Rarete"], errors="coerce").fillna(0).astype("Int64")

    return df

# ----------- Données -----------
fichiers = {
    "Collines": charger_fichier("Collines.csv"),
    "Forêts": charger_fichier("Forets.csv"),
    "Plaines": charger_fichier("Plaines.csv"),
    "Montagnes": charger_fichier("Montagnes.csv"),
    "Marais": charger_fichier("Marais.csv"),
    "Sous-sols": charger_fichier("Sous-sols.csv"),
}

# ----------- Fonctions -----------
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

    # Sauvegarde historique
    if env not in st.session_state.historique:
        st.session_state.historique[env] = []

    st.session_state.historique[env].append(resultat_html)
    st.session_state.compteur += nb

    return resultat_html

# ----------- Interface -----------
st.title("🌱 Mini-Jeu de Plantes")

env = st.selectbox("Choisissez un environnement :", list(fichiers.keys()))

col1, col2, col3 = st.columns(3)

if col1.button("Tirer 1 plante"):
    df = fichiers.get(env)
    if not df.empty:
        st.markdown(tirer_plantes(df, 1, env), unsafe_allow_html=True)

if col2.button("Tirer 3 plantes"):
    df = fichiers.get(env)
    if not df.empty:
        st.markdown(tirer_plantes(df, 3, env), unsafe_allow_html=True)

if col3.button("Tirer 5 plantes"):
    df = fichiers.get(env)
    if not df.empty:
        st.markdown(tirer_plantes(df, 5, env), unsafe_allow_html=True)

# ----------- Historique -----------
st.divider()
st.subheader("📜 Historique des tirages")

st.write(f"Total de plantes tirées : **{st.session_state.compteur}**")

if st.session_state.historique:

    for environnement, tirages in st.session_state.historique.items():
        with st.expander(f"🌍 {environnement} ({len(tirages)} tirages)"):
            for element in tirages:
                st.markdown(element, unsafe_allow_html=True)

colA, colB = st.columns(2)

if colA.button("🗑️ Vider l'historique"):
    st.session_state.historique = {}
    st.session_state.compteur = 0
    st.rerun()

if colB.button("📥 Télécharger l'historique"):
    historique_txt = ""
    for env, tirages in st.session_state.historique.items():
        historique_txt += f"\n=== {env} ===\n"
        for t in tirages:
            historique_txt += t + "\n"

    st.download_button(
        "Télécharger en HTML",
        historique_txt,
        file_name="historique_plantes.html",
        mime="text/html"
    )
