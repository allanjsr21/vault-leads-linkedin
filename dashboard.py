"""
Dashboard da Vault Capital — Agente de Leads LinkedIn
Rode com: streamlit run dashboard.py
"""

import sys
import os
import time
import pandas as pd
import streamlit as st

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

st.set_page_config(
    page_title="Vault Capital — Leads LinkedIn",
    page_icon="⚡",
    layout="wide",
)

# ── Estilo ─────────────────────────────────────────────────────────────────────
st.markdown("""
<link rel="stylesheet"
      href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"
      crossorigin="anonymous" />
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<style>
    /* ── Animations ── */
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    @keyframes pulse-glow {
        0%, 100% { opacity: 0.4; }
        50% { opacity: 1; }
    }
    @keyframes fade-in-up {
        from { opacity: 0; transform: translateY(20px) scale(0.95); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-8px); }
    }
    @keyframes orb-float-1 {
        0%, 100% { transform: translate(0, 0) scale(1); }
        33% { transform: translate(30px, -20px) scale(1.05); }
        66% { transform: translate(-20px, 15px) scale(0.95); }
    }
    @keyframes orb-float-2 {
        0%, 100% { transform: translate(0, 0) scale(1); }
        33% { transform: translate(-25px, 25px) scale(0.95); }
        66% { transform: translate(15px, -30px) scale(1.05); }
    }
    @keyframes scan-line {
        0% { top: -10%; }
        100% { top: 110%; }
    }
    @keyframes gradient-shift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    ::selection { background: rgba(212,175,55,0.4); color: #fff; }

    /* ── Background — big visible orbs + dot grid ── */
    [data-testid="stAppViewContainer"] {
        background: #07080e;
    }

    /* Dot grid pattern overlay */
    [data-testid="stAppViewContainer"]::after {
        content: '';
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background-image: radial-gradient(rgba(255,255,255,0.04) 1px, transparent 1px);
        background-size: 24px 24px;
        pointer-events: none;
        z-index: 0;
    }

    /* Top accent line — rainbow animated */
    [data-testid="stAppViewContainer"]::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, #d4af37, #f59e0b, #fb923c, #f43f5e, #a78bfa, #6366f1, #0ea5e9, #34d399, #d4af37);
        background-size: 300% 100%;
        animation: gradient-shift 6s linear infinite;
        z-index: 9999;
    }

    /* Floating orbs — visible colored blobs */
    .orb-container {
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        pointer-events: none;
        z-index: 0;
        overflow: hidden;
    }
    .orb {
        position: absolute;
        border-radius: 50%;
        filter: blur(80px);
    }
    .orb-1 {
        width: 500px; height: 500px;
        background: radial-gradient(circle, rgba(212,175,55,0.15) 0%, transparent 70%);
        top: -10%; left: -5%;
        animation: orb-float-1 15s ease-in-out infinite;
    }
    .orb-2 {
        width: 450px; height: 450px;
        background: radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%);
        top: 20%; right: -10%;
        animation: orb-float-2 18s ease-in-out infinite;
    }
    .orb-3 {
        width: 400px; height: 400px;
        background: radial-gradient(circle, rgba(52,211,153,0.08) 0%, transparent 70%);
        bottom: -5%; left: 30%;
        animation: orb-float-1 20s ease-in-out infinite reverse;
    }
    .orb-4 {
        width: 350px; height: 350px;
        background: radial-gradient(circle, rgba(251,146,60,0.08) 0%, transparent 70%);
        top: 50%; left: 10%;
        animation: orb-float-2 16s ease-in-out infinite reverse;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: rgba(7,8,14,0.92) !important;
        backdrop-filter: blur(40px) saturate(150%) !important;
        -webkit-backdrop-filter: blur(40px) saturate(150%) !important;
        border-right: 1px solid rgba(212,175,55,0.08) !important;
    }
    [data-testid="stSidebar"]::before {
        content: '';
        position: absolute;
        top: 0; right: 0;
        width: 1px; height: 100%;
        background: linear-gradient(180deg, rgba(212,175,55,0.6) 0%, rgba(99,102,241,0.3) 50%, transparent 80%);
    }

    /* ── Radio ── */
    [data-testid="stRadio"] [role="radio"] {
        border-color: rgba(255,255,255,0.06) !important;
        transition: all 0.25s ease !important;
    }
    [data-testid="stRadio"] [role="radio"][aria-checked="true"] {
        border-color: #d4af37 !important;
        background: linear-gradient(135deg, #d4af37, #f59e0b) !important;
        box-shadow: 0 0 20px rgba(212,175,55,0.4), 0 0 40px rgba(212,175,55,0.15) !important;
    }
    [data-testid="stRadio"] label {
        color: rgba(255,255,255,0.25) !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stRadio"] label:has([aria-checked="true"]) {
        color: #d4af37 !important;
        text-shadow: 0 0 20px rgba(212,175,55,0.3) !important;
    }

    h1, h2, h3, h4 { color: #d4af37 !important; }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #d4af37 0%, #f59e0b 50%, #d4af37 100%) !important;
        background-size: 200% 100% !important;
        color: #07080e !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 0.6rem 1.4rem !important;
        letter-spacing: 0.5px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 20px rgba(212,175,55,0.3), 0 0 40px rgba(212,175,55,0.1) !important;
        font-size: 0.82rem !important;
    }
    .stButton > button:hover {
        background-position: 100% 0 !important;
        box-shadow: 0 6px 30px rgba(212,175,55,0.45), 0 0 60px rgba(212,175,55,0.15) !important;
        transform: translateY(-2px) !important;
    }
    .stButton > button:active {
        transform: scale(0.96) !important;
        box-shadow: 0 2px 10px rgba(212,175,55,0.2) !important;
    }

    /* ── Metric cards — glass + thick colored left border ── */
    .metric-card {
        background: rgba(12,14,28,0.65);
        backdrop-filter: blur(24px) saturate(140%);
        -webkit-backdrop-filter: blur(24px) saturate(140%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 20px;
        padding: 1.5rem 1rem 1.3rem;
        text-align: center;
        transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        animation: fade-in-up 0.6s ease-out both;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.05),
            0 8px 32px rgba(0,0,0,0.5);
    }
    .metric-card:nth-child(1) { animation-delay: 0.0s; }
    .metric-card:nth-child(2) { animation-delay: 0.08s; }
    .metric-card:nth-child(3) { animation-delay: 0.16s; }
    .metric-card:nth-child(4) { animation-delay: 0.24s; }
    .metric-card:nth-child(5) { animation-delay: 0.32s; }
    .metric-card:nth-child(6) { animation-delay: 0.40s; }

    /* Top accent — thick colored bar */
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        border-radius: 20px 20px 0 0;
    }

    /* Radial glow from top on hover */
    .metric-card::after {
        content: '';
        position: absolute;
        top: -40%; left: -20%;
        width: 140%; height: 140%;
        border-radius: 50%;
        opacity: 0;
        transition: opacity 0.5s ease;
        pointer-events: none;
    }
    .metric-card:hover {
        transform: translateY(-6px) scale(1.02);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.08),
            0 20px 60px rgba(0,0,0,0.6);
    }
    .metric-card:hover::after { opacity: 1; }

    /* ── Per-color card themes ── */
    .mc-gold::before { background: #d4af37; }
    .mc-gold:hover { border-color: rgba(212,175,55,0.25); box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 20px 60px rgba(0,0,0,0.6), 0 0 80px rgba(212,175,55,0.12); }
    .mc-gold::after { background: radial-gradient(circle at 50% 0%, rgba(212,175,55,0.12) 0%, transparent 60%); }

    .mc-orange::before { background: #fb923c; }
    .mc-orange:hover { border-color: rgba(251,146,60,0.25) !important; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 20px 60px rgba(0,0,0,0.6), 0 0 80px rgba(251,146,60,0.15) !important; }
    .mc-orange::after { background: radial-gradient(circle at 50% 0%, rgba(251,146,60,0.15) 0%, transparent 60%); }

    .mc-purple::before { background: #a78bfa; }
    .mc-purple:hover { border-color: rgba(167,139,250,0.25) !important; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 20px 60px rgba(0,0,0,0.6), 0 0 80px rgba(167,139,250,0.15) !important; }
    .mc-purple::after { background: radial-gradient(circle at 50% 0%, rgba(167,139,250,0.15) 0%, transparent 60%); }

    .mc-silver::before { background: linear-gradient(90deg, #94a3b8, #e2e8f0, #94a3b8); }
    .mc-silver:hover { border-color: rgba(226,232,240,0.20) !important; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 20px 60px rgba(0,0,0,0.6), 0 0 80px rgba(226,232,240,0.08) !important; }
    .mc-silver::after { background: radial-gradient(circle at 50% 0%, rgba(226,232,240,0.08) 0%, transparent 60%); }

    .mc-green::before { background: #34d399; }
    .mc-green:hover { border-color: rgba(52,211,153,0.25) !important; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 20px 60px rgba(0,0,0,0.6), 0 0 80px rgba(52,211,153,0.15) !important; }
    .mc-green::after { background: radial-gradient(circle at 50% 0%, rgba(52,211,153,0.15) 0%, transparent 60%); }

    .mc-blue::before { background: #60a5fa; }
    .mc-blue:hover { border-color: rgba(96,165,250,0.25) !important; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 20px 60px rgba(0,0,0,0.6), 0 0 80px rgba(96,165,250,0.15) !important; }
    .mc-blue::after { background: radial-gradient(circle at 50% 0%, rgba(96,165,250,0.15) 0%, transparent 60%); }

    .metric-icon {
        font-size: 1.3rem;
        margin-bottom: 0.7rem;
        display: block;
        opacity: 0.7;
    }
    .metric-number {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 3.2rem;
        font-weight: 700;
        letter-spacing: -0.04em;
        line-height: 1;
        display: block;
        text-shadow: none;
    }
    .metric-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.55rem;
        color: rgba(255,255,255,0.30);
        margin-top: 12px;
        text-transform: uppercase;
        letter-spacing: 0.2em;
        font-weight: 600;
        display: block;
    }

    /* ── Log box — terminal ── */
    .log-box {
        background: rgba(7,8,14,0.85);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 1.2rem 1.4rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: rgba(130,140,200,0.5);
        height: 200px;
        overflow-y: auto;
        line-height: 1.9;
        position: relative;
    }
    .log-box::after {
        content: '';
        position: absolute;
        left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(52,211,153,0.08), transparent);
        animation: scan-line 6s linear infinite;
        pointer-events: none;
    }
    .log-box::before {
        content: 'vault@terminal ~$';
        position: absolute;
        top: 1.1rem; left: 1.4rem;
        color: rgba(52,211,153,0.4);
        font-size: 0.65rem;
        font-weight: 600;
        text-shadow: 0 0 10px rgba(52,211,153,0.3);
    }
    .log-box pre { margin: 0; white-space: pre-wrap; padding-left: 0; padding-top: 2.5rem; }
    .log-box::-webkit-scrollbar { width: 3px; }
    .log-box::-webkit-scrollbar-track { background: transparent; }
    .log-box::-webkit-scrollbar-thumb { background: rgba(52,211,153,0.12); border-radius: 3px; }

    /* ── Sidebar components ── */
    .sidebar-logo {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 0.6rem 0 1rem;
    }
    .sidebar-logo-icon {
        width: 46px; height: 46px;
        background: linear-gradient(135deg, #d4af37, #f59e0b);
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.3rem;
        color: #07080e;
        box-shadow: 0 6px 30px rgba(212,175,55,0.4), 0 0 50px rgba(212,175,55,0.15);
        animation: float 6s ease-in-out infinite;
    }
    .sidebar-logo-text {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        background: linear-gradient(135deg, #d4af37, #f5c842, #d4af37);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: gradient-shift 4s ease infinite;
        letter-spacing: -0.03em;
    }
    .sidebar-logo-sub {
        font-size: 0.58rem;
        color: rgba(255,255,255,0.18);
        margin-top: 3px;
        letter-spacing: 0.2em;
        text-transform: uppercase;
    }

    .section-header {
        display: flex;
        align-items: center;
        gap: 8px;
        color: rgba(255,255,255,0.20);
        font-size: 0.58rem;
        font-weight: 700;
        margin: 1.4rem 0 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.2em;
    }
    .section-header i { font-size: 0.5rem; color: rgba(212,175,55,0.35); }

    /* ── Status badges ── */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 10px;
        border-radius: 100px;
        font-size: 0.68rem;
        font-weight: 500;
        backdrop-filter: blur(8px);
    }
    .badge-pending  { background: rgba(212,175,55,0.10); color: #d4af37; border: 1px solid rgba(212,175,55,0.15); text-shadow: 0 0 12px rgba(212,175,55,0.4); }
    .badge-approved { background: rgba(52,211,153,0.10); color: #34d399; border: 1px solid rgba(52,211,153,0.15); text-shadow: 0 0 12px rgba(52,211,153,0.4); }
    .badge-sent     { background: rgba(96,165,250,0.10); color: #60a5fa; border: 1px solid rgba(96,165,250,0.15); text-shadow: 0 0 12px rgba(96,165,250,0.4); }
    .badge-failed   { background: rgba(248,113,113,0.10); color: #f87171; border: 1px solid rgba(248,113,113,0.15); text-shadow: 0 0 12px rgba(248,113,113,0.4); }
    .badge-skipped  { background: rgba(107,114,128,0.06); color: #6b7280; border: 1px solid rgba(107,114,128,0.08); }

    /* ── Score badges ── */
    .score-pill {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 4px 14px;
        border-radius: 100px;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .score-hot {
        background: rgba(251,146,60,0.12);
        color: #fb923c;
        border: 1px solid rgba(251,146,60,0.25);
        text-shadow: 0 0 15px rgba(251,146,60,0.5);
        box-shadow: 0 0 25px rgba(251,146,60,0.10);
    }
    .score-warm {
        background: rgba(250,204,21,0.10);
        color: #facc15;
        border: 1px solid rgba(250,204,21,0.20);
        text-shadow: 0 0 12px rgba(250,204,21,0.4);
    }
    .score-cold {
        background: rgba(107,114,128,0.06);
        color: rgba(107,114,128,0.6);
        border: 1px solid rgba(107,114,128,0.1);
    }

    .score-legend {
        display: flex;
        gap: 18px;
        align-items: center;
        font-size: 0.68rem;
        color: rgba(255,255,255,0.18);
        margin-bottom: 1rem;
    }

    /* ── Table ── */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 16px !important;
        overflow: visible !important;
        box-shadow: 0 8px 40px rgba(0,0,0,0.4) !important;
    }
    /* Toolbar sempre visível (fullscreen, download, search) */
    [data-testid="stElementToolbar"] {
        opacity: 1 !important;
        visibility: visible !important;
        display: flex !important;
        z-index: 999 !important;
    }
    [data-testid="stElementToolbar"] button {
        opacity: 1 !important;
        visibility: visible !important;
        color: rgba(212,175,55,0.7) !important;
        background: rgba(212,175,55,0.08) !important;
        border-radius: 6px !important;
    }
    [data-testid="stElementToolbar"] button:hover {
        color: #d4af37 !important;
        background: rgba(212,175,55,0.2) !important;
    }

    hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent) !important;
    }

    /* ── Inputs ── */
    .stTextInput > div > div > input {
        background: rgba(12,14,28,0.5) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 12px !important;
        color: rgba(255,255,255,0.85) !important;
        transition: all 0.25s ease !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: rgba(212,175,55,0.35) !important;
        box-shadow: 0 0 0 3px rgba(212,175,55,0.10), 0 0 40px rgba(212,175,55,0.08) !important;
    }
    .stTextInput > div > div > input::placeholder { color: rgba(255,255,255,0.15) !important; }
    [data-baseweb="select"] > div {
        background: rgba(12,14,28,0.5) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 12px !important;
        color: rgba(255,255,255,0.85) !important;
    }
    .stRadio > div { gap: 6px; }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(212,175,55,0.12); border-radius: 5px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(212,175,55,0.25); }

    /* ── Section titles ── */
    .section-title {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .section-title-bar {
        width: 4px; height: 22px;
        border-radius: 4px;
        box-shadow: 0 0 15px currentColor;
    }
    .section-title-text {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1rem;
        font-weight: 600;
        letter-spacing: -0.02em;
    }

    /* ── Info panel ── */
    .info-panel {
        margin-top: 1.5rem;
        padding: 1rem 1.1rem;
        background: rgba(12,14,28,0.4);
        border: 1px solid rgba(212,175,55,0.08);
        border-left: 3px solid rgba(212,175,55,0.3);
        border-radius: 0 12px 12px 0;
        font-size: 0.66rem;
        color: rgba(255,255,255,0.25);
        line-height: 1.9;
    }
    .info-panel b { color: rgba(212,175,55,0.6); }
    .info-panel i { color: rgba(212,175,55,0.3); margin-right: 4px; }

    /* ── Divider ── */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(212,175,55,0.10), rgba(99,102,241,0.08), transparent);
        margin: 2rem 0;
    }

    /* ── Empty state ── */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        color: rgba(255,255,255,0.15);
    }
    .empty-state i {
        font-size: 3.5rem;
        display: block;
        margin-bottom: 1.2rem;
        opacity: 0.2;
        filter: drop-shadow(0 0 30px rgba(212,175,55,0.3));
    }
    .empty-state b { color: rgba(212,175,55,0.6); }

    /* ── Lead count ── */
    .lead-count {
        font-size: 0.68rem;
        color: rgba(255,255,255,0.15);
        margin-top: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* ── Header ── */
    .vault-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.8rem;
        font-weight: 700;
        letter-spacing: -0.04em;
        background: linear-gradient(135deg, #fff 0%, #d4af37 30%, #f59e0b 50%, #d4af37 70%, #fff 100%);
        background-size: 300% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: gradient-shift 5s ease infinite;
        line-height: 1.1;
        filter: drop-shadow(0 0 30px rgba(212,175,55,0.2));
    }
    .vault-subtitle {
        font-size: 0.72rem;
        color: rgba(255,255,255,0.18);
        letter-spacing: 0.15em;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 10px;
        margin-top: 6px;
    }
    .vault-subtitle i { color: rgba(99,102,241,0.5); }
    .vault-badge {
        background: rgba(212,175,55,0.10);
        border: 1px solid rgba(212,175,55,0.20);
        border-radius: 100px;
        padding: 5px 18px;
        font-size: 0.72rem;
        color: #d4af37;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-shadow: 0 0 20px rgba(212,175,55,0.4);
        box-shadow: 0 0 25px rgba(212,175,55,0.08);
    }
    .online-dot {
        width: 6px; height: 6px;
        background: #34d399;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 8px #34d399, 0 0 20px rgba(52,211,153,0.3);
        animation: pulse-glow 2s ease-in-out infinite;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div class="sidebar-logo-icon"><i class="fa-solid fa-bolt"></i></div>
        <div>
            <div class="sidebar-logo-text">Vault Capital</div>
            <div class="sidebar-logo-sub">Lead Generation</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("""
    <div class="section-header">
        <i class="fa-solid fa-crosshairs"></i> Público-Alvo
    </div>
    """, unsafe_allow_html=True)

    profile_choice = st.radio(
        "perfil",
        options=["1", "2"],
        format_func=lambda x: "Autocustódia" if x == "1" else "Consultoria",
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown("""
    <div class="section-header">
        <i class="fa-solid fa-sliders"></i> Ações
    </div>
    """, unsafe_allow_html=True)

    btn_collect     = st.button("Coletar Leads",      icon=":material/search:",        use_container_width=True)
    # Mostrar botão LinkedIn Direto apenas se cookies estiverem configurados
    _has_voyager = bool(getattr(config, "LINKEDIN_LI_AT", ""))
    if _has_voyager:
        st.markdown(
            '<span style="display:inline-block; background:rgba(10,102,194,0.18); '
            'border:1px solid rgba(10,102,194,0.40); border-radius:100px; '
            'padding:2px 10px; font-size:0.62rem; color:#60a5fa; font-weight:600; '
            'letter-spacing:0.05em; margin-bottom:4px;">🔵 LinkedIn Direto ativo</span>',
            unsafe_allow_html=True,
        )
    btn_collect_voyager = st.button(
        "LinkedIn Direto",
        icon=":material/linked_services:",
        use_container_width=True,
        disabled=not _has_voyager,
        help="Busca direto no LinkedIn via Voyager API. Requer cookies li_at e JSESSIONID.",
    )
    btn_ai_score    = st.button("Score via IA",        icon=":material/psychology:",    use_container_width=True)
    btn_enrich      = st.button("Enriquecer Emails",   icon=":material/alternate_email:", use_container_width=True)
    btn_send        = st.button("Enviar DMs",          icon=":material/send:",          use_container_width=True)

    st.markdown("---")

    btn_sync        = st.button("Sincronizar Sheets",  icon=":material/sync:",          use_container_width=True)
    btn_load_sheets = st.button("Carregar do Sheets",  icon=":material/cloud_download:", use_container_width=True)
    btn_clear       = st.button("Limpar tabela",       icon=":material/delete:",        use_container_width=True)

    st.markdown("""
    <div class="info-panel">
        <i class="fa-solid fa-circle-info"></i>
        <b>Score IA</b>: Claude analisa bio e dá nota<br>
        <i class="fa-solid fa-circle-info"></i>
        <b>Enriquecer</b>: busca email via Hunter.io<br>
        <i class="fa-solid fa-circle-info"></i>
        <b>Coletar</b>: keywords + posts + eventos<br>
        <i class="fa-brands fa-linkedin" style="color:#60a5fa;"></i>
        <b>LinkedIn Direto</b>: Voyager API (cookies)
    </div>
    """, unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def apply_profile(choice: str):
    import config
    profile = config.AUDIENCE_PROFILES[choice]
    config.SEARCH_KEYWORDS = profile["keywords"]
    config.LOCATION_FILTER = profile.get("location_filter", "Brazil")
    config.SHEET_NAME      = profile["sheet_name"]
    config.LEADS_CSV       = profile["leads_csv"]
    config.DM_TEMPLATE     = profile["dm_template"]
    import leads_manager
    leads_manager.LEADS_CSV = config.LEADS_CSV
    return profile


@st.cache_data(ttl=30)
def load_dataframe(sheet_name: str) -> pd.DataFrame:
    from dataclasses import asdict
    from leads_manager import _use_sheets

    if _use_sheets():
        from sheets_manager import sheets_load_leads
        leads = sheets_load_leads()
    else:
        from leads_manager import _csv_load_leads
        leads = _csv_load_leads()

    if not leads:
        return pd.DataFrame(columns=["name", "linkedin_url", "job_title", "company", "location", "status", "source", "sent_at"])
    return pd.DataFrame([asdict(l) for l in leads.values()])


def status_badge(status: str) -> str:
    icons = {
        "pending":  ('<i class="fa-regular fa-clock"></i>',        "badge-pending"),
        "approved": ('<i class="fa-solid fa-circle-check"></i>',    "badge-approved"),
        "sent":     ('<i class="fa-solid fa-paper-plane"></i>',     "badge-sent"),
        "failed":   ('<i class="fa-solid fa-triangle-exclamation"></i>', "badge-failed"),
        "skipped":  ('<i class="fa-solid fa-minus"></i>',           "badge-skipped"),
    }
    icon_html, cls = icons.get(status, ('<i class="fa-solid fa-circle"></i>', "badge-skipped"))
    return f'<span class="status-badge {cls}">{icon_html} {status}</span>'


def status_color(status: str) -> str:
    return {
        "pending":  "🟡",
        "approved": "🟢",
        "sent":     "✅",
        "failed":   "🔴",
        "skipped":  "⚪",
    }.get(status, "⚫")


def compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona colunas 'score' e 'prioridade' ao dataframe."""
    from scorer import score_lead, score_label
    from leads_manager import Lead

    scores  = []
    labels  = []
    for _, row in df.iterrows():
        lead = Lead(
            linkedin_url = row.get("linkedin_url", ""),
            name         = row.get("name", ""),
            job_title    = row.get("job_title", ""),
            company      = row.get("company", ""),
            location     = row.get("location", ""),
            bio          = row.get("bio", ""),
            status       = row.get("status", "pending"),
            source       = row.get("source", ""),
        )
        s = score_lead(lead)
        scores.append(s)
        labels.append(score_label(s))

    df = df.copy()
    df["score"]      = scores
    df["prioridade"] = labels
    return df


# ── Estado de sessão ───────────────────────────────────────────────────────────
_EMPTY_DF = pd.DataFrame(columns=["name", "linkedin_url", "job_title", "company", "location", "status", "source", "sent_at"])

if "logs"       not in st.session_state: st.session_state.logs       = []
if "running"    not in st.session_state: st.session_state.running    = False
if "sheet_url"  not in st.session_state: st.session_state.sheet_url  = ""
if "session_df" not in st.session_state: st.session_state.session_df = _EMPTY_DF.copy()


def add_log(msg: str):
    ts = time.strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{ts}] {msg}")
    if len(st.session_state.logs) > 200:
        st.session_state.logs = st.session_state.logs[-200:]


