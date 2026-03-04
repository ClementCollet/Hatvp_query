import streamlit as st
import pandas as pd
import unicodedata
import gzip
import json
import io
import zipfile
import requests
import tempfile
import os
from pathlib import Path

# ─── CONFIG PAGE ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="HATVP Explorer",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
}

/* Fond général */
.stApp {
    background-color: #0e1117;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #131720;
    border-right: 1px solid #1e2535;
}

/* Titres */
h1 { 
    font-family: 'Syne', sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -1px !important;
}
h2, h3 {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
}

/* Cards doc */
.doc-card {
    background: linear-gradient(135deg, #131720 0%, #1a2035 100%);
    border: 1px solid #2a3550;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 14px;
}
.doc-card h4 {
    color: #e8c97a;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 15px;
    margin: 0 0 8px 0;
}
.doc-card p {
    color: #8899bb;
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    margin: 0;
    line-height: 1.6;
}
.doc-card code {
    background: #0e1117;
    color: #7dd3fc;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 12px;
}

/* Mode badge */
.mode-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    font-weight: 500;
    margin-bottom: 8px;
}
.mode-objets {
    background: #1e3a5f;
    color: #7dd3fc;
    border: 1px solid #2563eb55;
}
.mode-secteurs {
    background: #2d1f4e;
    color: #c4b5fd;
    border: 1px solid #7c3aed55;
}

