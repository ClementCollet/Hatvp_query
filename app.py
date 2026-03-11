"""
HATVP To Table — Application Streamlit
Interface utilisateur : sidebar, en-tête, recherche, affichage, export.
"""

import streamlit as st
import pandas as pd

from hatvp import (
    load_all_tables,
    search_objets, search_secteurs, search_organisations,
    search_personnes, search_donneurs_ordre,
    enrich_actions,
    build_actions_sheet, build_orgs_sheet, build_persons_sheet, build_clients_sheet,
    build_excel,
    send_feedback_email,
    COL_SECTEUR, COL_OBJET, COL_REP_ID, COL_DENOM,
    COL_EXO_ID, COL_ACT_ID, COL_ARI_ID_APP,
)

# ─── CONFIG ───────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="HATVP To Table — Lobbying & transparence en France",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── SEO ──────────────────────────────────────────────────────────────────────

st.markdown("""
<meta name="description" content="Explorez et téléchargez les données du répertoire des représentants d'intérêts (lobbyistes) de la HATVP. Recherche full-text, export Excel en un clic — actions de lobbying, organisations, dirigeants.">
<meta name="keywords" content="HATVP, lobbying, représentants d'intérêts, transparence, open data, répertoire, France, lobbyistes">
<meta name="robots" content="index, follow">
<meta property="og:title" content="HATVP To Table — Données de lobbying en France">
<meta property="og:description" content="Accédez simplement aux données open data de la Haute Autorité pour la Transparence de la Vie Publique : recherchez parmi 95 000 actions de lobbying déclarées et exportez en Excel.">
<meta property="og:type" content="website">
<meta property="og:locale" content="fr_FR">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="HATVP To Table — Lobbying & transparence en France">
<meta name="twitter:description" content="Recherchez et téléchargez les données HATVP sur le lobbying en France. Export Excel en un clic.">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "HATVP To Table",
  "description": "Outil de recherche et d'export des données open data de la Haute Autorité pour la Transparence de la Vie Publique (HATVP) sur le lobbying en France.",
  "applicationCategory": "DataVisualization",
  "inLanguage": "fr",
  "isAccessibleForFree": true,
  "about": {
    "@type": "Dataset",
    "name": "Répertoire des représentants d'intérêts — HATVP",
    "url": "https://www.hatvp.fr/le-repertoire/",
    "publisher": {
      "@type": "GovernmentOrganization",
      "name": "Haute Autorité pour la Transparence de la Vie Publique",
      "url": "https://www.hatvp.fr"
    }
  }
}
</script>
""", unsafe_allow_html=True)

# ─── STYLES ───────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
.stApp { background-color: #0d1b35; }
[data-testid="stSidebar"] { background-color: #122040; border-right: 1px solid #1e3560; min-width: 340px !important; max-width: 340px !important; }
[data-testid="stSidebar"] > div:first-child { width: 360px !important; }
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
        "<p style='font-family:DM Mono,monospace;font-size:11px;color:#334466;line-height:1.6;'>"
        "Données open data · "
        "<a href='https://www.hatvp.fr/le-repertoire/' target='_blank' "
        "style='color:#4466aa;text-decoration:none;'>hatvp.fr/le-repertoire</a>"
        " · Cache 12h</p>",
        unsafe_allow_html=True)

# ─── EN-TÊTE ──────────────────────────────────────────────────────────────────

st.markdown("""
<h1 style='color:#e2e8f0;margin-bottom:4px;'>🏛️ HATVP To Table</h1>
<p style='font-family:DM Mono,monospace;color:#8899bb;font-size:14px;margin-top:0;margin-bottom:12px;'>
Accès simplifié aux données open data de la
<a href='https://www.hatvp.fr/le-repertoire/' target='_blank' style='color:#7dd3fc;text-decoration:none;'>
Haute Autorité pour la Transparence de la Vie Publique (HATVP)</a>
</p>
<p style='font-family:DM Mono,monospace;color:#556688;font-size:13px;margin-top:0;line-height:1.7;'>
La HATVP tient le répertoire officiel des représentants d'intérêts (lobbyistes) en France.
Ces données sont publiques mais leur format brut est difficile à exploiter.
<strong style='color:#8899bb;'>HATVP To Table</strong> vous permet de les
<strong style='color:#8899bb;'>rechercher par mot-clé</strong> et de les
<strong style='color:#8899bb;'>télécharger en tableau Excel</strong> structuré — actions de lobbying, organisations, dirigeants et collaborateurs.
</p>
""", unsafe_allow_html=True)
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

ids_retenus            = []
df_objets_match        = pd.DataFrame()
_dirigeants_for_s3     = df_dirigeants
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