# ── Config de perfil ───────────────────────────────────────────────────────────
import config
profile_data = apply_profile(profile_choice)

# ── Cabeçalho ──────────────────────────────────────────────────────────────────
profile_label = "Autocustódia" if profile_choice == "1" else "Consultoria"
profile_icon  = "fa-shield-halved" if profile_choice == "1" else "fa-briefcase"

# Floating orbs (background decoration)
st.markdown("""
<div class="orb-container">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
    <div class="orb orb-4"></div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="display:flex; align-items:center; gap:20px; margin-bottom:0.4rem;">
    <div class="vault-header">Vault Capital</div>
    <div class="vault-badge">
        <i class="fa-solid {profile_icon}" style="margin-right:5px; opacity:0.8;"></i>{profile_label}
    </div>
</div>
<div class="vault-subtitle" style="margin-bottom:2.2rem;">
    <i class="fa-brands fa-linkedin" style="font-size:0.85rem;"></i>
    <span>Lead Generation Agent</span>
    <span class="online-dot"></span>
    <span style="color:rgba(52,211,153,0.4); font-size:0.65rem;">Online</span>
</div>
""", unsafe_allow_html=True)

# ── Métricas ───────────────────────────────────────────────────────────────────
df = st.session_state.session_df

# Calcula scores se há leads
if not df.empty:
    df_scored = compute_scores(df)
    st.session_state.session_df = df_scored
    df = df_scored

