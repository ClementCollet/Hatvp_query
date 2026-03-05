"""
HATVP To Table — Application Streamlit
Export Excel 3 onglets :
  1. Actions de lobbying  : 1 ligne par action (objet, période, types, responsables, domaines)
  2. Organisations        : 1 ligne par organisation
  3. Dirigeants & Collab. : 1 ligne par personne
"""

import streamlit as st
import pandas as pd
import unicodedata
import gzip
import io
import zipfile
import requests
import tempfile
from pathlib import Path
from io import BytesIO

# ─── CONFIG ───────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="HATVP To Table",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
.stApp { background-color: #0e1117; }
[data-testid="stSidebar"] { background-color: #131720; border-right: 1px solid #1e2535; }
h1 { font-family: 'Syne', sans-serif !important; font-weight: 800 !important; letter-spacing: -1px !important; }
h2, h3 { font-family: 'Syne', sans-serif !important; font-weight: 700 !important; }
.doc-card { background: linear-gradient(135deg, #131720 0%, #1a2035 100%); border: 1px solid #2a3550; border-radius: 12px; padding: 20px 24px; margin-bottom: 14px; }
.doc-card h4 { color: #e8c97a; font-family: 'Syne', sans-serif; font-weight: 700; font-size: 15px; margin: 0 0 8px 0; }
.doc-card p { color: #8899bb; font-family: 'DM Mono', monospace; font-size: 13px; margin: 0; line-height: 1.6; }
.doc-card code { background: #0e1117; color: #7dd3fc; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
.stat-row { display: flex; gap: 12px; margin: 16px 0; }
.stat-box { flex: 1; background: #131720; border: 1px solid #1e2535; border-radius: 10px; padding: 16px; text-align: center; }
.stat-number { font-family: 'Syne', sans-serif; font-size: 28px; font-weight: 800; color: #e8c97a; line-height: 1; }
.stat-label { font-family: 'DM Mono', monospace; font-size: 11px; color: #556688; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
.mode-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-family: 'DM Mono', monospace; font-size: 12px; font-weight: 500; margin-bottom: 8px; }
.mode-objets { background: #1e3a5f; color: #7dd3fc; border: 1px solid #2563eb55; }
.mode-secteurs { background: #2d1f4e; color: #c4b5fd; border: 1px solid #7c3aed55; }
.sector-pill { display: inline-block; background: #1a2035; border: 1px solid #2a3550; border-radius: 20px; padding: 5px 14px; margin: 4px; font-family: 'DM Mono', monospace; font-size: 12px; color: #93b4d8; }
.stButton > button { background: linear-gradient(135deg, #1d4ed8, #2563eb) !important; color: white !important; border: none !important; border-radius: 8px !important; font-family: 'Syne', sans-serif !important; font-weight: 600 !important; }
.stDownloadButton > button { background: linear-gradient(135deg, #065f46, #047857) !important; color: white !important; border: none !important; border-radius: 8px !important; font-family: 'Syne', sans-serif !important; font-weight: 600 !important; }
.stTextInput > div > div > input { background: #131720 !important; border: 1px solid #2a3550 !important; border-radius: 8px !important; color: #e2e8f0 !important; font-family: 'DM Mono', monospace !important; }
.stSelectbox > div > div { background: #131720 !important; border: 1px solid #2a3550 !important; border-radius: 8px !important; }
hr { border-color: #1e2535 !important; }
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTES ───────────────────────────────────────────────────────────────

CACHE_DIR = Path(tempfile.gettempdir()) / "hatvp_cache"
ZIP_URL   = "https://www.hatvp.fr/agora/opendata/csv/Vues_Separees_CSV.zip"

COL_SECTEUR = "secteur_activite"
COL_OBJET   = "objet_activite"
COL_REP_ID  = "representants_id"
COL_DENOM   = "denomination"
COL_EXO_ID  = "exercices_id"
COL_ACT_ID  = "activite_id"
TABLE_KEYWORDS = {
    "secteurs":       ["secteur"],
    "infos":          ["information", "generale"],
    "objets":         ["objet", "activite"],
    "exercices":      ["exercice"],
    "dirigeants":     ["dirigeant"],
    "collaborateurs": ["collaborateur"],
    "ari":            ["observation"],   # 14_observations.csv : activite_id ↔ action_representation_interet_id
    "actions":        ["action", "menee"],
    "ministeres":     ["ministere"],
    "domaines":       ["domaine"],
    "decisions":      ["decision"],
}

def find_csv_in_zip(csv_names, keywords):
    kw_low = [k.lower() for k in keywords]
    candidates = [n for n in csv_names if all(k in n.lower() for k in kw_low)]
    return max(candidates, key=len) if candidates else None

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
    return pd.DataFrame()

def strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")

def normalize(text):
    return strip_accents(str(text).lower())

def generate_variants(keyword):
    kw = keyword.strip()
    variants = set()
    for f in {kw, kw.lower(), kw.capitalize(),
               strip_accents(kw), strip_accents(kw).lower(), strip_accents(kw).capitalize()}:
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

# ─── CHARGEMENT DONNÉES ───────────────────────────────────────────────────────

@st.cache_data(show_spinner=False, ttl=3600 * 12)
def load_all_tables():
    CACHE_DIR.mkdir(exist_ok=True)
    zip_cache = CACHE_DIR / "vues_separees.zip"
    if not zip_cache.exists():
        resp = requests.get(ZIP_URL, stream=True, timeout=300)
        resp.raise_for_status()
        with open(zip_cache, "wb") as f:
            for chunk in resp.iter_content(65536):
                f.write(chunk)
    zip_bytes = zip_cache.read_bytes()
    tables = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = z.namelist()
        csv_names = [n for n in names if n.lower().endswith(".csv")]
        for key, keywords in TABLE_KEYWORDS.items():
            match = find_csv_in_zip(csv_names, keywords)
            if match:
                tables[key] = read_csv_bytes(z.read(match))
    return tables

# ─── MATCHING ─────────────────────────────────────────────────────────────────

def _word_boundary_match(needle: str, haystack: str) -> bool:
    """Vérifie que needle est un mot entier dans haystack (matching exact)."""
    import re
    pattern = r"(?<![\w\u00C0-\u024F])" + re.escape(needle) + r"(?![\w\u00C0-\u024F])"
    return bool(re.search(pattern, haystack, re.IGNORECASE))

def search_secteurs(keyword, df_secteurs, exact=False):
    variants = generate_variants(keyword) if not exact else [keyword.strip()]
    results = {}
    for variant in variants:
        v_norm = normalize(variant)
        if exact:
            mask = df_secteurs[COL_SECTEUR].dropna().apply(
                lambda s: _word_boundary_match(v_norm, normalize(s)))
        else:
            mask = df_secteurs[COL_SECTEUR].dropna().apply(
                lambda s: v_norm in normalize(s))
        matched = df_secteurs.loc[mask.index[mask], COL_SECTEUR].unique().tolist()
        if matched:
            results[variant] = sorted(set(matched))
    seen, groups = {}, []
    for v, secs in results.items():
        key = frozenset(secs)
        if key not in seen:
            seen[key] = v
            groups.append((v, secs))
    return groups

def search_objets(keyword, df_objets, exact=False):
    if exact:
        # Mot entier uniquement — pas de variantes tronquées
        kw_norm = normalize(keyword.strip())
        mask = df_objets[COL_OBJET].dropna().apply(
            lambda s: _word_boundary_match(kw_norm, normalize(s)))
    else:
        # Mode élargi : variantes + sous-chaînes
        kw_norms = list(set(normalize(v) for v in generate_variants(keyword)))
        mask = df_objets[COL_OBJET].dropna().apply(
            lambda s: any(kw in normalize(s) for kw in kw_norms))
    return df_objets.loc[mask.index[mask]]

# ─── ENRICHISSEMENT ───────────────────────────────────────────────────────────

COL_ARI_ID_APP = "action_representation_interet_id"

def _agg(df, group_col, val_col, out_name):
    return (df[df[val_col].notna() & (df[val_col].astype(str) != "nan")]
            .groupby(group_col)[val_col]
            .apply(lambda x: " | ".join(sorted(set(str(v) for v in x))))
            .reset_index().rename(columns={val_col: out_name}))

def enrich_actions(df_objets_matched, df_exercices,
                   df_ari, df_actions, df_ministeres, df_domaines):
    """Jointures via 14_observations.csv comme table pivot."""

    # 1. objets → exercices
    exo_cols = ["exercices_id", "representants_id"]
    for c in ["annee_debut", "annee_fin"]:
        if c in df_exercices.columns:
            exo_cols.append(c)
    df = df_objets_matched.merge(
        df_exercices[exo_cols].drop_duplicates(), on="exercices_id", how="left")

    # 2. objets → observations (activite_id → action_representation_interet_id)
    if not df_ari.empty and "activite_id" in df_ari.columns and COL_ARI_ID_APP in df_ari.columns:
        df = df.merge(df_ari[["activite_id", COL_ARI_ID_APP]].drop_duplicates(),
                      on="activite_id", how="left")
    else:
        df[COL_ARI_ID_APP] = None

    # 3. ari_id → types d'actions
    if not df_actions.empty and COL_ARI_ID_APP in df_actions.columns:
        acol = next((c for c in df_actions.columns if "action_menee" in c and "autre" not in c), None)
        if acol:
            df = df.merge(_agg(df_actions, COL_ARI_ID_APP, acol, "types_actions"),
                          on=COL_ARI_ID_APP, how="left")
        else:
            df["types_actions"] = None
    else:
        df["types_actions"] = None

    # 4. ari_id → responsables publics
    if not df_ministeres.empty and COL_ARI_ID_APP in df_ministeres.columns:
        rcol = next((c for c in df_ministeres.columns
                     if "responsable_public" in c and "autre" not in c), None)
        if rcol:
            df = df.merge(_agg(df_ministeres, COL_ARI_ID_APP, rcol, "responsables_publics"),
                          on=COL_ARI_ID_APP, how="left")
        else:
            df["responsables_publics"] = None
    else:
        df["responsables_publics"] = None

    # 5. activite_id → domaines (direct)
    if not df_domaines.empty and "activite_id" in df_domaines.columns:
        dcol = next((c for c in df_domaines.columns if "domaine" in c), None)
        if dcol:
            df = df.merge(_agg(df_domaines, "activite_id", dcol, "domaines_intervention"),
                          on="activite_id", how="left")
        else:
            df["domaines_intervention"] = None
    else:
        df["domaines_intervention"] = None

    return df

# ─── CONSTRUCTION DES ONGLETS ─────────────────────────────────────────────────

def build_actions_sheet(df_enriched, df_infos):
    org_cols = [c for c in [COL_REP_ID, COL_DENOM, "nom_usage_hatvp",
                             "label_categorie_organisation", "ville", "site_web"]
                if c in df_infos.columns]
    df = df_enriched.merge(
        df_infos[org_cols].drop_duplicates(subset=[COL_REP_ID]),
        on=COL_REP_ID, how="left")
    wanted = [COL_DENOM, "nom_usage_hatvp", "label_categorie_organisation", "ville",
              COL_REP_ID, COL_OBJET, "annee_debut", "annee_fin",
              "types_actions", "responsables_publics", "domaines_intervention",
              "identifiant_fiche", COL_ACT_ID]
    cols = list(dict.fromkeys(c for c in wanted if c in df.columns))
    rename = {
        COL_DENOM:                    "Organisation",
        "nom_usage_hatvp":            "Nom HATVP",
        "label_categorie_organisation":"Catégorie",
        "ville":                      "Ville",
        COL_REP_ID:                   "ID Organisation",
        COL_OBJET:                    "Objet de l'action",
        "annee_debut":                "Période début",
        "annee_fin":                  "Période fin",
        "types_actions":              "Types d'actions",
        "responsables_publics":       "Responsables publics contactés",
        "domaines_intervention":      "Domaines d'intervention",
        "identifiant_fiche":          "ID Fiche HATVP",
        COL_ACT_ID:                   "ID Activité",
    }
    df = df[cols].rename(columns={k: v for k, v in rename.items() if k in cols})
    sort_col = "Organisation" if "Organisation" in df.columns else df.columns[0]
    return df.sort_values([sort_col, "Période début"] if "Période début" in df.columns
                          else [sort_col], na_position="last")

def build_orgs_sheet(ids, df_infos, df_enriched):
    df_summary = (
        df_enriched.groupby(COL_REP_ID)[COL_OBJET]
        .apply(lambda x: " | ".join(sorted(set(str(v)[:120] for v in x.dropna()))))
        .reset_index().rename(columns={COL_OBJET: "objets_activite_matches"})
    )
    df = df_infos[df_infos[COL_REP_ID].isin(ids)].merge(df_summary, on=COL_REP_ID, how="left")
    wanted = [COL_REP_ID, COL_DENOM, "nom_usage_hatvp", "sigle_hatvp",
              "label_categorie_organisation", "adresse", "code_postal", "ville", "pays",
              "site_web", "page_linkedin", "page_twitter",
              "objets_activite_matches", "date_premiere_publication",
              "identifiant_national", "type_identifiant_national"]
    cols = list(dict.fromkeys(c for c in wanted if c in df.columns))
    return (df[cols].drop_duplicates(subset=[COL_REP_ID])
            .sort_values(COL_DENOM if COL_DENOM in cols else cols[0], na_position="last"))

def build_persons_sheet(ids, df_orgs, df_dirigeants, df_collaborateurs):
    org_ref_cols = [c for c in [COL_REP_ID, COL_DENOM, "nom_usage_hatvp",
                                 "label_categorie_organisation", "ville", "site_web",
                                 "objets_activite_matches"] if c in df_orgs.columns]
    df_org = df_orgs[org_ref_cols].copy()
    frames = []
    for df_src, statut, rmap in [
        (df_dirigeants, "Dirigeant", {
            "civilite_dirigeant": "civilite", "nom_dirigeant": "nom",
            "prenom_dirigeant": "prenom", "fonction_dirigeant": "fonction",
            "nom_prenom_dirigeant": "nom_prenom"}),
        (df_collaborateurs, "Collaborateur", {
            "civilite_collaborateur": "civilite", "nom_collaborateur": "nom",
            "prenom_collaborateur": "prenom", "fonction_collaborateur": "fonction",
            "nom_prenom_collaborateur": "nom_prenom"}),
    ]:
        if df_src.empty or COL_REP_ID not in df_src.columns:
            continue
        df_f = df_src[df_src[COL_REP_ID].isin(ids)].copy()
        if df_f.empty:
            continue
        df_f["statut"] = statut
        df_f = df_f.rename(columns={k: v for k, v in rmap.items() if k in df_f.columns})
        frames.append(df_f)
    if not frames:
        return pd.DataFrame()
    df_p = pd.concat(frames, ignore_index=True).merge(df_org, on=COL_REP_ID, how="left")
    wanted = ["statut", "civilite", "nom", "prenom", "fonction", "nom_prenom",
              COL_REP_ID, COL_DENOM, "nom_usage_hatvp",
              "label_categorie_organisation", "ville", "site_web", "objets_activite_matches"]
    cols = list(dict.fromkeys(c for c in wanted if c in df_p.columns))
    return df_p[cols].sort_values([COL_DENOM, "statut", "nom"], na_position="last")

# ─── EXPORT EXCEL ─────────────────────────────────────────────────────────────

def build_excel(sheets):
    """sheets = liste de (nom, df). Retourne bytes."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets:
            if df is None or df.empty:
                continue
            df.to_excel(writer, sheet_name=name, index=False)
            ws = writer.sheets[name]
            for col_idx, col_name in enumerate(df.columns, 1):
                max_len = max(len(str(col_name)),
                              int(df[col_name].astype(str).str.len().quantile(0.9))
                              if len(df) > 0 else 0)
                ws.column_dimensions[
                    ws.cell(row=1, column=col_idx).column_letter
                ].width = min(max_len + 2, 60)
    return buf.getvalue()

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🏛️ HATVP To Table")
    st.markdown(
        "<p style='font-family:DM Mono,monospace;font-size:12px;color:#556688;'>"
        "Répertoire des représentants d'intérêts · HATVP</p>",
        unsafe_allow_html=True)
    st.divider()
    st.markdown("### 🔍 Recherche")
    keyword = st.text_input("Mot-clé",
        placeholder="ex : taxe carbone, CVAE, MiCA, énergie...",
        help="Les accents et la casse sont ignorés.")
    mode = st.radio("Mode de recherche",
        ["Objets d'activité", "Secteurs d'activité"], index=0,
        help="**Objets** : full-text dans ~95 000 descriptions. **Secteurs** : 31 catégories.")
    mode_key = "objets" if mode == "Objets d'activité" else "secteurs"

    st.markdown("#### 🎯 Précision du matching")
    matching_mode = st.radio(
        "Mode de matching",
        ["Élargi", "Exact"],
        index=0,
        help=(
            "**Élargi** — trouve les variantes et sous-chaînes. "
            "*« seb »* matche *SEB*, *Sebastian*, *Sébastien*...\n\n"
            "**Exact** — mot entier uniquement. "
            "*« seb »* matche *SEB SA* mais pas *Sebastian* ni *Sébastien*."
        )
    )
    exact_match = (matching_mode == "Exact")
    st.divider()
    st.markdown("### ⚙️ Options")
    max_preview = st.slider("Lignes à afficher", 5, 50, 15)
    show_all_cols = st.checkbox("Toutes les colonnes", value=False)
    st.divider()
    st.markdown(
        "<p style='font-family:DM Mono,monospace;font-size:11px;color:#334466;'>"
        "Données HATVP · Cache 12h</p>", unsafe_allow_html=True)

# ─── EN-TÊTE ──────────────────────────────────────────────────────────────────

st.markdown(
    "<h1 style='color:#e2e8f0;margin-bottom:4px;'>🏛️ HATVP To Table</h1>"
    "<p style='font-family:DM Mono,monospace;color:#556688;font-size:14px;margin-top:0;'>"
    "Explorez le répertoire des représentants d'intérêts (lobbyistes) français et téléchargez facilement les données compactées</p>",
    unsafe_allow_html=True)
st.divider()

# ─── DOCUMENTATION ────────────────────────────────────────────────────────────

with st.expander("📖 Comment utiliser cet outil ?", expanded=not keyword):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
<div class="doc-card">
<h4>🔎 Mode Objets d'activité <span style="color:#7dd3fc;font-size:11px;">(défaut · recommandé)</span></h4>
<p>Recherche full-text dans les ~95 000 descriptions libres des actions de lobbying.<br><br>
<strong>Exemples :</strong><br>
→ <code>taxe carbone</code> · <code>CVAE</code> · <code>MiCA</code><br>
→ <code>réforme des retraites</code> · <code>loi APER</code><br>
→ <code>intelligence artificielle</code> · <code>RGPD</code>
</p></div>""", unsafe_allow_html=True)
        st.markdown("""
<div class="doc-card">
<h4>📂 Mode Secteurs d'activité</h4>
<p>Recherche dans les 31 secteurs prédéfinis déclarés par chaque représentant.<br><br>
<strong>Exemples :</strong><br>
→ <code>Energie</code> · <code>Santé</code> · <code>Numérique</code><br>
→ <code>Agriculture</code> · <code>Transports</code> · <code>Finance</code>
</p></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""
<div class="doc-card">
<h4>📋 Structure de l'export Excel (3 onglets)</h4>
<p>
<strong style="color:#e2e8f0;">Onglet 1 — Actions de lobbying</strong><br>
→ 1 ligne par action · objet · période concernée<br>
→ Types d'actions menées · Responsables publics contactés<br>
→ Domaines d'intervention<br><br>
<strong style="color:#e2e8f0;">Onglet 2 — Organisations</strong><br>
→ 1 ligne par organisation · toutes les infos<br><br>
<strong style="color:#e2e8f0;">Onglet 3 — Dirigeants & Collaborateurs</strong><br>
→ 1 ligne par personne · statut · fonction · organisation
</p></div>""", unsafe_allow_html=True)
        st.markdown("""
<div class="doc-card">
<h4>🎯 Matching Élargi vs Exact</h4>
<p>
<strong style="color:#e2e8f0;">Élargi</strong> (défaut) — sous-chaînes + variantes orthographiques<br>
→ <code>seb</code> trouve <em>SEB SA</em>, <em>Sebastian</em>, <em>Sébastien</em><br>
→ <code>energie</code> trouve <em>énergie</em>, <em>énergétique</em>, <em>Energie verte</em><br>
→ Idéal pour explorer un thème large<br><br>
<strong style="color:#e2e8f0;">Exact</strong> — mot entier uniquement (frontières de mots)<br>
→ <code>seb</code> trouve <em>SEB SA</em>, <em>groupe SEB</em> mais pas <em>Sebastian</em><br>
→ <code>loi</code> trouve <em>la loi</em>, <em>cette loi,</em> mais pas <em>lobbying</em><br>
→ Idéal pour rechercher un nom propre, un sigle ou un acronyme
</p></div>
<div class="doc-card">
<h4>⚡ Conseils</h4>
<p>
→ Les <strong style="color:#e2e8f0;">accents et la casse</strong> sont ignorés dans les deux modes<br>
→ En mode Objets, préférez des <strong style="color:#e2e8f0;">termes précis</strong><br>
→ La <strong style="color:#e2e8f0;">période</strong> correspond à l'exercice déclaratif
(ex: 01/04/2024 – 31/03/2025), pas à la date de publication<br>
→ Source : <a href="https://www.hatvp.fr/le-repertoire/" target="_blank"
style="color:#7dd3fc;">hatvp.fr/le-repertoire</a>
</p></div>""", unsafe_allow_html=True)

# ─── CHARGEMENT ───────────────────────────────────────────────────────────────

with st.spinner("⏳ Chargement des données HATVP... (première visite ~20 sec)"):
    try:
        tables = load_all_tables()
    except Exception as e:
        st.error(f"❌ Erreur de chargement : {e}")
        st.stop()

required_keys = ["infos", "secteurs", "objets", "exercices",
                 "dirigeants", "collaborateurs", "ari",
                 "actions", "ministeres", "domaines"]
missing = [k for k in required_keys if k not in tables]
if missing:
    st.error(f"❌ Tables manquantes : {missing}. Essayez --refresh-cache.")
    st.stop()

df_infos          = tables["infos"]
df_secteurs       = tables["secteurs"]
df_objets         = tables["objets"]
df_exercices      = tables["exercices"]
df_dirigeants     = tables["dirigeants"]
df_collaborateurs = tables["collaborateurs"]
df_ari            = tables["ari"]
df_actions        = tables["actions"]
df_ministeres     = tables["ministeres"]
df_domaines       = tables["domaines"]

# Stats
st.markdown(f"""
<div class="stat-row">
  <div class="stat-box"><div class="stat-number">{len(df_infos):,}</div><div class="stat-label">Représentants</div></div>
  <div class="stat-box"><div class="stat-number">{len(df_objets):,}</div><div class="stat-label">Objets d'activité</div></div>
  <div class="stat-box"><div class="stat-number">{df_secteurs[COL_SECTEUR].nunique()}</div><div class="stat-label">Secteurs</div></div>
  <div class="stat-box"><div class="stat-number">{len(df_actions):,}</div><div class="stat-label">Actions déclarées</div></div>
</div>""", unsafe_allow_html=True)

# Secteurs pills
if mode_key == "secteurs" and not keyword:
    st.markdown("#### 📋 Secteurs disponibles")
    all_s = df_secteurs[COL_SECTEUR].dropna().value_counts()
    pills = "".join(f'<span class="sector-pill">{s} <span style="color:#334466;">({n})</span></span>'
                    for s, n in all_s.items())
    st.markdown(f'<div style="margin:12px 0;">{pills}</div>', unsafe_allow_html=True)

st.divider()

if not keyword:
    st.markdown(
        "<div style='text-align:center;padding:40px;color:#334466;font-family:DM Mono,monospace;'>"
        "← Saisissez un mot-clé dans la barre de gauche pour commencer</div>",
        unsafe_allow_html=True)
    st.stop()

# ─── RECHERCHE ────────────────────────────────────────────────────────────────

badge_class = "mode-objets" if mode_key == "objets" else "mode-secteurs"
st.markdown(
    f'<span class="mode-badge {badge_class}">Mode : {mode}</span>',
    unsafe_allow_html=True)
st.markdown(f"### Résultats pour **« {keyword} »**")

ids_retenus     = []
df_objets_match = pd.DataFrame()

# ── Mode OBJETS ───────────────────────────────────────────────────────────────
if mode_key == "objets":
    df_objets_match = search_objets(keyword, df_objets, exact=exact_match)
    if df_objets_match.empty:
        st.warning(f"Aucun objet d'activité ne contient « {keyword} ».")
        st.stop()
    exo_rep = df_exercices[[COL_EXO_ID, COL_REP_ID]].drop_duplicates()
    ids_retenus = (df_objets_match.merge(exo_rep, on=COL_EXO_ID, how="left")
                   [COL_REP_ID].dropna().unique().tolist())

    st.markdown(f"""
<div style='background:#1e3a5f22;border:1px solid #2563eb44;border-radius:10px;padding:16px 20px;margin:12px 0;'>
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#7dd3fc;'>{len(df_objets_match):,}</span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>actions trouvées</span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#e8c97a;'>{len(ids_retenus):,}</span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>organisations</span>
</div>""", unsafe_allow_html=True)

    with st.expander(f"📝 Aperçu des {min(10, len(df_objets_match))} premiers objets matchés"):
        for _, row in df_objets_match.head(10).iterrows():
            objet = str(row[COL_OBJET])
            st.markdown(
                f"<div style='font-family:DM Mono,monospace;font-size:12px;color:#93b4d8;"
                f"padding:8px 12px;border-left:2px solid #2563eb44;margin-bottom:6px;'>{objet}</div>",
                unsafe_allow_html=True)

# ── Mode SECTEURS ─────────────────────────────────────────────────────────────
else:
    groups = search_secteurs(keyword, df_secteurs, exact=exact_match)
    if not groups:
        st.warning(f"Aucun secteur ne correspond à « {keyword} ».")
        st.stop()
    all_sectors_found = sorted(set(s for _, secs in groups for s in secs))
    val_counts = df_secteurs[COL_SECTEUR].value_counts()
    selected_sectors = st.multiselect(
        "Secteurs trouvés — sélectionnez ceux à inclure :",
        options=all_sectors_found, default=all_sectors_found,
        format_func=lambda s: f"{s}  ({val_counts.get(s, 0)} déclarations)")
    if not selected_sectors:
        st.info("Sélectionnez au moins un secteur.")
        st.stop()
    ids_retenus = (df_secteurs[df_secteurs[COL_SECTEUR].isin(selected_sectors)]
                   [COL_REP_ID].dropna().unique().tolist())
    exo_ids = df_exercices[df_exercices[COL_REP_ID].isin(ids_retenus)][COL_EXO_ID].unique()
    df_objets_match = df_objets[df_objets[COL_EXO_ID].isin(exo_ids)]

    st.markdown(f"""
<div style='background:#2d1f4e22;border:1px solid #7c3aed44;border-radius:10px;padding:16px 20px;margin:12px 0;'>
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#c4b5fd;'>{len(df_objets_match):,}</span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>actions associées</span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#e8c97a;'>{len(ids_retenus):,}</span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>organisations</span>
</div>""", unsafe_allow_html=True)

# ─── ENRICHISSEMENT ───────────────────────────────────────────────────────────

if df_objets_match.empty:
    st.warning("Aucune action trouvée.")
    st.stop()

with st.spinner("🔀 Enrichissement des actions (période, types, responsables)..."):
    df_enriched = enrich_actions(
        df_objets_match, df_exercices,
        df_ari, df_actions, df_ministeres, df_domaines)
    if COL_REP_ID in df_enriched.columns:
        df_enriched = df_enriched[df_enriched[COL_REP_ID].isin(ids_retenus)]

# ─── CONSTRUCTION ONGLETS ─────────────────────────────────────────────────────

df_s1 = build_actions_sheet(df_enriched, df_infos)
df_s2 = build_orgs_sheet(ids_retenus, df_infos, df_enriched)
df_s3 = build_persons_sheet(ids_retenus, df_s2, df_dirigeants, df_collaborateurs)

# ─── AFFICHAGE ONGLETS ────────────────────────────────────────────────────────

st.divider()

tab1, tab2, tab3 = st.tabs([
    f"📋 Actions ({len(df_s1)})",
    f"🏢 Organisations ({len(df_s2)})",
    f"👤 Personnes ({len(df_s3) if not df_s3.empty else 0})",
])

RENAME = {
    COL_REP_ID: "ID", COL_DENOM: "Organisation", "nom_usage_hatvp": "Nom HATVP",
    "sigle_hatvp": "Sigle", "label_categorie_organisation": "Catégorie",
    "ville": "Ville", "pays": "Pays", "site_web": "Site web",
    "page_linkedin": "LinkedIn", "page_twitter": "Twitter",
    "date_premiere_publication": "1ère publication",
    "objets_activite_matches": "Objets matchés",
    "identifiant_national": "SIREN/RNA",
    "statut": "Statut", "civilite": "Civilité", "nom": "Nom",
    "prenom": "Prénom", "fonction": "Fonction", "nom_prenom": "Nom complet",
}

def show_tab(df, default_cols, label):
    if df is None or df.empty:
        st.info(f"Aucune donnée {label}.")
        return
    display_cols = list(df.columns) if show_all_cols else [c for c in default_cols if c in df.columns]
    df_disp = df[display_cols].head(max_preview).reset_index(drop=True)
    df_disp = df_disp.rename(columns={k: v for k, v in RENAME.items() if k in df_disp.columns})
    st.dataframe(df_disp, use_container_width=True, height=420)
    if len(df) > max_preview:
        st.caption(f"Affichage limité à {max_preview} lignes sur {len(df)}. Téléchargez l'Excel pour tout voir.")

with tab1:
    show_tab(df_s1,
             ["Organisation", "Objet de l'action", "Période début", "Période fin",
              "Types d'actions", "Responsables publics contactés", "Domaines d'intervention"],
             "d'actions")

with tab2:
    show_tab(df_s2,
             [COL_DENOM, "nom_usage_hatvp", "label_categorie_organisation",
              "ville", "site_web", "objets_activite_matches"],
             "d'organisations")

with tab3:
    show_tab(df_s3,
             ["statut", "nom_prenom", "fonction", COL_DENOM, "ville"],
             "de personnes")

# ─── EXPORT ───────────────────────────────────────────────────────────────────

st.divider()
excel_bytes = build_excel([
    ("Actions de lobbying",         df_s1),
    ("Organisations",               df_s2),
    ("Dirigeants & Collaborateurs", df_s3),
])
filename = f"hatvp_{keyword.replace(' ','_')}_{mode_key}.xlsx"
n3 = len(df_s3) if not df_s3.empty else 0
st.download_button(
    label=f"⬇️  Télécharger Excel — {len(df_s1)} actions · {len(df_s2)} orgs · {n3} personnes",
    data=excel_bytes,
    file_name=filename,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)