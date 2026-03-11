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

# ─── THÈME ────────────────────────────────────────────────────────────────────

if "theme" not in st.session_state:
    st.session_state.theme = "light"

dark = st.session_state.theme == "dark"

# Palette clair
LIGHT = {
    "bg_page": "#f8fafc",          "bg_sidebar": "#ffffff",
    "bg_card": "#ffffff",           "card_shadow": "box-shadow:0 1px 3px rgba(0,0,0,0.05);",
    "bg_input": "#ffffff",          "border": "#e2e8f0",
    "border_card": "#e2e8f0",       "hr": "#e2e8f0",
    "text_primary": "#1e293b",      "text_secondary": "#64748b",
    "text_muted": "#94a3b8",        "text_strong": "#334155",
    "accent": "#2563eb",            "link": "#2563eb",
    "stat_number": "#2563eb",       "stat_label": "#94a3b8",
    "card_heading": "#1e293b",      "card_text": "#64748b",
    "code_bg": "#f1f5f9",           "code_text": "#2563eb",
    "pill_bg": "#f1f5f9",           "pill_border": "#e2e8f0",
    "pill_text": "#475569",         "pill_count": "#94a3b8",
    "badge_objets":   ("bg:#dbeafe", "color:#1d4ed8", "border:#93c5fd"),
    "badge_secteurs": ("bg:#ede9fe", "color:#6d28d9", "border:#c4b5fd"),
    "badge_orgs":     ("bg:#d1fae5", "color:#065f46", "border:#6ee7b7"),
    "badge_pers":     ("bg:#fee2e2", "color:#991b1b", "border:#fca5a5"),
    "badge_do":       ("bg:#f3e8ff", "color:#6b21a8", "border:#d8b4fe"),
    "box_objets":   {"bg":"#eff6ff","br":"#bfdbfe","n1":"#1d4ed8","n2":"#d97706","lbl":"#64748b","pv":"#475569","pb":"#93c5fd"},
    "box_secteurs": {"bg":"#f5f3ff","br":"#ddd6fe","n1":"#6d28d9","n2":"#d97706","lbl":"#64748b"},
    "box_orgs":     {"bg":"#f0fdf4","br":"#bbf7d0","n1":"#059669","n2":"#d97706","lbl":"#64748b","pv":"#059669","pb":"#6ee7b7"},
    "box_pers":     {"bg":"#fef2f2","br":"#fecaca","n1":"#dc2626","n2":"#059669","n3":"#d97706","lbl":"#64748b","pv":"#dc2626","pb":"#fca5a5","st":"#94a3b8"},
    "box_do":       {"bg":"#faf5ff","br":"#e9d5ff","n1":"#9333ea","n2":"#059669","n3":"#d97706","lbl":"#64748b","pv":"#9333ea","pb":"#d8b4fe"},
    "doc_label": "#2563eb",  "doc_np": "#dc2626",  "doc_ndo": "#9333ea",
    "doc_o1": "#1d4ed8",     "doc_o2": "#059669",  "doc_o3": "#dc2626",   "doc_o4": "#d97706",
    "doc_strong": "#1e293b", "doc_link": "#2563eb",
    "h1": "#1e293b",         "h1_sub": "#64748b",   "h1_link": "#2563eb",
    "h1_desc": "#475569",    "h1_strong": "#334155",
    "empty": "#94a3b8",
    # overrides CSS Streamlit natif
    "st_bg": "#f8fafc",      "st_sbg": "#ffffff",   "st_text": "#1e293b",
}

