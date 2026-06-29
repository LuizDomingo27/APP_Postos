"""
ui/styles.py
-------------
Centraliza todo o CSS customizado da aplicação. A ideia de manter o CSS
como uma função que devolve uma string (em vez de espalhar `st.markdown`
pelo código) é permitir reaproveitar o mesmo tema em qualquer página ou
componente futuro, e ter um único lugar para ajustar cores/fontes.

O tema usa CSS Custom Properties (variáveis CSS) espelhando
`core.config.Theme`, então qualquer ajuste de paleta deve ser feito nos
dois lugares (Theme = usado pelo ECharts / Python, CSS vars = usado pelo
HTML/CSS). Manter os dois sincronizados é responsabilidade de quem
alterar a paleta no futuro.
"""

from __future__ import annotations

from core.config import Theme


def build_css() -> str:
    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

:root {{
    --bg-primary: {Theme.BG_PRIMARY};
    --bg-secondary: {Theme.BG_SECONDARY};
    --card-bg: {Theme.CARD_BG};
    --card-border: {Theme.CARD_BORDER};
    --accent: {Theme.ACCENT};
    --accent-soft: {Theme.ACCENT_SOFT};
    --accent-glow: {Theme.ACCENT_GLOW};
    --positive: {Theme.POSITIVE};
    --negative: {Theme.NEGATIVE};
    --neutral: {Theme.NEUTRAL};
    --text-primary: {Theme.TEXT_PRIMARY};
    --text-muted: {Theme.TEXT_MUTED};
    --font-heading: {Theme.FONT_HEADING};
    --font-body: {Theme.FONT_BODY};
}}

/* ---------- Base ---------- */
html, body, [class*="css"] {{
    font-family: var(--font-body);
}}

.stApp {{
    background: radial-gradient(circle at top left, #0E171B 0%, var(--bg-primary) 55%);
}}

h1, h2, h3, h4 {{
    font-family: var(--font-heading) !important;
    color: var(--text-primary) !important;
    letter-spacing: 0.2px;
}}

p, span, label, div {{
    color: var(--text-primary);
}}

/* ---------- Cabeçalho ---------- */
.app-header {{
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 0.25rem 0 1.25rem 0;
    border-bottom: 1px solid var(--card-border);
    margin-bottom: 1.5rem;
}}

.app-header .title-row {{
    display: flex;
    align-items: center;
    gap: 0.6rem;
}}

.app-header .title-row .icon {{
    font-size: 1.9rem;
    filter: drop-shadow(0 0 10px var(--accent-glow));
}}

.app-header h1 {{
    font-size: 1.65rem;
    margin: 0;
}}

.app-header .subtitle {{
    color: var(--text-muted);
    font-size: 0.92rem;
    margin-top: 2px;
}}

/* ---------- Grid de Cards (KPIs) ---------- */
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 14px;
    margin-bottom: 1.6rem;
}}

.kpi-card {{
    background: linear-gradient(180deg, var(--card-bg) 0%, rgba(20, 28, 33, 0.6) 100%);
    border: 1px solid var(--card-border);
    border-radius: 14px;
    padding: 1.05rem 1.15rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.15s ease, border-color 0.15s ease;
}}

.kpi-card::before {{
    content: "";
    position: absolute;
    inset: 0;
    background: radial-gradient(120px 60px at 90% -10%, var(--accent-glow), transparent 70%);
    pointer-events: none;
}}

.kpi-card:hover {{
    transform: translateY(-2px);
    border-color: var(--accent-soft);
}}

.kpi-card .kpi-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.35rem;
}}

.kpi-card .kpi-icon {{
    font-size: 1.15rem;
    opacity: 0.9;
}}

.kpi-card .kpi-label {{
    font-size: 0.78rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-bottom: 0.15rem;
}}

.kpi-card .kpi-value {{
    font-family: var(--font-heading);
    font-size: 1.65rem;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.1;
}}

