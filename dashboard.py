"""Onítẹ́tẹ́ - Daily Prediction, Live Score Tracker & Historical Analytics Dashboard.
Powered by Eighty-Two AI Engine.
"""

import json
import logging
import os
import threading
import time
import webbrowser
from typing import Dict, Any, Optional, List
from flask import Flask, jsonify, render_template_string, request
import pandas as pd

from statarea_scraper import StatareaScraper, AccumulatorEngine, ResultsTracker

app = Flask(__name__)
logger = logging.getLogger(__name__)

SCRAPER_STATE = {
    "is_running": False,
    "status": "Idle",
    "progress_pct": 0,
    "progress_text": "",
    "last_run": None,
    "total_fixtures": 0,
    "error": None,
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUNDLED_OUTPUT_DIR = os.path.join(BASE_DIR, "output")


def _resolve_output_dir() -> str:
    """Resolve writable directory for data storage, supporting Vercel and local environments."""
    is_serverless = bool(
        os.environ.get("VERCEL") or 
        os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or 
        os.environ.get("LAMBDA_TASK_ROOT") or
        not os.access(BASE_DIR, os.W_OK)
    )
    if is_serverless:
        target_dir = os.path.join("/tmp", "output")
        try:
            os.makedirs(target_dir, exist_ok=True)
            if os.path.exists(BUNDLED_OUTPUT_DIR):
                import shutil
                for fname in os.listdir(BUNDLED_OUTPUT_DIR):
                    src = os.path.join(BUNDLED_OUTPUT_DIR, fname)
                    dst = os.path.join(target_dir, fname)
                    if os.path.isfile(src) and not os.path.exists(dst):
                        try:
                            shutil.copy2(src, dst)
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Could not prepare serverless /tmp/output: {e}")
        return target_dir
    return BUNDLED_OUTPUT_DIR


OUTPUT_DIR = _resolve_output_dir()


def get_data_paths():
    """Retrieve verified file paths for slips, fixtures, metrics, and ledger."""
    global OUTPUT_DIR
    OUTPUT_DIR = _resolve_output_dir()
    paths = {
        "slips_json": os.path.join(OUTPUT_DIR, "daily_5odds_slip.json"),
        "fixtures_csv": os.path.join(OUTPUT_DIR, "analysis_fixtures_today.csv"),
        "metrics_csv": os.path.join(OUTPUT_DIR, "analysis_team_metrics.csv"),
        "h2h_csv": os.path.join(OUTPUT_DIR, "analysis_h2h_records.csv"),
        "ledger_json": os.path.join(OUTPUT_DIR, "results_ledger.json"),
    }
    # Ensure all files exist, falling back to bundled read-only assets if needed
    for key, target_path in paths.items():
        if not os.path.exists(target_path):
            fname = os.path.basename(target_path)
            bundled_path = os.path.join(BUNDLED_OUTPUT_DIR, fname)
            if os.path.exists(bundled_path):
                try:
                    import shutil
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    shutil.copy2(bundled_path, target_path)
                except Exception:
                    paths[key] = bundled_path
    return paths


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Onítẹ́tẹ́ | AI Soccer Prediction & Performance Analytics</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['Plus Jakarta Sans', 'sans-serif'],
          },
          colors: {
            brand: {
              50: '#fff7ed',
              500: '#ff6b35',
              600: '#ea580c',
              900: '#7c2d12',
            },
            accent: {
              500: '#3b82f6',
              600: '#2563eb',
            },
            dark: {
              bg: '#07090f',
              card: '#111827',
              border: '#1e293b',
              surface: '#141c2e',
            }
          }
        }
      }
    }
  </script>
  <style>
    /* Mandatory Eighty-Two Brand Animations */
    @keyframes eightytwoRingRotate { from{transform:rotate(0deg)} to{transform:rotate(360deg)} } 
    @keyframes eightytwoRingRotateRev { from{transform:rotate(0deg)} to{transform:rotate(-360deg)} } 
    @keyframes eightytwoRimPulse { 0%,100%{opacity:.45} 50%{opacity:.95} } 
    @keyframes eightytwoCenterFade { 0%,100%{opacity:1} 50%{opacity:.78} } 
    @keyframes eightytwoDotGlow { 0%,100%{r:3.5;opacity:.7} 50%{r:5;opacity:1} }

    .badge-outer {
      transform-origin: 250px 250px;
      animation: eightytwoRingRotate 22s linear infinite;
    }
    .badge-inner {
      transform-origin: 250px 250px;
      animation: eightytwoRingRotateRev 14s linear infinite;
    }
    .badge-rim {
      animation: eightytwoRimPulse 4s ease-in-out infinite;
    }
    .badge-center {
      animation: eightytwoCenterFade 4s ease-in-out infinite;
    }
    .badge-dot {
      animation: eightytwoDotGlow 4s ease-in-out infinite;
    }

    body {
      background-color: #07090f;
      color: #f3f4f6;
      overflow-x: hidden;
    }
    .glass-card {
      background: #0f172a;
      border: 1px solid rgba(255, 107, 53, 0.15);
    }
    @supports (backdrop-filter: blur(12px)) or (-webkit-backdrop-filter: blur(12px)) {
      .glass-card {
        background: rgba(15, 23, 42, 0.94);
        -webkit-backdrop-filter: blur(12px);
        backdrop-filter: blur(12px);
      }
    }
    .nav-header {
      background-color: #07090f;
      border-bottom: 1px solid #1e293b;
    }
    @supports (backdrop-filter: blur(16px)) or (-webkit-backdrop-filter: blur(16px)) {
      .nav-header {
        background-color: rgba(7, 9, 15, 0.98);
        -webkit-backdrop-filter: blur(16px);
        backdrop-filter: blur(16px);
      }
    }
    .glow-orange {
      box-shadow: 0 0 30px -5px rgba(255, 107, 53, 0.25);
    }
    .glow-blue {
      box-shadow: 0 0 30px -5px rgba(59, 130, 246, 0.25);
    }
    .custom-scroll::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    .custom-scroll::-webkit-scrollbar-thumb {
      background: #1e293b;
      border-radius: 4px;
    }
  </style>
