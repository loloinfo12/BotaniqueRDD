import streamlit as st
import pandas as pd
import random
import hashlib
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from supabase import create_client, Client

# ==========================
# CONFIGURATION
# ==========================
ADMIN_USER = "admin"
ADMIN_HASH = "3a5763614660da0211b90045a806e2105a528a06a4dc9694299484092dd74d3e"  # SHA256 mot de passe admin

# ==========================
# SUPABASE CLIENT
# ==========================
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase()

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
for key in ["joueur", "role", "last_tirage"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ==========================
# SUPABASE UTILS
# ==========================
def ajouter_joueur(pseudo, role="joueur", mdp_hash=""):
    supabase.table("joueurs").upsert({
        "pseudo": pseudo, "role": role, "password_hash": mdp_hash
    }).execute()

def verifier_login(pseudo, mdp_hash):
    res = supabase.table("joueurs").select("role").eq("pseudo", pseudo).eq("password_hash", mdp_hash).execute()
    if res.data:
        return res.data[0]["role"]
    return None

def get_inventaire(pseudo):
    res = supabase.table("inventaires").select("plante, quantite").eq("pseudo", pseudo).execute()
    return {row["plante"]: row["quantite"] for row in res.data}

def ajouter_au_inventaire(pseudo, plante, quantite):
    res = supabase.table("inventaires").select("quantite").eq("pseudo", pseudo).eq("plante", plante).execute()
    if res.data:
        nouvelle_qt = res.data[0]["quantite"] + quantite
        supabase.table("inventaires").update({"quantite": nouvelle_qt}).eq("pseudo", pseudo).eq("plante", plante).execute()
    else:
        supabase.table("inventaires").insert({"pseudo": pseudo, "plante": plante, "quantite": quantite}).execute()

def retirer_de_inventaire(pseudo, plante, quantite):
    res = supabase.table("inventaires").select("quantite").eq("pseudo", pseudo).eq("plante", plante).execute()
    if res.data:
        nouvelle_qt = res.data[0]["quantite"] - quantite
        if nouvelle_qt <= 0:
            supabase.table("inventaires").delete().eq("pseudo", pseudo).eq("plante", plante).execute()
        else:
            supabase.table("inventaires").update({"quantite": nouvelle_qt}).eq("pseudo", pseudo).eq("plante", plante).execute()

def ajouter_journal(pseudo, plante, quantite, effet):
    supabase.table("journal_usages").insert({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pseudo": pseudo,
        "plante": plante,
        "quantite": quantite,
        "effet": effet
    }).execute()

def ajouter_historique_tirage(env, plante):
    supabase.table("historique_tirages").insert({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "env": env,
        "plante": plante
    }).execute()

def ajouter_historique_distribution(pseudo, plante, quantite):
    supabase.table("historique_distributions").insert({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pseudo": pseudo,
        "plante": plante,
        "quantite": quantite
    }).execute()

def get_journal(pseudo):
    res = supabase.table("journal_usages").select("date, plante, quantite, effet").eq("pseudo", pseudo).order("date", desc=True).execute()
    return [{"Date": r["date"], "Plante": r["plante"], "Quantité": r["quantite"], "Effet": r["effet"]} for r in res.data]

def get_historique_tirages():
    res = supabase.table("historique_tirages").select("date, env, plante").order("date", desc=True).execute()
    return [(r["date"], r["env"], r["plante"]) for r in res.data]

def get_joueurs():
    res = supabase.table("joueurs").select("pseudo").eq("role", "joueur").execute()
    return [r["pseudo"] for r in res.data]

def supprimer_joueur(pseudo):
    supabase.table("inventaires").delete().eq("pseudo", pseudo).execute()
    supabase.table("journal_usages").delete().eq("pseudo", pseudo).execute()
    supabase.table("historique_distributions").delete().eq("pseudo", pseudo).execute()
    supabase.table("joueurs").delete().eq("pseudo", pseudo).execute()

# ==========================
# LOAD CSV
# ==========================
@st.cache_data
def charger_fichier(nom):
    try:
        df = pd.read_csv(nom, sep=";", encoding="cp1252", low_memory=False)
    except:
        return {"table": [], "df": pd.DataFrame(), "lookup": {}}

    df = df.iloc[:, :8].copy()
    df.columns = ["Nom", "Usage", "Habitat", "Informations", "Rarete", "Debut", "Fin", "Proliferation"]
    
    # Remplacement des ?? par '
    df = df.apply(lambda col: col.str.replace("??", "'", regex=False) if col.dtype == "object" else col)

    df["Debut"] = pd.to_numeric(df["Debut"], errors="coerce").fillna(0).astype(int)
    df["Fin"] = pd.to_numeric(df["Fin"], errors="coerce").fillna(1000).astype(int)
    df["Rarete"] = pd.to_numeric(df["Rarete"], errors="coerce").fillna(0)

    max_val = int(df["Fin"].max())
    table = [None] * (max_val + 1)
    for _, row in df.iterrows():
        for i in range(row["Debut"], row["Fin"] + 1):
            table[i] = row
    lookup = {row["Nom"]: row for _, row in df.iterrows()}
    return {"table": table, "df": df, "lookup": lookup}

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
def tirer_plantes(data, nb):
    table = data["table"]
    if not table:
        return pd.DataFrame()
    tirages = []
    max_val = len(table) - 1
    while len(tirages) < nb:
        val = random.randint(1, max_val)
        plante = table[val]
        if plante is not None:
            tirages.append(plante)
    return pd.DataFrame(tirages)

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
            else:
                role = verifier_login(pseudo, hash_input)
                if role:
                    st.session_state.joueur = pseudo
                    st.session_state.role = role
                else:
                    st.warning("Identifiants invalides")

        if signup:
            hash_input = hashlib.sha256(mdp.encode()).hexdigest()
            ajouter_joueur(pseudo, role="joueur", mdp_hash=hash_input)
            st.success("Compte créé ! Vous pouvez maintenant vous connecter.")

# ==========================
# INTERFACE JOUEUR
# ==========================
if st.session_state.role == "joueur":
    st_autorefresh(interval=5000, key="raffraichissement_auto")
    joueur = st.session_state.joueur
    inventaire = get_inventaire(joueur)

    tabs_joueur = st.tabs(["📦 Inventaire", "📜 Journal"])

    with tabs_joueur[0]:
        st.subheader("📦 Mon Inventaire")
        if inventaire:
            data_inv = []
            for plante, qt in inventaire.items():
                type_plante = "Inconnu"
                for data in fichiers.values():
                    if plante in data["lookup"]:
                        type_plante = data["lookup"][plante]["Usage"]
                        break
                usage_lower = type_plante.lower()
                if any(m in usage_lower for m in ["soin", "médic", "guér", "curatif"]): icone = "❤️"
                elif any(m in usage_lower for m in ["tox", "poison"]): icone = "☠️"
                elif "aliment" in usage_lower: icone = "🍽️"
                elif "arom" in usage_lower: icone = "🌿"
                elif "mag" in usage_lower: icone = "✨"
                elif "bois" in usage_lower or "résine" in usage_lower: icone = "🪵"
                else: icone = "🌱"
                data_inv.append({"Plante": f"{icone} {plante}", "Type": type_plante, "Quantité": qt})
            st.dataframe(pd.DataFrame(data_inv), use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("🌿 Utiliser une plante")
            plante_select = st.selectbox("Choisir une plante", list(inventaire.keys()))
            plante_info = None
            for data in fichiers.values():
                if plante_select in data["lookup"]:
                    plante_info = data["lookup"][plante_select]
                    break
            if plante_info is not None:
                st.markdown(f"""
**Usage :** {plante_info['Usage']}  
**Habitat :** {plante_info['Habitat']}  
**Rareté :** {plante_info['Rarete']}  
**Prolifération :** {plante_info['Proliferation']}  
**Informations :** {plante_info['Informations']}
""")
            max_qt = inventaire[plante_select]
            quantite_utilisee = st.number_input("Quantité à utiliser", min_value=1, max_value=max_qt, value=1)
            if st.button("Utiliser"):
                usage = plante_info["Usage"].lower()
                if any(m in usage for m in ["soin", "médic", "guér", "curatif"]): message = f"❤️ {plante_select} utilisée pour ses vertus médicinales."
                elif any(m in usage for m in ["tox", "poison"]): message = f"☠️ {plante_select} manipulée avec prudence (toxique)."
                elif "aliment" in usage: message = f"🍽️ {plante_select} consommée."
                elif "arom" in usage: message = f"🌿 {plante_select} utilisée pour son arôme."
                elif "mag" in usage: message = f"✨ {plante_select} intégrée à un rituel."
                elif "bois" in usage or "résine" in usage: message = f"🪵 {plante_select} transformée pour un usage matériel."
                else: message = f"🌱 {plante_select} utilisée."
                st.info(message)
                retirer_de_inventaire(joueur, plante_select, quantite_utilisee)
                ajouter_journal(joueur, plante_select, quantite_utilisee, message)
        else:
            st.info("Votre inventaire est vide. L'administrateur peut vous attribuer des plantes.")

    with tabs_joueur[1]:
        st.subheader("📜 Journal personnel")
        journal = get_journal(joueur)
        if journal:
            st.dataframe(pd.DataFrame(journal), use_container_width=True, hide_index=True)
        else:
            st.info("Aucune utilisation enregistrée.")

# ==========================
# INTERFACE ADMIN
# ==========================
elif st.session_state.role == "admin":
    tab_gestion, tab_attribution, tab_historique, tab_users = st.tabs([
        "🎮 Gestion",
        "🌿 Attribution manuelle",
        "📜 Historique",
        "👥 Utilisateurs"
    ])

    with tab_gestion:
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("🎲 Tirage")
            env = st.selectbox("Environnement", list(fichiers.keys()))
            c1, c2, c3 = st.columns(3)
            nb = 0
            if c1.button("1"): nb = 1
            if c2.button("3"): nb = 3
            if c3.button("5"): nb = 5

            if nb > 0:
                tirage = tirer_plantes(fichiers[env], nb)
                st.session_state.last_tirage = tirage
                for _, row in tirage.iterrows():
                    ajouter_historique_tirage(env, row["Nom"])

            if isinstance(st.session_state.last_tirage, pd.DataFrame) and not st.session_state.last_tirage.empty:
                for _, row in st.session_state.last_tirage.iterrows():
                    type_lower = row["Usage"].lower()
                    row_class = "champignon" if "champignon" in type_lower else "herbe"
                    row_type = "🍄 Champignon" if "champignon" in type_lower else "🌱 Herbe"
                    rarete = row["Rarete"]
                    nb_etoiles = min(max(-int(rarete), 0), 5)
                    etoiles = "⭐" * nb_etoiles
                    st.markdown(f"""
                    <div class="card {row_class}">
                    <h3>{row_type} {row['Nom']}</h3>
                    <p><b>Usage :</b> {row['Usage']}</p>
                    <p><b>Habitat :</b> {row['Habitat']}</p>
                    <p><b>Rareté :</b> {etoiles} ({rarete})</p>
                    <p><b>Prolifération :</b> {row['Proliferation']}</p>
                    <p><b>Informations :</b><br>{row['Informations']}</p>
                    </div>
                    """, unsafe_allow_html=True)

        with col_right:
            st.subheader("🎁 Distribution")
            joueurs = get_joueurs()
            if joueurs and isinstance(st.session_state.last_tirage, pd.DataFrame) and not st.session_state.last_tirage.empty:
                joueur = st.selectbox("Joueur", joueurs)
                plante = st.selectbox("Plante", st.session_state.last_tirage["Nom"].tolist())
                qte = st.number_input("Quantité", 1, 10, 1)
                if st.button("Distribuer"):
                    ajouter_au_inventaire(joueur, plante, qte)
                    ajouter_historique_distribution(joueur, plante, qte)
                    st.success(f"✅ {qte}x {plante} distribué(s) à {joueur}")
            else:
                st.info("Aucun tirage ou aucun joueur disponible.")

    with tab_attribution:
        st.subheader("🌿 Attribution manuelle d'une plante")
        col_left, col_right = st.columns([1, 1])

        with col_left:
            env = st.selectbox("Choisir un environnement", list(fichiers.keys()), key="env_manual")
            if env:
                df_env = fichiers[env]["df"]
                plante = st.selectbox("Choisir une plante", df_env["Nom"].tolist(), key="plante_manual")
                joueurs = get_joueurs()
                if joueurs:
                    joueur = st.selectbox("Choisir un joueur", joueurs, key="joueur_manual")
                    qte = st.number_input("Quantité", 1, 20, 1)
                    if st.button("Attribuer la plante"):
                        ajouter_au_inventaire(joueur, plante, qte)
                        ajouter_historique_distribution(joueur, plante, qte)
                        st.success(f"✅ {qte}x {plante} attribué(s) à {joueur}")
                else:
                    st.warning("Aucun joueur disponible.")

        with col_right:
            if env and plante:
                plante_info = df_env[df_env["Nom"] == plante].iloc[0]
                type_lower = plante_info["Usage"].lower()
                row_class = "champignon" if "champignon" in type_lower else "herbe"
                row_type = "🍄 Champignon" if "champignon" in type_lower else "🌱 Herbe"
                rarete = plante_info["Rarete"]
                nb_etoiles = min(max(-int(rarete), 0), 5)
                etoiles = "⭐" * nb_etoiles
                st.markdown(f"""
                <div class="card {row_class}">
                <h3>{row_type} {plante_info['Nom']}</h3>
                <p><b>Usage :</b> {plante_info['Usage']}</p>
                <p><b>Habitat :</b> {plante_info['Habitat']}</p>
                <p><b>Rareté :</b> {etoiles} ({rarete})</p>
                <p><b>Prolifération :</b> {plante_info['Proliferation']}</p>
                <p><b>Informations :</b><br>{plante_info['Informations']}</p>
                </div>
                """, unsafe_allow_html=True)

    with tab_historique:
        st.subheader("📜 Historique des tirages")
        hist = get_historique_tirages()
        if hist:
            st.dataframe(
                pd.DataFrame(hist, columns=["Date", "Environnement", "Plante"]),
                use_container_width=True
            )
        else:
            st.info("Aucun tirage enregistré.")

    with tab_users:
        st.subheader("👥 Gestion des joueurs")
        joueurs = get_joueurs()

        if joueurs:
            st.subheader("📦 Inventaires des joueurs")
            for j in joueurs:
                inv = get_inventaire(j)
                with st.expander(f"🧑 {j} — {len(inv)} plante(s)"):
                    if inv:
                        st.dataframe(
                            pd.DataFrame([{"Plante": p, "Quantité": q} for p, q in inv.items()]),
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("Inventaire vide.")

            st.divider()
            st.subheader("🗑️ Supprimer un joueur")
            joueur_suppr = st.selectbox("Sélectionner un joueur à supprimer", joueurs)
            confirm = st.checkbox(f"Confirmer la suppression de '{joueur_suppr}'")
            if st.button("Supprimer ce joueur") and confirm:
                supprimer_joueur(joueur_suppr)
                st.success(f"Le joueur '{joueur_suppr}' a été supprimé.")
                st.rerun()
        else:
            st.info("Aucun joueur enregistré.")