.kpi-card .kpi-delta {{
    font-size: 0.8rem;
    margin-top: 0.45rem;
    font-weight: 500;
}}

.kpi-delta.positive {{ color: var(--positive); }}
.kpi-delta.negative {{ color: var(--negative); }}
.kpi-delta.neutral  {{ color: var(--neutral); }}

/* ---------- Cartão genérico (seções) ---------- */
.section-card {{
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 14px;
    padding: 1.1rem 1.25rem;
    margin-bottom: 1.1rem;
}}

.section-card h4 {{
    margin-top: 0;
    font-size: 1.02rem;
}}

.delta-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 999px;
    background: rgba(63, 224, 197, 0.08);
    border: 1px solid var(--card-border);
    font-size: 0.85rem;
    font-weight: 500;
    margin-right: 8px;
}}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {{
    background: var(--bg-secondary);
    border-right: 1px solid var(--card-border);
}}

section[data-testid="stSidebar"] .block-container {{
    padding-top: 1.4rem;
}}

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] {{
    gap: 6px;
    border-bottom: 1px solid var(--card-border);
}}

.stTabs [data-baseweb="tab"] {{
    color: var(--text-muted);
    font-family: var(--font-heading);
    font-weight: 500;
    padding: 8px 4px;
}}

.stTabs [aria-selected="true"] {{
    color: var(--accent) !important;
}}

/* ---------- Inputs ---------- */
div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div {{
    background-color: var(--bg-secondary) !important;
    border-color: var(--card-border) !important;
}}

.stButton button, .stDownloadButton button {{
    border-radius: 10px;
    border: 1px solid var(--card-border);
    background-color: var(--bg-secondary);
    color: var(--text-primary);
}}

.stButton button:hover, .stDownloadButton button:hover {{
    border-color: var(--accent);
    color: var(--accent);
}}

/* ---------- Responsividade ---------- */
@media (max-width: 640px) {{
    .kpi-grid {{
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 10px;
    }}
    .kpi-card .kpi-value {{
        font-size: 1.35rem;
    }}
    .app-header h1 {{
        font-size: 1.3rem;
    }}
}}

/* ---------- Tabela Customizada ---------- */
.custom-table-container {{
    max-height: 420px;
    overflow-y: auto;
    border: 1px solid var(--card-border);
    border-radius: 12px;
    margin-top: 12px;
    background-color: var(--card-bg);
}}

/* Custom scrollbar for the table container */
.custom-table-container::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}
.custom-table-container::-webkit-scrollbar-track {{ 
    background: transparent;
}}
.custom-table-container::-webkit-scrollbar-thumb {{
    background: var(--card-border);
    border-radius: 10px;
}}
.custom-table-container::-webkit-scrollbar-thumb:hover {{
    background: var(--accent-soft);
}}

.custom-table {{
    width: 100%;
    border-collapse: collapse;
    font-family: var(--font-body);
    font-size: 0.88rem;
}}

.custom-table thead tr {{
    background-color: var(--bg-secondary) !important;
    position: sticky;
    top: 0;
    z-index: 5;
}}

.custom-table th {{
    padding: 12px 16px;
    font-family: var(--font-heading);
    font-weight: 700;
    color: #00FF87;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    border-bottom: 2px solid #00FF87 !important;
    background: linear-gradient(180deg, #0d2218 0%, var(--bg-secondary) 100%);
    text-shadow: 0 0 12px rgba(0, 255, 135, 0.55);
}}

.custom-table td {{
    padding: 10px 16px;
    border-bottom: 1px solid var(--card-border);
    color: var(--text-primary);
    vertical-align: middle;
}}

.custom-table tbody tr {{
    background-color: transparent;
    transition: background-color 0.15s ease;
}}

.custom-table tbody tr:hover {{
    background-color: rgba(63, 224, 197, 0.05) !important;
}}

.custom-table tbody tr:last-child td {{
    border-bottom: none;
}}

.badge-abs {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.8rem;
    min-width: 65px;
}}

