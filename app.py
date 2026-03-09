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
import os
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
.stApp { background-color: #0d1b35; }
[data-testid="stSidebar"] { background-color: #122040; border-right: 1px solid #1e3560; }
h1 { font-family: 'Syne', sans-serif !important; font-weight: 800 !important; letter-spacing: -1px !important; }
h2, h3 { font-family: 'Syne', sans-serif !important; font-weight: 700 !important; }
.doc-card { background: linear-gradient(135deg, #122040 0%, #1a2e58 100%); border: 1px solid #2d4480; border-radius: 12px; padding: 20px 24px; margin-bottom: 14px; }
.doc-card h4 { color: #e8c97a; font-family: 'Syne', sans-serif; font-weight: 700; font-size: 15px; margin: 0 0 8px 0; }
.doc-card p { color: #8899bb; font-family: 'DM Mono', monospace; font-size: 13px; margin: 0; line-height: 1.6; }
.doc-card code { background: #0d1b35; color: #7dd3fc; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
.stat-row { display: flex; gap: 12px; margin: 16px 0; }
.stat-box { flex: 1; background: #122040; border: 1px solid #1e3560; border-radius: 10px; padding: 16px; text-align: center; }
.stat-number { font-family: 'Syne', sans-serif; font-size: 28px; font-weight: 800; color: #e8c97a; line-height: 1; }
.stat-label { font-family: 'DM Mono', monospace; font-size: 11px; color: #6677aa; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
.mode-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-family: 'DM Mono', monospace; font-size: 12px; font-weight: 500; margin-bottom: 8px; }
.mode-objets { background: #1e4070; color: #93c5fd; border: 1px solid #3b82f655; }
.mode-secteurs { background: #2d1f4e; color: #c4b5fd; border: 1px solid #7c3aed55; }
.mode-orgs { background: #1a3a2a; color: #6ee7b7; border: 1px solid #05966955; }
.mode-personnes { background: #3a2020; color: #fca5a5; border: 1px solid #dc262655; }
.mode-donneurs { background: #2a1f40; color: #d8b4fe; border: 1px solid #a855f755; }
.sector-pill { display: inline-block; background: #1a2e58; border: 1px solid #2d4480; border-radius: 20px; padding: 5px 14px; margin: 4px; font-family: 'DM Mono', monospace; font-size: 12px; color: #93b4d8; }
.stButton > button { background: linear-gradient(135deg, #2563eb, #3b82f6) !important; color: white !important; border: none !important; border-radius: 8px !important; font-family: 'Syne', sans-serif !important; font-weight: 600 !important; }
.stDownloadButton > button { background: linear-gradient(135deg, #065f46, #047857) !important; color: white !important; border: none !important; border-radius: 8px !important; font-family: 'Syne', sans-serif !important; font-weight: 600 !important; }
.stTextInput > div > div > input { background: #122040 !important; border: 1px solid #2d4480 !important; border-radius: 8px !important; color: #e2e8f0 !important; font-family: 'DM Mono', monospace !important; }
.stSelectbox > div > div { background: #122040 !important; border: 1px solid #2d4480 !important; border-radius: 8px !important; }
hr { border-color: #1e3560 !important; }
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
    "clients":        ["client"],
    "beneficiaires":  ["beneficiaire"],
}

def find_csv_in_zip(csv_names, keywords):
    kw_low = [k.lower() for k in keywords]
    candidates = [n for n in csv_names if all(k in n.lower() for k in kw_low)]
    return max(candidates, key=len) if candidates else None

def _nc(c):
    """Normalise un nom de colonne brut (même logique que normalize_cols)."""
    return c.strip().lower().replace(" ", "_").strip('"').strip("'")

def _col_filter(fixed=(), patterns=(), exclude=()):
    """Retourne un callable usecols qui filtre sur noms normalisés."""
    fixed_set = set(fixed)
    def keep(c):
        nc = _nc(c)
        if exclude and any(e in nc for e in exclude):
            return False
        return nc in fixed_set or any(p in nc for p in patterns)
    return keep

TABLE_COLS = {
    "secteurs":       _col_filter({"secteur_activite", "representants_id"}),
    "infos":          _col_filter({"representants_id", "denomination", "nom_usage_hatvp",
                                   "sigle_hatvp", "label_categorie_organisation", "adresse",
                                   "code_postal", "ville", "pays", "site_web", "page_linkedin",
                                   "page_twitter", "date_premiere_publication",
                                   "identifiant_national", "type_identifiant_national"}),
    "objets":         _col_filter({"objet_activite", "exercices_id", "activite_id"}),
    "exercices":      _col_filter({"exercices_id", "representants_id",
                                   "annee_debut", "annee_fin"}),
    "dirigeants":     _col_filter({"representants_id", "civilite_dirigeant", "nom_dirigeant",
                                   "prenom_dirigeant", "fonction_dirigeant",
                                   "nom_prenom_dirigeant"}),
    "collaborateurs": _col_filter({"representants_id", "civilite_collaborateur",
                                   "nom_collaborateur", "prenom_collaborateur",
                                   "fonction_collaborateur", "nom_prenom_collaborateur"}),
    "ari":            _col_filter({"activite_id", "action_representation_interet_id"}),
    "actions":        _col_filter({"action_representation_interet_id"}, ("action_menee",),
                                  exclude=("autre",)),
    "ministeres":     _col_filter({"action_representation_interet_id"}, ("responsable_public",),
                                  exclude=("autre",)),
    "domaines":       _col_filter({"activite_id"}, ("domaine",)),
    "clients":        _col_filter({"representants_id", "denomination_client",
                                   "identifiant_national_client", "ancienclient",
                                   "datecessation"}),
    "beneficiaires":  _col_filter({"beneficiaire_action_menee",
                                   "action_representation_interet_id",
                                   "action_menee_en_propre"}),
}

# ─── UTILITAIRES ──────────────────────────────────────────────────────────────

def normalize_cols(df):
    df.columns = [_nc(c) for c in df.columns]
    return df

def read_csv_bytes(raw_bytes, usecols=None):
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
            df = pd.read_csv(io.StringIO(text), sep=s, low_memory=False,
                             on_bad_lines="skip", usecols=usecols)
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

@st.cache_resource(show_spinner=False)
def load_all_tables():
    CACHE_DIR.mkdir(exist_ok=True)
    zip_cache = CACHE_DIR / "vues_separees.zip"
    if not zip_cache.exists():
        resp = requests.get(ZIP_URL, stream=True, timeout=300)
        resp.raise_for_status()
        with open(zip_cache, "wb") as f:
            for chunk in resp.iter_content(65536):
                f.write(chunk)
    tables = {}
    with zipfile.ZipFile(zip_cache) as z:
        names = z.namelist()
        csv_names = [n for n in names if n.lower().endswith(".csv")]
        for key, keywords in TABLE_KEYWORDS.items():
            match = find_csv_in_zip(csv_names, keywords)
            if match:
                tables[key] = read_csv_bytes(z.read(match), usecols=TABLE_COLS.get(key))
    return tables

# ─── MATCHING ─────────────────────────────────────────────────────────────────

def _word_boundary_match(needle: str, haystack: str) -> bool:
    """Vérifie que needle est un mot entier dans haystack (matching exact)."""
    import re
    pattern = r"(?<![\w\u00C0-\u024F])" + re.escape(needle) + r"(?![\w\u00C0-\u024F])"
    return bool(re.search(pattern, haystack, re.IGNORECASE))

def _make_matcher(keyword, exact):
    """Retourne un callable qui teste si une chaîne matche le mot-clé."""
    if exact:
        kw_norm = normalize(keyword.strip())
        return lambda s: _word_boundary_match(kw_norm, normalize(str(s)))
    else:
        kw_norms = list(set(normalize(v) for v in generate_variants(keyword)))
        return lambda s: any(kw in normalize(str(s)) for kw in kw_norms)

def _series_matches_rules(series, rules, exact):
    """Masque booléen sur une Series : True si toutes les règles include matchent et aucune exclude."""
    mask = pd.Series(True, index=series.index)
    for r in rules:
        kw = r["keyword"].strip()
        if not kw:
            continue
        matcher = _make_matcher(kw, exact)
        kw_mask = series.fillna("").apply(matcher)
        if r["op"] == "Inclure":
            mask = mask & kw_mask
        else:
            mask = mask & ~kw_mask
    return mask

def _df_matches_rules(df, cols, rules, exact):
    """Masque booléen sur un DataFrame : True si AU MOINS UNE colonne matche toutes les règles."""
    mask = pd.Series(True, index=df.index)
    for r in rules:
        kw = r["keyword"].strip()
        if not kw:
            continue
        matcher = _make_matcher(kw, exact)
        col_match = df[cols].apply(lambda col: col.fillna("").apply(matcher)).any(axis=1)
        if r["op"] == "Inclure":
            mask = mask & col_match
        else:
            mask = mask & ~col_match
    return mask

def search_secteurs(rules, df_secteurs, exact=False):
    """Retourne la liste triée des secteurs matchant les règles."""
    sectors = df_secteurs[COL_SECTEUR].drop_duplicates().dropna()
    mask = _series_matches_rules(sectors, rules, exact)
    return sorted(sectors[mask].unique().tolist())

def search_objets(rules, df_objets, exact=False):
    mask = _series_matches_rules(df_objets[COL_OBJET], rules, exact)
    return df_objets.loc[mask]

def search_organisations(rules, df_infos, exact=False):
    search_cols = [c for c in ["denomination", "nom_usage_hatvp", "sigle_hatvp"]
                   if c in df_infos.columns]
    mask = _df_matches_rules(df_infos, search_cols, rules, exact)
    return df_infos.loc[mask]

def search_donneurs_ordre(rules, df_clients, exact=False):
    """Recherche dans les noms de clients (donneurs d'ordre) déclarés par les cabinets mandataires."""
    if "denomination_client" not in df_clients.columns or df_clients.empty:
        return pd.DataFrame()
    mask = _series_matches_rules(df_clients["denomination_client"], rules, exact)
    return df_clients.loc[mask]

def search_personnes(rules, df_dirigeants, df_collaborateurs, exact=False):
    frames = []
    for df_src, statut, name_cols in [
        (df_dirigeants, "Dirigeant",
         ["nom_dirigeant", "prenom_dirigeant", "nom_prenom_dirigeant"]),
        (df_collaborateurs, "Collaborateur",
         ["nom_collaborateur", "prenom_collaborateur", "nom_prenom_collaborateur"]),
    ]:
        if df_src.empty: continue
        cols = [c for c in name_cols if c in df_src.columns]
        if not cols: continue
        mask = _df_matches_rules(df_src, cols, rules, exact)
        matched = df_src.loc[mask].copy()
        matched["_statut_match"] = statut
        frames.append(matched)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

# ─── ENRICHISSEMENT ───────────────────────────────────────────────────────────

COL_ARI_ID_APP = "action_representation_interet_id"

def _agg(df, group_col, val_col, out_name):
    return (df[df[val_col].notna() & (df[val_col].astype(str) != "nan")]
            .groupby(group_col)[val_col]
            .apply(lambda x: " | ".join(sorted(set(str(v) for v in x))))
            .reset_index().rename(columns={val_col: out_name}))

def enrich_actions(df_objets_matched, df_exercices,
                   df_ari, df_actions, df_ministeres, df_domaines, df_beneficiaires=None):
    """Jointures via 14_observations.csv comme table pivot."""
    if df_beneficiaires is None:
        df_beneficiaires = pd.DataFrame()

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

    # 6. ari_id → donneur d'ordre (bénéficiaire quand action faite pour un tiers)
    if (not df_beneficiaires.empty
            and COL_ARI_ID_APP in df_beneficiaires.columns
            and "action_menee_en_propre" in df_beneficiaires.columns):
        df_tiers = df_beneficiaires[
            df_beneficiaires["action_menee_en_propre"].astype(str) == "0"
        ]
        if not df_tiers.empty:
            df = df.merge(
                _agg(df_tiers, COL_ARI_ID_APP, "beneficiaire_action_menee", "donneur_ordre"),
                on=COL_ARI_ID_APP, how="left")
        else:
            df["donneur_ordre"] = None
    else:
        df["donneur_ordre"] = None

    return df

# ─── CONSTRUCTION DES ONGLETS ─────────────────────────────────────────────────

def build_actions_sheet(df_enriched, df_infos):
    org_cols = [c for c in [COL_REP_ID, COL_DENOM, "nom_usage_hatvp",
                             "label_categorie_organisation", "ville", "site_web"]
                if c in df_infos.columns]
    df = df_enriched.merge(
        df_infos[org_cols].drop_duplicates(subset=[COL_REP_ID]),
        on=COL_REP_ID, how="left")
    wanted = [COL_DENOM, "label_categorie_organisation", "ville",
              COL_OBJET, "annee_debut", "annee_fin",
              "donneur_ordre", "types_actions", "responsables_publics", "domaines_intervention"]
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
        "donneur_ordre":              "Donneur d'ordre",
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
    wanted = ["statut", "civilite", "nom", "prenom", "fonction",
              COL_DENOM, "label_categorie_organisation", "ville", "site_web", "objets_activite_matches"]
    cols = list(dict.fromkeys(c for c in wanted if c in df_p.columns))
    return df_p[cols].sort_values([COL_DENOM, "statut", "nom"], na_position="last")

def build_clients_sheet(ids, df_clients, df_infos, ari_ids=None, df_beneficiaires=None,
                        allowed_clients=None):
    if df_clients.empty or "representants_id" not in df_clients.columns:
        return pd.DataFrame()
    df = df_clients[df_clients["representants_id"].isin(ids)].copy()
    if df.empty:
        return pd.DataFrame()
    # Restreindre à une liste explicite de clients (mode donneurs d'ordre)
    if allowed_clients is not None and "denomination_client" in df.columns:
        df = df[df["denomination_client"].isin(allowed_clients)]
    # Restreindre aux clients effectivement liés aux actions matchées
    if (ari_ids is not None and df_beneficiaires is not None
            and not df_beneficiaires.empty
            and COL_ARI_ID_APP in df_beneficiaires.columns
            and "action_menee_en_propre" in df_beneficiaires.columns
            and "beneficiaire_action_menee" in df_beneficiaires.columns):
        df_tiers = df_beneficiaires[
            (df_beneficiaires[COL_ARI_ID_APP].isin(ari_ids)) &
            (df_beneficiaires["action_menee_en_propre"].astype(str) == "0")
        ]
        if not df_tiers.empty:
            matched_clients = set(df_tiers["beneficiaire_action_menee"].dropna().unique())
            df = df[df["denomination_client"].isin(matched_clients)]
    if df.empty:
        return pd.DataFrame()
    cab_cols = [c for c in ["representants_id", "denomination", "nom_usage_hatvp",
                             "label_categorie_organisation"] if c in df_infos.columns]
    df = df.merge(df_infos[cab_cols].drop_duplicates("representants_id"),
                  on="representants_id", how="left")
    wanted = ["denomination", "nom_usage_hatvp", "label_categorie_organisation",
              "denomination_client", "identifiant_national_client",
              "ancienclient", "datecessation"]
    cols = [c for c in wanted if c in df.columns]
    rename = {
        "denomination":               "Cabinet mandataire",
        "nom_usage_hatvp":            "Nom HATVP cabinet",
        "label_categorie_organisation": "Catégorie cabinet",
        "representants_id":           "ID Cabinet",
        "denomination_client":        "Client (donneur d'ordre)",
        "identifiant_national_client": "SIREN client",
        "ancienclient":               "Ancien client",
        "datecessation":              "Date cessation",
    }
    df = df[cols].rename(columns={k: v for k, v in rename.items() if k in cols})
    sort_col = "Cabinet mandataire" if "Cabinet mandataire" in df.columns else df.columns[0]
    return df.sort_values(sort_col, na_position="last")

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

# ─── FEEDBACK ─────────────────────────────────────────────────────────────────

def send_feedback_email(fb_type, message, user_email=""):
    form_id = os.environ.get("FORMSPREE_FORM_ID", "xqeyegea")
    if not form_id:
        return False, "Formspree non configuré (variable FORMSPREE_FORM_ID manquante)"
    body = f"Type : {fb_type}\n"
    if user_email:
        body += f"Email utilisateur : {user_email}\n"
    body += f"\nMessage :\n{message}"
    payload = {
        "subject": f"[HATVP To Table] {fb_type}",
        "message": body,
    }
    if user_email:
        payload["_replyto"] = user_email
    try:
        r = requests.post(
            f"https://formspree.io/f/{form_id}",
            json=payload,
            headers={"Accept": "application/json"},
            timeout=10,
        )
        if r.status_code == 200:
            return True, ""
        return False, f"Erreur Formspree : {r.status_code}"
    except Exception as e:
        return False, str(e)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🏛️ HATVP To Table")
    st.markdown(
        "<p style='font-family:DM Mono,monospace;font-size:12px;color:#556688;'>"
        "Répertoire des représentants d'intérêts · HATVP</p>",
        unsafe_allow_html=True)
    st.divider()
    st.markdown("### 🔍 Recherche")
    if "kw_rules" not in st.session_state:
        st.session_state.kw_rules = [{"keyword": "", "op": "Inclure"}]

    st.markdown("**Mots-clés**")
    to_delete = None
    for i, rule in enumerate(st.session_state.kw_rules):
        c1, c2, c3 = st.columns([3, 2, 0.6])
        with c1:
            st.session_state.kw_rules[i]["keyword"] = st.text_input(
                f"kw{i}", value=rule["keyword"], key=f"kw_{i}",
                label_visibility="collapsed",
                placeholder="ex : énergie, MiCA...")
        with c2:
            st.session_state.kw_rules[i]["op"] = st.selectbox(
                f"op{i}", ["Inclure", "Exclure"], key=f"op_{i}",
                label_visibility="collapsed",
                index=0 if rule["op"] == "Inclure" else 1)
        with c3:
            if len(st.session_state.kw_rules) > 1:
                if st.button("✕", key=f"del_{i}", use_container_width=True):
                    to_delete = i
    if to_delete is not None:
        st.session_state.kw_rules.pop(to_delete)
        st.rerun()
    if st.button("＋ Ajouter un critère", use_container_width=True):
        st.session_state.kw_rules.append({"keyword": "", "op": "Inclure"})
        st.rerun()

    keyword_rules = [r for r in st.session_state.kw_rules if r["keyword"].strip()]
    include_kws = [r["keyword"].strip() for r in keyword_rules if r["op"] == "Inclure"]
    exclude_kws = [r["keyword"].strip() for r in keyword_rules if r["op"] == "Exclure"]
    keyword_label = " ET ".join(f"« {k} »" for k in include_kws) if include_kws else ""
    if exclude_kws:
        keyword_label += (" SAUF " if keyword_label else "") + ", ".join(f"« {k} »" for k in exclude_kws)
    keyword_slug = "_".join((include_kws + exclude_kws)[:3]).replace(" ", "-")
    mode = st.radio("Mode de recherche",
        ["Objets d'activité", "Secteurs d'activité", "Organisations", "Personnes",
         "Donneurs d'ordre"], index=0,
        help=(
            "**Objets** : full-text dans ~95 000 descriptions. "
            "**Secteurs** : 31 catégories. "
            "**Organisations** : nom, sigle. "
            "**Personnes** : nom/prénom des dirigeants et collaborateurs."
        ))
    mode_key = {
        "Objets d'activité":  "objets",
        "Secteurs d'activité": "secteurs",
        "Organisations":       "organisations",
        "Personnes":           "personnes",
        "Donneurs d'ordre":    "donneurs",
    }[mode]

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
    st.divider()
    with st.popover("💬 Donner un feedback", use_container_width=True):
        st.markdown("##### Envoyer un retour")
        with st.form("feedback_form", clear_on_submit=True):
            fb_type = st.selectbox(
                "Type de retour",
                ["Suggestion", "Bug / Erreur", "Question", "Autre"])
            fb_msg = st.text_area(
                "Message *",
                placeholder="Décrivez votre retour, suggestion ou problème...",
                height=120)
            fb_email = st.text_input(
                "Votre email (optionnel)",
                placeholder="Pour un suivi éventuel")
            submitted = st.form_submit_button("Envoyer", use_container_width=True)
            if submitted:
                if not fb_msg.strip():
                    st.error("Le message ne peut pas être vide.")
                else:
                    ok, err = send_feedback_email(fb_type, fb_msg.strip(), fb_email.strip())
                    if ok:
                        st.success("Merci pour votre retour !")
                    else:
                        st.error(f"Erreur d'envoi : {err}")
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

with st.expander("📖 Comment utiliser cet outil ?", expanded=not keyword_rules):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
<div class="doc-card">
<h4>🔎 Mode Objets d'activité <span style="color:#7dd3fc;font-size:11px;">(défaut · recommandé)</span></h4>
<p>Recherche full-text dans les ~95 000 descriptions libres des actions de lobbying déclarées.<br><br>
<strong>Exemples :</strong><br>
→ <code>taxe carbone</code> · <code>CVAE</code> · <code>MiCA</code><br>
→ <code>réforme des retraites</code> · <code>loi APER</code><br>
→ <code>intelligence artificielle</code> · <code>RGPD</code>
</p></div>""", unsafe_allow_html=True)
        st.markdown("""
<div class="doc-card">
<h4>📂 Mode Secteurs d'activité</h4>
<p>Recherche dans les 31 secteurs prédéfinis déclarés par chaque représentant.<br>
Retourne toutes les organisations actives dans ce secteur, avec l'ensemble de leurs actions.<br><br>
<strong>Exemples :</strong><br>
→ <code>Energie</code> · <code>Santé</code> · <code>Numérique</code><br>
→ <code>Agriculture</code> · <code>Transports</code> · <code>Finance</code>
</p></div>""", unsafe_allow_html=True)
        st.markdown("""
<div class="doc-card">
<h4>🏢 Mode Organisations</h4>
<p>Recherche par nom, nom d'usage ou sigle dans le registre des représentants.<br>
Retourne les organisations dont le nom correspond, avec l'ensemble de leurs actions déclarées.<br><br>
<strong>Exemples :</strong><br>
→ <code>Total</code> · <code>BNP</code> · <code>MEDEF</code><br>
→ <code>France Assureurs</code> · <code>FNSEA</code>
</p></div>""", unsafe_allow_html=True)
        st.markdown("""
<div class="doc-card">
<h4>👤 Mode Personnes</h4>
<p>Recherche par nom ou prénom parmi les dirigeants et collaborateurs déclarés.<br>
<strong style="color:#fca5a5;">Nuance importante :</strong> l'onglet Personnes de l'export ne contient
que les personnes ayant effectivement matché — pas tous les membres des organisations trouvées.<br>
Les onglets Actions et Organisations couvrent en revanche toutes les activités de ces organisations.<br><br>
<strong>Exemples :</strong><br>
→ <code>Dupont</code> · <code>Jean Martin</code>
</p></div>""", unsafe_allow_html=True)
        st.markdown("""
<div class="doc-card">
<h4>🤝 Mode Donneurs d'ordre</h4>
<p>Recherche par nom de client dans les mandats déclarés par les cabinets de lobbying.<br>
Retourne uniquement les organisations qui agissent en tant que <em>mandataires</em> (cabinets) pour le compte de l'entité recherchée, ainsi que les actions menées spécifiquement pour ce donneur d'ordre.<br><br>
<strong style="color:#d8b4fe;">Nuance :</strong> l'onglet Clients de l'export contient les mandats correspondant au donneur d'ordre matché — pas tous les clients des cabinets trouvés.<br><br>
<strong>Exemples :</strong><br>
→ <code>Total</code> · <code>EDF</code> · <code>BNP Paribas</code>
</p></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""
<div class="doc-card">
<h4>📋 Structure de l'export Excel (4 onglets)</h4>
<p>
Quel que soit le mode de recherche, l'export suit toujours la même structure :<br><br>
<strong style="color:#93c5fd;">Onglet 1 — Actions de lobbying</strong><br>
→ 1 ligne par action déclarée par les organisations matchées<br>
→ Objet de l'action · période concernée · donneur d'ordre (si cabinet mandataire)<br>
→ Types d'actions menées · Responsables publics contactés · Domaines d'intervention<br><br>
<strong style="color:#6ee7b7;">Onglet 2 — Organisations</strong><br>
→ 1 ligne par organisation matchée<br>
→ Coordonnées · catégorie · identifiants · récapitulatif des actions<br><br>
<strong style="color:#fca5a5;">Onglet 3 — Dirigeants & Collaborateurs</strong><br>
→ 1 ligne par personne associée aux organisations matchées<br>
→ <em>En mode Personnes :</em> uniquement les personnes ayant matché<br><br>
<strong style="color:#e8c97a;">Onglet 4 — Clients & Mandats</strong><br>
→ Uniquement si les organisations matchées sont des <em>cabinets mandataires</em><br>
→ <em>Modes Objets / Secteurs :</em> clients liés aux actions ayant matché uniquement<br>
→ <em>Modes Organisations / Personnes :</em> tous les clients déclarés des organisations listées<br>
→ <em>Mode Donneurs d'ordre :</em> les donneurs d'ordre matchés avec leurs cabinets mandataires
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
→ Idéal pour un nom propre, un sigle ou un acronyme
</p></div>
<div class="doc-card">
<h4>⚡ Conseils</h4>
<p>
→ Les <strong style="color:#e2e8f0;">accents et la casse</strong> sont ignorés dans tous les modes<br>
→ En mode Objets, préférez des <strong style="color:#e2e8f0;">termes précis</strong><br>
→ En mode Personnes, le mode <strong style="color:#e2e8f0;">Exact</strong> est recommandé pour éviter les faux positifs sur les noms<br>
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
df_clients        = tables.get("clients",       pd.DataFrame())
df_beneficiaires  = tables.get("beneficiaires", pd.DataFrame())

# Stats
st.markdown(f"""
<div class="stat-row">
  <div class="stat-box"><div class="stat-number">{len(df_infos):,}</div><div class="stat-label">Représentants</div></div>
  <div class="stat-box"><div class="stat-number">{len(df_objets):,}</div><div class="stat-label">Objets d'activité</div></div>
  <div class="stat-box"><div class="stat-number">{df_secteurs[COL_SECTEUR].nunique()}</div><div class="stat-label">Secteurs</div></div>
  <div class="stat-box"><div class="stat-number">{len(df_actions):,}</div><div class="stat-label">Actions déclarées</div></div>
</div>""", unsafe_allow_html=True)

# Secteurs pills
if mode_key == "secteurs" and not keyword_rules:
    st.markdown("#### 📋 Secteurs disponibles")
    all_s = df_secteurs[COL_SECTEUR].dropna().value_counts()
    pills = "".join(f'<span class="sector-pill">{s} <span style="color:#334466;">({n})</span></span>'
                    for s, n in all_s.items())
    st.markdown(f'<div style="margin:12px 0;">{pills}</div>', unsafe_allow_html=True)

st.divider()

if not keyword_rules:
    st.markdown(
        "<div style='text-align:center;padding:40px;color:#334466;font-family:DM Mono,monospace;'>"
        "← Saisissez au moins un mot-clé dans la barre de gauche pour commencer</div>",
        unsafe_allow_html=True)
    st.stop()

# ─── RECHERCHE ────────────────────────────────────────────────────────────────

badge_class = {
    "objets": "mode-objets", "secteurs": "mode-secteurs",
    "organisations": "mode-orgs", "personnes": "mode-personnes",
    "donneurs": "mode-donneurs",
}.get(mode_key, "mode-objets")
st.markdown(
    f'<span class="mode-badge {badge_class}">Mode : {mode}</span>',
    unsafe_allow_html=True)
st.markdown(f"### Résultats pour **{keyword_label}**")

ids_retenus        = []
df_objets_match    = pd.DataFrame()
_dirigeants_for_s3    = df_dirigeants
_collaborateurs_for_s3 = df_collaborateurs

# ── Mode OBJETS ───────────────────────────────────────────────────────────────
if mode_key == "objets":
    df_objets_match = search_objets(keyword_rules, df_objets, exact=exact_match)
    if df_objets_match.empty:
        st.warning(f"Aucun objet d'activité ne correspond à {keyword_label}.")
        st.stop()
    exo_rep = df_exercices[[COL_EXO_ID, COL_REP_ID]].drop_duplicates()
    ids_retenus = (df_objets_match.merge(exo_rep, on=COL_EXO_ID, how="left")
                   [COL_REP_ID].dropna().unique().tolist())

    st.markdown(f"""
<div style='background:#1e407022;border:1px solid #3b82f644;border-radius:10px;padding:16px 20px;margin:12px 0;'>
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#93c5fd;'>{len(df_objets_match):,}</span>
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
                f"padding:8px 12px;border-left:2px solid #3b82f644;margin-bottom:6px;'>{objet}</div>",
                unsafe_allow_html=True)

# ── Mode SECTEURS ─────────────────────────────────────────────────────────────
elif mode_key == "secteurs":
    all_sectors_found = search_secteurs(keyword_rules, df_secteurs, exact=exact_match)
    if not all_sectors_found:
        st.warning(f"Aucun secteur ne correspond à {keyword_label}.")
        st.stop()
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

# ── Mode ORGANISATIONS ────────────────────────────────────────────────────────
elif mode_key == "organisations":
    df_orgs_match = search_organisations(keyword_rules, df_infos, exact=exact_match)
    if df_orgs_match.empty:
        st.warning(f"Aucune organisation ne correspond à {keyword_label}.")
        st.stop()
    ids_retenus = df_orgs_match[COL_REP_ID].dropna().unique().tolist()
    exo_ids = df_exercices[df_exercices[COL_REP_ID].isin(ids_retenus)][COL_EXO_ID].unique()
    df_objets_match = df_objets[df_objets[COL_EXO_ID].isin(exo_ids)]

    st.markdown(f"""
<div style='background:#1a3a2a22;border:1px solid #05966944;border-radius:10px;padding:16px 20px;margin:12px 0;'>
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#6ee7b7;'>{len(ids_retenus):,}</span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>organisations trouvées</span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#e8c97a;'>{len(df_objets_match):,}</span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>actions associées</span>
</div>""", unsafe_allow_html=True)

    with st.expander(f"🏢 Aperçu des {min(10, len(df_orgs_match))} premières organisations matchées"):
        for _, row in df_orgs_match.head(10).iterrows():
            nom = str(row.get(COL_DENOM, "")) or str(row.get("nom_usage_hatvp", ""))
            st.markdown(
                f"<div style='font-family:DM Mono,monospace;font-size:12px;color:#6ee7b7;"
                f"padding:8px 12px;border-left:2px solid #05966944;margin-bottom:6px;'>{nom}</div>",
                unsafe_allow_html=True)

# ── Mode PERSONNES ────────────────────────────────────────────────────────────
elif mode_key == "personnes":
    df_pers_match = search_personnes(keyword_rules, df_dirigeants, df_collaborateurs, exact=exact_match)
    if df_pers_match.empty:
        st.warning(f"Aucune personne ne correspond à {keyword_label}.")
        st.stop()
    ids_retenus = df_pers_match[COL_REP_ID].dropna().unique().tolist()
    exo_ids = df_exercices[df_exercices[COL_REP_ID].isin(ids_retenus)][COL_EXO_ID].unique()
    df_objets_match = df_objets[df_objets[COL_EXO_ID].isin(exo_ids)]
    # Restreindre la table personnes aux seules personnes matchées
    _dirigeants_for_s3 = (df_pers_match[df_pers_match["_statut_match"] == "Dirigeant"]
                          .drop(columns=["_statut_match"]))
    _collaborateurs_for_s3 = (df_pers_match[df_pers_match["_statut_match"] == "Collaborateur"]
                               .drop(columns=["_statut_match"]))

    nb_pers = len(df_pers_match)
    st.markdown(f"""
<div style='background:#3a202022;border:1px solid #dc262644;border-radius:10px;padding:16px 20px;margin:12px 0;'>
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#fca5a5;'>{nb_pers:,}</span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>personnes trouvées</span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#6ee7b7;'>{len(ids_retenus):,}</span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>organisations</span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#e8c97a;'>{len(df_objets_match):,}</span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>actions associées</span>
</div>""", unsafe_allow_html=True)

    with st.expander(f"👤 Aperçu des {min(10, nb_pers)} premières personnes matchées"):
        for _, row in df_pers_match.head(10).iterrows():
            nom_col = next((c for c in ["nom_prenom_dirigeant", "nom_prenom_collaborateur",
                                        "nom_dirigeant", "nom_collaborateur"] if c in row.index), None)
            nom = str(row[nom_col]) if nom_col else ""
            statut = row.get("_statut_match", "")
            st.markdown(
                f"<div style='font-family:DM Mono,monospace;font-size:12px;color:#fca5a5;"
                f"padding:8px 12px;border-left:2px solid #dc262644;margin-bottom:6px;'>"
                f"<span style='color:#556688;'>{statut}</span> — {nom}</div>",
                unsafe_allow_html=True)

# ── Mode DONNEURS D'ORDRE ─────────────────────────────────────────────────────
elif mode_key == "donneurs":
    df_do_match = search_donneurs_ordre(keyword_rules, df_clients, exact=exact_match)
    if df_do_match.empty:
        st.warning(f"Aucun donneur d'ordre ne correspond à {keyword_label}.")
        st.stop()

    matched_client_names = set(df_do_match["denomination_client"].dropna().unique())
    ids_retenus = df_do_match["representants_id"].dropna().unique().tolist()

    # Actions menées pour ces donneurs d'ordre via df_beneficiaires
    if (not df_beneficiaires.empty
            and COL_ARI_ID_APP in df_beneficiaires.columns
            and "action_menee_en_propre" in df_beneficiaires.columns
            and "beneficiaire_action_menee" in df_beneficiaires.columns):
        df_tiers_do = df_beneficiaires[
            (df_beneficiaires["action_menee_en_propre"].astype(str) == "0") &
            (df_beneficiaires["beneficiaire_action_menee"].isin(matched_client_names))
        ]
        ari_ids_do = df_tiers_do[COL_ARI_ID_APP].dropna().unique()
        if len(ari_ids_do) and not df_ari.empty and COL_ACT_ID in df_ari.columns:
            act_ids_do = df_ari[df_ari[COL_ARI_ID_APP].isin(ari_ids_do)][COL_ACT_ID].dropna().unique()
            df_objets_match = df_objets[df_objets[COL_ACT_ID].isin(act_ids_do)]
        else:
            df_objets_match = pd.DataFrame(columns=df_objets.columns)
    else:
        exo_ids = df_exercices[df_exercices[COL_REP_ID].isin(ids_retenus)][COL_EXO_ID].unique()
        df_objets_match = df_objets[df_objets[COL_EXO_ID].isin(exo_ids)]

    nb_do = len(matched_client_names)
    st.markdown(f"""
<div style='background:#2a1f4022;border:1px solid #a855f744;border-radius:10px;padding:16px 20px;margin:12px 0;'>
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#d8b4fe;'>{nb_do:,}</span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>donneurs d'ordre trouvés</span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#6ee7b7;'>{len(ids_retenus):,}</span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>cabinets mandataires</span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:#e8c97a;'>{len(df_objets_match):,}</span>
  <span style='font-family:DM Mono,monospace;color:#8899bb;font-size:13px;margin-left:8px;'>actions associées</span>
</div>""", unsafe_allow_html=True)

    with st.expander(f"🤝 Aperçu des {min(10, nb_do)} premiers donneurs d'ordre matchés"):
        for name in list(matched_client_names)[:10]:
            st.markdown(
                f"<div style='font-family:DM Mono,monospace;font-size:12px;color:#d8b4fe;"
                f"padding:8px 12px;border-left:2px solid #a855f744;margin-bottom:6px;'>{name}</div>",
                unsafe_allow_html=True)

# ─── ENRICHISSEMENT ───────────────────────────────────────────────────────────

if df_objets_match.empty:
    st.warning("Aucune action trouvée.")
    st.stop()

with st.spinner("🔀 Enrichissement des actions (période, types, responsables)..."):
    df_enriched = enrich_actions(
        df_objets_match, df_exercices,
        df_ari, df_actions, df_ministeres, df_domaines, df_beneficiaires)
    if COL_REP_ID in df_enriched.columns:
        df_enriched = df_enriched[df_enriched[COL_REP_ID].isin(ids_retenus)]

# ─── CONSTRUCTION ONGLETS ─────────────────────────────────────────────────────

df_s1 = build_actions_sheet(df_enriched, df_infos)
df_s2 = build_orgs_sheet(ids_retenus, df_infos, df_enriched)
df_s3 = build_persons_sheet(ids_retenus, df_s2, _dirigeants_for_s3, _collaborateurs_for_s3)
# En mode objets/secteurs : clients filtrés aux actions matchées uniquement
# En mode objets/secteurs : clients filtrés aux actions matchées uniquement
# En mode organisations/personnes : tous les clients des organisations listées
# En mode donneurs : uniquement les clients matchés (via allowed_clients)
if mode_key in ("objets", "secteurs"):
    _ari_ids_matched = (df_enriched[COL_ARI_ID_APP].dropna().unique()
                        if COL_ARI_ID_APP in df_enriched.columns else None)
    _allowed_clients = None
elif mode_key == "donneurs":
    _ari_ids_matched = None
    _allowed_clients = matched_client_names
else:
    _ari_ids_matched = None
    _allowed_clients = None
df_s4 = build_clients_sheet(ids_retenus, df_clients, df_infos,
                             ari_ids=_ari_ids_matched, df_beneficiaires=df_beneficiaires,
                             allowed_clients=_allowed_clients)

# ─── AFFICHAGE ONGLETS ────────────────────────────────────────────────────────

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    f"📋 Actions ({len(df_s1)})",
    f"🏢 Organisations ({len(df_s2)})",
    f"👤 Personnes ({len(df_s3) if not df_s3.empty else 0})",
    f"🤝 Clients ({len(df_s4) if not df_s4.empty else 0})",
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

def show_tab(df, label):
    if df is None or df.empty:
        st.info(f"Aucune donnée {label}.")
        return
    df_disp = df.head(max_preview).reset_index(drop=True)
    df_disp = df_disp.rename(columns={k: v for k, v in RENAME.items() if k in df_disp.columns})
    st.dataframe(df_disp, use_container_width=True, height=420)
    if len(df) > max_preview:
        st.caption(f"Affichage limité à {max_preview} lignes sur {len(df)}. Téléchargez l'Excel pour tout voir.")

with tab1:
    show_tab(df_s1, "d'actions")

with tab2:
    _df_s2_export = df_s2.drop(columns=[COL_REP_ID], errors="ignore")
    show_tab(_df_s2_export, "d'organisations")

with tab3:
    show_tab(df_s3, "de personnes")

with tab4:
    if df_s4.empty:
        st.info("Aucun client déclaré — les organisations matchées ne sont pas des mandataires, ou cette donnée n'est pas disponible.")
    else:
        show_tab(df_s4, "de clients")

# ─── EXPORT ───────────────────────────────────────────────────────────────────

st.divider()
excel_bytes = build_excel([
    ("Actions de lobbying",         df_s1),
    ("Organisations",               _df_s2_export),
    ("Dirigeants & Collaborateurs", df_s3),
    ("Clients & Mandats",           df_s4),
])
filename = f"hatvp_{keyword_slug}_{mode_key}.xlsx"
n3 = len(df_s3) if not df_s3.empty else 0
n4 = len(df_s4) if not df_s4.empty else 0
st.download_button(
    label=f"⬇️  Télécharger Excel — {len(df_s1)} actions · {len(df_s2)} orgs · {n3} personnes · {n4} clients",
    data=excel_bytes,
    file_name=filename,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)