# sauvegarder ce fichier comme app.py
import streamlit as st
import pandas as pd
import chardet 
import random

# ----------- Chargement des fichiers -----------
@st.cache_data
def charger_fichier(nom_fichier):
      try:
        # Lire en latin1 pour récupérer les caractères spéciaux
        df = pd.read_csv(nom_fichier, sep=";", encoding="latin1", low_memory=False)
        
        # Réencoder toutes les colonnes texte en UTF-8
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].apply(lambda x: str(x).encode('latin1').decode('utf-8', errors='replace'))

    except FileNotFoundError:
        st.warning(f"⚠ Fichier {nom_fichier} introuvable.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur lors de la lecture de {nom_fichier} : {e}")
        return pd.DataFrame()

    # Limiter à 8 colonnes et renommer
    if len(df.columns) > 8:
        df = df.iloc[:, :8]
    df.columns = ["Nom","Usage","Habitat","Informations","Rarete","Debut","Fin","Proliferation"]

    # Conversion des colonnes numériques
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
        "Collines": ("⛰️", "#C8FFC8"),   # pastel vert clair
        "Forêts": ("🌳", "#B4FFB4"),
        "Plaines": ("🌾", "#FFFFC8"),    # pastel jaune
        "Montagnes": ("🏔️", "#DCDCDC"),  # gris clair
        "Marais": ("🐸", "#B4FFFF"),      # pastel bleu/vert
        "Sous-sols": ("🕳️", "#C8C8C8"),  # gris clair
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

                # Carte HTML
                texte_html = f"""
                <div style="
                    background-color:{habitat_color};
                    border:2px solid #888;
                    border-radius:10px;
                    padding:10px;
                    margin-bottom:10px;
                ">
                    <p style="color:{rarete_color}; font-weight:bold; font-size:16px;">{stars} {emoji_usage} {habitat_emoji} Nom : {ligne['Nom']}</p>
                    <p>Usage : {ligne['Usage']}</p>
                    <p>Infos : {ligne['Informations']}</p>
                    <p>Prolifération : {ligne['Proliferation']}</p>
                </div>
                """
                resultat_html += texte_html
    return resultat_html

# ----------- Interface Streamlit -----------
st.title("Mini-Jeu de Plantes 🌱")

env = st.selectbox("Choisissez un environnement :", list(fichiers.keys()))

col1, col2, col3 = st.columns(3)
if col1.button("Tirer 1 plante"):
    df = fichiers.get(env)
    if df is not None and not df.empty:
        st.markdown(tirer_plantes(df, 1, env), unsafe_allow_html=True)
if col2.button("Tirer 3 plantes"):
    df = fichiers.get(env)
    if df is not None and not df.empty:
        st.markdown(tirer_plantes(df, 3, env), unsafe_allow_html=True)
if col3.button("Tirer 5 plantes"):
    df = fichiers.get(env)
    if df is not None and not df.empty:
        st.markdown(tirer_plantes(df, 5, env), unsafe_allow_html=True)