</head>
<body class="min-h-screen flex flex-col antialiased selection:bg-brand-500 selection:text-white">

  <!-- TOP NAVIGATION BAR WITH ANIMATING EIGHTY-TWO LOGO -->
  <header class="sticky top-0 z-50 nav-header px-3.5 sm:px-6 py-2.5 sm:py-3 shadow-xl shadow-black/50">
    <div class="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-3">
      <div class="flex items-center justify-between w-full md:w-auto">
        <div class="flex items-center space-x-3">
          <!-- OFFICIAL ANIMATED EIGHTY-TWO BADGE -->
          <div class="w-10 h-10 sm:w-11 sm:h-11 relative flex items-center justify-center filter drop-shadow-[0_0_12px_rgba(255,107,53,0.35)] flex-shrink-0">
            <svg width="40" height="40" viewBox="0 0 500 500" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Eighty-Two (82) element badge" style="display: block; overflow: visible;">
              <title>Eighty-Two (82)</title>
              <defs>
                <radialGradient id="badge-bg" cx="40%" cy="35%" r="65%">
                  <stop offset="0%" stop-color="#141c2e" />
                  <stop offset="100%" stop-color="#07090f" />
                </radialGradient>
                <radialGradient id="badge-disk" cx="38%" cy="30%" r="70%">
                  <stop offset="0%" stop-color="#1a2540" />
                  <stop offset="100%" stop-color="#0b101c" />
                </radialGradient>
                <linearGradient id="badge-ring" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#ff6b35" stop-opacity=".85" />
                  <stop offset="50%" stop-color="#ff9a6c" stop-opacity=".5" />
                  <stop offset="100%" stop-color="#ff6b35" stop-opacity=".1" />
                </linearGradient>
                <linearGradient id="badge-num" x1="20%" y1="10%" x2="80%" y2="90%">
                  <stop offset="0%" stop-color="#ffffff" />
                  <stop offset="60%" stop-color="#e8f0fe" />
                  <stop offset="100%" stop-color="#ff6b35" />
                </linearGradient>
                <filter id="badge-glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="6" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>
              <circle cx="250" cy="250" r="236" fill="url(#badge-bg)" />
              <circle cx="250" cy="250" r="232" fill="none" stroke="#ff6b35" stroke-width="1.5" stroke-opacity=".5" class="badge-rim" />
              <g class="badge-outer">
                <circle cx="250" cy="250" r="218" fill="none" stroke="url(#badge-ring)" stroke-width="1.5" stroke-dasharray="14 9 3 9" />
                <circle cx="250" cy="32" r="3.5" fill="#ff6b35" opacity=".7" class="badge-dot" />
                <circle cx="250" cy="468" r="3.5" fill="#ff6b35" opacity=".7" class="badge-dot" />
              </g>
              <g class="badge-inner">
                <circle cx="250" cy="250" r="198" fill="none" stroke="#ff6b35" stroke-width="1" stroke-dasharray="4 16" stroke-opacity=".4" />
                <circle cx="52" cy="250" r="2.5" fill="#ff9a6c" opacity=".6" />
                <circle cx="448" cy="250" r="2.5" fill="#ff9a6c" opacity=".6" />
              </g>
              <circle cx="250" cy="250" r="184" fill="url(#badge-disk)" stroke="#ff6b35" stroke-width="1.5" stroke-opacity=".3" />
              <text x="250" y="272" font-family="'Helvetica Neue', Helvetica, Arial, sans-serif" font-size="172" font-weight="800" letter-spacing="-6" fill="url(#badge-num)" text-anchor="middle" dominant-baseline="middle" filter="url(#badge-glow)" class="badge-center">82</text>
              <text x="250" y="176" font-family="'Helvetica Neue', Helvetica, Arial, sans-serif" font-size="11" font-weight="400" letter-spacing="5" fill="#3a4a60" text-anchor="middle">EIGHTY-TWO</text>
              <text x="250" y="398" font-family="'Helvetica Neue', Helvetica, Arial, sans-serif" font-size="10" font-weight="300" letter-spacing="3" fill="#1e2e44" text-anchor="middle">207.2 u</text>
              <line x1="185" y1="387" x2="215" y2="387" stroke="#ff6b35" stroke-width="1" opacity=".4" />
              <line x1="285" y1="387" x2="315" y2="387" stroke="#ff6b35" stroke-width="1" opacity=".4" />
            </svg>
          </div>

          <div>
            <div class="flex items-center space-x-2">
              <h1 class="text-lg sm:text-xl font-extrabold tracking-tight bg-gradient-to-r from-white via-orange-100 to-brand-500 bg-clip-text text-transparent">
                Onítẹ́tẹ́
              </h1>
              <span class="px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-500 text-[10px] font-extrabold tracking-wider border border-brand-500/30 uppercase flex items-center space-x-1">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping mr-0.5"></span>
                <span>Live Engine</span>
              </span>
            </div>
            <p class="text-[11px] sm:text-xs text-gray-400 font-medium">Daily Multi-Tier AI Predictions (1.5x • 3x • 5x • 10x) & Live Score Tracking</p>
          </div>
        </div>

        <!-- Mobile Action Buttons -->
        <div class="flex items-center space-x-2 md:hidden">
          <button id="btnUpdateScoresMob" onclick="updateLiveScores()" class="p-2.5 rounded-xl bg-dark-surface hover:bg-gray-800 border border-dark-border text-xs text-gray-200 transition" title="Settle & Live Scores">
            <i class="fa-solid fa-arrows-rotate text-xs text-emerald-400"></i>
          </button>
          <button id="btnTriggerScrapeMob" onclick="triggerScrape()" class="p-2.5 rounded-xl bg-gradient-to-r from-brand-500 to-orange-600 text-white text-xs shadow-md shadow-brand-500/20 transition" title="Scrape Today">
            <i class="fa-solid fa-bolt text-xs"></i>
          </button>
        </div>
      </div>

      <!-- NAVIGATION TABS -->
      <div class="grid grid-cols-2 md:flex items-center bg-dark-surface p-1 rounded-xl border border-dark-border w-full md:w-auto">
        <button id="tabPredictionsBtn" onclick="switchTab('predictions')" class="px-4 py-2 md:py-1.5 rounded-lg text-xs font-bold transition text-white bg-brand-500 shadow-md text-center">
          <i class="fa-solid fa-ticket mr-1.5"></i> Daily Slips
        </button>
        <button id="tabAnalyticsBtn" onclick="switchTab('analytics')" class="px-4 py-2 md:py-1.5 rounded-lg text-xs font-bold transition text-gray-400 hover:text-white text-center">
          <i class="fa-solid fa-chart-pie mr-1.5"></i> Analytics & P&L
        </button>
      </div>

      <!-- Desktop Action Buttons -->
      <div class="hidden md:flex items-center space-x-3">
        <!-- Live Auto-Sync Toggle -->
        <button id="btnAutoSync" onclick="toggleAutoSync()" class="px-3 py-2 rounded-xl bg-dark-surface border border-dark-border text-xs font-semibold transition flex items-center space-x-2 text-gray-300 hover:text-white" title="Toggle 30s auto-refresh for live scores">
          <span id="autoSyncDot" class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span id="autoSyncText">Auto Live: ON (30s)</span>
        </button>

        <button id="btnUpdateScores" onclick="updateLiveScores()" class="px-3.5 py-2 rounded-xl bg-dark-surface hover:bg-gray-800 border border-dark-border text-xs font-semibold transition flex items-center space-x-2 text-gray-200 hover:text-white">
          <i class="fa-solid fa-arrows-rotate text-xs text-emerald-400"></i>
          <span>⚡ Sync Live Scores</span>
        </button>

        <button id="btnTriggerScrape" onclick="triggerScrape()" class="px-4 py-2 rounded-xl bg-gradient-to-r from-brand-500 to-orange-600 hover:from-brand-600 hover:to-orange-700 text-white text-xs font-bold shadow-lg shadow-brand-500/25 transition flex items-center space-x-2">
          <i class="fa-solid fa-bolt"></i>
          <span>Scrape Today</span>
        </button>
      </div>
    </div>
  </header>

  <!-- MAIN CONTENT WRAPPER -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-3.5 sm:px-6 py-6 sm:py-8 space-y-6 sm:space-y-8">
    
    <!-- TAB 1: PREDICTIONS VIEW -->
    <div id="tabPredictions" class="space-y-6 sm:space-y-8">
      
      <!-- 4-TIER QUICK OVERVIEW BAR -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <!-- Tier 1: 1.5 Odds Ultra Banker -->
        <div onclick="selectSlipTier('1.5')" id="tierCard15" class="cursor-pointer glass-card rounded-2xl p-4 border border-dark-border hover:border-emerald-500/50 transition relative overflow-hidden group">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[10px] font-extrabold text-emerald-400 uppercase tracking-wider flex items-center space-x-1">
              <i class="fa-solid fa-shield-check"></i>
              <span>1.5-Odds Ultra Banker</span>
            </span>
            <span id="tierStatus15" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-dark-surface border border-dark-border text-gray-400">Active</span>
          </div>
          <div class="flex items-baseline justify-between mt-1">
            <div id="tierOdds15" class="text-2xl font-extrabold text-white group-hover:text-emerald-400 transition">1.50x</div>
            <div id="tierConf15" class="text-xs font-bold text-emerald-400/90">90%+ Conf</div>
          </div>
          <div id="tierLegs15" class="text-[11px] text-gray-400 mt-1">2-3 Ultra-Safe Legs</div>
        </div>

        <!-- Tier 2: 3.0 Odds Banker -->
        <div onclick="selectSlipTier('3')" id="tierCard3" class="cursor-pointer glass-card rounded-2xl p-4 border border-dark-border hover:border-blue-500/50 transition relative overflow-hidden group">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[10px] font-extrabold text-blue-400 uppercase tracking-wider flex items-center space-x-1">
              <i class="fa-solid fa-bullseye"></i>
              <span>3-Odds Banker</span>
            </span>
            <span id="tierStatus3" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-dark-surface border border-dark-border text-gray-400">Active</span>
          </div>
          <div class="flex items-baseline justify-between mt-1">
            <div id="tierOdds3" class="text-2xl font-extrabold text-white group-hover:text-blue-400 transition">3.00x</div>
            <div id="tierConf3" class="text-xs font-bold text-blue-400/90">80%+ Conf</div>
          </div>
          <div id="tierLegs3" class="text-[11px] text-gray-400 mt-1">3-4 Balanced Legs</div>
        </div>

        <!-- Tier 3: 5.0 Odds Banker -->
        <div onclick="selectSlipTier('5')" id="tierCard5" class="cursor-pointer glass-card rounded-2xl p-4 border border-brand-500/40 glow-orange hover:border-brand-500 transition relative overflow-hidden group">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[10px] font-extrabold text-brand-400 uppercase tracking-wider flex items-center space-x-1">
              <i class="fa-solid fa-shield-halved"></i>
              <span>5-Odds Banker</span>
            </span>
            <span id="tierStatus5" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-brand-500/20 text-brand-400 border border-brand-500/30">Primary</span>
          </div>
          <div class="flex items-baseline justify-between mt-1">
            <div id="tierOdds5" class="text-2xl font-extrabold text-brand-400 group-hover:text-brand-300 transition">5.00x</div>
            <div id="tierConf5" class="text-xs font-bold text-brand-400/90">75%+ Conf</div>
          </div>
          <div id="tierLegs5" class="text-[11px] text-gray-400 mt-1">4-6 Conservative Legs</div>
        </div>

        <!-- Tier 4: 10.0 Odds Multiplier -->
        <div onclick="selectSlipTier('10')" id="tierCard10" class="cursor-pointer glass-card rounded-2xl p-4 border border-dark-border hover:border-purple-500/50 transition relative overflow-hidden group">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[10px] font-extrabold text-purple-400 uppercase tracking-wider flex items-center space-x-1">
              <i class="fa-solid fa-gem"></i>
              <span>10-Odds Multiplier</span>
            </span>
            <span id="tierStatus10" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-dark-surface border border-dark-border text-gray-400">Active</span>
          </div>
          <div class="flex items-baseline justify-between mt-1">
            <div id="tierOdds10" class="text-2xl font-extrabold text-white group-hover:text-purple-400 transition">10.00x</div>
            <div id="tierConf10" class="text-xs font-bold text-purple-400/90">70%+ Conf</div>
          </div>
          <div id="tierLegs10" class="text-[11px] text-gray-400 mt-1">5-8 Safe Legs</div>
        </div>
      </div>

      <!-- ACCUMULATOR SLIP SECTION -->
      <div class="space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <!-- TIER SELECTOR TABS -->
            <div class="flex flex-wrap items-center gap-1.5 bg-dark-surface p-1 rounded-xl border border-dark-border">
              <button id="btnTier15" onclick="selectSlipTier('1.5')" class="px-3 py-1.5 rounded-lg text-xs font-bold transition text-gray-400 hover:text-white">
                🛡️ 1.5 Odds
              </button>
              <button id="btnTier3" onclick="selectSlipTier('3')" class="px-3 py-1.5 rounded-lg text-xs font-bold transition text-gray-400 hover:text-white">
                🎯 3 Odds
              </button>
              <button id="btnTier5" onclick="selectSlipTier('5')" class="px-3 py-1.5 rounded-lg text-xs font-bold transition text-white bg-brand-500 shadow-md">
                🚀 5 Odds (Banker)
              </button>
              <button id="btnTier10" onclick="selectSlipTier('10')" class="px-3 py-1.5 rounded-lg text-xs font-bold transition text-gray-400 hover:text-white">
                💎 10 Odds
              </button>
            </div>
          </div>

          <div class="flex items-center space-x-2">
            <button onclick="copyCurrentSlip()" class="w-full sm:w-auto px-3.5 py-2 rounded-xl bg-dark-surface hover:bg-gray-800 text-xs font-semibold text-gray-300 border border-dark-border transition flex items-center justify-center space-x-2">
              <i class="fa-regular fa-copy text-brand-500"></i>
              <span>Copy Selected Ticket</span>
            </button>
            <button onclick="copyAllSlips()" class="w-full sm:w-auto px-3.5 py-2 rounded-xl bg-dark-surface hover:bg-gray-800 text-xs font-semibold text-gray-300 border border-dark-border transition flex items-center justify-center space-x-2" title="Copy all 4 tiers">
              <i class="fa-solid fa-copy text-accent-500"></i>
              <span>Copy All (1.5x - 10x)</span>
            </button>
          </div>
        </div>

        <div class="max-w-4xl mx-auto" id="slipsContainer">
          <!-- Active Ticket Card -->
          <div id="activeSlipCard" class="glass-card rounded-2xl p-4 sm:p-7 border border-brand-500/30 glow-orange flex flex-col justify-between relative overflow-hidden">
            <div id="slipBadgeHeader" class="absolute top-0 right-0 px-3 sm:px-4 py-1 bg-brand-500/20 border-b border-l border-brand-500/30 text-brand-400 text-[10px] sm:text-xs font-bold rounded-bl-xl uppercase tracking-wider">
              Selected Daily Slip
            </div>
            <div>
              <div class="flex items-center space-x-3.5 mb-3 pr-28">
                <div id="slipIconBox" class="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-brand-500/20 text-brand-500 flex items-center justify-center font-bold border border-brand-500/30 flex-shrink-0">
                  <i id="slipIcon" class="fa-solid fa-shield-halved text-sm sm:text-base"></i>
                </div>
                <div>
                  <h3 class="text-base sm:text-xl font-bold text-white" id="dailyTitle">Onítẹ́tẹ́ Daily 5-Odds Banker Slip</h3>
                  <p class="text-[11px] sm:text-xs text-gray-400" id="dailyDesc">Ultra-conservative multi-market daily ticket with strict risk constraints.</p>
                </div>
              </div>

              <div class="grid grid-cols-3 py-2.5 px-4 rounded-xl bg-dark-surface/80 border border-dark-border my-4 text-center">
                <div>
                  <span class="text-[10px] sm:text-xs text-gray-400 block">Total Odds</span>
                  <span class="text-base sm:text-xl font-extrabold text-brand-400" id="dailyTotalOdds">5.00x</span>
                </div>
                <div class="border-x border-dark-border">
                  <span class="text-[10px] sm:text-xs text-gray-400 block">Avg Confidence</span>
                  <span class="text-base sm:text-xl font-extrabold text-white" id="dailyAvgConf">75.0%</span>
                </div>
                <div>
                  <span class="text-[10px] sm:text-xs text-gray-400 block">Total Legs</span>
                  <span class="text-base sm:text-xl font-extrabold text-gray-200" id="dailyLegsCount">5</span>
                </div>
              </div>

              <!-- Legs List -->
              <div class="space-y-2.5 sm:space-y-3 mt-4" id="dailyLegsList"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- TODAY'S FULL FIXTURES TABLE SECTION -->
      <div class="glass-card rounded-2xl p-4 sm:p-6 border border-dark-border space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 class="text-lg sm:text-xl font-bold text-white flex items-center space-x-2">
              <span>📊 Onítẹ́tẹ́ Match Explorer</span>
            </h3>
            <p class="text-[11px] sm:text-xs text-gray-400">Search all daily fixtures with model coefficients and community voting</p>
          </div>

          <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 w-full sm:w-auto">
            <div class="relative w-full sm:w-64">
              <i class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-xs"></i>
              <input type="text" id="searchInput" oninput="filterTable()" placeholder="Search team or league..." class="pl-9 pr-4 py-2 rounded-xl bg-dark-surface border border-dark-border text-xs sm:text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-brand-500 transition w-full">
            </div>
            <select id="marketFilter" onchange="filterTable()" class="px-3 py-2 rounded-xl bg-dark-surface border border-dark-border text-xs sm:text-sm text-gray-200 focus:outline-none focus:border-brand-500 w-full sm:w-auto">
              <option value="all">All Tips</option>
              <option value="1">Tip 1 (Home)</option>
              <option value="X">Tip X (Draw)</option>
              <option value="2">Tip 2 (Away)</option>
              <option value="1X">Tip 1X (Double Chance)</option>
              <option value="12">Tip 12</option>
            </select>
          </div>
        </div>

        <!-- Table Container with Touch Scroll -->
        <div class="overflow-x-auto custom-scroll rounded-xl border border-dark-border -mx-1 sm:mx-0">
          <table class="w-full text-left text-xs sm:text-sm text-gray-300 min-w-[700px]">
            <thead class="bg-dark-surface/90 text-[10px] sm:text-xs uppercase text-gray-400 font-semibold border-b border-dark-border">
              <tr>
                <th class="px-3 sm:px-4 py-3">Time</th>
                <th class="px-3 sm:px-4 py-3">Competition</th>
                <th class="px-3 sm:px-4 py-3">Match</th>
                <th class="px-3 sm:px-4 py-3 text-center">Tip</th>
                <th class="px-3 sm:px-4 py-3 text-center">1 (%)</th>
                <th class="px-3 sm:px-4 py-3 text-center">X (%)</th>
                <th class="px-3 sm:px-4 py-3 text-center">2 (%)</th>
                <th class="px-3 sm:px-4 py-3 text-center">O 1.5</th>
                <th class="px-3 sm:px-4 py-3 text-center">O 2.5</th>
                <th class="px-3 sm:px-4 py-3 text-center">BTTS</th>
                <th class="px-3 sm:px-4 py-3 text-center">Votes (1/X/2)</th>
              </tr>
            </thead>
            <tbody id="fixturesTableBody" class="divide-y divide-dark-border bg-dark-card/50"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 2: ANALYTICS & P&L VIEW -->
    <div id="tabAnalytics" class="space-y-6 sm:space-y-8 hidden">
      <!-- ANALYTICS KPI SUMMARY (2-cols mobile, 5-cols desktop) -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-5">
        <div class="glass-card rounded-2xl p-3.5 sm:p-5 border border-brand-500/40 glow-orange col-span-2 sm:col-span-1">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[10px] sm:text-xs font-semibold text-brand-400 uppercase tracking-wider">Net Profit</span>
            <i class="fa-solid fa-coins text-brand-500 text-xs sm:text-base"></i>
          </div>
          <div id="anNetProfit" class="text-2xl sm:text-3xl font-extrabold text-brand-400">+0.00u</div>
          <div class="text-[10px] sm:text-xs text-gray-400 mt-1">1u flat stake baseline</div>
        </div>

        <div class="glass-card rounded-2xl p-3.5 sm:p-5 border border-emerald-500/30">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[10px] sm:text-xs font-semibold text-emerald-400 uppercase tracking-wider">Win Rate</span>
            <i class="fa-solid fa-trophy text-emerald-500 text-xs sm:text-base"></i>
          </div>
          <div id="anWinRate" class="text-2xl sm:text-3xl font-extrabold text-emerald-400">0.0%</div>
          <div id="anSettledRatio" class="text-[10px] sm:text-xs text-gray-400 mt-1 truncate">0 / 0 settled slips</div>
        </div>

        <div class="glass-card rounded-2xl p-3.5 sm:p-5 border border-accent-500/30">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[10px] sm:text-xs font-semibold text-accent-400 uppercase tracking-wider">ROI</span>
            <i class="fa-solid fa-percent text-accent-500 text-xs sm:text-base"></i>
          </div>
          <div id="anRoi" class="text-2xl sm:text-3xl font-extrabold text-accent-400">0.0%</div>
          <div class="text-[10px] sm:text-xs text-gray-400 mt-1 truncate">Lifetime return</div>
        </div>

        <div class="glass-card rounded-2xl p-3.5 sm:p-5 border border-dark-border">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[10px] sm:text-xs font-semibold text-gray-400 uppercase tracking-wider">Total Slips</span>
            <i class="fa-solid fa-receipt text-gray-400 text-xs sm:text-base"></i>
          </div>
          <div id="anTotalSlips" class="text-2xl sm:text-3xl font-extrabold text-white">0</div>
          <div id="anPendingCount" class="text-[10px] sm:text-xs text-amber-400 mt-1 font-semibold truncate">0 in-play</div>
        </div>

        <div class="glass-card rounded-2xl p-3.5 sm:p-5 border border-dark-border col-span-2 sm:col-span-1">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[10px] sm:text-xs font-semibold text-gray-400 uppercase tracking-wider">Streak</span>
            <i class="fa-solid fa-fire text-brand-500 text-xs sm:text-base"></i>
          </div>
          <div id="anCurrentStreak" class="text-xl sm:text-2xl font-extrabold text-white truncate">--</div>
          <div class="text-[10px] sm:text-xs text-gray-400 mt-1 truncate">Consecutive outcomes</div>
        </div>
      </div>

      <!-- MARKET ACCURACY BREAKDOWN BARS -->
      <div class="glass-card rounded-2xl p-4 sm:p-6 border border-dark-border space-y-4">
        <div>
          <h3 class="text-lg sm:text-xl font-bold text-white flex items-center space-x-2">
            <span>🎯 Market Accuracy Breakdown</span>
          </h3>
          <p class="text-[11px] sm:text-xs text-gray-400">Hit rates across conservative betting markets</p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4" id="marketAccuracyCards">
          <!-- Dynamically populated -->
        </div>
      </div>

      <!-- TIMEFRAME RESULTS & SETTLEMENT LEDGER -->
      <div class="glass-card rounded-2xl p-4 sm:p-6 border border-dark-border space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 class="text-lg sm:text-xl font-bold text-white flex items-center space-x-2">
              <span>📋 Multi-Timeframe Historical Ledger</span>
            </h3>
            <p class="text-[11px] sm:text-xs text-gray-400">Complete record of daily, weekly, and monthly performance</p>
          </div>

          <!-- Timeframe Selector -->
          <div class="grid grid-cols-2 sm:flex items-center bg-dark-surface p-1 rounded-xl border border-dark-border gap-1 w-full sm:w-auto">
            <button id="tfSlipsBtn" onclick="switchTimeframe('slips')" class="px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-brand-500 transition text-center">Detailed Slips</button>
            <button id="tfDailyBtn" onclick="switchTimeframe('daily')" class="px-3 py-1.5 rounded-lg text-xs font-bold text-gray-400 hover:text-white transition text-center">Daily</button>
            <button id="tfWeeklyBtn" onclick="switchTimeframe('weekly')" class="px-3 py-1.5 rounded-lg text-xs font-bold text-gray-400 hover:text-white transition text-center">Weekly</button>
            <button id="tfMonthlyBtn" onclick="switchTimeframe('monthly')" class="px-3 py-1.5 rounded-lg text-xs font-bold text-gray-400 hover:text-white transition text-center">Monthly</button>
          </div>
        </div>

        <!-- Ledger Container -->
        <div id="ledgerContainer" class="space-y-3 sm:space-y-4"></div>
      </div>
    </div>
  </main>

  <!-- FOOTER -->
  <footer class="border-t border-dark-border py-6 mt-12 bg-dark-surface/30">
    <div class="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between text-xs text-gray-500 gap-4">
      <div class="flex items-center space-x-2">
        <span class="font-bold text-gray-300">Onítẹ́tẹ́</span>
        <span>•</span>
        <span>Eighty-Two Limited AI Prediction Engine</span>
      </div>
      <div>
        <span>Daily 1.5x, 3x, 5x, 10x Odds • Real-Time Score Settlement • Multi-Timeframe Records</span>
      </div>
    </div>
  </footer>

  <!-- TOAST NOTIFICATION -->
  <div id="toast" class="fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:bottom-6 max-w-md px-4 py-3 rounded-2xl bg-dark-card/98 border border-dark-border text-white text-xs sm:text-sm font-semibold shadow-2xl transition-all duration-300 transform translate-y-28 opacity-0 flex items-center justify-between gap-3 z-[9999] pointer-events-auto">
    <div class="flex items-center space-x-2.5 min-w-0">
      <i id="toastIcon" class="fa-solid fa-circle-check text-brand-500 text-sm flex-shrink-0"></i>
      <span id="toastMsg" class="truncate font-medium">Action completed</span>
    </div>
    <button onclick="hideToast()" class="text-gray-400 hover:text-white p-1 flex-shrink-0" aria-label="Close notification">
      <i class="fa-solid fa-xmark text-xs"></i>
    </button>
  </div>

  <!-- JAVASCRIPT LOGIC -->
  <script>
    let rawSlips = null;
    let rawFixtures = [];
    let rawAnalytics = null;
    let activeTab = 'predictions';
    let activeTimeframe = 'slips';
    let selectedTier = '5'; // '1.5', '3', '5', '10'
    let autoSyncEnabled = true;
    let autoSyncTimer = null;

    async function loadData(showToastAlert = false) {
      try {
        const [slipsRes, fixturesRes, analyticsRes] = await Promise.all([
          fetch('/api/slips'),
          fetch('/api/fixtures'),
          fetch('/api/analytics')
        ]);
        rawSlips = await slipsRes.json();
        rawFixtures = await fixturesRes.json();
        rawAnalytics = await analyticsRes.json();

        updateTierOverviews(rawSlips);
        renderActiveSlip();
        renderFixtures(rawFixtures);
        renderAnalytics(rawAnalytics);
        updateStats();

        if (showToastAlert) {
          showToast("Live data synchronized!", "success");
        }
      } catch (err) {
        console.error("Error loading data:", err);
        if (showToastAlert) showToast("Error loading daily data", "error");
      }
    }

    function switchTab(tab) {
      activeTab = tab;
      const tabPred = document.getElementById('tabPredictions');
      const tabAnal = document.getElementById('tabAnalytics');
      const btnPred = document.getElementById('tabPredictionsBtn');
      const btnAnal = document.getElementById('tabAnalyticsBtn');

      if (tab === 'predictions') {
        tabPred.classList.remove('hidden');
        tabAnal.classList.add('hidden');
        btnPred.className = "px-4 py-1.5 rounded-lg text-xs font-bold transition text-white bg-brand-500 shadow-md";
        btnAnal.className = "px-4 py-1.5 rounded-lg text-xs font-bold transition text-gray-400 hover:text-white";
      } else {
        tabPred.classList.add('hidden');
        tabAnal.classList.remove('hidden');
        btnAnal.className = "px-4 py-1.5 rounded-lg text-xs font-bold transition text-white bg-brand-500 shadow-md";
        btnPred.className = "px-4 py-1.5 rounded-lg text-xs font-bold transition text-gray-400 hover:text-white";
        renderAnalytics(rawAnalytics);
      }
    }

    function updateTierOverviews(data) {
      if (!data) return;
      
      const t15 = data.slip_1_5odds;
      const t3 = data.slip_3odds;
      const t5 = data.slip_5odds || data.daily_ticket || data.banker_ticket;
      const t10 = data.slip_10odds;

      if (t15) {
        document.getElementById('tierOdds15').innerText = `${t15.total_odds}x`;
        document.getElementById('tierConf15').innerText = `${t15.average_confidence}% Conf`;
        document.getElementById('tierLegs15').innerText = `${t15.legs_count} Ultra-Safe Legs`;
      }
      if (t3) {
        document.getElementById('tierOdds3').innerText = `${t3.total_odds}x`;
        document.getElementById('tierConf3').innerText = `${t3.average_confidence}% Conf`;
        document.getElementById('tierLegs3').innerText = `${t3.legs_count} Balanced Legs`;
      }
      if (t5) {
        document.getElementById('tierOdds5').innerText = `${t5.total_odds}x`;
        document.getElementById('tierConf5').innerText = `${t5.average_confidence}% Conf`;
        document.getElementById('tierLegs5').innerText = `${t5.legs_count} Conservative Legs`;
      }
      if (t10) {
        document.getElementById('tierOdds10').innerText = `${t10.total_odds}x`;
        document.getElementById('tierConf10').innerText = `${t10.average_confidence}% Conf`;
        document.getElementById('tierLegs10').innerText = `${t10.legs_count} Safe Legs`;
      }
    }

    function selectSlipTier(tier) {
      selectedTier = tier;
      ['15', '3', '5', '10'].forEach(t => {
        const btn = document.getElementById(`btnTier${t}`);
        const card = document.getElementById(`tierCard${t}`);
        const cleanTier = t === '15' ? '1.5' : t;
        
        if (cleanTier === tier) {
          if (btn) btn.className = "px-3 py-1.5 rounded-lg text-xs font-bold transition text-white bg-brand-500 shadow-md";
          if (card) {
            card.classList.add('border-brand-500', 'glow-orange');
            card.classList.remove('border-dark-border');
          }
        } else {
          if (btn) btn.className = "px-3 py-1.5 rounded-lg text-xs font-bold transition text-gray-400 hover:text-white";
          if (card) {
            card.classList.remove('border-brand-500', 'glow-orange');
            card.classList.add('border-dark-border');
          }
        }
      });

      renderActiveSlip();
    }

    function getSelectedSlipObject() {
      if (!rawSlips) return null;
      if (selectedTier === '1.5') return rawSlips.slip_1_5odds;
      if (selectedTier === '3') return rawSlips.slip_3odds;
      if (selectedTier === '10') return rawSlips.slip_10odds;
      return rawSlips.slip_5odds || rawSlips.daily_ticket || rawSlips.banker_ticket;
    }

    function renderActiveSlip() {
      const slip = getSelectedSlipObject();
      if (!slip) {
        document.getElementById('dailyTitle').innerText = "No Slip Available";
        document.getElementById('dailyDesc').innerText = "Run scrape or analysis to generate tickets.";
        document.getElementById('dailyLegsList').innerHTML = `<div class="p-6 text-center text-gray-500">No predictions generated yet for this tier.</div>`;
        return;
      }

      document.getElementById('dailyTitle').innerText = slip.name || `Onítẹ́tẹ́ ${selectedTier}-Odds Slip`;
      document.getElementById('dailyDesc').innerText = slip.description || 'Ultra-conservative multi-market daily ticket.';
      document.getElementById('dailyTotalOdds').innerText = `${slip.total_odds}x`;
      document.getElementById('dailyAvgConf').innerText = `${slip.average_confidence}%`;
      document.getElementById('dailyLegsCount').innerText = slip.legs_count;

      const list = document.getElementById('dailyLegsList');
      list.innerHTML = slip.legs.map(leg => createLegCard(leg, 'brand')).join('');
    }

    function createLegCard(leg, theme) {
      const isBrand = theme === 'brand';
      const badgeBg = isBrand ? 'bg-brand-500/15 text-brand-500 border-brand-500/30' : 'bg-accent-500/15 text-accent-400 border-accent-500/30';
      const oddsColor = isBrand ? 'text-brand-400' : 'text-accent-400';

      // Real live score status indicator
      let scoreBadge = '';
      if (leg.home_goals !== undefined && leg.home_goals !== null && leg.away_goals !== undefined && leg.away_goals !== null) {
        const isWon = leg.status === 'WON';
        const isLost = leg.status === 'LOST';
        const isLive = leg.status === 'LIVE';

        if (isWon) {
          scoreBadge = `<span class="px-2 py-0.5 rounded-md font-mono font-bold text-[10px] sm:text-[11px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center space-x-1 whitespace-nowrap"><i class="fa-solid fa-check text-[9px]"></i><span>${leg.home_goals} - ${leg.away_goals} (FT)</span></span>`;
        } else if (isLost) {
          scoreBadge = `<span class="px-2 py-0.5 rounded-md font-mono font-bold text-[10px] sm:text-[11px] bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center space-x-1 whitespace-nowrap"><i class="fa-solid fa-xmark text-[9px]"></i><span>${leg.home_goals} - ${leg.away_goals} (FT)</span></span>`;
        } else if (isLive) {
          const liveMin = leg.live_minute || 'LIVE';
          scoreBadge = `<span class="px-2 py-0.5 rounded-md font-mono font-bold text-[10px] sm:text-[11px] bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center space-x-1 animate-pulse whitespace-nowrap"><i class="fa-solid fa-circle-dot text-[9px]"></i><span>${leg.home_goals} - ${leg.away_goals} (${liveMin})</span></span>`;
        } else {
          scoreBadge = `<span class="px-2 py-0.5 rounded-md font-mono font-semibold text-[10px] sm:text-[11px] bg-gray-800 text-gray-300 border border-gray-700 whitespace-nowrap">${leg.home_goals} - ${leg.away_goals}</span>`;
        }
      } else {
        scoreBadge = `<span class="px-2 py-0.5 rounded-md font-mono text-[10px] sm:text-[11px] bg-dark-bg text-gray-500 border border-dark-border/60 whitespace-nowrap">${leg.time || 'Scheduled'}</span>`;
      }

      return `
        <div class="p-3 sm:p-3.5 rounded-xl bg-dark-surface/50 border border-dark-border hover:border-gray-700 transition">
          <div class="flex flex-wrap items-center justify-between gap-1.5 mb-2">
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="text-xs font-mono font-semibold text-gray-400">${leg.time || '18:00'}</span>
              <span class="text-[11px] px-2 py-0.5 rounded-md ${badgeBg} border font-bold">${leg.market}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-dark-surface border border-dark-border text-gray-400 uppercase font-semibold">${leg.risk_level || 'Safe'}</span>
            </div>
            <div class="flex items-center space-x-2 ml-auto">
              ${scoreBadge}
              <span class="text-sm font-extrabold ${oddsColor}">
                ${leg.estimated_odds}x
              </span>
            </div>
          </div>

          <div class="font-bold text-white text-sm sm:text-base mb-1 truncate">
            ${leg.home_team} <span class="text-gray-500 font-normal">vs</span> ${leg.away_team}
          </div>

          <div class="flex flex-wrap items-center justify-between text-xs mt-2 pt-2 border-t border-dark-border/50 gap-1">
            <div class="text-gray-200 font-semibold flex items-center space-x-1.5">
              <i class="fa-solid fa-shield-check text-brand-500 text-xs"></i>
              <span>${leg.selection}</span>
            </div>
            <div class="text-gray-400 font-medium text-xs">
              Conf: <span class="text-white font-bold">${leg.confidence_score}%</span>
            </div>
          </div>

          <div class="text-[11px] text-gray-400 mt-1.5 leading-snug bg-dark-bg/60 p-2 rounded-lg border border-dark-border/60">
            ↳ <span class="text-gray-300">${leg.justification || 'High probability safety consensus.'}</span>
          </div>
        </div>
      `;
    }

    function renderFixtures(fixtures) {
      const tbody = document.getElementById('fixturesTableBody');
      if (!fixtures || fixtures.length === 0) {
        tbody.innerHTML = `<tr><td colspan="11" class="text-center py-6 text-gray-500">No fixtures available.</td></tr>`;
        return;
      }

      tbody.innerHTML = fixtures.map(f => `
        <tr class="hover:bg-dark-surface/60 transition">
          <td class="px-4 py-3 font-mono text-xs text-gray-400">${f.time || '-'}</td>
          <td class="px-4 py-3 text-xs text-gray-400">
            <span class="px-2 py-0.5 rounded bg-dark-surface border border-dark-border text-gray-300 font-medium">${f.competition || 'LEAGUE'}</span>
          </td>
          <td class="px-4 py-3 font-semibold text-white">
            ${f.home_team} <span class="text-gray-500 font-normal">vs</span> ${f.away_team}
          </td>
          <td class="px-4 py-3 text-center">
            <span class="px-2 py-1 rounded-md bg-brand-500/20 text-brand-500 font-bold text-xs border border-brand-500/30">${f.tip || '-'}</span>
          </td>
          <td class="px-4 py-3 text-center font-mono ${f.coef_1 >= 60 ? 'text-brand-500 font-bold' : 'text-gray-300'}">${f.coef_1 || 0}%</td>
          <td class="px-4 py-3 text-center font-mono text-gray-400">${f.coef_x || 0}%</td>
          <td class="px-4 py-3 text-center font-mono ${f.coef_2 >= 60 ? 'text-brand-500 font-bold' : 'text-gray-300'}">${f.coef_2 || 0}%</td>
          <td class="px-4 py-3 text-center font-mono ${f.coef_o15 >= 85 ? 'text-emerald-400 font-bold' : 'text-gray-400'}">${f.coef_o15 || 0}%</td>
          <td class="px-4 py-3 text-center font-mono ${f.coef_o25 >= 60 ? 'text-emerald-400 font-bold' : 'text-gray-400'}">${f.coef_o25 || 0}%</td>
          <td class="px-4 py-3 text-center font-mono ${f.coef_bts >= 65 ? 'text-blue-400 font-bold' : 'text-gray-400'}">${f.coef_bts || 0}%</td>
          <td class="px-4 py-3 text-center font-mono text-xs text-gray-400">${f.vote_1 || 0} / ${f.vote_x || 0} / ${f.vote_2 || 0}</td>
        </tr>
      `).join('');
    }

    function renderAnalytics(data) {
      if (!data || !data.summary) return;
      const sum = data.summary;

      const profitPrefix = sum.net_profit >= 0 ? '+' : '';
      const profitColor = sum.net_profit >= 0 ? 'text-brand-400' : 'text-rose-400';
      document.getElementById('anNetProfit').innerText = `${profitPrefix}${sum.net_profit}u`;
      document.getElementById('anNetProfit').className = `text-3xl font-extrabold ${profitColor}`;
      
      document.getElementById('anWinRate').innerText = `${sum.win_rate}%`;
      document.getElementById('anSettledRatio').innerText = `${sum.won_count} won / ${sum.lost_count} lost (${sum.settled_count} settled)`;
      document.getElementById('anRoi').innerText = `${sum.roi_pct}%`;
      document.getElementById('anTotalSlips').innerText = sum.total_slips;
      document.getElementById('anPendingCount').innerText = `${sum.pending_count} in-play / pending`;
      document.getElementById('anCurrentStreak').innerText = sum.current_streak;

      // Market Accuracy Breakdown Cards
      const marketDiv = document.getElementById('marketAccuracyCards');
      if (data.market_accuracy && data.market_accuracy.length > 0) {
        marketDiv.innerHTML = data.market_accuracy.map(m => `
          <div class="p-4 rounded-xl bg-dark-surface/60 border border-dark-border">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-semibold text-gray-300">${m.market}</span>
              <span class="text-sm font-extrabold text-brand-400">${m.win_rate}%</span>
            </div>
            <div class="w-full h-2 rounded-full bg-dark-bg overflow-hidden">
              <div class="h-full bg-gradient-to-r from-brand-500 to-emerald-500 rounded-full" style="width: ${m.win_rate}%"></div>
            </div>
            <div class="flex justify-between text-[11px] text-gray-500 mt-2">
              <span>${m.won} Won / ${m.total} Total</span>
              <span>${m.lost} Lost</span>
            </div>
          </div>
        `).join('');
      }

      renderTimeframeContent();
    }

    function switchTimeframe(tf) {
      activeTimeframe = tf;
      ['slips', 'daily', 'weekly', 'monthly'].forEach(key => {
        const btn = document.getElementById(`tf${key.charAt(0).toUpperCase() + key.slice(1)}Btn`);
        if (btn) {
          if (key === tf) {
            btn.className = "px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-brand-500 transition text-center";
          } else {
            btn.className = "px-3 py-1.5 rounded-lg text-xs font-bold text-gray-400 hover:text-white transition text-center";
          }
        }
      });
      renderTimeframeContent();
    }

    function renderTimeframeContent() {
      if (!rawAnalytics) return;
      const container = document.getElementById('ledgerContainer');

      if (activeTimeframe === 'slips') {
        const slips = rawAnalytics.recent_slips || [];
        if (slips.length === 0) {
          container.innerHTML = `<div class="p-6 text-center text-gray-500">No settled slips found in ledger.</div>`;
          return;
        }

        container.innerHTML = slips.map(s => {
          const isWon = s.status === 'WON';
          const isLost = s.status === 'LOST';
          const isLive = s.status === 'LIVE';

          let statusBadge = `<span class="px-2.5 py-1 rounded-full bg-gray-700/50 text-gray-300 text-xs font-bold border border-gray-600">PENDING</span>`;
          if (isWon) statusBadge = `<span class="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold border border-emerald-500/30"><i class="fa-solid fa-check mr-1"></i> WON</span>`;
          if (isLost) statusBadge = `<span class="px-2.5 py-1 rounded-full bg-rose-500/20 text-rose-400 text-xs font-bold border border-rose-500/30"><i class="fa-solid fa-xmark mr-1"></i> LOST</span>`;
          if (isLive) statusBadge = `<span class="px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-400 text-xs font-bold border border-amber-500/30 animate-pulse"><i class="fa-solid fa-circle-dot mr-1"></i> LIVE</span>`;

          const pCol = s.profit > 0 ? 'text-brand-400' : (s.profit < 0 ? 'text-rose-400' : 'text-gray-400');
          const pPrefix = s.profit > 0 ? '+' : '';

          return `
            <div class="p-5 rounded-2xl bg-dark-surface/50 border border-dark-border space-y-4">
              <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-dark-border/60">
                <div class="flex items-center space-x-3">
                  ${statusBadge}
                  <div>
                    <h4 class="font-bold text-white text-base">${s.slip_name}</h4>
                    <span class="text-xs text-gray-400 font-mono">${s.date} • ${s.legs_count} Legs • Avg Conf: ${s.average_confidence}%</span>
                  </div>
                </div>

                <div class="flex items-center space-x-4 text-sm">
                  <div>
                    <span class="text-xs text-gray-400">Total Odds:</span>
                    <span class="font-bold text-white ml-1">${s.total_odds}x</span>
                  </div>
                  <div class="h-4 w-px bg-dark-border"></div>
                  <div>
                    <span class="text-xs text-gray-400">Net Profit:</span>
                    <span class="font-extrabold ${pCol} ml-1">${pPrefix}${s.profit}u</span>
                  </div>
                </div>
              </div>

              <!-- Legs Breakdown -->
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                ${s.legs.map(l => {
                  let lBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] bg-gray-800 text-gray-400 font-bold border border-gray-700">PENDING</span>`;
                  if (l.status === 'WON') lBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">WON</span>`;
                  if (l.status === 'LOST') lBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] bg-rose-500/20 text-rose-400 font-bold border border-rose-500/30">LOST</span>`;
                  if (l.status === 'LIVE') lBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-400 font-bold border border-amber-500/30 animate-pulse">LIVE</span>`;

                  const scoreText = (l.home_goals !== null && l.away_goals !== null) ? `${l.home_goals} - ${l.away_goals} (${l.match_status})` : 'Scheduled';

                  return `
                    <div class="p-3 rounded-xl bg-dark-bg/60 border border-dark-border/60 text-xs space-y-1.5">
                      <div class="flex items-center justify-between">
                        <span class="font-bold text-white">${l.home_team} vs ${l.away_team}</span>
                        ${lBadge}
                      </div>
                      <div class="flex items-center justify-between text-gray-400">
                        <span class="text-gray-300 font-semibold">${l.selection} @ ${l.estimated_odds}x</span>
                        <span class="font-mono text-[11px] text-gray-400">${scoreText}</span>
                      </div>
                    </div>
                  `;
                }).join('')}
              </div>
            </div>
          `;
        }).join('');
      } else if (activeTimeframe === 'daily') {
        const days = rawAnalytics.daily || [];
        container.innerHTML = renderAggregateTable(days, 'Date', 'date');
      } else if (activeTimeframe === 'weekly') {
        const weeks = rawAnalytics.weekly || [];
        container.innerHTML = renderAggregateTable(weeks, 'Week', 'week');
      } else if (activeTimeframe === 'monthly') {
        const months = rawAnalytics.monthly || [];
        container.innerHTML = renderAggregateTable(months, 'Month', 'month');
      }
    }

    function renderAggregateTable(items, label, key) {
      if (items.length === 0) return `<div class="p-6 text-center text-gray-500">No records found.</div>`;

      return `
        <div class="overflow-x-auto custom-scroll rounded-xl border border-dark-border">
          <table class="w-full text-left text-sm text-gray-300">
            <thead class="bg-dark-surface/90 text-xs uppercase text-gray-400 font-semibold border-b border-dark-border">
              <tr>
                <th class="px-4 py-3">${label}</th>
                <th class="px-4 py-3 text-center">Total Slips</th>
                <th class="px-4 py-3 text-center">Won</th>
                <th class="px-4 py-3 text-center">Lost</th>
                <th class="px-4 py-3 text-center">Win Rate</th>
                <th class="px-4 py-3 text-center">Staked</th>
                <th class="px-4 py-3 text-right">Net Profit</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-dark-border bg-dark-card/50 font-mono">
              ${items.map(it => {
                const pCol = it.profit >= 0 ? 'text-brand-400 font-bold' : 'text-rose-400 font-bold';
                const pPre = it.profit >= 0 ? '+' : '';
                return `
                  <tr class="hover:bg-dark-surface/60 transition">
                    <td class="px-4 py-3 font-sans font-bold text-white">${it[key]}</td>
                    <td class="px-4 py-3 text-center">${it.total}</td>
                    <td class="px-4 py-3 text-center text-emerald-400 font-bold">${it.won}</td>
                    <td class="px-4 py-3 text-center text-rose-400 font-bold">${it.lost}</td>
                    <td class="px-4 py-3 text-center text-white">${it.win_rate || 0}%</td>
                    <td class="px-4 py-3 text-center text-gray-400">${it.staked || it.total}u</td>
                    <td class="px-4 py-3 text-right ${pCol}">${pPre}${it.profit}u</td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    function filterTable() {
      const query = document.getElementById('searchInput').value.toLowerCase();
      const tipFilter = document.getElementById('marketFilter').value;

      const filtered = rawFixtures.filter(f => {
        const matchesQuery = (
          (f.home_team && f.home_team.toLowerCase().includes(query)) ||
          (f.away_team && f.away_team.toLowerCase().includes(query)) ||
          (f.competition && f.competition.toLowerCase().includes(query))
        );
        const matchesTip = tipFilter === 'all' || (f.tip === tipFilter);
        return matchesQuery && matchesTip;
      });

      renderFixtures(filtered);
    }

    function updateStats() {
      const el = document.getElementById('statTotalFixtures');
      if (el) el.innerText = rawFixtures.length;
    }

    async function updateLiveScores() {
      const btn = document.getElementById('btnUpdateScores');
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-xs"></i> <span>Syncing...</span>`;
      }
      showToast("Fetching live match scores & settling slips...", "info");

      try {
        const res = await fetch('/api/update-scores', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          const count = data.live_scores_count || 0;
          showToast(`⚡ Synced ${count} match scores & settled tickets!`, "success");
          loadData(true);
        } else {
          showToast(data.message || "Failed to update live scores", "error");
        }
      } catch (err) {
        showToast("Error updating live scores", "error");
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `<i class="fa-solid fa-arrows-rotate text-xs text-emerald-400"></i> <span>⚡ Sync Live Scores</span>`;
        }
      }
    }

    function toggleAutoSync() {
      autoSyncEnabled = !autoSyncEnabled;
      const dot = document.getElementById('autoSyncDot');
      const text = document.getElementById('autoSyncText');

      if (autoSyncEnabled) {
        dot.className = "w-2 h-2 rounded-full bg-emerald-400 animate-pulse";
        text.innerText = "Auto Live: ON (30s)";
        startAutoSyncInterval();
        showToast("Live auto-sync enabled (30s)", "success");
      } else {
        dot.className = "w-2 h-2 rounded-full bg-gray-500";
        text.innerText = "Auto Live: OFF";
        if (autoSyncTimer) clearInterval(autoSyncTimer);
        showToast("Live auto-sync paused", "info");
      }
    }

    function startAutoSyncInterval() {
      if (autoSyncTimer) clearInterval(autoSyncTimer);
      autoSyncTimer = setInterval(() => {
        if (autoSyncEnabled) {
          fetch('/api/update-scores', { method: 'POST' })
            .then(() => loadData(false))
            .catch(() => {});
        }
      }, 30000);
    }

    async function triggerScrape() {
      const btn = document.getElementById('btnTriggerScrape');
      if (!btn) return;
      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Initiating...</span>`;
      showToast("Starting live scraper in background...", "info");

      try {
        const res = await fetch('/api/scrape', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        const data = await res.json();
        if (data.success) {
          showToast("Scraper active! Monitoring live progress...", "success");
          pollScraperStatus();
        } else {
          showToast(data.message || "Scraper already running", "info");
          pollScraperStatus();
        }
      } catch (err) {
        showToast("Error triggering scraper", "error");
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-bolt"></i> <span>Scrape Today</span>`;
      }
    }

    let pollScraperTimer = null;
    function pollScraperStatus() {
      if (pollScraperTimer) clearInterval(pollScraperTimer);
      const btn = document.getElementById('btnTriggerScrape');

      pollScraperTimer = setInterval(async () => {
        try {
          const res = await fetch('/api/status');
          const status = await res.json();

          if (btn) {
            if (status.is_running) {
              btn.disabled = true;
              const pText = status.progress_pct > 0 ? `${status.progress_pct}%` : 'Running...';
              btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-accent-500"></i> <span>Scraping (${pText})</span>`;
            } else {
              clearInterval(pollScraperTimer);
              btn.disabled = false;
              btn.innerHTML = `<i class="fa-solid fa-bolt"></i> <span>Scrape Today</span>`;

              if (status.error) {
                showToast("Scraper error: " + status.error, "error");
              } else if (status.last_run) {
                loadData(true);
                showToast(`Scrape completed! ${status.total_fixtures || 0} fixtures updated.`, "success");
              }
            }
          }
        } catch (err) {
          // ignore transient poll error
        }
      }, 1500);
    }

    function copyCurrentSlip() {
      const slip = getSelectedSlipObject();
      if (!slip) return;
      let text = `⚽ ONÍTẸ́TẸ́ ${slip.name.toUpperCase()} (${slip.total_odds}x Odds)\n`;
      text += `Avg Confidence: ${slip.average_confidence}% | Legs: ${slip.legs_count}\n\n`;
      slip.legs.forEach(l => {
        const score = (l.home_goals !== null && l.away_goals !== null) ? ` [${l.home_goals}-${l.away_goals} ${l.match_status}]` : '';
        text += `• ${l.time} | ${l.home_team} vs ${l.away_team} -> ${l.selection} @ ${l.estimated_odds}x${score}\n`;
      });
      text += `\nGenerated by Onítẹ́tẹ́ AI Engine`;

      navigator.clipboard.writeText(text);
      showToast(`${slip.name} copied to clipboard!`, "success");
    }

    function copyAllSlips() {
      if (!rawSlips) return;
      const tiers = [
        rawSlips.slip_1_5odds,
        rawSlips.slip_3odds,
        rawSlips.slip_5odds || rawSlips.daily_ticket,
        rawSlips.slip_10odds,
      ].filter(Boolean);

      if (tiers.length === 0) return;

      let text = `🛡️ ONÍTẸ́TẸ́ DAILY MULTI-TIER SLIPS (1.5x, 3x, 5x, 10x)\n`;
      text += `==============================================\n`;

      tiers.forEach(s => {
        text += `\n>> ${s.name.toUpperCase()} (${s.total_odds}x Total Odds | ${s.average_confidence}% Conf)\n`;
        s.legs.forEach(l => {
          text += `  • ${l.time} | ${l.home_team} vs ${l.away_team} -> ${l.selection} @ ${l.estimated_odds}x\n`;
        });
      });

      text += `\nGenerated by Onítẹ́tẹ́ AI Engine`;
      navigator.clipboard.writeText(text);
      showToast("All 4 daily slips copied to clipboard!", "success");
    }

    let toastTimeout = null;
    function hideToast() {
      const toast = document.getElementById('toast');
      if (toast) {
        toast.classList.remove('translate-y-0', 'opacity-100');
        toast.classList.add('translate-y-28', 'opacity-0');
      }
      if (toastTimeout) clearTimeout(toastTimeout);
    }

    function showToast(msg, type = "success") {
      const toast = document.getElementById('toast');
      const toastMsg = document.getElementById('toastMsg');
      const toastIcon = document.getElementById('toastIcon');

      let cleanMsg = String(msg || '');
      if (cleanMsg.length > 140) {
        cleanMsg = cleanMsg.substring(0, 137) + '...';
      }

      toastMsg.innerText = cleanMsg;
      if (type === 'error') {
        toastIcon.className = "fa-solid fa-circle-exclamation text-rose-500 text-sm flex-shrink-0";
      } else if (type === 'info') {
        toastIcon.className = "fa-solid fa-circle-info text-blue-400 text-sm flex-shrink-0";
      } else {
        toastIcon.className = "fa-solid fa-circle-check text-brand-500 text-sm flex-shrink-0";
      }

      toast.classList.remove('translate-y-28', 'opacity-0');
      toast.classList.add('translate-y-0', 'opacity-100');

      if (toastTimeout) clearTimeout(toastTimeout);
      toastTimeout = setTimeout(() => {
        hideToast();
      }, 4000);
    }

    window.addEventListener('DOMContentLoaded', () => {
      loadData();
      startAutoSyncInterval();
    });
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    """Serve the single-page application dashboard."""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/slips", methods=["GET"])
def get_slips():
    """Return the generated 5-odds accumulator slips with real live scores."""
    paths = get_data_paths()
    if not os.path.exists(paths["slips_json"]):
        try:
            engine = AccumulatorEngine(output_dir=OUTPUT_DIR)
            engine.generate_and_save()
        except Exception as e:
            return jsonify({"error": f"Failed to generate slips: {e}"}), 500

    try:
        with open(paths["slips_json"], "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fixtures", methods=["GET"])
