import streamlit as st
import pandas as pd
import random
import json
import os
import hashlib
import time
from datetime import datetime

# ==========================
# CONFIGURATION
# ==========================
INVENTAIRE_FILE = "inventaires.json"
HISTORIQUE_TIRAGES_FILE = "historique_tirages.json"
JOURNAL_FILE = "journal_usages.json"

ADMIN_USER = "admin"
ADMIN_HASH = "3a5763614660da0211b90045a806e2105a528a06a4dc9694299484092dd74d3e"  # SHA256

# ==========================
# FLAG RERUN
# ==========================
if "need_rerun" not in st.session_state:
    st.session_state.need_rerun = False

if st.session_state.need_rerun:
    st.session_state.need_rerun = False
    st.experimental_rerun()

# ==========================
# SESSION INIT
# ==========================
for key in ["joueur","role","inventaires","last_tirage",
            "historique_tirages_admin","journal_usages","last_refresh"]:
    if key not in st.session_state:
        if key in ["inventaires","journal_usages"]:
            st.session_state[key] = {}
        elif "historique" in key:
            st.session_state[key] = []
        elif key=="last_refresh":
            st.session_state[key] = time.time()
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
st.session_state.journal_usages = charger_json(JOURNAL_FILE,{})

# ==========================
# LOAD CSV
# ==========================
@st.cache_data
def charger_fichier(nom):
    try:
        df = pd.read_csv(nom, sep=";", encoding="utf-8-sig", low_memory=False)
    except:
        return pd.DataFrame()
    df = df.iloc[:, :8]
    df.columns = ["Nom","Usage","Habitat","Informations","Rarete","Debut","Fin","Proliferation"]
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
    if df.empty: return pd.DataFrame()
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
        mdp = st.text_input("Mot de passe", type="password")
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
if st.session_state.role=="joueur":
    joueur = st.session_state.joueur
    inventaire = st.session_state.inventaires.get(joueur, {})

    # Rafraîchissement auto toutes les 5s
    if time.time()-st.session_state.last_refresh>5:
        st.session_state.inventaires[joueur] = charger_json(INVENTAIRE_FILE,{}).get(joueur,{})
        st.session_state.last_refresh = time.time()
        st.session_state.need_rerun=True

    tabs_joueur = st.tabs(["📦 Inventaire","📜 Journal"])

    # --------------------
    # INVENTAIRE
    # --------------------
    with tabs_joueur[0]:
        st.subheader("📦 Mon Inventaire")
        if inventaire:
            data_inv=[]
            for plante, qt in inventaire.items():
                type_plante="Inconnu"
                for df in fichiers.values():
                    res=df[df["Nom"]==plante]
                    if not res.empty:
                        type_plante=res.iloc[0]["Usage"]
                        break
                usage_lower = type_plante.lower()
                if any(m in usage_lower for m in ["soin","médic","guér","curatif"]): icone="❤️"
                elif any(m in usage_lower for m in ["tox","poison"]): icone="☠️"
                elif "aliment" in usage_lower: icone="🍽️"
                elif "arom" in usage_lower: icone="🌿"
                elif "mag" in usage_lower: icone="✨"
                elif "champignon" in usage_lower: icone="🍄"
                elif "bois" in usage_lower or "résine" in usage_lower: icone="🪵"
                else: icone="🌱"
                data_inv.append({"Plante": f"{icone} {plante}","Type":type_plante,"Quantité":qt})
            st.dataframe(pd.DataFrame(data_inv), use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("🌿 Utiliser une plante")
            plante_select=st.selectbox("Choisir une plante", list(inventaire.keys()))
            max_qt=inventaire[plante_select]
            quantite_utilisee=st.number_input("Quantité à utiliser", min_value=1, max_value=max_qt, value=1)

            if st.button("Utiliser"):
                # Message narratif
                type_plante_lower = type_plante.lower()
                if any(m in type_plante_lower for m in ["soin","médic","guér","curatif"]):
                    message = f"❤️ {plante_select} utilisée pour ses vertus médicinales."
                elif any(m in type_plante_lower for m in ["tox","poison"]):
                    message = f"☠️ {plante_select} manipulée avec prudence (toxique)."
                elif "aliment" in type_plante_lower:
                    message = f"🍽️ {plante_select} consommée."
                elif "arom" in type_plante_lower:
                    message = f"🌿 {plante_select} utilisée pour son arôme."
                elif "mag" in type_plante_lower:
                    message = f"✨ {plante_select} intégrée à un rituel."
                elif "champignon" in type_plante_lower:
                    message = f"🍄 {plante_select} transformée pour usage spécial."
                elif "bois" in type_plante_lower or "résine" in type_plante_lower:
                    message = f"🪵 {plante_select} transformée pour un usage matériel."
                else:
                    message = f"🌱 {plante_select} utilisée."
                st.info(message)

                # Retirer plante
                inventaire[plante_select]-=quantite_utilisee
                if inventaire[plante_select]<=0:
                    del inventaire[plante_select]
                st.session_state.inventaires[joueur]=inventaire
                sauvegarder_json(INVENTAIRE_FILE, st.session_state.inventaires)

                # Journal
                if joueur not in st.session_state.journal_usages:
                    st.session_state.journal_usages[joueur]=[]
                st.session_state.journal_usages[joueur].append({
                    "Date":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Plante":plante_select,
                    "Quantité":quantite_utilisee,
                    "Effet":message
                })
                sauvegarder_json(JOURNAL_FILE, st.session_state.journal_usages)
                st.session_state.need_rerun=True

        else:
            st.info("Inventaire vide.")

    # --------------------
    # JOURNAL
    # --------------------
    with tabs_joueur[1]:
        st.subheader("📜 Journal personnel")
        journal = st.session_state.journal_usages.get(joueur, [])
        if journal:
            st.dataframe(pd.DataFrame(journal), use_container_width=True, hide_index=True)
            if st.button("🗑️ Effacer mon journal"):
                st.session_state.journal_usages[joueur]=[]
                sauvegarder_json(JOURNAL_FILE, st.session_state.journal_usages)
                st.session_state.need_rerun=True
        else:
            st.info("Aucune utilisation enregistrée.")

# ==========================
# INTERFACE ADMIN
# ==========================
elif st.session_state.role=="admin":
    tabs = st.tabs(["🎮 Gestion","📜 Historique"])
    with tabs[0]:
        col_left,col_right = st.columns(2)
        with col_left:
            st.subheader("🎲 Tirage")
            env = st.selectbox("Environnement", list(fichiers.keys()))
            c1,c2,c3 = st.columns(3)
            nb=0
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
<p><b>Usage :</b> {row['Usage']}</p>
<p><b>Habitat :</b> {row['Habitat']}</p>
<p><b>Rareté :</b> {row['Rarete']}</p>
<p><b>Prolifération :</b> {row['Proliferation']}</p>
<p><b>Infos :</b><br>{row['Informations']}</p>
</div>
""", unsafe_allow_html=True)
                    st.session_state.historique_tirages_admin.append({
                        "Date":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Env":env,
                        "Plante":row["Nom"]
                    })
                sauvegarder_json(HISTORIQUE_TIRAGES_FILE, st.session_state.historique_tirages_admin)
        with col_right:
            st.subheader("🎁 Distribution")
            if isinstance(st.session_state.last_tirage,pd.DataFrame) and not st.session_state.last_tirage.empty:
                joueur = st.selectbox("Joueur", list(st.session_state.inventaires.keys()))
                plante = st.selectbox("Plante", st.session_state.last_tirage["Nom"].tolist())
                qte = st.number_input("Quantité",1,10,1)
                if st.button("Distribuer"):
                    inv = st.session_state.inventaires[joueur]
                    inv[plante] = inv.get(plante,0)+qte
                    st.session_state.inventaires[joueur] = inv
                    sauvegarder_json(INVENTAIRE_FILE, st.session_state.inventaires)
                    st.success("Distribution effectuée")
                    st.session_state.need_rerun=True
    with tabs[1]:
        st.subheader("📜 Historique des tirages")
        if st.session_state.historique_tirages_admin:
            st.dataframe(pd.DataFrame(st.session_state.historique_tirages_admin), use_container_width=True)
        else:
            st.info("Aucun tirage enregistré.")