# Palette sombre
DARK = {
    "bg_page": "#0d1b35",          "bg_sidebar": "#122040",
    "bg_card": "linear-gradient(135deg,#122040 0%,#1a2e58 100%)",
    "card_shadow": "",
    "bg_input": "#122040",          "border": "#1e3560",
    "border_card": "#2d4480",       "hr": "#1e3560",
    "text_primary": "#e2e8f0",      "text_secondary": "#8899bb",
    "text_muted": "#556688",        "text_strong": "#8899bb",
    "accent": "#3b82f6",            "link": "#7dd3fc",
    "stat_number": "#e8c97a",       "stat_label": "#6677aa",
    "card_heading": "#e8c97a",      "card_text": "#8899bb",
    "code_bg": "#0d1b35",           "code_text": "#7dd3fc",
    "pill_bg": "#1a2e58",           "pill_border": "#2d4480",
    "pill_text": "#93b4d8",         "pill_count": "#334466",
    "badge_objets":   ("bg:#1e4070", "color:#93c5fd", "border:#3b82f655"),
    "badge_secteurs": ("bg:#2d1f4e", "color:#c4b5fd", "border:#7c3aed55"),
    "badge_orgs":     ("bg:#1a3a2a", "color:#6ee7b7", "border:#05966955"),
    "badge_pers":     ("bg:#3a2020", "color:#fca5a5", "border:#dc262655"),
    "badge_do":       ("bg:#2a1f40", "color:#d8b4fe", "border:#a855f755"),
    "box_objets":   {"bg":"#1e407022","br":"#3b82f644","n1":"#93c5fd","n2":"#e8c97a","lbl":"#8899bb","pv":"#93b4d8","pb":"#3b82f644"},
    "box_secteurs": {"bg":"#2d1f4e22","br":"#7c3aed44","n1":"#c4b5fd","n2":"#e8c97a","lbl":"#8899bb"},
    "box_orgs":     {"bg":"#1a3a2a22","br":"#05966944","n1":"#6ee7b7","n2":"#e8c97a","lbl":"#8899bb","pv":"#6ee7b7","pb":"#05966944"},
    "box_pers":     {"bg":"#3a202022","br":"#dc262644","n1":"#fca5a5","n2":"#6ee7b7","n3":"#e8c97a","lbl":"#8899bb","pv":"#fca5a5","pb":"#dc262644","st":"#556688"},
    "box_do":       {"bg":"#2a1f4022","br":"#a855f744","n1":"#d8b4fe","n2":"#6ee7b7","n3":"#e8c97a","lbl":"#8899bb","pv":"#d8b4fe","pb":"#a855f744"},
    "doc_label": "#7dd3fc", "doc_np": "#fca5a5",  "doc_ndo": "#d8b4fe",
    "doc_o1": "#93c5fd",    "doc_o2": "#6ee7b7",  "doc_o3": "#fca5a5",   "doc_o4": "#e8c97a",
    "doc_strong": "#e2e8f0","doc_link": "#7dd3fc",
    "h1": "#e2e8f0",        "h1_sub": "#8899bb",   "h1_link": "#7dd3fc",
    "h1_desc": "#556688",   "h1_strong": "#8899bb",
    "empty": "#334466",
    "st_bg": "#0d1b35",     "st_sbg": "#122040",   "st_text": "#e2e8f0",
}

C = DARK if dark else LIGHT

# Badge helpers
def _badge_css(t):
    bg, color, border = t
    return f"background:{bg[3:]};color:{color[6:]};border:1px solid {border[7:]};"

# ─── SEO ──────────────────────────────────────────────────────────────────────

# ⚠️ Mets à jour cette URL si tu configures un domaine personnalisé
SITE_URL = "https://hatvp-explorer.onrender.com"