/* Stat boxes */
.stat-row {
    display: flex;
    gap: 12px;
    margin: 16px 0;
}
.stat-box {
    flex: 1;
    background: #131720;
    border: 1px solid #1e2535;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
}
.stat-number {
    font-family: 'Syne', sans-serif;
    font-size: 28px;
    font-weight: 800;
    color: #e8c97a;
    line-height: 1;
}
.stat-label {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: #556688;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Résultat aperçu */
.result-header {
    background: linear-gradient(90deg, #1e3a5f, #131720);
    border: 1px solid #2563eb44;
    border-radius: 10px;
    padding: 16px 20px;
    margin: 16px 0;
    display: flex;
    align-items: center;
    gap: 12px;
}

/* Secteur pill */
.sector-pill {
    display: inline-block;
    background: #1a2035;
    border: 1px solid #2a3550;
    border-radius: 20px;
    padding: 5px 14px;
    margin: 4px;
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    color: #93b4d8;
    cursor: pointer;
}
.sector-pill:hover {
    border-color: #e8c97a;
    color: #e8c97a;
}

/* Override Streamlit buttons */
.stButton > button {
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    padding: 12px 28px !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #2563eb, #3b82f6) !important;
    box-shadow: 0 4px 20px #2563eb44 !important;
}

/* Download button */
.stDownloadButton > button {
    background: linear-gradient(135deg, #065f46, #047857) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
}

/* Inputs */
.stTextInput > div > div > input {
    background: #131720 !important;
    border: 1px solid #2a3550 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-family: 'DM Mono', monospace !important;
}
.stSelectbox > div > div {
    background: #131720 !important;
    border: 1px solid #2a3550 !important;
    border-radius: 8px !important;
}
.stMultiSelect > div > div {
    background: #131720 !important;
    border: 1px solid #2a3550 !important;
}

/* Divider */
hr { border-color: #1e2535 !important; }

/* Warning / info */
.stAlert {
    border-radius: 10px !important;
}

/* Checkbox */
.stCheckbox > label {
    font-family: 'DM Mono', monospace !important;
    color: #8899bb !important;
}
</style>
""", unsafe_allow_html=True)

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

CACHE_DIR = Path(tempfile.gettempdir()) / "hatvp_cache"
ZIP_URL   = "https://www.hatvp.fr/agora/opendata/csv/Vues_Separees_CSV.zip"

COL_SECTEUR      = "secteur_activite"
COL_OBJET        = "objet_activite"
COL_REP_ID       = "representants_id"
COL_DENOMINATION = "denomination"
COL_EXO_ID       = "exercices_id"

# ─── UTILITAIRES ──────────────────────────────────────────────────────────────

def normalize_cols(df):
    df.columns = [c.strip().lower().replace(" ", "_").strip('"').strip("'") for c in df.columns]
    return df

def read_csv_bytes(raw_bytes):
    if raw_bytes[:2] == b"\x1f\x8b":
        with gzip.open(io.BytesIO(raw_bytes)) as f:
            raw_bytes = f.read()
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            text = raw_bytes.decode(enc); break
        except UnicodeDecodeError:
            continue
    else:
        text = raw_bytes.decode("latin-1", errors="replace")
    first_line = text.split("\n")[0]
    sep = ";" if first_line.count(";") >= first_line.count(",") else ","
    for s in [sep, ("," if sep == ";" else ";")]:
        try:
            df = pd.read_csv(io.StringIO(text), sep=s, low_memory=False, on_bad_lines="skip")
            if len(df.columns) > 1:
                return normalize_cols(df)
        except Exception:
            continue
    raise ValueError("Impossible de parser le CSV.")

def strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")

def normalize(text):
    return strip_accents(str(text).lower())

def generate_variants(keyword):
    kw = keyword.strip()
    variants = set()
    forms = {kw, kw.lower(), kw.capitalize(),
             strip_accents(kw), strip_accents(kw).lower(), strip_accents(kw).capitalize()}
    for f in forms:
        variants.add(f)
        if len(f) > 6: variants.add(f[:-1])
        if len(f) > 7: variants.add(f[:-2])
    for v in list(variants):
        s = v
        for src, dst in [("é","e"),("è","e"),("ê","e"),("ë","e"),("à","a"),
                         ("â","a"),("î","i"),("ô","o"),("û","u"),("ù","u"),("ç","c")]:
            s = s.replace(src, dst)
        variants.add(s)
    return sorted(variants, key=lambda x: -len(x))

# ─── CHARGEMENT DES DONNÉES ───────────────────────────────────────────────────

@st.cache_data(show_spinner=False, ttl=3600*12)  # Cache 12h
def load_all_tables():
    """Télécharge le ZIP HATVP et extrait les 4 tables. Mis en cache 12h."""
    CACHE_DIR.mkdir(exist_ok=True)
    zip_cache = CACHE_DIR / "vues_separees.zip"

    if not zip_cache.exists():
        resp = requests.get(ZIP_URL, stream=True, timeout=300)
        resp.raise_for_status()
        with open(zip_cache, "wb") as f:
            for chunk in resp.iter_content(65536):
                f.write(chunk)

    zip_bytes = zip_cache.read_bytes()
    targets = {
        "secteurs":   "9_secteurs_activites.csv",
        "infos":      "1_informations_generales.csv",
        "objets":     "8_objets_activites.csv",
        "exercices":  "15_exercices.csv",
    }
    tables = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = z.namelist()
        for key, fname in targets.items():
            match = next((n for n in names if n.endswith(fname)), None)
            if match:
                tables[key] = read_csv_bytes(z.read(match))
    return tables

# ─── LOGIQUE MÉTIER ───────────────────────────────────────────────────────────

def search_secteurs(keyword, df_secteurs):
    variants  = generate_variants(keyword)
    results   = {}
    for variant in variants:
        v_norm = normalize(variant)
        mask   = df_secteurs[COL_SECTEUR].dropna().apply(lambda s: v_norm in normalize(s))
        matched = df_secteurs.loc[mask.index[mask], COL_SECTEUR].unique().tolist()
        if matched:
            results[variant] = sorted(set(matched))
    # Dédupliquer
    seen, groups = {}, []
    for v, secs in results.items():
        key = frozenset(secs)
        if key not in seen:
            seen[key] = v
            groups.append((v, secs))
    return groups

def search_objets(keyword, df_objets):
    kw_norms = list(set(normalize(v) for v in generate_variants(keyword)))
    mask = df_objets[COL_OBJET].dropna().apply(
        lambda s: any(kw in normalize(s) for kw in kw_norms))
    return df_objets.loc[mask.index[mask]]

def build_export(ids_retenus, df_infos, df_match, col_extra, col_extra_name):
    df_grouped = (
        df_match.groupby(COL_REP_ID)[col_extra]
        .apply(lambda x: " | ".join(sorted(set(str(v)[:150] for v in x.dropna()))))
        .reset_index()
        .rename(columns={col_extra: col_extra_name})
    )
    df_infos_f = df_infos[df_infos[COL_REP_ID].isin(ids_retenus)].copy()
    df_final   = df_infos_f.merge(df_grouped, on=COL_REP_ID, how="left")
    wanted = [
        COL_REP_ID, COL_DENOMINATION, "nom_usage_hatvp", "sigle_hatvp",
        "label_categorie_organisation", "adresse", "code_postal", "ville", "pays",
        "site_web", "page_linkedin", "page_twitter",
        col_extra_name, "date_premiere_publication",
        "identifiant_national", "type_identifiant_national",
    ]
    cols = list(dict.fromkeys(c for c in wanted if c in df_final.columns))
    return (df_final[cols]
            .drop_duplicates(subset=[COL_REP_ID])
            .sort_values(COL_DENOMINATION if COL_DENOMINATION in cols else cols[0],
                         na_position="last"))

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🏛️ HATVP Explorer")
    st.markdown(
        "<p style='font-family:DM Mono,monospace;font-size:12px;color:#556688;'>"
        "Répertoire des représentants d'intérêts · Haute Autorité pour la Transparence de la Vie Publique"
        "</p>", unsafe_allow_html=True
    )
    st.divider()

    st.markdown("### 🔍 Recherche")

    keyword = st.text_input(
        "Mot-clé",
        placeholder="ex : taxe carbone, CVAE, MiCA, énergie...",
        help="Saisissez un ou plusieurs mots. Les accents et la casse sont ignorés."
    )

    mode = st.radio(
        "Mode de recherche",
        options=["Objets d'activité", "Secteurs d'activité"],
        index=0,
        help=(
            "**Objets d'activité** : recherche dans ~95 000 descriptions libres "
            "des actions de lobbying. Très précis.\n\n"
            "**Secteurs d'activité** : recherche dans 31 catégories prédéfinies "
            "(Energie, Santé, Numérique…). Plus large."
        )
    )
    mode_key = "objets" if mode == "Objets d'activité" else "secteurs"

    st.divider()
    st.markdown("### ⚙️ Options")

    max_preview = st.slider("Lignes à afficher", 5, 50, 15)
    show_all_cols = st.checkbox("Afficher toutes les colonnes", value=False)

    st.divider()
    st.markdown(
        "<p style='font-family:DM Mono,monospace;font-size:11px;color:#334466;'>"
        "Données mises à jour chaque nuit par la HATVP.<br>"
        "Cache local : 12h."
        "</p>", unsafe_allow_html=True
    )

# ─── CONTENU PRINCIPAL ────────────────────────────────────────────────────────

# ── En-tête ───────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='color:#e2e8f0;margin-bottom:4px;'>🏛️ HATVP Explorer</h1>"
    "<p style='font-family:DM Mono,monospace;color:#556688;font-size:14px;margin-top:0;'>"
    "Explorez le répertoire des représentants d'intérêts (lobbyistes) français"
    "</p>",
    unsafe_allow_html=True
)

st.divider()

# ── Documentation ──────────────────────────────────────────────────────────────
with st.expander("📖 Comment utiliser cet outil ?", expanded=not keyword):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
<div class="doc-card">
<h4>🔎 Mode Objets d'activité <span style="color:#7dd3fc;font-size:11px;">(défaut · recommandé)</span></h4>
<p>Recherche dans les <strong style="color:#e2e8f0;">~95 000 descriptions libres</strong> 
des actions de lobbying déclarées.<br><br>
Idéal pour des recherches précises sur des sujets réglementaires ou législatifs spécifiques.<br><br>
<strong>Exemples :</strong><br>
→ <code>taxe carbone</code> · <code>CVAE</code> · <code>MiCA</code><br>
→ <code>réforme des retraites</code> · <code>loi APER</code><br>
→ <code>intelligence artificielle</code> · <code>RGPD</code>
</p>
</div>
""", unsafe_allow_html=True)

        st.markdown("""
<div class="doc-card">
<h4>📂 Mode Secteurs d'activité</h4>
<p>Recherche dans les <strong style="color:#e2e8f0;">31 secteurs prédéfinis</strong> 
déclarés par chaque représentant.<br><br>
Idéal pour obtenir une vue d'ensemble d'un domaine.<br><br>
<strong>Secteurs disponibles :</strong><br>
→ <code>Energie</code> · <code>Santé</code> · <code>Numérique</code><br>
→ <code>Agriculture</code> · <code>Transports</code> · <code>Finance</code><br>
→ <code>Environnement</code> · <code>Justice</code> · <code>Défense</code>…
</p>
</div>
""", unsafe_allow_html=True)

    with col2:
        st.markdown("""
<div class="doc-card">
<h4>📋 Résultats & export</h4>
<p>
Après une recherche, vous obtenez la liste des <strong style="color:#e2e8f0;">organisations et 
personnes</strong> ayant déclaré une activité correspondante, avec :<br><br>
→ Nom, catégorie, ville<br>
→ Site web, LinkedIn, Twitter<br>
→ Date de première publication<br>
→ Objets ou secteurs matchés<br><br>
Un bouton <strong style="color:#6ee7b7;">Télécharger le CSV</strong> permet d'exporter 
l'intégralité des résultats.
</p>
</div>
""", unsafe_allow_html=True)

        st.markdown("""
<div class="doc-card">
<h4>⚡ Conseils</h4>
<p>
→ Les <strong style="color:#e2e8f0;">accents et la casse</strong> sont ignorés<br>
→ En mode Objets, préférez des <strong style="color:#e2e8f0;">termes précis</strong> 
(sigles, noms de lois)<br>
→ En mode Secteurs, utilisez un <strong style="color:#e2e8f0;">mot court</strong> 
("energ", "sant")<br>
→ Les données sont celles publiées par la <strong style="color:#e2e8f0;">HATVP</strong> 
et couvrent les 6 dernières années<br>
→ Source officielle : 
<a href="https://www.hatvp.fr/le-repertoire/" target="_blank" style="color:#7dd3fc;">
hatvp.fr/le-repertoire</a>
</p>
</div>
""", unsafe_allow_html=True)

# ── Chargement des données ─────────────────────────────────────────────────────
with st.spinner("⏳ Chargement des données HATVP... (première visite ~15 sec)"):
    try:
        tables = load_all_tables()
        data_ok = all(k in tables for k in ["secteurs", "infos", "objets", "exercices"])
    except Exception as e:
        st.error(f"❌ Erreur de chargement des données : {e}")
        st.stop()

if not data_ok:
    st.error("❌ Certaines tables sont manquantes. Réessayez dans quelques instants.")
    st.stop()

# Stats générales
df_infos     = tables["infos"]
df_secteurs  = tables["secteurs"]
df_objets    = tables["objets"]
df_exercices = tables["exercices"]

st.markdown(f"""
<div class="stat-row">
  <div class="stat-box">
    <div class="stat-number">{len(df_infos):,}</div>
    <div class="stat-label">Représentants</div>
  </div>
  <div class="stat-box">
    <div class="stat-number">{len(df_objets):,}</div>
    <div class="stat-label">Objets d'activité</div>
  </div>
  <div class="stat-box">
    <div class="stat-number">{df_secteurs[COL_SECTEUR].nunique()}</div>
    <div class="stat-label">Secteurs</div>
  </div>
  <div class="stat-box">
    <div class="stat-number">{len(df_exercices):,}</div>
    <div class="stat-label">Exercices déclarés</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Affichage des secteurs si mode secteurs ───────────────────────────────────
if mode_key == "secteurs" and not keyword:
    st.markdown("#### 📋 Secteurs disponibles")
    all_sectors = df_secteurs[COL_SECTEUR].dropna().value_counts()
    pills_html = "".join(
        f'<span class="sector-pill">{s} <span style="color:#334466;">({n})</span></span>'
        for s, n in all_sectors.items()
    )
    st.markdown(f'<div style="margin:12px 0;">{pills_html}</div>', unsafe_allow_html=True)

# ── Zone de recherche ─────────────────────────────────────────────────────────
st.divider()

if not keyword:
    st.markdown(
        "<div style='text-align:center;padding:40px;color:#334466;font-family:DM Mono,monospace;'>"
        "← Saisissez un mot-clé dans la barre de gauche pour commencer"
        "</div>",
        unsafe_allow_html=True
    )
    st.stop()

# ── Exécution de la recherche ─────────────────────────────────────────────────

badge_class = "mode-objets" if mode_key == "objets" else "mode-secteurs"
badge_label = "Objets d'activité" if mode_key == "objets" else "Secteurs d'activité"
st.markdown(
    f'<span class="mode-badge {badge_class}">Mode : {badge_label}</span>',
    unsafe_allow_html=True
)
st.markdown(f"### Résultats pour **« {keyword} »**")

# ─── MODE OBJETS ──────────────────────────────────────────────────────────────
if mode_key == "objets":
    df_match_obj = search_objets(keyword, df_objets)

    if df_match_obj.empty:
        st.warning(f"Aucun objet d'activité ne contient « {keyword} ». Essayez un terme plus court ou différent.")
        st.stop()

    # Jointure objets → exercices → representants_id
    df_obj_rep = df_match_obj.merge(
        df_exercices[[COL_EXO_ID, COL_REP_ID]].drop_duplicates(),
        on=COL_EXO_ID, how="left"
    )
    ids_retenus = df_obj_rep[COL_REP_ID].dropna().unique().tolist()

    st.markdown(f"""
<div style='background:#1e3a5f22;border:1px solid #2563eb44;border-radius:10px;
            padding:16px 20px;margin:12px 0;'>
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#7dd3fc;'>
    {len(df_match_obj):,}
  </span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>
    objets d'activité trouvés
  </span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#e8c97a;'>
    {len(ids_retenus):,}
  </span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>
    représentants concernés
  </span>
</div>
""", unsafe_allow_html=True)

    # Aperçu des objets matchés
    with st.expander(f"📝 Aperçu des {min(15, len(df_match_obj))} premiers objets matchés"):
        for _, row in df_match_obj.head(15).iterrows():
            objet = str(row[COL_OBJET])
            st.markdown(
                f"<div style='font-family:DM Mono,monospace;font-size:12px;color:#93b4d8;"
                f"padding:8px 12px;border-left:2px solid #2563eb44;margin-bottom:6px;'>"
                f"{objet}</div>",
                unsafe_allow_html=True
            )

    df_export = build_export(
        ids_retenus, df_infos, df_obj_rep,
        col_extra=COL_OBJET, col_extra_name="objets_activite_matches"
    )

# ─── MODE SECTEURS ────────────────────────────────────────────────────────────
else:
    groups = search_secteurs(keyword, df_secteurs)

    if not groups:
        st.warning(f"Aucun secteur ne correspond à « {keyword} ». Consultez la liste des secteurs disponibles ci-dessus.")
        st.stop()

    val_counts = df_secteurs[COL_SECTEUR].value_counts()
    all_sectors_found = sorted(set(s for _, secs in groups for s in secs))

    # Sélection des secteurs
    st.markdown("**Secteurs trouvés — sélectionnez ceux à inclure :**")
    selected_sectors = st.multiselect(
        "Secteurs",
        options=all_sectors_found,
        default=all_sectors_found,
        format_func=lambda s: f"{s}  ({val_counts.get(s, 0)} déclarations)",
        label_visibility="collapsed"
    )

    if not selected_sectors:
        st.info("Sélectionnez au moins un secteur.")
        st.stop()

    df_match_sec = df_secteurs[df_secteurs[COL_SECTEUR].isin(selected_sectors)]
    ids_retenus  = df_match_sec[COL_REP_ID].dropna().unique().tolist()

    total_decl = sum(val_counts.get(s, 0) for s in selected_sectors)
    st.markdown(f"""
<div style='background:#2d1f4e22;border:1px solid #7c3aed44;border-radius:10px;
            padding:16px 20px;margin:12px 0;'>
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#c4b5fd;'>
    {total_decl:,}
  </span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>
    déclarations sectorielles
  </span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#e8c97a;'>
    {len(ids_retenus):,}
  </span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>
    représentants concernés
  </span>
</div>
""", unsafe_allow_html=True)

    df_export = build_export(
        ids_retenus, df_infos, df_match_sec,
        col_extra=COL_SECTEUR, col_extra_name="secteurs_activite_declares"
    )

# ─── TABLEAU DE RÉSULTATS ─────────────────────────────────────────────────────

st.divider()
st.markdown(f"#### 📊 {len(df_export)} représentants")

# Colonnes à afficher par défaut
default_cols = [c for c in [
    COL_DENOMINATION, "nom_usage_hatvp", "label_categorie_organisation",
    "ville", "site_web",
    "objets_activite_matches" if mode_key == "objets" else "secteurs_activite_declares",
] if c in df_export.columns]

display_cols = list(df_export.columns) if show_all_cols else default_cols
df_display   = df_export[display_cols].head(max_preview).reset_index(drop=True)

# Renommage lisible
rename_map = {
    COL_REP_ID:                   "ID",
    COL_DENOMINATION:             "Organisation",
    "nom_usage_hatvp":            "Nom HATVP",
    "sigle_hatvp":                "Sigle",
    "label_categorie_organisation": "Catégorie",
    "ville":                       "Ville",
    "pays":                        "Pays",
    "site_web":                    "Site web",
    "page_linkedin":               "LinkedIn",
    "page_twitter":                "Twitter",
    "date_premiere_publication":   "1ère publication",
    "objets_activite_matches":     "Objets matchés",
    "secteurs_activite_declares":  "Secteurs déclarés",
    "identifiant_national":        "SIREN/RNA",
}
df_display = df_display.rename(columns={k: v for k, v in rename_map.items() if k in df_display.columns})

st.dataframe(df_display, use_container_width=True, height=420)

if len(df_export) > max_preview:
    st.caption(f"Affichage limité à {max_preview} lignes. Téléchargez le CSV pour voir tous les {len(df_export)} résultats.")

# ─── EXPORT CSV ───────────────────────────────────────────────────────────────

csv_bytes = df_export.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
filename  = f"hatvp_{keyword.replace(' ','_')}_{mode_key}.csv"

st.download_button(
    label=f"⬇️  Télécharger le CSV complet ({len(df_export)} lignes)",
    data=csv_bytes,
    file_name=filename,
    mime="text/csv",
)