.badge-abs.high {{
    background-color: rgba(255, 107, 107, 0.12);
    color: var(--negative);
    border: 1px solid rgba(255, 107, 107, 0.2);
}}

.badge-abs.low {{
    background-color: rgba(63, 224, 197, 0.12);
    color: var(--positive);
    border: 1px solid rgba(63, 224, 197, 0.2);
}}

.badge-abs.medium {{
    background-color: rgba(138, 160, 168, 0.12);
    color: var(--neutral);
    border: 1px solid rgba(138, 160, 168, 0.2);
}}

#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}

/* ---------- Tooltips ECharts ---------- */
/* As tooltips do ECharts são customizadas via JS e herdam estilos inline */

/* ══════════ Página de Cadastro / Formulário ══════════ */

/* Cabeçalho de seção numerado */
.form-section-hdr {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0.5rem 0 0.55rem 0;
    border-bottom: 1px solid var(--card-border);
    margin-bottom: 0.85rem;
    margin-top: 0.1rem;
}}

.form-section-hdr .fsh-num {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border-radius: 6px;
    background: rgba(63, 224, 197, 0.12);
    border: 1px solid rgba(63, 224, 197, 0.28);
    font-family: var(--font-heading);
    font-size: 0.68rem;
    font-weight: 700;
    color: var(--accent);
    flex-shrink: 0;
    letter-spacing: 0;
}}

.form-section-hdr .fsh-icon {{
    font-size: 0.95rem;
}}

.form-section-hdr .fsh-title {{
    font-family: var(--font-heading) !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    margin: 0 !important;
    letter-spacing: 0.2px;
}}

.form-section-hdr .fsh-hint {{
    margin-left: auto;
    font-size: 0.73rem;
    color: var(--text-muted);
    font-style: italic;
    padding-right: 2px;
}}

/* Botão primário de ação */
button[data-testid="baseButton-primary"] {{
    background: linear-gradient(135deg, #3FE0C5 0%, #2BB7A3 100%) !important;
    color: #071210 !important;
    border: 1px solid #3FE0C5 !important;
    font-weight: 700 !important;
    font-family: 'Sora', sans-serif !important;
    font-size: 0.97rem !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 18px rgba(63, 224, 197, 0.22) !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.3px;
}}

button[data-testid="baseButton-primary"]:hover {{
    box-shadow: 0 6px 28px rgba(63, 224, 197, 0.42) !important;
    transform: translateY(-1px) !important;
}}

/* Chips de coluna (importação em lote) */
.col-chips {{
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 0.55rem;
}}

.col-chip {{
    display: inline-flex;
    align-items: center;
    padding: 3px 9px;
    border-radius: 6px;
    background: rgba(63, 224, 197, 0.07);
    border: 1px solid rgba(63, 224, 197, 0.18);
    font-size: 0.76rem;
    font-family: 'Courier New', monospace;
    color: var(--accent);
    font-weight: 600;
    white-space: nowrap;
}}

/* Caixa de info do import */
.import-info-box {{
    background: linear-gradient(145deg, rgba(63, 224, 197, 0.05) 0%, rgba(20, 28, 33, 0.85) 100%);
    border: 1px solid rgba(63, 224, 197, 0.14);
    border-left: 3px solid var(--accent);
    border-radius: 10px;
    padding: 0.9rem 1.15rem 1rem;
    margin-bottom: 1.1rem;
}}

.import-info-box .iib-title {{
    font-family: var(--font-heading);
    font-size: 0.86rem;
    font-weight: 600;
    color: var(--accent);
    margin-bottom: 0.3rem;
    display: flex;
    align-items: center;
    gap: 6px;
}}

.import-info-box .iib-desc {{
    font-size: 0.81rem;
    color: var(--text-muted);
    margin-bottom: 0.55rem;
    line-height: 1.55;
}}
</style>"""