st.markdown(f"""
<link rel="canonical" href="{SITE_URL}">
<meta name="description" content="Consultez le répertoire HATVP des lobbyistes en France : plus de 95 000 actions de lobbying déclarées, recherche par mot-clé, organisation ou personne, export Excel structuré. Données open data de la Haute Autorité pour la Transparence de la Vie Publique.">
<meta name="keywords" content="HATVP, lobbying, représentants d'intérêts, transparence, open data, répertoire, France, lobbyistes, actions de lobbying, export Excel">
<meta name="robots" content="index, follow">
<meta name="author" content="HATVP To Table">

<meta property="og:title" content="HATVP To Table — Répertoire des lobbyistes en France">
<meta property="og:description" content="Recherchez et téléchargez les données open data HATVP : 95 000 actions de lobbying déclarées, organisations, dirigeants — export Excel en un clic.">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE_URL}">
<meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="HATVP To Table">

<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="HATVP To Table — Répertoire des lobbyistes en France">
<meta name="twitter:description" content="Recherchez et téléchargez les données HATVP sur le lobbying en France. Export Excel en un clic.">
<meta name="twitter:site" content="@hatvp">

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "HATVP To Table",
  "url": "{SITE_URL}",
  "description": "Outil de recherche et d'export des données open data de la HATVP sur le lobbying en France. Permet de rechercher parmi plus de 95 000 actions de lobbying déclarées par les représentants d'intérêts inscrits au répertoire officiel.",
  "applicationCategory": "DataVisualization",
  "inLanguage": "fr",
  "isAccessibleForFree": true,
  "featureList": [
    "Recherche full-text dans les actions de lobbying",
    "Recherche par secteur, organisation, personne ou donneur d'ordre",
    "Export Excel structuré en 4 onglets",
    "Matching élargi ou exact"
  ],
  "about": {{
    "@type": "Dataset",
    "name": "Répertoire des représentants d'intérêts — HATVP",
    "url": "https://www.hatvp.fr/le-repertoire/",
    "license": "https://www.etalab.gouv.fr/licence-ouverte-open-licence",
    "publisher": {{
      "@type": "GovernmentOrganization",
      "name": "Haute Autorité pour la Transparence de la Vie Publique",
      "url": "https://www.hatvp.fr",
      "sameAs": "https://fr.wikipedia.org/wiki/Haute_Autorit%C3%A9_pour_la_transparence_de_la_vie_publique"
    }}
  }}
}}
</script>
""", unsafe_allow_html=True)

# ─── STYLES ───────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');
html, body, [class*="css"] {{ font-family: 'Syne', sans-serif; }}

/* Overrides Streamlit natifs */
.stApp                             {{ background-color: {C['bg_page']} !important; }}
[data-testid="stAppViewContainer"] {{ background-color: {C['bg_page']} !important; }}
[data-testid="stHeader"]           {{ background-color: {C['bg_page']} !important; }}
.stMarkdown, .stText, p, label     {{ color: {C['text_primary']} !important; }}
[data-testid="stSidebar"]          {{ background-color: {C['bg_sidebar']}; border-right:1px solid {C['border']}; min-width:380px !important; max-width:380px !important; }}
[data-testid="stSidebar"] > div:first-child {{ width:380px !important; }}
[data-testid="stSidebar"] * {{ color: {C['text_primary']} !important; }}

h1 {{ font-family:'Syne',sans-serif !important; font-weight:800 !important; letter-spacing:-1px !important; }}
h2, h3 {{ font-family:'Syne',sans-serif !important; font-weight:700 !important; }}

.doc-card {{ background:{C['bg_card']}; border:1px solid {C['border_card']}; border-radius:12px; padding:20px 24px; margin-bottom:14px; {C['card_shadow']} }}
.doc-card h4 {{ color:{C['card_heading']}; font-family:'Syne',sans-serif; font-weight:700; font-size:15px; margin:0 0 8px 0; }}
.doc-card p  {{ color:{C['card_text']}; font-family:'DM Mono',monospace; font-size:13px; margin:0; line-height:1.6; }}
.doc-card code {{ background:{C['code_bg']}; color:{C['code_text']}; padding:2px 6px; border-radius:4px; font-size:12px; }}

.stat-row {{ display:flex; gap:12px; margin:16px 0; }}
.stat-box {{ flex:1; background:{C['bg_card']}; border:1px solid {C['border']}; border-radius:10px; padding:16px; text-align:center; {C['card_shadow']} }}
.stat-number {{ font-family:'Syne',sans-serif; font-size:28px; font-weight:800; color:{C['stat_number']}; line-height:1; }}
.stat-label  {{ font-family:'DM Mono',monospace; font-size:11px; color:{C['stat_label']}; margin-top:4px; text-transform:uppercase; letter-spacing:0.5px; }}

.mode-badge    {{ display:inline-block; padding:4px 12px; border-radius:20px; font-family:'DM Mono',monospace; font-size:12px; font-weight:500; margin-bottom:8px; }}
.mode-objets   {{ {_badge_css(C['badge_objets'])} }}
.mode-secteurs {{ {_badge_css(C['badge_secteurs'])} }}
.mode-orgs     {{ {_badge_css(C['badge_orgs'])} }}
.mode-personnes {{ {_badge_css(C['badge_pers'])} }}
.mode-donneurs {{ {_badge_css(C['badge_do'])} }}