def get_fixtures():
    """Return the normalized fixtures table as JSON."""
    paths = get_data_paths()
    if not os.path.exists(paths["fixtures_csv"]):
        return jsonify([])

    try:
        df = pd.read_csv(paths["fixtures_csv"])
        df = df.fillna("")
        return jsonify(df.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    """Return Daily, Weekly, Monthly performance analytics & P&L ledger."""
    try:
        tracker = ResultsTracker(output_dir=OUTPUT_DIR)
        analytics_data = tracker.compute_analytics()
        return jsonify(analytics_data)
    except Exception as e:
        logger.error(f"Error computing analytics: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/update-scores", methods=["POST"])
def update_scores():
    """Fetch live match scores and settle today's slips."""
    try:
        tracker = ResultsTracker(output_dir=OUTPUT_DIR)
        settlement_res = tracker.settle_today_slips()
        return jsonify(settlement_res)
    except Exception as e:
        logger.error(f"Error settling slips: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def get_status():
    """Return background scraper execution status."""
    return jsonify(SCRAPER_STATE)


@app.route("/api/refresh-slips", methods=["POST"])
def refresh_slips():
    """Re-analyze and rebuild accumulator slips from existing data."""
    try:
        engine = AccumulatorEngine(output_dir=OUTPUT_DIR)
        res = engine.generate_and_save()
        paths = get_data_paths()
        with open(paths["slips_json"], "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({"success": True, "slips": data})
    except Exception as e:
        logger.error(f"Error rebuilding slips: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


def _run_scraper_job(limit: Optional[int] = None):
    """Background scraper execution job with real-time progress updates."""
    global SCRAPER_STATE
    SCRAPER_STATE["is_running"] = True
    SCRAPER_STATE["progress_pct"] = 0
    SCRAPER_STATE["progress_text"] = "Crawling fixture predictions list..."
    SCRAPER_STATE["status"] = "Crawling fixture predictions..."
    SCRAPER_STATE["error"] = None

    def on_progress(idx, total, title):
        pct = round((idx / total) * 100) if total else 0
        SCRAPER_STATE["progress_pct"] = pct
        SCRAPER_STATE["progress_text"] = f"{idx}/{total}: {title}"
        SCRAPER_STATE["status"] = f"Scraping ({pct}%): {title}"

    try:
        scraper = StatareaScraper(output_dir=OUTPUT_DIR)
        results = scraper.run(limit=limit, export=True, progress_callback=on_progress)
        SCRAPER_STATE["total_fixtures"] = len(results)
        SCRAPER_STATE["progress_pct"] = 100
        SCRAPER_STATE["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
        SCRAPER_STATE["status"] = f"Completed successfully ({len(results)} matches)"
    except Exception as e:
        logger.error(f"Scraper error: {e}")
        SCRAPER_STATE["error"] = str(e)
        SCRAPER_STATE["status"] = f"Failed: {e}"
    finally:
        SCRAPER_STATE["is_running"] = False


@app.route("/api/scrape", methods=["POST"])
def trigger_scrape():
    """Trigger a live background crawl across today's Statarea fixtures."""
    global SCRAPER_STATE
    if SCRAPER_STATE["is_running"]:
        return jsonify({"success": False, "message": "Scraper is already running."}), 400

    data = request.get_json(silent=True) or {}
    limit = data.get("limit")

    thread = threading.Thread(target=_run_scraper_job, kwargs={"limit": limit}, daemon=True)
    thread.start()
    return jsonify({"success": True, "message": "Scraper job started in background."})


def start_server(port: int = 5000, open_browser: bool = True):
    """Start the dashboard server and optionally open the browser."""
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    url = f"http://localhost:{port}"
    print("\n" + "=" * 60)
    print(f"  [+] Onitete (Eighty-Two AI) Dashboard Live at:")
    print(f"      {url}")
    print("=" * 60 + "\n")

    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    start_server(port=5000, open_browser=False)
