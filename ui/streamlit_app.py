import streamlit as st
import sys
import os
import json
import uuid
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(override=True)

# Point pydub at ffmpeg when it isn't on PATH (e.g. fresh winget install)
_FFMPEG_BIN = r"C:\Users\laksh\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
if os.path.isdir(_FFMPEG_BIN):
    os.environ["PATH"] = _FFMPEG_BIN + os.pathsep + os.environ.get("PATH", "")

from agents.orchestrator import intake_graph, monitoring_graph, build_monitoring_graph
from agents.monitoring_agent import generate_checkin_questions

st.set_page_config(
    page_title="Nexus",
    page_icon="🌿",
    layout="wide"
)

st.markdown("""
<style>
/* ══════════════════════════════════════════════════════════════
   NEXUS  ·  Warm Clinical Edition
   Palette adapted from "Modern Lifestyle Store" design
   Cream #FBF8EF · Sage #A3B18A · Deep Sage #8A9A6B
   Taupe #E7E0D4  · Ink  #2B2B26 · Clay #B08A6E
   Fonts: Playfair Display (headings) + Mulish (body/UI)
══════════════════════════════════════════════════════════════ */

/* ── FONTS ───────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&family=Mulish:wght@300;400;500;600;700;800&display=swap');

/* ── DESIGN TOKENS ───────────────────────────────────────────── */
:root {
  --c-bg:       #FBF8EF;
  --c-surface:  #FFFFFF;
  --c-border:   #E7E0D4;
  --c-taupe:    #E7E0D4;
  --c-taupe-dk: #CFC4B4;
  --c-ink:      #2B2B26;
  --c-sage:     #A3B18A;
  --c-sage-dk:  #8A9A6B;
  --c-sage-lt:  #EFF3E9;
  --c-clay:     #B08A6E;
  --c-clay-lt:  #F7EEE6;
  --c-text:     #2B2B26;
  --c-text-2:   #5A5750;
  --c-text-3:   #9A938A;
  --r-card:     16px;
  --r-btn:      999px;
  --shadow-sm:  0 1px 3px rgba(43,43,38,0.06), 0 4px 16px rgba(43,43,38,0.04);
  --shadow-md:  0 4px 24px rgba(43,43,38,0.10), 0 1px 4px rgba(43,43,38,0.05);
}

/* ── GLOBAL BASE ─────────────────────────────────────────────── */
html, body, .stApp {
    font-family: 'Mulish', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    background-color: var(--c-bg) !important;
    color: var(--c-text) !important;
    -webkit-font-smoothing: antialiased;
}
.stApp { background: var(--c-bg) !important; }

/* ── MAIN CONTENT CONTAINER ──────────────────────────────────── */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
    max-width: 1080px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-left: 2.25rem !important;
    padding-right: 2.25rem !important;
}

/* ── TYPOGRAPHY ──────────────────────────────────────────────── */
[data-testid="stMarkdownContainer"] h1,
[data-testid="stHeadingWithActionElements"] h1 {
    font-family: 'Playfair Display', Georgia, serif !important;
    font-size: 2.1rem !important;
    font-weight: 700 !important;
    color: var(--c-ink) !important;
    letter-spacing: -0.2px !important;
    line-height: 1.25 !important;
}
[data-testid="stMarkdownContainer"] h2,
[data-testid="stHeadingWithActionElements"] h2 {
    font-family: 'Playfair Display', Georgia, serif !important;
    font-size: 1.4rem !important;
    font-weight: 600 !important;
    color: var(--c-ink) !important;
    margin-top: 2rem !important;
    letter-spacing: -0.1px !important;
}
[data-testid="stMarkdownContainer"] h3,
[data-testid="stHeadingWithActionElements"] h3 {
    font-family: 'Mulish', sans-serif !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    color: var(--c-sage-dk) !important;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
.stMarkdown p {
    font-size: 1.05rem !important;
    color: var(--c-text) !important;
    line-height: 1.72 !important;
    font-family: 'Mulish', sans-serif !important;
}
[data-testid="stMarkdownContainer"] strong { color: var(--c-ink) !important; }
[data-testid="stMain"] label,
[data-testid="stForm"] label {
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: var(--c-ink) !important;
    font-family: 'Mulish', sans-serif !important;
}

/* ── SIDEBAR ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(170deg, #1A1A16 0%, #2B2B26 100%) !important;
    border-right: none !important;
    min-width: 268px !important;
    box-shadow: 4px 0 28px rgba(43,43,38,0.22) !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem !important;
}
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] strong,
[data-testid="stSidebar"] em,
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stMarkdown * {
    color: #EDE8DA !important;
    font-size: 1rem !important;
    font-family: 'Mulish', sans-serif !important;
}
/* Restore Material Symbols font for sidebar icon buttons (collapse/expand toggle) */
[data-testid="stSidebar"] button span,
[data-testid="stSidebarCollapsedControl"] span,
[data-testid="collapsedControl"] span {
    font-family: inherit !important;
    font-size: inherit !important;
    color: inherit !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.08) !important;
    margin: 1rem 0 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    color: #EDE8DA !important;
    border-radius: 10px !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    font-family: 'Mulish', sans-serif !important;
    padding: 0.75rem 1.1rem !important;
    min-height: 52px !important;
    text-align: left !important;
    margin-bottom: 6px !important;
    transition: background 0.15s, border-color 0.15s, color 0.15s !important;
    width: 100% !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(163,177,138,0.20) !important;
    border-color: rgba(163,177,138,0.40) !important;
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    color: #FBF8EF !important;
    font-weight: 700 !important;
    font-size: 1.35rem !important;
}
[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
    color: rgba(237,232,218,0.55) !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.7px !important;
}
[data-testid="stSidebar"] .stWarning {
    background: rgba(176,138,110,0.18) !important;
    border-radius: 10px !important;
}

/* ── INTERACTIVE ELEMENTS — all sage, zero purple/blue ──────── */

/* 1. Native accent-color — covers any hidden <input> BaseUI wraps */
input[type="checkbox"],
input[type="radio"] {
    accent-color: var(--c-sage-dk) !important;
}

/* 2. Checkboxes — Streamlit wraps in [data-testid="stCheckbox"], not just BaseUI */
[data-testid="stCheckbox"] input[type="checkbox"],
[data-baseweb="checkbox"] input[type="checkbox"] {
    accent-color: var(--c-sage-dk) !important;
    width: 18px !important;
    height: 18px !important;
}
/* Unchecked border */
[data-testid="stCheckbox"] [role="checkbox"],
[data-baseweb="checkbox"] [role="checkbox"] {
    border-color: var(--c-taupe-dk) !important;
    border-radius: 4px !important;
}
/* Checked fill — all selector variants across Streamlit versions */
[data-testid="stCheckbox"] [role="checkbox"][aria-checked="true"],
[data-testid="stCheckbox"] [aria-checked="true"],
[data-testid="stCheckbox"] [aria-checked="true"] > div,
[data-testid="stCheckbox"] [aria-checked="true"] > span,
[data-baseweb="checkbox"] [role="checkbox"][aria-checked="true"],
[data-baseweb="checkbox"] [aria-checked="true"],
[data-baseweb="checkbox"] [aria-checked="true"] > div,
[data-baseweb="checkbox"] [aria-checked="true"] > span {
    background-color: var(--c-sage-dk) !important;
    border-color: var(--c-sage-dk) !important;
}

/* 3. Radio buttons — checked fill */
[data-baseweb="radio"] [role="radio"][aria-checked="true"] > div,
[data-baseweb="radio"] [aria-checked="true"] > div:first-child,
[data-baseweb="radio"] [aria-checked="true"] > div {
    background: var(--c-sage-dk) !important;
    border-color: var(--c-sage-dk) !important;
}

/* 4. Slider — thumb and filled track */
[data-testid="stSlider"] [role="slider"],
[data-baseweb="slider"] [role="slider"] {
    background: var(--c-sage-dk) !important;
    border-color: var(--c-sage-dk) !important;
}
[data-testid="stSlider"] > div > div > div > div,
[data-baseweb="slider"] div[class*="Fill"],
[data-baseweb="slider"] > div > div > div:nth-child(2) {
    background: var(--c-sage-dk) !important;
}

/* 5. Multiselect tags */
[data-baseweb="tag"] {
    background: var(--c-sage-lt) !important;
    border-color: rgba(163,177,138,0.4) !important;
    border-radius: 999px !important;
}
[data-baseweb="tag"] span { color: var(--c-sage-dk) !important; }
[data-baseweb="tag"] [role="button"] { color: var(--c-sage-dk) !important; }

/* 6. Select / dropdown — highlighted option */
[data-baseweb="menu"] li[aria-selected="true"],
[data-baseweb="menu"] li:hover,
[data-baseweb="select"] [aria-selected="true"] {
    background: var(--c-sage-lt) !important;
    color: var(--c-sage-dk) !important;
}

/* 7. Date-picker — full calendar override */
/* Popup background (lavender → cream) */
[data-baseweb="calendar"],
[data-baseweb="calendar"] > div,
[data-baseweb="calendar"] [role="grid"],
[data-baseweb="calendar"] [role="grid"] > div {
    background: var(--c-surface) !important;
    border-color: var(--c-taupe) !important;
}
/* Day-name header row — subtle taupe strip */
[data-baseweb="calendar"] [role="row"]:first-of-type {
    background: var(--c-taupe) !important;
}
/* All day buttons — transparent by default */
[data-baseweb="calendar"] button {
    background: transparent !important;
    color: var(--c-ink) !important;
    border-radius: 50% !important;
}
/* Selected day — aria-selected is ON the button itself, not a parent */
[data-baseweb="calendar"] button[aria-selected="true"],
[data-baseweb="calendar"] button[data-selected="true"] {
    background: var(--c-sage-dk) !important;
    color: #FFFFFF !important;
}
/* Today — outline ring */
[data-baseweb="calendar"] button[aria-current="date"] {
    outline: 2px solid var(--c-sage) !important;
    outline-offset: -2px !important;
}
/* Hover */
[data-baseweb="calendar"] button:not([aria-selected="true"]):hover {
    background: var(--c-sage-lt) !important;
}
/* Progress bar fill — target every nesting depth Streamlit uses */
[data-testid="stProgressBar"] > div,
[data-testid="stProgressBar"] div[role="progressbar"] > div,
[data-testid="stProgressBar"] > div > div > div,
[data-testid="stProgressBar"] [role="progressbar"] > div,
.stProgress [role="progressbar"] > div,
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--c-sage), var(--c-sage-dk)) !important;
    border-radius: 20px !important;
}
/* File uploader — cream background, no lavender */
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploader"] > div {
    background: var(--c-surface) !important;
    border-color: var(--c-taupe) !important;
    border-radius: var(--r-card) !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--c-sage) !important;
    background: var(--c-sage-lt) !important;
}
[data-testid="stFileUploader"] button {
    color: var(--c-sage-dk) !important;
    border-color: var(--c-sage) !important;
    border-radius: 999px !important;
}
[data-testid="stDownloadButton"] > button {
    border-color: var(--c-sage) !important;
    color: var(--c-sage-dk) !important;
    border-radius: 999px !important;
}
a { color: var(--c-clay) !important; }
a:hover { color: var(--c-ink) !important; }
*:focus-visible { outline-color: var(--c-sage-dk) !important; outline-offset: 2px; }

/* ── INPUTS ──────────────────────────────────────────────────── */
/* Wrapper borders and border-radius */
[data-baseweb="input"],
[data-baseweb="input"] > div,
[data-baseweb="input"] > div > div,
[data-baseweb="textarea"],
[data-baseweb="textarea"] > div,
[data-testid="stTextInput"] > div,
[data-testid="stTextInput"] > div > div,
[data-testid="stNumberInput"] > div,
[data-testid="stNumberInput"] > div > div,
[data-testid="stDateInput"] > div > div {
    border-radius: 12px !important;
    border-color: var(--c-taupe) !important;
    background: #FDFBF5 !important;
    font-size: 1.02rem !important;
    transition: border-color 0.15s !important;
    font-family: 'Mulish', sans-serif !important;
}
/* Focus ring */
[data-baseweb="input"] > div:focus-within,
[data-baseweb="textarea"] > div:focus-within,
[data-testid="stTextInput"] > div:focus-within {
    border-color: var(--c-sage) !important;
    box-shadow: 0 0 0 3px rgba(163,177,138,0.15) !important;
}
/* The actual <input>/<textarea> — Streamlit sets background-color inline here */
input:not([type="checkbox"]):not([type="radio"]),
textarea {
    font-size: 1.02rem !important;
    font-family: 'Mulish', sans-serif !important;
    color: var(--c-ink) !important;
    background-color: #FDFBF5 !important;
}
/* Hide "Press Enter to submit form" tooltip — redundant when a submit button exists */
[data-testid="InputInstructions"] { display: none !important; }
[data-baseweb="select"] {
    border-radius: 12px !important;
    font-size: 1.02rem !important;
}

/* ── MAIN BUTTONS — pill-shaped, sage ────────────────────────── */
.stButton > button {
    border-radius: 999px !important;
    font-family: 'Mulish', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    min-height: 48px !important;
    padding: 0.6rem 1.8rem !important;
    border: 1.5px solid var(--c-sage) !important;
    color: var(--c-sage-dk) !important;
    background: var(--c-surface) !important;
    transition: all 0.18s ease !important;
    letter-spacing: 0.02em !important;
}
.stButton > button:hover {
    background: var(--c-sage-dk) !important;
    color: white !important;
    border-color: var(--c-sage-dk) !important;
    box-shadow: 0 4px 18px rgba(138,154,107,0.30) !important;
    transform: translateY(-1px) !important;
}

/* Form submit — filled sage pill */
[data-testid="stFormSubmitButton"] > button {
    background: var(--c-sage-dk) !important;
    color: white !important;
    border: none !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    min-height: 52px !important;
    border-radius: 999px !important;
    font-family: 'Mulish', sans-serif !important;
    letter-spacing: 0.03em !important;
    box-shadow: 0 2px 12px rgba(138,154,107,0.30) !important;
}
[data-testid="stFormSubmitButton"] > button:hover {
    background: #7A8B5C !important;
    box-shadow: 0 6px 22px rgba(138,154,107,0.38) !important;
    transform: translateY(-1px) !important;
}

/* ── TABS — pill-shaped ──────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--c-taupe);
    border-radius: 999px;
    padding: 5px;
    gap: 4px;
    border-bottom: none !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 999px !important;
    font-size: 0.97rem !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.25rem !important;
    min-height: 44px !important;
    color: var(--c-text-2) !important;
    font-family: 'Mulish', sans-serif !important;
}
.stTabs [aria-selected="true"] {
    background: var(--c-surface) !important;
    box-shadow: var(--shadow-sm) !important;
    color: var(--c-sage-dk) !important;
    font-weight: 700 !important;
}

/* ── METRICS ─────────────────────────────────────────────────── */
[data-testid="stMetricLabel"] {
    color: var(--c-text-2) !important;
    font-size: 0.82rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.7px !important;
    font-weight: 700 !important;
    font-family: 'Mulish', sans-serif !important;
}
[data-testid="stMetricValue"] {
    color: var(--c-ink) !important;
    font-weight: 700 !important;
    font-size: 2.1rem !important;
    font-family: 'Playfair Display', Georgia, serif !important;
}

/* ── ALERTS ──────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: var(--r-card) !important;
    border-left-width: 4px !important;
    font-size: 1.02rem !important;
    padding: 1.1rem 1.4rem !important;
    line-height: 1.65 !important;
    font-family: 'Mulish', sans-serif !important;
}

/* ── EXPANDERS ───────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1.5px solid var(--c-border) !important;
    border-radius: var(--r-card) !important;
    background: var(--c-surface) !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stExpander"]:hover {
    border-color: var(--c-sage) !important;
}

/* ── PROGRESS BARS ───────────────────────────────────────────── */
.stProgress > div > div { border-radius: 20px !important; }

/* ── RADIO & CHECKBOX ────────────────────────────────────────── */
[data-baseweb="radio"] label,
[data-baseweb="checkbox"] label {
    font-size: 1.02rem !important;
    color: var(--c-text) !important;
    line-height: 1.5 !important;
    font-family: 'Mulish', sans-serif !important;
}

/* ── SLIDERS ─────────────────────────────────────────────────── */
.stSlider { padding: 0.6rem 0 0.3rem !important; }

/* ── CAPTIONS ────────────────────────────────────────────────── */
.stCaption, [data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
    font-size: 0.9rem !important;
    color: var(--c-text-3) !important;
    line-height: 1.6 !important;
    font-family: 'Mulish', sans-serif !important;
}

/* ── SPINNER ─────────────────────────────────────────────────── */
[data-testid="stSpinner"] p {
    font-size: 1.02rem !important;
    color: var(--c-text-2) !important;
    font-family: 'Mulish', sans-serif !important;
}

/* ══════════════════════════════════════════════════════════════
   CUSTOM COMPONENTS
══════════════════════════════════════════════════════════════ */

/* ── PAGE HEADER BAR — white card, clay+sage left accent ─────── */
.nexus-page-header {
    background: linear-gradient(120deg, #F5F1E4 0%, #FDFBF4 60%, #FFFFFF 100%);
    border: 1.5px solid var(--c-taupe);
    border-radius: var(--r-card);
    padding: 1.75rem 2.25rem;
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    gap: 1.5rem;
    box-shadow: 0 2px 12px rgba(43,43,38,0.08), 0 1px 3px rgba(43,43,38,0.04);
    position: relative;
    overflow: hidden;
}
.nexus-page-header::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 6px;
    background: linear-gradient(180deg, var(--c-sage) 0%, var(--c-clay) 100%);
    border-radius: 4px 0 0 4px;
}
.nph-logo {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 2rem;
    font-weight: 700;
    color: var(--c-ink);
    letter-spacing: -0.4px;
    margin: 0;
    line-height: 1.15;
}
.nph-sub {
    font-size: 1rem;
    color: var(--c-text-2);
    letter-spacing: 0.1px;
    margin: 6px 0 0 0;
    font-weight: 500;
    font-family: 'Mulish', sans-serif;
}
.nph-badge {
    margin-left: auto;
    flex-shrink: 0;
    background: linear-gradient(135deg, var(--c-sage-lt) 0%, #E8EEE0 100%);
    border: 1.5px solid rgba(163,177,138,0.55);
    border-radius: 999px;
    padding: 12px 26px;
    font-size: 1.05rem;
    color: var(--c-sage-dk);
    font-weight: 700;
    white-space: nowrap;
    font-family: 'Mulish', sans-serif;
    box-shadow: 0 1px 6px rgba(138,154,107,0.18);
}

/* ── HERO / ONBOARDING BANNER — warm cream, dark ink text ────── */
.nexus-hero {
    background: linear-gradient(150deg, #EDE7D3 0%, #FAF7ED 70%, #FBF8EF 100%);
    border: 1.5px solid var(--c-taupe);
    border-radius: 20px;
    padding: 3.25rem 2.75rem;
    margin-bottom: 2.5rem;
    box-shadow: var(--shadow-sm);
    position: relative;
    overflow: hidden;
}
.nexus-hero::after {
    content: '';
    position: absolute;
    right: 0; top: 0; bottom: 0;
    width: 5px;
    background: linear-gradient(180deg, var(--c-sage), var(--c-clay));
    border-radius: 0 20px 20px 0;
}
.nexus-trust-row {
    display: flex;
    gap: 0.65rem;
    margin-top: 1.85rem;
    flex-wrap: wrap;
}
.nexus-trust-item {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.9rem !important;
    color: var(--c-sage-dk) !important;
    font-weight: 700;
    background: var(--c-sage-lt);
    border: 1px solid rgba(163,177,138,0.45);
    border-radius: 999px;
    padding: 6px 14px;
    font-family: 'Mulish', sans-serif;
}

/* ── INFO CARD ───────────────────────────────────────────────── */
.clinical-card {
    background: var(--c-surface);
    border: 1.5px solid var(--c-border);
    border-radius: var(--r-card);
    padding: 1.6rem 1.85rem;
    margin-bottom: 1.25rem;
    box-shadow: var(--shadow-sm);
}
.card-section-label {
    font-size: 0.73rem;
    font-weight: 800;
    color: var(--c-clay);
    text-transform: uppercase;
    letter-spacing: 1.3px;
    margin-bottom: 0.6rem;
    font-family: 'Mulish', sans-serif;
}

/* ── STATUS PILLS ────────────────────────────────────────────── */
.pill-green  { background:#EBF5EE; color:#2E6B4A; border:1.5px solid rgba(74,140,111,0.35); border-radius:999px; padding:5px 16px; font-weight:700; font-size:0.9rem; display:inline-block; font-family:'Mulish',sans-serif; }
.pill-yellow { background:#FEF6EA; color:#8A5A1A; border:1.5px solid rgba(176,138,110,0.40); border-radius:999px; padding:5px 16px; font-weight:700; font-size:0.9rem; display:inline-block; font-family:'Mulish',sans-serif; }
.pill-red    { background:#FDF1EF; color:#9B2C1E; border:1.5px solid rgba(192,57,43,0.30);  border-radius:999px; padding:5px 16px; font-weight:700; font-size:0.9rem; display:inline-block; font-family:'Mulish',sans-serif; }

/* ── SECTION DIVIDER LABEL ───────────────────────────────────── */
.section-label {
    font-size: 0.73rem;
    font-weight: 800;
    color: var(--c-clay);
    text-transform: uppercase;
    letter-spacing: 1.3px;
    margin: 1.85rem 0 0.6rem;
    border-top: 1.5px solid var(--c-taupe);
    padding-top: 1.2rem;
    font-family: 'Mulish', sans-serif;
}

/* ── FOOTER ──────────────────────────────────────────────────── */
.nexus-footer {
    margin-top: 3.5rem;
    padding: 1.5rem 2rem;
    background: var(--c-surface);
    border: 1.5px solid var(--c-border);
    border-radius: var(--r-card);
    text-align: center;
    font-size: 0.9rem !important;
    color: var(--c-text-2) !important;
    line-height: 1.8;
    box-shadow: var(--shadow-sm);
    font-family: 'Mulish', sans-serif;
}
.nexus-footer strong { color: var(--c-ink) !important; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "recovery_state" not in st.session_state:
    st.session_state.recovery_state = None
if "page" not in st.session_state:
    st.session_state.page = "onboarding"
if "show_typed_form" not in st.session_state:
    st.session_state.show_typed_form = False
if "history_phase" not in st.session_state:
    # phases: "ask" | "form" | "ask_more"
    st.session_state.history_phase = "ask"
if "history_selected_date" not in st.session_state:
    st.session_state.history_selected_date = None

# ─── PAGE HEADER COMPONENT ───────────────────────────────────────────────────
def render_header(page_title: str, page_sub: str = ""):
    state = st.session_state.get("recovery_state")
    badge_html = ""
    if state:
        name = state.get("patient_name", "")
        discharge_str = state.get("discharge_date", "")
        try:
            d_date = datetime.strptime(discharge_str, "%Y-%m-%d").date()
            current_day = max(1, (datetime.now().date() - d_date).days + 1)
        except Exception:
            current_day = state.get("recovery_day", 1)
        if name:
            badge_html = f'<span class="nph-badge">🌿 {name} &nbsp;·&nbsp; Day {current_day} of 30</span>'
    sub = f" &nbsp;·&nbsp; {page_sub}" if page_sub else ""
    st.markdown(f"""
<div class="nexus-page-header">
  <div style="flex:1">
    <p class="nph-logo">🌿 Nexus</p>
    <p class="nph-sub">Post-Hospital Recovery Co-Pilot{sub}</p>
  </div>
  {badge_html}
</div>""", unsafe_allow_html=True)


def render_footer():
    st.markdown("""
<div class="nexus-footer">
  Nexus is a recovery support tool and does <strong>not</strong> provide medical advice.<br>
  In an emergency, call <strong>911</strong> immediately.<br>
  &copy; 2026 Nexus Health &nbsp;·&nbsp; Your data is stored securely &nbsp;·&nbsp; HIPAA-compliant
</div>""", unsafe_allow_html=True)


# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="padding:1.5rem 0.5rem 1.5rem">
  <div style="font-size:3.2rem;font-weight:700;color:#FBF8EF;letter-spacing:-0.5px;line-height:1.0;font-family:'Playfair Display',Georgia,serif">🌿 Nexus</div>
  <div style="font-size:1.1rem;color:rgba(237,232,218,0.72);letter-spacing:0.4px;margin-top:10px;font-weight:500;font-family:'Mulish',sans-serif">Recovery Co-Pilot</div>
</div>""", unsafe_allow_html=True)

    if st.session_state.recovery_state:
        state = st.session_state.recovery_state
        discharge_str = state.get("discharge_date", "")
        try:
            d_date = datetime.strptime(discharge_str, "%Y-%m-%d").date()
            current_day = max(1, (datetime.now().date() - d_date).days + 1)
        except Exception:
            current_day = state.get("recovery_day", 1)

        checkin_history = state.get("check_in_history", [])
        last_class = checkin_history[-1]["classification"] if checkin_history else None
        icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(last_class, "")

        patient_name = state.get("patient_name", "Patient")
        _last_cl_html = (
            "<div>"
            "<div style=\"font-size:0.68rem;color:rgba(237,232,218,0.50);text-transform:uppercase;"
            "letter-spacing:0.6px;font-family:Mulish,sans-serif\">Last Check-in</div>"
            f"<div style=\"font-size:1.05rem;font-weight:600;color:#FBF8EF;font-family:Mulish,sans-serif\">{icon} {last_class}</div>"
            "</div>"
        ) if last_class else ""
        st.markdown(f"""
<div style="background:rgba(255,255,255,0.07);border-radius:12px;padding:1rem 1.1rem;margin:0 0 0.75rem;border:1px solid rgba(255,255,255,0.08)">
  <div style="font-size:0.72rem;color:rgba(237,232,218,0.55);text-transform:uppercase;letter-spacing:0.8px;font-weight:700;font-family:'Mulish',sans-serif">Patient</div>
  <div style="font-size:1.12rem;font-weight:700;color:#FBF8EF;margin-top:4px;font-family:'Playfair Display',Georgia,serif">{patient_name}</div>
  <div style="display:flex;gap:1.25rem;margin-top:0.7rem">
    <div>
      <div style="font-size:0.68rem;color:rgba(237,232,218,0.50);text-transform:uppercase;letter-spacing:0.6px;font-family:'Mulish',sans-serif">Day</div>
      <div style="font-size:1.3rem;font-weight:800;color:#FBF8EF;font-family:'Playfair Display',Georgia,serif">{current_day}<span style="font-size:0.82rem;font-weight:400;color:rgba(237,232,218,0.45);font-family:'Mulish',sans-serif"> / 30</span></div>
    </div>
    {_last_cl_html}
  </div>
</div>""", unsafe_allow_html=True)

        pending = [i for i in state.get("human_approval_queue", [])
                   if i["status"] == "pending"]
        if pending:
            st.warning(f"⚠️ {len(pending)} item(s) need your review")

        diag = state.get("diagnosis", "")
        if diag:
            st.markdown(f'<div style="font-size:0.82rem;color:rgba(237,232,218,0.45);padding:0 0.25rem 0.5rem;line-height:1.5;font-family:\'Mulish\',sans-serif">{diag}</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown('<div style="font-size:0.68rem;color:rgba(237,232,218,0.40);letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;padding:0 0.1rem;font-family:\'Mulish\',sans-serif;font-weight:700">Navigation</div>', unsafe_allow_html=True)
    if st.button("📋  Care Plan", use_container_width=True):
        st.session_state.page = "care_plan"
    if st.button("🎤  Daily Check-in", use_container_width=True):
        st.session_state.page = "checkin"
    if st.button("📬  Approvals", use_container_width=True):
        st.session_state.page = "approvals"
    if st.button("📊  Dashboard", use_container_width=True):
        st.session_state.page = "dashboard"
    if st.button("📄  Provider Summary", use_container_width=True):
        st.session_state.page = "provider_summary"
    if st.button("🏥  Hospital History", use_container_width=True):
        st.session_state.page = "hospital_history"

# ── Helper to avoid duplicating monitoring logic ──────────────────────────────
def _run_monitoring(state):
    with st.spinner("Analyzing your check-in..."):
        monitoring_graph = build_monitoring_graph()
        result_state = monitoring_graph.invoke(state)

    st.session_state.recovery_state = result_state
    last_checkin = result_state["check_in_history"][-1]
    classification = last_checkin["classification"]

    if classification == "RED":
        if result_state.get("show_911_screen"):
            st.error("🚨 CALL 911 NOW")
            st.title("EMERGENCY — CALL 911 IMMEDIATELY")
        elif result_state.get("show_er_guidance"):
            st.error("⚠️ You should go to the ER")
            if result_state.get("er_handoff_summary"):
                st.text_area("Show this to ER staff:", result_state["er_handoff_summary"])
        else:
            st.warning("We've flagged some concerns and drafted a message to your care team.")
            st.session_state.page = "approvals"
            st.rerun()
    elif classification == "YELLOW":
        st.warning(f"⚠️ We noticed some things today: {last_checkin.get('summary')}")
        rec_action = last_checkin.get("recommended_action") or \
            result_state.get("last_monitoring_result", {}).get("recommended_action", "")
        if rec_action:
            st.info(f"**What to do:** {rec_action}")
    else:
        st.success(f"✅ Great — {last_checkin.get('summary')}")


def generate_provider_summary_text(state: dict) -> str:
    history = state.get("check_in_history", [])
    vitals = state.get("daily_vitals_log", [])
    meds = [m["name"] for m in state.get("medications", [])]

    lines = [
        "NEXUS — PROVIDER SUMMARY",
        "=" * 40,
        f"Patient: {state.get('patient_name')}",
        f"Diagnosis: {state.get('diagnosis')}",
        f"Discharged: {state.get('discharge_date')}",
        f"Summary generated: Day {state.get('recovery_day', 0)} of recovery",
        "",
        "VITALS TREND",
        "-" * 20,
    ]
    for v in vitals:
        weight_str = f"Weight: {v['weight_lbs']} lbs" if v.get("weight_lbs") else ""
        bp_str = f"BP: {v['bp_systolic']}/{v['bp_diastolic']}" if v.get("bp_systolic") else ""
        lines.append(f"Day {v['day']}: {weight_str} {bp_str} Energy: {v.get('energy_score', '?')}/10")

    lines += ["", "MEDICATION ADHERENCE", "-" * 20]
    for med in meds:
        taken = sum(1 for v in vitals if med in v.get("meds_taken", []))
        lines.append(f"{med}: {taken}/{len(vitals)} days")

    lines += ["", "FLAGGED ANOMALIES", "-" * 20]
    for c in history:
        if c["classification"] in ["YELLOW", "RED"]:
            lines.append(f"Day {c['day']} [{c['classification']}]: {c.get('summary', '')}")

    lines += ["", "— Generated by Nexus (synthetic demo data) —"]
    return "\n".join(lines)


# ─── PAGE: ONBOARDING ────────────────────────────────────────────────────────
if st.session_state.page == "onboarding" and not st.session_state.recovery_state:
    st.markdown("""
<div class="nexus-hero">
  <div style="font-size:2.65rem;font-weight:700;color:#2B2B26;line-height:1.2;margin-bottom:0.85rem;font-family:'Playfair Display',Georgia,serif">Welcome to Nexus</div>
  <div style="font-size:1.12rem;color:#5A5750;line-height:1.78;font-family:'Mulish',sans-serif;max-width:580px">Your personal recovery co-pilot — helping you stay safe, informed, and connected to your care team from the comfort of home.</div>
  <div class="nexus-trust-row">
    <span class="nexus-trust-item">✓ &nbsp;AI-powered daily check-ins</span>
    <span class="nexus-trust-item">✓ &nbsp;Medication tracking</span>
    <span class="nexus-trust-item">✓ &nbsp;Automatic care team alerts</span>
    <span class="nexus-trust-item">✓ &nbsp;Provider-ready summaries</span>
  </div>
</div>""", unsafe_allow_html=True)

    col_form, col_info = st.columns([3, 2], gap="large")
    with col_info:
        st.markdown("""
<div class="clinical-card" style="margin-top:0.25rem">
  <div class="card-section-label">What you will need</div>
  <ul style="margin:0.6rem 0 0;padding-left:1.3rem;line-height:2.1;font-size:1rem;color:#2B2B26;font-family:'Mulish',sans-serif">
    <li>Your hospital discharge summary PDF</li>
    <li>Your discharge date</li>
    <li>An emergency contact (optional)</li>
  </ul>
</div>
<div class="clinical-card">
  <div class="card-section-label">How it works</div>
  <ol style="margin:0.6rem 0 0;padding-left:1.3rem;line-height:2.2;font-size:1rem;color:#2B2B26;font-family:'Mulish',sans-serif">
    <li>Upload your discharge PDF — Nexus reads it for you</li>
    <li>Log any past days if you are setting up late</li>
    <li>Complete a short daily check-in each morning</li>
    <li>Your care team is alerted if anything needs attention</li>
  </ol>
</div>
<div style="font-size:0.9rem;color:#9A938A;margin-top:0.5rem;line-height:1.7;padding:0 0.1rem;font-family:'Mulish',sans-serif">
  🔒 &nbsp;Your data is encrypted and never shared without your consent.
</div>""", unsafe_allow_html=True)

    with col_form:
        st.markdown('<div class="card-section-label" style="margin-bottom:0.85rem">Set up your recovery plan</div>', unsafe_allow_html=True)
        with st.form("onboarding_form"):
            col1, col2 = st.columns(2)
            with col1:
                patient_name = st.text_input("Patient name *")
                discharge_date = st.date_input("Discharge date *", value=None)
            with col2:
                caregiver_name = st.text_input("Caregiver name (optional)")
                caregiver_email = st.text_input("Caregiver email (optional)")

            st.markdown('<div class="section-label">Emergency Contact</div>', unsafe_allow_html=True)
            ec_col1, ec_col2 = st.columns(2)
            with ec_col1:
                ec_name = st.text_input("Contact name")
            with ec_col2:
                ec_phone = st.text_input("Contact phone")
            ec_consent = st.checkbox(
                "I consent to automatic emergency contact notification if a life-threatening "
                "symptom is detected during a check-in"
            )

            st.markdown('<div class="section-label">Discharge Summary</div>', unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "Upload your discharge summary PDF *",
                type=["pdf"],
                label_visibility="collapsed"
            )

            submitted = st.form_submit_button("Start My Recovery Plan →", use_container_width=True)

        if submitted:
            if not patient_name or not uploaded_file or not discharge_date:
                st.error("Please provide your name, discharge date, and discharge summary PDF.")
            else:
                patient_id = str(uuid.uuid4())[:8]
                pdf_path = f"data/{patient_id}_discharge.pdf"
                os.makedirs("data", exist_ok=True)
                with open(pdf_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                initial_state = {
                    "patient_id": patient_id,
                    "patient_name": patient_name,
                    "caregiver_name": caregiver_name,
                    "caregiver_email": caregiver_email,
                    "emergency_contact_name": ec_name,
                    "emergency_contact_phone": ec_phone,
                    "emergency_contact_consented": ec_consent,
                    "discharge_date": str(discharge_date),
                    "recovery_day": 0,
                    "diagnosis": "",
                    "icd10_code": None,
                    "medications": [],
                    "appointments": [],
                    "warning_signs_er": [],
                    "warning_signs_call": [],
                    "dietary_restrictions": [],
                    "activity_restrictions": [],
                    "current_agent": "intake_agent",
                    "needs_clarification": [],
                    "active_flags": [],
                    "human_approval_queue": [],
                    "check_in_history": [],
                    "daily_vitals_log": [],
                    "hospitalization_history": [],
                    "messages": [],
                    "intake_complete": False,
                    "care_plan_complete": False,
                    "last_check_in_date": None,
                    "pinecone_namespace": f"patient_{patient_id}",
                    "pdf_path": pdf_path
                }

                with st.spinner("Reading your discharge summary… this takes about 30 seconds."):
                    result_state = intake_graph.invoke(initial_state)

                if os.path.exists(pdf_path):
                    os.remove(pdf_path)

                st.session_state.recovery_state = result_state

                if result_state.get("intake_complete"):
                    st.success(f"✅ Recovery plan created for {patient_name}!")
                    st.session_state.history_phase = "ask"
                    st.session_state.page = "historical_checkin"
                    st.rerun()
                else:
                    st.error("We had trouble reading your PDF. Please try uploading again.")
                    for flag in result_state.get("active_flags", []):
                        st.warning(flag)

    render_footer()

# ─── PAGE: HISTORICAL CHECK-IN BACKFILL ──────────────────────────────────────
elif st.session_state.page == "historical_checkin":
    state = st.session_state.recovery_state
    if not state:
        st.session_state.page = "onboarding"
        st.rerun()

    discharge_str = state.get("discharge_date", "")
    try:
        discharge_date_obj = datetime.strptime(discharge_str, "%Y-%m-%d").date()
    except Exception:
        st.session_state.page = "care_plan"
        st.rerun()

    yesterday = datetime.now().date() - timedelta(days=1)
    logged_days = {c["day"] for c in state.get("check_in_history", [])}

    # Build list of (day_number, date) pairs not yet logged, from Day 1 up to yesterday
    available = []
    for offset in range((yesterday - discharge_date_obj).days):
        d = discharge_date_obj + timedelta(days=offset + 1)
        day_num = offset + 1
        if day_num not in logged_days:
            available.append((day_num, d))

    # Nothing to backfill → skip straight to care plan
    if not available:
        st.session_state.page = "care_plan"
        st.rerun()

    phase = st.session_state.history_phase

    # ── PHASE: ask ────────────────────────────────────────────────────────────
    if phase == "ask":
        render_header("Recovery History", "Backfill")
        days_str = f"{len(available)} day{'s' if len(available) != 1 else ''}"
        st.write(
            f"You have **{days_str}** of recovery history available to log "
            f"(from {discharge_date_obj + timedelta(days=1)} to {yesterday}). "
            "Adding past data helps the dashboard and your provider summary be more complete."
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, log a past day →", use_container_width=True):
                st.session_state.history_phase = "form"
                st.rerun()
        with col2:
            if st.button("Skip — go to my care plan", use_container_width=True):
                st.session_state.page = "care_plan"
                st.rerun()

    # ── PHASE: form ───────────────────────────────────────────────────────────
    elif phase == "form":
        render_header("Log a Past Day", "Backfill")

        available_dates = [d for _, d in available]
        default_date = available_dates[-1]  # default to most recent unlogged day

        selected_date = st.date_input(
            "Which day are you logging?",
            value=default_date,
            min_value=available_dates[0],   # earliest available
            max_value=available_dates[-1],  # latest available (yesterday)
        )

        # Compute day number from selected date
        if selected_date:
            recovery_day = (selected_date - discharge_date_obj).days
        else:
            recovery_day = available[0][0]

        state["recovery_day"] = recovery_day
        questions = generate_checkin_questions(state)
        responses = {}

        with st.form("history_checkin_form"):
            st.markdown(f"**Recovery Day {recovery_day} — {selected_date}**")

            st.markdown("#### 💊 Medications")
            for q in questions:
                if q["type"] != "med_checkbox":
                    continue
                responses[q["id"]] = st.radio(
                    q.get("med_name", q["id"]),
                    options=["Yes — I took it", "No — I missed it"],
                    index=None,
                    horizontal=True,
                    key=f"hist_{recovery_day}_{q['id']}"
                )

            st.markdown("#### 📊 How were you feeling?")
            for q in questions:
                if q["type"] not in ("scale_1_10", "number_lbs", "yes_no_detail"):
                    continue
                if q["type"] == "scale_1_10":
                    responses[q["id"]] = st.slider(
                        q["question"], 1, 10, value=None,
                        key=f"hist_{recovery_day}_{q['id']}"
                    )
                elif q["type"] == "number_lbs":
                    responses[q["id"]] = st.number_input(
                        q["question"], min_value=50, max_value=500,
                        value=None, step=1, key=f"hist_{recovery_day}_{q['id']}"
                    )
                elif q["type"] == "yes_no_detail":
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        responses[q["id"]] = st.radio(
                            q["question"], ["Yes", "No"],
                            index=None, key=f"hist_{recovery_day}_{q['id']}"
                        )
                    with col2:
                        responses[f"{q['id']}_detail"] = st.text_input(
                            "Any details?", key=f"histd_{recovery_day}_{q['id']}"
                        )

            st.markdown("#### ⚠️ Symptoms on that day")
            for q in questions:
                if q["type"] not in ("symptom_checklist", "multi_select"):
                    continue
                st.write(q["question"])
                selected = []
                for i, opt in enumerate(q.get("options", [])):
                    if st.checkbox(opt, key=f"hist_{recovery_day}_{q['id']}_{i}"):
                        selected.append(opt)
                responses[q["id"]] = selected

            st.markdown("#### 💬 Anything else from that day?")
            for q in questions:
                if q["type"] != "free_text":
                    continue
                responses[q["id"]] = st.text_area(
                    q["question"], key=f"hist_{recovery_day}_{q['id']}"
                )

            submitted = st.form_submit_button("Save this day →")

        if submitted:
            state["todays_checkin_responses"] = responses
            state["checkin_method"] = "historical_typed"
            with st.spinner("Saving..."):
                monitoring_graph = build_monitoring_graph()
                result_state = monitoring_graph.invoke(state)
            st.session_state.recovery_state = result_state
            st.session_state.history_selected_date = selected_date
            st.session_state.history_phase = "ask_more"
            st.rerun()

    # ── PHASE: ask_more ───────────────────────────────────────────────────────
    elif phase == "ask_more":
        saved_date = st.session_state.history_selected_date
        last = state.get("check_in_history", [{}])[-1]
        icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(
            last.get("classification", ""), "⚪"
        )
        st.success(f"✅ Day logged — {icon} {last.get('classification', '')}")
        if last.get("summary"):
            st.info(last["summary"])

        # Recompute remaining available days
        logged_days_updated = {c["day"] for c in state.get("check_in_history", [])}
        remaining = [
            (offset + 1, discharge_date_obj + timedelta(days=offset + 1))
            for offset in range((yesterday - discharge_date_obj).days)
            if (offset + 1) not in logged_days_updated
        ]

        if remaining:
            st.write(f"**{len(remaining)} day{'s' if len(remaining) != 1 else ''} still available to log.**")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, log another day →", use_container_width=True):
                    st.session_state.history_phase = "form"
                    st.rerun()
            with col2:
                if st.button("No, go to my care plan →", use_container_width=True):
                    st.session_state.page = "care_plan"
                    st.rerun()
        else:
            st.info("All past days have been logged.")
            if st.button("Go to my care plan →", use_container_width=True):
                st.session_state.page = "care_plan"
                st.rerun()

# ─── PAGE: CARE PLAN ─────────────────────────────────────────────────────────
elif st.session_state.page == "care_plan":
    state = st.session_state.recovery_state
    if not state:
        st.warning("Please complete onboarding first.")
    else:
        render_header("Care Plan", state.get("diagnosis", "")[:40])

        # Show medication flags first if any
        pending_med_flags = [i for i in state.get("human_approval_queue", [])
                             if i["type"] == "medication_conflict" and i["status"] == "pending"]

        if pending_med_flags:
            st.error("⚠️ One or more medications need a quick check before you take them.")
            for flag in pending_med_flags:
                # First line of content is "Medication to check: ..."
                first_line = flag["content"].split("\n")[0] if flag["content"] else "Medication flag"
                label = first_line.replace("Medication to check: ", "").strip()
                with st.expander(f"View details — {label}", expanded=True):
                    for line in flag["content"].split("\n"):
                        if line.strip():
                            st.markdown(f"- {line.strip()}")
                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("I've spoken with my pharmacist", key=f"approve_{flag['id']}"):
                            flag["status"] = "approved"
                            st.rerun()
                    with col2:
                        if st.button("I need more help", key=f"help_{flag['id']}"):
                            st.info("Call your pharmacy or 1-800-PHARMACY (1-800-742-7629).")

        # Display care plan
        care_plan = state.get("care_plan", {})
        if care_plan:
            tab1, tab2, tab3, tab4 = st.tabs([
                "📅 First 7 Days", "💊 Medications", "⚠️ Warning Signs", "📋 Appointments"
            ])

            with tab1:
                st.subheader("Your first week, day by day")
                for day_plan in care_plan.get("first_7_days", []):
                    with st.expander(f"Day {day_plan.get('day', '?')}"):
                        for task in day_plan.get("tasks", []):
                            st.checkbox(task, key=f"task_{day_plan.get('day')}_{task[:20]}")

            with tab2:
                st.subheader("Your medications")
                for med in care_plan.get("medication_schedule", []):
                    st.info(f"💊 {med}")

            with tab3:
                st.subheader("Go to the ER immediately if:")
                for sign in state.get("warning_signs_er", []):
                    st.error(f"🔴 {sign}")
                st.subheader("Call your doctor within 24 hours if:")
                for sign in state.get("warning_signs_call", []):
                    st.warning(f"🟡 {sign}")

            with tab4:
                st.subheader("Follow-up appointments")
                for appt in state.get("appointments", []):
                    st.write(f"📅 {appt.get('provider')} ({appt.get('specialty')}) — "
                             f"Required within: {appt.get('timeframe_required')}")

        if st.button("Start Today's Check-in →"):
            state["recovery_day"] = max(1, state.get("recovery_day", 0))
            st.session_state.page = "checkin"
            st.rerun()

# ─── PAGE: DAILY CHECK-IN ────────────────────────────────────────────────────
elif st.session_state.page == "checkin":
    state = st.session_state.recovery_state
    if not state:
        st.warning("Please complete onboarding first.")
    else:
        # ── DATE PICKER ──────────────────────────────────────────────────────
        discharge_str = state.get("discharge_date", "")
        try:
            discharge_date_obj = datetime.strptime(discharge_str, "%Y-%m-%d").date()
        except Exception:
            discharge_date_obj = None

        today = datetime.now().date()
        checkin_date = st.date_input(
            "Check-in date",
            value=None,
            min_value=discharge_date_obj or today,
            max_value=today,
        )

        if checkin_date is None:
            st.info("Please select a check-in date above to continue.")
            st.stop()

        if discharge_date_obj:
            recovery_day = max(1, (checkin_date - discharge_date_obj).days + 1)
        else:
            recovery_day = max(1, state.get("recovery_day", 1))
        state["recovery_day"] = recovery_day

        render_header(f"Daily Check-in", f"{checkin_date.strftime('%B %d, %Y')} · Day {recovery_day}")

        questions = generate_checkin_questions(state)
        responses = {}

        # ── VOICE GUIDANCE ───────────────────────────────────────────────────
        meds = [m["name"] for m in state.get("medications", []) if not m.get("interaction_flag")]
        guidance_items = []
        if meds:
            guidance_items.append(f"**Medications taken today:** mention each by name — {', '.join(meds)}")
        guidance_items.append("**Your overall energy level** (say a number from 1 to 10)")
        if any(q["id"] == "weight" for q in questions):
            guidance_items.append("**Your weight this morning** in pounds")
        if any(q["id"] == "swelling" for q in questions):
            guidance_items.append("**Any swelling** in your ankles, feet, or legs (yes/no and how much)")
        if any(q["id"] == "breathing" for q in questions):
            guidance_items.append("**Any shortness of breath** while resting or lying flat")
        guidance_items.append("**Any warning symptoms** such as chest pain, dizziness, or fever")
        guidance_items.append("**Any other concerns** you want your care team to know about")

        st.info(
            "**Before you record, please mention all of these:**\n\n" +
            "\n".join(f"- {item}" for item in guidance_items)
        )

        # ── VOICE INPUT ──────────────────────────────────────────────────────
        st.subheader("🎤 Speak Your Check-in (Recommended)")
        st.caption("Click record, speak naturally about how you're feeling, then click stop.")

        try:
            from audiorecorder import audiorecorder
            audio = audiorecorder("🎤 Start Recording", "⏹ Stop Recording")

            if len(audio) > 0:
                import io
                audio_buffer = io.BytesIO()
                audio.export(audio_buffer, format="wav")
                audio_bytes = audio_buffer.getvalue()

                # Use audio hash to detect new recording vs page rerun.
                # This prevents re-transcribing and re-parsing on every Streamlit rerun.
                audio_hash = hash(audio_bytes)
                if st.session_state.get("_voice_audio_hash") != audio_hash:
                    st.session_state._voice_audio_hash = audio_hash
                    st.session_state._voice_stt_result = None
                    st.session_state._voice_parsed_responses = None

                if st.session_state._voice_stt_result is None:
                    with st.spinner("Transcribing your voice check-in..."):
                        from tools.elevenlabs_stt import transcribe_audio, parse_transcript_to_responses
                        st.session_state._voice_stt_result = transcribe_audio(audio_bytes, mime_type="audio/wav")
                else:
                    from tools.elevenlabs_stt import parse_transcript_to_responses

                stt_result = st.session_state._voice_stt_result

                if stt_result["success"]:
                    transcript = stt_result["transcript"]
                    st.success("✅ Voice check-in received")
                    st.info(f"**What we heard:** {transcript}")

                    if st.session_state._voice_parsed_responses is None:
                        with st.spinner("Understanding your responses..."):
                            st.session_state._voice_parsed_responses = parse_transcript_to_responses(
                                transcript, questions, state
                            )

                    # Work from a copy so form widget values can safely override nulls
                    responses = dict(st.session_state._voice_parsed_responses)

                    missing_qs = [q for q in questions if responses.get(q["id"]) is None]

                    st.subheader("We understood the following:")
                    for q in questions:
                        val = responses.get(q["id"])
                        if val is not None:
                            st.write(f"✅ **{q['question']}** → {val}")

                    if missing_qs:
                        st.warning(
                            f"We didn't catch answers to {len(missing_qs)} question(s) from your recording. "
                            "Please fill these in:"
                        )
                        with st.form("voice_fill_gaps"):
                            for q in missing_qs:
                                if q["type"] == "med_checkbox":
                                    responses[q["id"]] = st.radio(
                                        q.get("med_name", q["id"]),
                                        options=["Yes — I took it", "No — I missed it"],
                                        index=None,
                                        horizontal=True,
                                        key=f"vg_{recovery_day}_{q['id']}"
                                    )
                                elif q["type"] == "scale_1_10":
                                    responses[q["id"]] = st.slider(
                                        q["question"], 1, 10, value=None,
                                        key=f"vg_{recovery_day}_{q['id']}"
                                    )
                                elif q["type"] == "number_lbs":
                                    responses[q["id"]] = st.number_input(
                                        q["question"], min_value=50, max_value=500,
                                        value=None, step=1, key=f"vg_{recovery_day}_{q['id']}"
                                    )
                                elif q["type"] == "yes_no_detail":
                                    col1, col2 = st.columns([1, 2])
                                    with col1:
                                        responses[q["id"]] = st.radio(
                                            q["question"], ["Yes", "No"],
                                            index=None, key=f"vg_{recovery_day}_{q['id']}"
                                        )
                                    with col2:
                                        responses[f"{q['id']}_detail"] = st.text_input(
                                            "Any details?", key=f"vgd_{recovery_day}_{q['id']}"
                                        )
                                elif q["type"] in ("symptom_checklist", "multi_select"):
                                    st.write(q["question"])
                                    selected = []
                                    for i, opt in enumerate(q.get("options", [])):
                                        if st.checkbox(opt, key=f"vg_{recovery_day}_{q['id']}_{i}"):
                                            selected.append(opt)
                                    responses[q["id"]] = selected
                                elif q["type"] == "free_text":
                                    responses[q["id"]] = st.text_area(
                                        q["question"], key=f"vg_{recovery_day}_{q['id']}"
                                    )
                            if st.form_submit_button("Complete & Submit Check-in"):
                                st.session_state._voice_audio_hash = None  # clear cache
                                state["todays_checkin_responses"] = responses
                                state["checkin_method"] = "voice+typed"
                                _run_monitoring(state)
                    else:
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ That's correct — submit"):
                                st.session_state._voice_audio_hash = None  # clear cache
                                state["todays_checkin_responses"] = responses
                                state["checkin_method"] = "voice"
                                _run_monitoring(state)
                        with col2:
                            if st.button("✏️ Edit my answers instead"):
                                st.session_state.show_typed_form = True
                                st.rerun()

                else:
                    st.warning(f"⚠️ Voice transcription issue: {stt_result['error']}")
                    st.info("No problem — please type your responses below.")
                    st.session_state.show_typed_form = True

        except ImportError:
            st.session_state.show_typed_form = True
        except FileNotFoundError:
            st.warning("⚠️ Voice recording requires ffmpeg, which isn't installed on this machine. Please type your responses below.")
            st.session_state.show_typed_form = True
        except Exception as e:
            st.warning(f"⚠️ Voice recording unavailable: {e}. Please type your responses below.")
            st.session_state.show_typed_form = True

        # ── TYPED FALLBACK ───────────────────────────────────────────────────
        show_typed = st.session_state.get("show_typed_form", False)
        with st.expander("📝 Type your responses instead", expanded=show_typed):
            with st.form("checkin_form"):
                st.markdown("#### 💊 Medications — did you take each one today?")
                for q in questions:
                    if q["type"] != "med_checkbox":
                        continue
                    responses[q["id"]] = st.radio(
                        q.get("med_name", q["id"]),
                        options=["Yes — I took it", "No — I missed it"],
                        index=None,
                        horizontal=True,
                        key=f"q_{recovery_day}_{q['id']}"
                    )

                st.markdown("#### 📊 How are you doing?")
                for q in questions:
                    if q["type"] not in ("scale_1_10", "number_lbs", "yes_no_detail"):
                        continue
                    if q["type"] == "scale_1_10":
                        responses[q["id"]] = st.slider(
                            q["question"], 1, 10, value=None, key=f"q_{recovery_day}_{q['id']}"
                        )
                    elif q["type"] == "number_lbs":
                        responses[q["id"]] = st.number_input(
                            q["question"], min_value=50, max_value=500,
                            value=None, step=1, key=f"q_{recovery_day}_{q['id']}"
                        )
                    elif q["type"] == "yes_no_detail":
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            responses[q["id"]] = st.radio(
                                q["question"], ["Yes", "No"],
                                index=None, key=f"q_{recovery_day}_{q['id']}"
                            )
                        with col2:
                            responses[f"{q['id']}_detail"] = st.text_input(
                                "Any details?", key=f"d_{recovery_day}_{q['id']}"
                            )

                st.markdown("#### ⚠️ Symptom check — tick any you are experiencing right now")
                for q in questions:
                    if q["type"] not in ("symptom_checklist", "multi_select"):
                        continue
                    st.write(q["question"])
                    selected = []
                    for i, opt in enumerate(q.get("options", [])):
                        if st.checkbox(opt, key=f"q_{recovery_day}_{q['id']}_{i}"):
                            selected.append(opt)
                    responses[q["id"]] = selected

                st.markdown("#### 💬 Anything else?")
                for q in questions:
                    if q["type"] != "free_text":
                        continue
                    responses[q["id"]] = st.text_area(q["question"], key=f"q_{recovery_day}_{q['id']}")

                submitted = st.form_submit_button("Submit Check-in")

            if submitted:
                state["todays_checkin_responses"] = responses
                state["checkin_method"] = "typed"
                _run_monitoring(state)

# ─── PAGE: APPROVAL QUEUE ────────────────────────────────────────────────────
elif st.session_state.page == "approvals":
    state = st.session_state.recovery_state
    if not state:
        st.warning("Please complete onboarding first.")
    else:
        render_header("Approvals", "Items Awaiting Review")
        pending = [i for i in state.get("human_approval_queue", [])
                   if i["status"] == "pending"]

        if not pending:
            st.success("Nothing pending — you're all caught up.")
        else:
            for item in pending:
                with st.expander(
                    f"{'⚠️ Medication Flag' if item['type'] == 'medication_conflict' else '📨 Message Draft'}"
                    f" — {item['created_at'][:10]}"
                ):
                    st.write(item["content"])

                    if item["type"] in ["escalation_message", "provider_message"]:
                        edited = st.text_area(
                            "Edit before sending:", item["content"],
                            key=f"edit_{item['id']}"
                        )
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("✅ Send Now", key=f"send_{item['id']}"):
                                item["status"] = "approved"
                                item["content"] = edited
                                st.success("Message queued for sending.")
                                st.rerun()
                        with col2:
                            if st.button("❌ Don't Send", key=f"reject_{item['id']}"):
                                item["status"] = "rejected"
                                st.rerun()
                        with col3:
                            if st.button("📞 I'll Call Instead", key=f"call_{item['id']}"):
                                item["status"] = "rejected"
                                st.info("Good idea. Call your doctor's office directly.")
                                st.rerun()

# ─── PAGE: DASHBOARD ─────────────────────────────────────────────────────────
elif st.session_state.page == "dashboard":
    state = st.session_state.recovery_state
    if not state:
        st.warning("Please complete onboarding first.")
    else:
        render_header("Recovery Dashboard")
        history = state.get("check_in_history", [])

        if not history:
            st.info("Complete your first check-in to see your dashboard.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                green = sum(1 for c in history if c["classification"] == "GREEN")
                st.metric("Green days", green)
            with col2:
                yellow = sum(1 for c in history if c["classification"] == "YELLOW")
                st.metric("Yellow days", yellow)
            with col3:
                red = sum(1 for c in history if c["classification"] == "RED")
                st.metric("Red days", red)

            st.subheader("Daily vitals & check-in log")
            for checkin in reversed(history):
                icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(
                    checkin["classification"], "⚪"
                )
                vitals = state.get("daily_vitals_log", [])
                day_vitals = next(
                    (v for v in vitals if v.get("day") == checkin["day"]), {}
                )
                weight_str = f"Weight {day_vitals['weight_lbs']} lbs · " if day_vitals.get("weight_lbs") else ""
                bp_str = f"BP {day_vitals['bp_systolic']}/{day_vitals['bp_diastolic']} · " if day_vitals.get("bp_systolic") else ""
                energy_str = f"Energy {day_vitals['energy_score']}/10 · " if day_vitals.get("energy_score") else ""
                st.write(
                    f"Day {checkin['day']} {icon} — {weight_str}{bp_str}{energy_str}"
                    f"{checkin.get('summary', '')}"
                )

            vitals_log = state.get("daily_vitals_log", [])
            if vitals_log:
                st.subheader("Medication adherence")
                meds = [m["name"] for m in state.get("medications", [])]
                for med in meds:
                    taken_days = sum(1 for v in vitals_log if med in v.get("meds_taken", []))
                    missed_days = sum(1 for v in vitals_log if med in v.get("meds_missed", []))
                    total_days = taken_days + missed_days  # only count days where we have an answer
                    if total_days == 0:
                        st.progress(0.0, text=f"{med}: no data yet")
                    else:
                        pct = taken_days / total_days
                        label = f"{med}: {taken_days}/{total_days} days"
                        if missed_days > 0:
                            label += f"  ({missed_days} missed)"
                        st.progress(pct, text=label)

# ─── PAGE: PROVIDER SUMMARY ───────────────────────────────────────────────────
elif st.session_state.page == "provider_summary":
    state = st.session_state.recovery_state
    if not state:
        st.warning("Please complete onboarding first.")
    else:
        render_header("Provider Summary", "Share at your next appointment")

        history = state.get("check_in_history", [])
        vitals_log = state.get("daily_vitals_log", [])

        if not history:
            st.info("Complete at least one check-in to generate your provider summary.")
        else:
            # Header card
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Patient:** {state.get('patient_name')}")
                st.markdown(f"**Diagnosis:** {state.get('diagnosis')}")
                st.markdown(
                    f"**Discharged:** {state.get('discharge_date')} · "
                    f"Day {state.get('recovery_day', 0)} of recovery"
                )
            with col2:
                st.download_button(
                    label="⬇️ Export summary",
                    data=generate_provider_summary_text(state),
                    file_name=f"recovery_summary_{state.get('patient_name', 'patient').replace(' ','_')}.txt",
                    mime="text/plain"
                )

            st.divider()

            # Vitals trend
            st.subheader("Vitals trend")
            if vitals_log:
                weights = [v["weight_lbs"] for v in vitals_log if v.get("weight_lbs")]
                if weights:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "Weight at discharge",
                            f"{weights[0]} lbs"
                        )
                    with col2:
                        st.metric(
                            "Weight today",
                            f"{weights[-1]} lbs",
                            delta=f"{round(weights[-1] - weights[0], 1)} lbs"
                        )
                    with col3:
                        energy_scores = [v["energy_score"] for v in vitals_log if v.get("energy_score")]
                        if energy_scores:
                            avg_e = round(sum(energy_scores) / len(energy_scores), 1)
                            st.metric("Avg energy", f"{avg_e} / 10")

            # Medication adherence
            st.subheader("Medication adherence")
            meds = [m["name"] for m in state.get("medications", [])]
            if not vitals_log:
                st.info("Medication adherence will appear here after the first check-in is submitted.")
            else:
                for med in meds:
                    taken = sum(1 for v in vitals_log if med in v.get("meds_taken", []))
                    total = len(vitals_log)
                    missed = total - taken
                    if missed == 0:
                        st.success(f"✅ {med} — {taken}/{total} days (perfect)")
                    else:
                        pct = int(taken / total * 100)
                        st.warning(f"⚠️ {med} — {taken}/{total} days taken ({missed} missed, {pct}%)")

            # Flagged anomalies
            st.subheader("Flagged anomalies")
            flagged = [c for c in history if c["classification"] in ["YELLOW", "RED"]]
            if not flagged:
                st.success("No anomalies flagged in this period.")
            else:
                for item in flagged:
                    icon = "🔴" if item["classification"] == "RED" else "🟡"
                    st.write(
                        f"{icon} **Day {item['day']}** — {item.get('summary', '')} "
                        f"({', '.join(item.get('flags', [])[:2])})"
                    )

            # Patient-reported symptoms summary
            st.subheader("Patient-reported summary")
            st.caption(
                "Agent-generated summary of what the patient reported across all check-ins. "
                "Review before sharing with your provider."
            )
            all_flags = []
            for c in history:
                for f in c.get("flags", []):
                    if not f.startswith("Classification system error"):
                        all_flags.append(f)
            if all_flags:
                from collections import Counter
                common = Counter(all_flags).most_common(5)
                for symptom, count in common:
                    st.write(f"- {symptom} (mentioned {count} time{'s' if count > 1 else ''})")
            else:
                st.info("No patient-reported symptoms to summarize yet.")


# ─── PAGE: HOSPITAL HISTORY ───────────────────────────────────────────────────
elif st.session_state.page == "hospital_history":
    state = st.session_state.recovery_state
    if not state:
        st.warning("Please complete onboarding first.")
    else:
        render_header("Hospital History", "Auto-imported from discharge PDF")

        hosp_history = state.get("hospitalization_history", [])

        if not hosp_history:
            st.info("No hospitalization records yet. Upload your discharge summary to auto-import the current stay.")
        else:
            for hosp in reversed(hosp_history):
                is_current = hosp.get("source") == "auto_imported"
                with st.container():
                    col1, col2 = st.columns([1, 6])
                    with col1:
                        year = hosp.get("admit_date", "")[:4] or hosp.get("discharge_date", "")[:4]
                        label = "Current" if is_current else year
                        st.markdown(
                            f"<div style='background:{'#EFF3E9' if is_current else '#F7F4EE'};"
                            f"border-radius:10px;padding:10px;text-align:center;"
                            f"color:#8A9A6B;font-size:13px;font-weight:700;font-family:Mulish,sans-serif'>{label}</div>",
                            unsafe_allow_html=True
                        )
                    with col2:
                        st.markdown(f"**{hosp.get('diagnosis', 'Unknown diagnosis')}**")
                        meta_parts = []
                        if hosp.get("hospital_name"):
                            meta_parts.append(hosp["hospital_name"])
                        if hosp.get("admit_date") and hosp.get("discharge_date"):
                            meta_parts.append(f"{hosp['admit_date']} → {hosp['discharge_date']}")
                        if hosp.get("treating_physician"):
                            meta_parts.append(f"Dr. {hosp['treating_physician']}")
                        st.caption(" · ".join(meta_parts))

                        tags = []
                        if hosp.get("specialty"):
                            tags.append(hosp["specialty"])
                        if hosp.get("icd10_code"):
                            tags.append(f"ICD-10: {hosp['icd10_code']}")
                        if tags:
                            st.caption(" · ".join(tags))

                        source_label = "Auto-imported from discharge PDF" if is_current else "Added manually"
                        st.caption(f"_{source_label}_")

                    st.divider()

        # Manual entry form
        st.subheader("Add a past hospitalization")
        with st.form("add_hospitalization"):
            col1, col2 = st.columns(2)
            with col1:
                admit = st.text_input("Admission date (YYYY-MM-DD)")
                hospital = st.text_input("Hospital name")
                diagnosis = st.text_input("Main diagnosis")
            with col2:
                discharge = st.text_input("Discharge date (YYYY-MM-DD)")
                physician = st.text_input("Treating physician (optional)")
                icd10 = st.text_input("ICD-10 code (optional)")

            notes = st.text_area("Any notes (procedures, reason for admission, etc.)", height=80)
            submitted = st.form_submit_button("Add hospitalization")

        if submitted and admit and discharge and diagnosis:
            import uuid as uuid_lib
            new_record = {
                "id": str(uuid_lib.uuid4()),
                "admit_date": admit,
                "discharge_date": discharge,
                "hospital_name": hospital,
                "diagnosis": diagnosis,
                "icd10_code": icd10 or None,
                "treating_physician": physician or None,
                "specialty": None,
                "notes": notes or None,
                "source": "manual_entry",
                "created_at": datetime.now().isoformat()
            }
            if "hospitalization_history" not in state:
                state["hospitalization_history"] = []
            state["hospitalization_history"].append(new_record)
            st.session_state.recovery_state = state
            st.success("Hospitalization record added.")
            st.rerun()
        elif submitted:
            st.error("Please fill in admission date, discharge date, and diagnosis at minimum.")