total    = len(df)
pending  = len(df[df["status"] == "pending"])       if total else 0
approved = len(df[df["status"] == "approved"])      if total else 0
sent     = len(df[df["status"] == "sent"])          if total else 0
hot      = len(df[df["prioridade"] == "Hot"])       if total and "prioridade" in df.columns else 0
emails   = len(df[df["email"].astype(str).str.strip() != ""])  if total and "email" in df.columns else 0

col1, col2, col3, col4, col5, col6 = st.columns(6)
metric_data = [
    (col1, "fa-users",        total,    "Total de Leads",     "#d4af37", "mc-gold"),
    (col2, "fa-fire",         hot,      "Hot Leads",          "#fb923c", "mc-orange"),
    (col3, "fa-envelope",     emails,   "Com Email",          "#a78bfa", "mc-purple"),
    (col4, "fa-hourglass-half",pending, "Aguardando",         "#e2e8f0", "mc-silver"),
    (col5, "fa-circle-check", approved, "Aprovados",          "#34d399", "mc-green"),
    (col6, "fa-paper-plane",  sent,     "DMs Enviadas",       "#60a5fa", "mc-blue"),
]
for col, icon, value, label, color, extra_class in metric_data:
    with col:
        st.markdown(f"""
        <div class="metric-card {extra_class}">
            <span class="metric-icon"><i class="fa-solid {icon}" style="color:{color};"></i></span>
            <span class="metric-number" style="color:{color};">{value}</span>
            <span class="metric-label">{label}</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='margin:1.2rem 0;'></div>", unsafe_allow_html=True)

# ── Ações ──────────────────────────────────────────────────────────────────────
if btn_collect:
    st.session_state.running = True
    add_log(f"Iniciando coleta — perfil: {profile_data['name']}")

    with st.spinner("Coletando leads via Brave Search..."):
        try:
            import config as _cfg
            add_log(f"Keywords: {len(_cfg.SEARCH_KEYWORDS)} configuradas")
            add_log(f"Sheet: {_cfg.SHEET_NAME}")
            add_log(f"Brave API Key: {'OK' if _cfg.BRAVE_SEARCH_API_KEY else 'VAZIO'}")

            from scraper import search_by_keywords, search_by_post_engagement, search_by_events
            from leads_manager import add_leads, load_leads

            # Fontes ativas
            sources_info = []
            if _cfg.BRAVE_SEARCH_API_KEY: sources_info.append("Brave Search")
            if getattr(_cfg, "GOOGLE_CSE_API_KEY", "") and getattr(_cfg, "GOOGLE_CSE_ID", ""):
                sources_info.append("Google Custom Search")
            add_log(f"Fontes ativas: {', '.join(sources_info) or 'Nenhuma!'}")

            add_log("Buscando por palavras-chave...")
            keyword_leads = search_by_keywords()
            brave_count  = sum(1 for l in keyword_leads if l.source == "brave")
            google_count = sum(1 for l in keyword_leads if l.source == "google")
            add_log(f"{len(keyword_leads)} perfis via keywords (Brave: {brave_count}, Google: {google_count})")

            add_log("Buscando autores de conteúdo crypto...")
            engagement_leads = search_by_post_engagement()
            add_log(f"{len(engagement_leads)} autores de artigos/posts encontrados")

            add_log("Buscando participantes de eventos crypto...")
            event_leads = search_by_events()
            add_log(f"{len(event_leads)} leads de eventos encontrados")

            all_leads = keyword_leads + engagement_leads + event_leads

            # ── Filtro inteligente via Gemini (se configurado) ──
            if getattr(_cfg, "GEMINI_API_KEY", ""):
                add_log(f"Filtrando {len(all_leads)} leads via Gemini IA...")
                from gemini_filter import qualify_leads_batch
                all_leads, rejected = qualify_leads_batch(
                    all_leads,
                    callback=lambda i, t, name, r: add_log(
                        f"  [{i}/{t}] {name}: {'ACEITO' if r is not False else 'REJEITADO'}"
                    ) if (i % 5 == 0 or r is False) else None,
                )
                add_log(f"Gemini: {len(all_leads)} aceitos, {rejected} rejeitados")
            else:
                add_log("Gemini não configurado — sem filtro IA")

            added, dupes = add_leads(all_leads)
            add_log(f"{added} novos leads salvos ({dupes} duplicatas ignoradas)")

            from dataclasses import asdict
            if all_leads:
                st.session_state.session_df = pd.DataFrame([asdict(l) for l in all_leads])
            else:
                st.session_state.session_df = _EMPTY_DF.copy()

            add_log("Planilha atualizada!")
            st.success(f"Coleta concluída! {added} leads novos.")
        except Exception as e:
            import traceback
            add_log(f"ERRO: {e}")
            add_log(traceback.format_exc())
            st.error(str(e))

    st.session_state.running = False
    st.rerun()

if btn_collect_voyager:
    st.session_state.running = True
    add_log("Iniciando coleta via LinkedIn Direto (Voyager API)...")

    with st.spinner("Buscando perfis direto no LinkedIn..."):
        try:
            import config as _cfg

            if not getattr(_cfg, "LINKEDIN_LI_AT", ""):
                st.error(
                    "LINKEDIN_LI_AT não configurado. "
                    "Abra o LinkedIn no navegador, pressione F12 → Application → "
                    "Cookies → linkedin.com, copie li_at e JSESSIONID e adicione "
                    "nos Streamlit secrets."
                )
            else:
                from scraper import search_linkedin_voyager
                from leads_manager import add_leads

                add_log(f"li_at configurado: OK")
                add_log(f"JSESSIONID configurado: {'OK' if getattr(_cfg, 'LINKEDIN_JSESSIONID', '') else 'VAZIO (opcional)'}")

                def _voyager_cb(done, total, kw):
                    add_log(f"  [{done}/{total}] keyword: {kw}")

                voyager_leads = search_linkedin_voyager(
                    max_results=getattr(_cfg, "MAX_LEADS_PER_RUN", 100),
                    callback=_voyager_cb,
                )
                add_log(f"{len(voyager_leads)} perfis coletados via Voyager")

                # Filtro inteligente via Gemini (se configurado)
                if getattr(_cfg, "GEMINI_API_KEY", "") and voyager_leads:
                    add_log(f"Filtrando {len(voyager_leads)} leads via Gemini IA...")
                    from gemini_filter import qualify_leads_batch
                    voyager_leads, rejected = qualify_leads_batch(
                        voyager_leads,
                        callback=lambda i, t, name, r: add_log(
                            f"  [{i}/{t}] {name}: {'ACEITO' if r is not False else 'REJEITADO'}"
                        ) if (i % 5 == 0 or r is False) else None,
                    )
                    add_log(f"Gemini: {len(voyager_leads)} aceitos, {rejected} rejeitados")

                added, dupes = add_leads(voyager_leads)
                add_log(f"{added} novos leads salvos ({dupes} duplicatas ignoradas)")

                from dataclasses import asdict
                if voyager_leads:
                    st.session_state.session_df = pd.DataFrame([asdict(l) for l in voyager_leads])
                else:
                    st.session_state.session_df = _EMPTY_DF.copy()

                add_log("Coleta via LinkedIn Direto concluída!")
                st.success(f"LinkedIn Direto: {added} leads novos coletados.")

        except Exception as e:
            import traceback
            add_log(f"ERRO: {e}")
            add_log(traceback.format_exc())
            st.error(str(e))

    st.session_state.running = False
    st.rerun()

if btn_send:
    st.session_state.running = True
    add_log(f"Iniciando envio de DMs — perfil: {profile_data['name']}")

    with st.spinner("Enviando DMs via Chrome..."):
        try:
            from sheets_manager import pull_approved_from_sheet
            from messenger import run_messenger

            add_log("Lendo aprovados do Google Sheets...")
            approved_leads = pull_approved_from_sheet()
            add_log(f"{len(approved_leads)} leads aprovados encontrados")

            run_messenger(dry_run=False)
            add_log("Envio concluído!")
            st.success("DMs enviadas com sucesso!")
        except Exception as e:
            add_log(f"ERRO: {e}")
            st.error(str(e))

    st.session_state.running = False
    st.rerun()

if btn_sync:
    with st.spinner("Sincronizando..."):
        try:
            from sheets_manager import pull_approved_from_sheet
            approved_leads = pull_approved_from_sheet()
            add_log(f"Sincronizado: {len(approved_leads)} aprovados")
            st.success(f"{len(approved_leads)} leads aprovados sincronizados do Sheets.")
        except Exception as e:
            add_log(f"ERRO: {e}")
            st.error(str(e))
    st.rerun()

if btn_load_sheets:
    with st.spinner("Carregando leads do Google Sheets..."):
        try:
            load_dataframe.clear()
            df_sheets = load_dataframe(config.SHEET_NAME)
            st.session_state.session_df = df_sheets
            add_log(f"Carregado {len(df_sheets)} leads do Sheets.")
            st.success(f"{len(df_sheets)} leads carregados do Google Sheets.")
        except Exception as e:
            add_log(f"ERRO ao carregar Sheets: {e}")
            st.error(str(e))
    st.rerun()

if btn_clear:
    # Limpa sessão E o CSV persistido
    st.session_state.session_df = _EMPTY_DF.copy()
    try:
        import leads_manager as _lm
        _lm._csv_save_leads({})  # salva CSV vazio
        add_log("Leads limpos (sessão + CSV).")
    except Exception as _e:
        add_log(f"Sessão limpa. CSV: {_e}")
    st.rerun()

if btn_ai_score:
    df_current = st.session_state.session_df
    if df_current.empty:
        st.warning("Nenhum lead carregado. Colete ou carregue leads primeiro.")
    else:
        import config as _cfg
        if not getattr(_cfg, "ANTHROPIC_API_KEY", ""):
            st.warning("ANTHROPIC_API_KEY não configurada. Adicione no Streamlit secrets.")
        else:
            with st.spinner("Analisando leads via Claude IA..."):
                try:
                    from scorer import ai_score_lead, score_label
                    from models import Lead as _Lead

                    add_log(f"Iniciando scoring via IA para {len(df_current)} leads...")
                    scored = 0
                    for idx, row in df_current.iterrows():
                        lead = _Lead(
                            linkedin_url=row.get("linkedin_url", ""),
                            name=row.get("name", ""),
                            job_title=row.get("job_title", ""),
                            company=row.get("company", ""),
                            location=row.get("location", ""),
                            bio=row.get("bio", ""),
                            source=row.get("source", ""),
                        )
                        result = ai_score_lead(lead)
                        if result:
                            df_current.at[idx, "score"] = result["score"]
                            df_current.at[idx, "prioridade"] = result["label"]
                            df_current.at[idx, "ai_score"] = result.get("reason", "")
                            scored += 1

                    st.session_state.session_df = df_current
                    add_log(f"IA analisou {scored}/{len(df_current)} leads com sucesso")
                    st.success(f"Score via IA concluído! {scored} leads analisados.")
                except Exception as e:
                    import traceback
                    add_log(f"ERRO IA: {e}")
                    add_log(traceback.format_exc())
                    st.error(str(e))
            st.rerun()

if btn_enrich:
    df_current = st.session_state.session_df
    if df_current.empty:
        st.warning("Nenhum lead carregado. Colete ou carregue leads primeiro.")
    else:
        import config as _cfg
        if not getattr(_cfg, "HUNTER_API_KEY", ""):
            st.warning("HUNTER_API_KEY não configurada. Adicione no Streamlit secrets.")
        else:
            with st.spinner("Buscando emails via Hunter.io..."):
                try:
                    from enricher import enrich_lead
                    from models import Lead as _Lead

                    add_log(f"Enriquecendo {len(df_current)} leads...")
                    found = 0
                    for idx, row in df_current.iterrows():
                        if row.get("email"):
                            continue  # já tem email
                        lead = _Lead(
                            linkedin_url=row.get("linkedin_url", ""),
                            name=row.get("name", ""),
                            company=row.get("company", ""),
                        )
                        result = enrich_lead(lead)
                        if result.get("email"):
                            df_current.at[idx, "email"] = result["email"]
                            found += 1

                    st.session_state.session_df = df_current
                    add_log(f"Emails encontrados: {found}/{len(df_current)}")
                    st.success(f"Enriquecimento concluído! {found} emails encontrados.")
                except Exception as e:
                    import traceback
                    add_log(f"ERRO Enrichment: {e}")
                    add_log(traceback.format_exc())
                    st.error(str(e))
            st.rerun()

# ── Tabela de leads ────────────────────────────────────────────────────────────
st.markdown("""
<div class="section-title" style="margin-bottom:1rem;">
    <div class="section-title-bar" style="background:linear-gradient(180deg,#d4af37,rgba(212,175,55,0.2));"></div>
    <span class="section-title-text" style="color:rgba(255,255,255,0.70);">Leads Coletados</span>
</div>
""", unsafe_allow_html=True)

df_table = st.session_state.session_df

# ── Filtros ────────────────────────────────────────────────────────────────────
col_search, col_status, col_loc, col_prio = st.columns([3, 1, 1, 1])

with col_search:
    search_text = st.text_input(
        "Buscar",
        placeholder="  Buscar por nome, cargo, empresa...",
        label_visibility="collapsed",
    )
with col_status:
    status_opts = ["Todos"] + sorted(df_table["status"].dropna().unique().tolist()) if not df_table.empty else ["Todos"]
    status_filter = st.selectbox("Status", status_opts, label_visibility="collapsed")

with col_loc:
    if not df_table.empty and "location" in df_table.columns:
        locs = df_table["location"].dropna().loc[lambda s: s.str.strip() != ""].unique().tolist()
    else:
        locs = []
    loc_opts = ["Todas"] + sorted(locs)
    loc_filter = st.selectbox("Localização", loc_opts, label_visibility="collapsed")

with col_prio:
    prio_opts = ["Todas", "Hot", "Warm", "Cold"]
    prio_filter = st.selectbox("Prioridade", prio_opts, label_visibility="collapsed")

# Aplica filtros
if not df_table.empty:
    if search_text:
        mask = df_table.apply(lambda row: search_text.lower() in " ".join(str(v) for v in row.values).lower(), axis=1)
        df_table = df_table[mask]
    if status_filter != "Todos":
        df_table = df_table[df_table["status"] == status_filter]
    if loc_filter != "Todas":
        df_table = df_table[df_table["location"] == loc_filter]
    if prio_filter != "Todas" and "prioridade" in df_table.columns:
        df_table = df_table[df_table["prioridade"] == prio_filter]

if df_table.empty:
    st.markdown("""
    <div class="empty-state">
        <i class="fa-solid fa-inbox"></i>
        Nenhum lead nesta sessão.<br>
        <span style="font-size:0.8rem;">Clique em <b>Coletar Leads</b> ou <b>Carregar do Sheets</b>.</span>
    </div>
    """, unsafe_allow_html=True)
else:
    df_display = df_table.copy()

    # Ordena por score decrescente
    if "score" in df_display.columns:
        df_display = df_display.sort_values("score", ascending=False)

    df_display["status"] = df_display["status"].apply(lambda s: f"{status_color(s)} {s}")

    # Emoji de prioridade na coluna
    prio_emoji = {"Hot": "🔥", "Warm": "🟡", "Cold": "❄️"}
    if "prioridade" in df_display.columns:
        df_display["prioridade"] = df_display.apply(
            lambda r: f"{prio_emoji.get(r['prioridade'], '')} {r['prioridade']}  {r.get('score', '')}pts",
            axis=1,
        )

    # Legenda de prioridade
    st.markdown("""
    <div class="score-legend">
        <span><span class="score-pill score-hot">🔥 Hot</span> &nbsp;65–100 pts — abordar primeiro</span>
        <span><span class="score-pill score-warm">🟡 Warm</span> &nbsp;35–64 pts — fila normal</span>
        <span><span class="score-pill score-cold">❄️ Cold</span> &nbsp;0–34 pts — baixa prioridade</span>
    </div>
    """, unsafe_allow_html=True)

    cols = ["prioridade", "name", "job_title", "company", "location", "email", "ai_score", "status", "linkedin_url"]
    cols = [c for c in cols if c in df_display.columns]
    # Remove colunas vazias
    cols = [c for c in cols if not df_display[c].astype(str).str.strip().eq("").all()]

    st.dataframe(
        df_display[cols],
        use_container_width=True,
        height=420,
        column_config={
            "prioridade":   st.column_config.TextColumn("Prioridade"),
            "name":         st.column_config.TextColumn("Nome"),
            "job_title":    st.column_config.TextColumn("Cargo"),
            "company":      st.column_config.TextColumn("Empresa"),
            "location":     st.column_config.TextColumn("Localização"),
            "email":        st.column_config.TextColumn("Email"),
            "ai_score":     st.column_config.TextColumn("IA Análise"),
            "status":       st.column_config.TextColumn("Status"),
            "linkedin_url": st.column_config.LinkColumn("LinkedIn"),
        },
    )
    st.markdown(f"""
    <div class="lead-count">
        <i class="fa-solid fa-circle" style="font-size:4px; color:rgba(212,175,55,0.3);"></i>
        {len(df_table)} leads exibidos &nbsp;·&nbsp; Google Sheets sync
    </div>
    """, unsafe_allow_html=True)

# ── Log de atividade ───────────────────────────────────────────────────────────
st.markdown("""
<div class="divider"></div>
<div class="section-title" style="margin-bottom:0.7rem;">
    <div class="section-title-bar" style="background:linear-gradient(180deg,rgba(99,102,241,0.5),rgba(99,102,241,0.1));"></div>
    <span class="section-title-text" style="color:rgba(255,255,255,0.35);">
        <i class="fa-solid fa-terminal" style="margin-right:8px; font-size:0.75rem; opacity:0.5;"></i>Log
    </span>
</div>
""", unsafe_allow_html=True)

log_text = "\n".join(st.session_state.logs[-50:]) if st.session_state.logs else "Nenhuma atividade ainda."
st.markdown(f'<div class="log-box"><pre>{log_text}</pre></div>', unsafe_allow_html=True)