.sector-pill {{ display:inline-block; background:{C['pill_bg']}; border:1px solid {C['pill_border']}; border-radius:20px; padding:5px 14px; margin:4px; font-family:'DM Mono',monospace; font-size:12px; color:{C['pill_text']}; }}

.stButton > button {{ background:linear-gradient(135deg,#2563eb,#3b82f6) !important; color:white !important; border:none !important; border-radius:8px !important; font-family:'Syne',sans-serif !important; font-weight:600 !important; }}
.stDownloadButton > button {{ background:linear-gradient(135deg,#065f46,#047857) !important; color:white !important; border:none !important; border-radius:8px !important; font-family:'Syne',sans-serif !important; font-weight:600 !important; }}
.stTextInput > div > div > input {{ background:{C['bg_input']} !important; border:1px solid {C['border']} !important; border-radius:8px !important; color:{C['text_primary']} !important; font-family:'DM Mono',monospace !important; }}
.stTextInput > div > div > input::placeholder {{ color:{C['text_muted']} !important; opacity:1 !important; }}
.stSelectbox > div > div {{ background:{C['bg_input']} !important; border:1px solid {C['border']} !important; border-radius:8px !important; }}

/* Tooltips (bulles d'aide "?") */
[data-baseweb="tooltip"] {{ background-color:{C['bg_card']} !important; border:1px solid {C['border']} !important; border-radius:8px !important; }}
[data-baseweb="tooltip"] * {{ color:{C['text_primary']} !important; }}
[role="tooltip"] {{ background-color:{C['bg_card']} !important; border:1px solid {C['border']} !important; border-radius:8px !important; color:{C['text_primary']} !important; }}
hr {{ border-color:{C['hr']} !important; }}

/* Popover (bouton Donner un feedback) */
[data-testid="stPopover"] button {{ background:linear-gradient(135deg,#2563eb,#3b82f6) !important; color:white !important; border:none !important; border-radius:8px !important; font-family:'Syne',sans-serif !important; font-weight:600 !important; }}

/* Expanders */
[data-testid="stExpander"] {{ border-color:{C['border']} !important; background-color:{C['bg_page']} !important; }}
[data-testid="stExpander"] summary {{ color:{C['text_primary']} !important; background-color:{C['bg_page']} !important; }}
[data-testid="stExpander"] details {{ background-color:{C['bg_page']} !important; }}
[data-testid="stExpander"] details > div {{ background-color:{C['bg_page']} !important; }}
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🏛️ HATVP To Table")
    st.markdown(
        f"<p style='font-family:DM Mono,monospace;font-size:12px;color:{C['text_muted']};'>"
        "Répertoire des représentants d'intérêts · HATVP</p>",
        unsafe_allow_html=True)

    # Toggle thème
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        if st.button("☀️ Clair", use_container_width=True,
                     type="secondary" if dark else "primary"):
            st.session_state.theme = "light"
            st.rerun()
    with t_col2:
        if st.button("🌙 Sombre", use_container_width=True,
                     type="primary" if dark else "secondary"):
            st.session_state.theme = "dark"
            st.rerun()

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
        f"<p style='font-family:DM Mono,monospace;font-size:11px;color:{C['text_muted']};line-height:1.6;'>"
        f"Données open data · "
        f"<a href='https://www.hatvp.fr/le-repertoire/' target='_blank' "
        f"style='color:{C['link']};text-decoration:none;'>hatvp.fr/le-repertoire</a>"
        f" · Cache 12h</p>",
        unsafe_allow_html=True)

# ─── EN-TÊTE ──────────────────────────────────────────────────────────────────

st.markdown(f"""
<h1 style='color:{C['h1']};margin-bottom:4px;'>🏛️ HATVP To Table</h1>
<p style='font-family:DM Mono,monospace;color:{C['h1_sub']};font-size:14px;margin-top:0;margin-bottom:12px;'>
Accès simplifié aux données open data de la
<a href='https://www.hatvp.fr/le-repertoire/' target='_blank' style='color:{C['h1_link']};text-decoration:none;'>
Haute Autorité pour la Transparence de la Vie Publique (HATVP)</a>
</p>
<p style='font-family:DM Mono,monospace;color:{C['h1_desc']};font-size:13px;margin-top:0;line-height:1.7;'>
La HATVP tient le répertoire officiel des représentants d'intérêts (lobbyistes) en France.
Ces données sont publiques mais leur format brut est difficile à exploiter.
<strong style='color:{C['h1_strong']};'>HATVP To Table</strong> vous permet de les
<strong style='color:{C['h1_strong']};'>rechercher par mot-clé</strong> et de les
<strong style='color:{C['h1_strong']};'>télécharger en tableau Excel</strong> structuré — actions de lobbying, organisations, dirigeants et collaborateurs.
</p>
""", unsafe_allow_html=True)
st.divider()

# ─── DOCUMENTATION ────────────────────────────────────────────────────────────

with st.expander("📖 Comment utiliser cet outil ?", expanded=not keyword_rules):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
<div class="doc-card">
<h4>🔎 Mode Objets d'activité <span style="color:{C['doc_label']};font-size:11px;">(défaut · recommandé)</span></h4>
<p>Recherche full-text dans les ~95 000 descriptions libres des actions de lobbying déclarées.<br><br>
<strong>Exemples :</strong><br>
→ <code>taxe carbone</code> · <code>CVAE</code> · <code>MiCA</code><br>
→ <code>réforme des retraites</code> · <code>loi APER</code><br>
→ <code>intelligence artificielle</code> · <code>RGPD</code>
</p></div>""", unsafe_allow_html=True)
        st.markdown(f"""
<div class="doc-card">
<h4>📂 Mode Secteurs d'activité</h4>
<p>Recherche dans les 31 secteurs prédéfinis déclarés par chaque représentant.<br>
Retourne toutes les organisations actives dans ce secteur, avec l'ensemble de leurs actions.<br><br>
<strong>Exemples :</strong><br>
→ <code>Energie</code> · <code>Santé</code> · <code>Numérique</code><br>
→ <code>Agriculture</code> · <code>Transports</code> · <code>Finance</code>
</p></div>""", unsafe_allow_html=True)
        st.markdown(f"""
<div class="doc-card">
<h4>🏢 Mode Organisations</h4>
<p>Recherche par nom, nom d'usage ou sigle dans le registre des représentants.<br>
Retourne les organisations dont le nom correspond, avec l'ensemble de leurs actions déclarées.<br><br>
<strong>Exemples :</strong><br>
→ <code>Total</code> · <code>BNP</code> · <code>MEDEF</code><br>
→ <code>France Assureurs</code> · <code>FNSEA</code>
</p></div>""", unsafe_allow_html=True)
        st.markdown(f"""
<div class="doc-card">
<h4>👤 Mode Personnes</h4>
<p>Recherche par nom ou prénom parmi les dirigeants et collaborateurs déclarés.<br>
<strong style="color:{C['doc_np']};">Nuance importante :</strong> l'onglet Personnes de l'export ne contient
que les personnes ayant effectivement matché — pas tous les membres des organisations trouvées.<br>
Les onglets Actions et Organisations couvrent en revanche toutes les activités de ces organisations.<br><br>
<strong>Exemples :</strong><br>
→ <code>Dupont</code> · <code>Jean Martin</code>
</p></div>""", unsafe_allow_html=True)
        st.markdown(f"""
<div class="doc-card">
<h4>🤝 Mode Donneurs d'ordre</h4>
<p>Recherche par nom de client dans les mandats déclarés par les cabinets de lobbying.<br>
Retourne uniquement les organisations qui agissent en tant que <em>mandataires</em> (cabinets) pour le compte de l'entité recherchée, ainsi que les actions menées spécifiquement pour ce donneur d'ordre.<br><br>
<strong style="color:{C['doc_ndo']};">Nuance :</strong> l'onglet Clients de l'export contient les mandats correspondant au donneur d'ordre matché — pas tous les clients des cabinets trouvés.<br><br>
<strong>Exemples :</strong><br>
→ <code>Total</code> · <code>EDF</code> · <code>BNP Paribas</code>
</p></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
<div class="doc-card">
<h4>📋 Structure de l'export Excel (4 onglets)</h4>
<p>
Quel que soit le mode de recherche, l'export suit toujours la même structure :<br><br>
<strong style="color:{C['doc_o1']};">Onglet 1 — Actions de lobbying</strong><br>
→ 1 ligne par action déclarée par les organisations matchées<br>
→ Objet de l'action · période concernée · donneur d'ordre (si cabinet mandataire)<br>
→ Types d'actions menées · Responsables publics contactés · Domaines d'intervention<br><br>
<strong style="color:{C['doc_o2']};">Onglet 2 — Organisations</strong><br>
→ 1 ligne par organisation matchée<br>
→ Coordonnées · catégorie · identifiants · récapitulatif des actions<br><br>
<strong style="color:{C['doc_o3']};">Onglet 3 — Dirigeants & Collaborateurs</strong><br>
→ 1 ligne par personne associée aux organisations matchées<br>
→ <em>En mode Personnes :</em> uniquement les personnes ayant matché<br><br>
<strong style="color:{C['doc_o4']};">Onglet 4 — Clients & Mandats</strong><br>
→ Uniquement si les organisations matchées sont des <em>cabinets mandataires</em><br>
→ <em>Modes Objets / Secteurs :</em> clients liés aux actions ayant matché uniquement<br>
→ <em>Modes Organisations / Personnes :</em> tous les clients déclarés des organisations listées<br>
→ <em>Mode Donneurs d'ordre :</em> les donneurs d'ordre matchés avec leurs cabinets mandataires
</p></div>""", unsafe_allow_html=True)
        st.markdown(f"""
<div class="doc-card">
<h4>🎯 Matching Élargi vs Exact</h4>
<p>
<strong style="color:{C['doc_strong']};">Élargi</strong> (défaut) — sous-chaînes + variantes orthographiques<br>
→ <code>seb</code> trouve <em>SEB SA</em>, <em>Sebastian</em>, <em>Sébastien</em><br>
→ <code>energie</code> trouve <em>énergie</em>, <em>énergétique</em>, <em>Energie verte</em><br>
→ Idéal pour explorer un thème large<br><br>
<strong style="color:{C['doc_strong']};">Exact</strong> — mot entier uniquement (frontières de mots)<br>
→ <code>seb</code> trouve <em>SEB SA</em>, <em>groupe SEB</em> mais pas <em>Sebastian</em><br>
→ <code>loi</code> trouve <em>la loi</em>, <em>cette loi,</em> mais pas <em>lobbying</em><br>
→ Idéal pour un nom propre, un sigle ou un acronyme
</p></div>
<div class="doc-card">
<h4>⚡ Conseils</h4>
<p>
→ Les <strong style="color:{C['doc_strong']};">accents et la casse</strong> sont ignorés dans tous les modes<br>
→ En mode Objets, préférez des <strong style="color:{C['doc_strong']};">termes précis</strong><br>
→ En mode Personnes, le mode <strong style="color:{C['doc_strong']};">Exact</strong> est recommandé pour éviter les faux positifs sur les noms<br>
→ La <strong style="color:{C['doc_strong']};">période</strong> correspond à l'exercice déclaratif
(ex: 01/04/2024 – 31/03/2025), pas à la date de publication<br>
→ Source : <a href="https://www.hatvp.fr/le-repertoire/" target="_blank"
style="color:{C['doc_link']};">hatvp.fr/le-repertoire</a>
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
    pills = "".join(
        f'<span class="sector-pill">{s} <span style="color:{C["pill_count"]};">({n})</span></span>'
        for s, n in all_s.items())
    st.markdown(f'<div style="margin:12px 0;">{pills}</div>', unsafe_allow_html=True)

st.divider()

if not keyword_rules:
    st.markdown(
        f"<div style='text-align:center;padding:40px;color:{C['empty']};font-family:DM Mono,monospace;'>"
        "← Saisissez au moins un mot-clé dans la barre de gauche pour commencer</div>",
        unsafe_allow_html=True)
    st.stop()

# ─── RECHERCHE ────────────────────────────────────────────────────────────────

badge_class = {
    "objets": "mode-objets", "secteurs": "mode-secteurs",
    "organisations": "mode-orgs", "personnes": "mode-personnes",
    "donneurs": "mode-donneurs",
}.get(mode_key, "mode-objets")
st.markdown(f'<span class="mode-badge {badge_class}">Mode : {mode}</span>', unsafe_allow_html=True)
st.markdown(f"### Résultats pour **{keyword_label}**")

ids_retenus            = []
df_objets_match        = pd.DataFrame()
_dirigeants_for_s3     = df_dirigeants
_collaborateurs_for_s3 = df_collaborateurs
B = C["box_objets"]  # raccourci, redéfini par mode

# ── Mode OBJETS ───────────────────────────────────────────────────────────────
if mode_key == "objets":
    B = C["box_objets"]
    df_objets_match = search_objets(keyword_rules, df_objets, exact=exact_match)
    if df_objets_match.empty:
        st.warning(f"Aucun objet d'activité ne correspond à {keyword_label}.")
        st.stop()
    exo_rep = df_exercices[[COL_EXO_ID, COL_REP_ID]].drop_duplicates()
    ids_retenus = (df_objets_match.merge(exo_rep, on=COL_EXO_ID, how="left")
                   [COL_REP_ID].dropna().unique().tolist())

    st.markdown(f"""
<div style='background:{B["bg"]};border:1px solid {B["br"]};border-radius:10px;padding:16px 20px;margin:12px 0;'>
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:{B["n1"]};'>{len(df_objets_match):,}</span>
  <span style='font-family:DM Mono,monospace;color:{B["lbl"]};font-size:13px;margin-left:8px;'>actions trouvées</span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:{B["n2"]};'>{len(ids_retenus):,}</span>
  <span style='font-family:DM Mono,monospace;color:{B["lbl"]};font-size:13px;margin-left:8px;'>organisations</span>
</div>""", unsafe_allow_html=True)

    with st.expander(f"📝 Aperçu des {min(10, len(df_objets_match))} premiers objets matchés"):
        for _, row in df_objets_match.head(10).iterrows():
            objet = str(row[COL_OBJET])
            st.markdown(
                f"<div style='font-family:DM Mono,monospace;font-size:12px;color:{B['pv']};"
                f"padding:8px 12px;border-left:2px solid {B['pb']};margin-bottom:6px;'>{objet}</div>",
                unsafe_allow_html=True)

# ── Mode SECTEURS ─────────────────────────────────────────────────────────────
elif mode_key == "secteurs":
    B = C["box_secteurs"]
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
<div style='background:{B["bg"]};border:1px solid {B["br"]};border-radius:10px;padding:16px 20px;margin:12px 0;'>
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:{B["n1"]};'>{len(df_objets_match):,}</span>
  <span style='font-family:DM Mono,monospace;color:{B["lbl"]};font-size:13px;margin-left:8px;'>actions associées</span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:{B["n2"]};'>{len(ids_retenus):,}</span>
  <span style='font-family:DM Mono,monospace;color:{B["lbl"]};font-size:13px;margin-left:8px;'>organisations</span>
</div>""", unsafe_allow_html=True)

# ── Mode ORGANISATIONS ────────────────────────────────────────────────────────
elif mode_key == "organisations":
    B = C["box_orgs"]
    df_orgs_match = search_organisations(keyword_rules, df_infos, exact=exact_match)
    if df_orgs_match.empty:
        st.warning(f"Aucune organisation ne correspond à {keyword_label}.")
        st.stop()
    ids_retenus = df_orgs_match[COL_REP_ID].dropna().unique().tolist()
    exo_ids = df_exercices[df_exercices[COL_REP_ID].isin(ids_retenus)][COL_EXO_ID].unique()
    df_objets_match = df_objets[df_objets[COL_EXO_ID].isin(exo_ids)]

    st.markdown(f"""
<div style='background:{B["bg"]};border:1px solid {B["br"]};border-radius:10px;padding:16px 20px;margin:12px 0;'>
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:{B["n1"]};'>{len(ids_retenus):,}</span>
  <span style='font-family:DM Mono,monospace;color:{B["lbl"]};font-size:13px;margin-left:8px;'>organisations trouvées</span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:{B["n2"]};'>{len(df_objets_match):,}</span>
  <span style='font-family:DM Mono,monospace;color:{B["lbl"]};font-size:13px;margin-left:8px;'>actions associées</span>
</div>""", unsafe_allow_html=True)

    with st.expander(f"🏢 Aperçu des {min(10, len(df_orgs_match))} premières organisations matchées"):
        for _, row in df_orgs_match.head(10).iterrows():
            nom = str(row.get(COL_DENOM, "")) or str(row.get("nom_usage_hatvp", ""))
            st.markdown(
                f"<div style='font-family:DM Mono,monospace;font-size:12px;color:{B['pv']};"
                f"padding:8px 12px;border-left:2px solid {B['pb']};margin-bottom:6px;'>{nom}</div>",
                unsafe_allow_html=True)

# ── Mode PERSONNES ────────────────────────────────────────────────────────────
elif mode_key == "personnes":
    B = C["box_pers"]
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
<div style='background:{B["bg"]};border:1px solid {B["br"]};border-radius:10px;padding:16px 20px;margin:12px 0;'>
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:{B["n1"]};'>{nb_pers:,}</span>
  <span style='font-family:DM Mono,monospace;color:{B["lbl"]};font-size:13px;margin-left:8px;'>personnes trouvées</span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:{B["n2"]};'>{len(ids_retenus):,}</span>
  <span style='font-family:DM Mono,monospace;color:{B["lbl"]};font-size:13px;margin-left:8px;'>organisations</span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:{B["n3"]};'>{len(df_objets_match):,}</span>
  <span style='font-family:DM Mono,monospace;color:{B["lbl"]};font-size:13px;margin-left:8px;'>actions associées</span>
</div>""", unsafe_allow_html=True)

    with st.expander(f"👤 Aperçu des {min(10, nb_pers)} premières personnes matchées"):
        for _, row in df_pers_match.head(10).iterrows():
            nom_col = next((c for c in ["nom_prenom_dirigeant", "nom_prenom_collaborateur",
                                        "nom_dirigeant", "nom_collaborateur"] if c in row.index), None)
            nom = str(row[nom_col]) if nom_col else ""
            statut = row.get("_statut_match", "")
            st.markdown(
                f"<div style='font-family:DM Mono,monospace;font-size:12px;color:{B['pv']};"
                f"padding:8px 12px;border-left:2px solid {B['pb']};margin-bottom:6px;'>"
                f"<span style='color:{B['st']};'>{statut}</span> — {nom}</div>",
                unsafe_allow_html=True)

# ── Mode DONNEURS D'ORDRE ─────────────────────────────────────────────────────
elif mode_key == "donneurs":
    B = C["box_do"]
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
<div style='background:{B["bg"]};border:1px solid {B["br"]};border-radius:10px;padding:16px 20px;margin:12px 0;'>
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:{B["n1"]};'>{nb_do:,}</span>
  <span style='font-family:DM Mono,monospace;color:{B["lbl"]};font-size:13px;margin-left:8px;'>donneurs d'ordre trouvés</span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:{B["n2"]};'>{len(ids_retenus):,}</span>
  <span style='font-family:DM Mono,monospace;color:{B["lbl"]};font-size:13px;margin-left:8px;'>cabinets mandataires</span>
  &nbsp;·&nbsp;
  <span style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:{B["n3"]};'>{len(df_objets_match):,}</span>
  <span style='font-family:DM Mono,monospace;color:{B["lbl"]};font-size:13px;margin-left:8px;'>actions associées</span>
</div>""", unsafe_allow_html=True)

    with st.expander(f"🤝 Aperçu des {min(10, nb_do)} premiers donneurs d'ordre matchés"):
        for name in list(matched_client_names)[:10]:
            st.markdown(
                f"<div style='font-family:DM Mono,monospace;font-size:12px;color:{B['pv']};"
                f"padding:8px 12px;border-left:2px solid {B['pb']};margin-bottom:6px;'>{name}</div>",
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
