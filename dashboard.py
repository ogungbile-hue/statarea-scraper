"""Onítẹ́tẹ́ - Daily Prediction, Live Score Tracker & Historical Analytics Dashboard.
Powered by Eighty-Two AI Engine.
"""

import json
import logging
import os
import threading
import time
import webbrowser
from typing import Dict, Any
from flask import Flask, jsonify, render_template_string, request
import pandas as pd

from statarea_scraper import StatareaScraper, AccumulatorEngine, ResultsTracker

app = Flask(__name__)
logger = logging.getLogger(__name__)

SCRAPER_STATE = {
    "is_running": False,
    "status": "Idle",
    "last_run": None,
    "total_fixtures": 0,
    "error": None,
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")


def get_data_paths():
    return {
        "slips_json": os.path.join(OUTPUT_DIR, "daily_5odds_slip.json"),
        "fixtures_csv": os.path.join(OUTPUT_DIR, "analysis_fixtures_today.csv"),
        "metrics_csv": os.path.join(OUTPUT_DIR, "analysis_team_metrics.csv"),
        "h2h_csv": os.path.join(OUTPUT_DIR, "analysis_h2h_records.csv"),
        "ledger_json": os.path.join(OUTPUT_DIR, "results_ledger.json"),
    }


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
    }
    .glass-card {
      background: rgba(20, 28, 46, 0.75);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 107, 53, 0.12);
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
  <header class="sticky top-0 z-50 glass-card border-b border-dark-border px-3.5 sm:px-6 py-3">
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
                  <stop offset="100%" stop-color="#0a0f1c" />
                </radialGradient>
                <linearGradient id="badge-num" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#f0f4ff" />
                  <stop offset="35%" stop-color="#ffffff" />
                  <stop offset="100%" stop-color="#8a96b8" />
                </linearGradient>
                <filter id="badge-glow" x="-30%" y="-30%" width="160%" height="160%">
                  <feGaussianBlur in="SourceGraphic" stdDeviation="8" result="blur" />
                  <feColorMatrix in="blur" type="matrix" values="1 0.3 0 0 0   0.2 0.1 0 0 0   0 0 0 0 0   0 0 0 0.6 0" result="orange" />
                  <feMerge>
                    <feMergeNode in="orange" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              <!-- Background -->
              <circle cx="250" cy="250" r="250" fill="url(#badge-bg)" />
              <circle cx="250" cy="250" r="214" fill="none" stroke="#0f1826" stroke-width="3" />

              <!-- Rotating outer ring + cardinal dots -->
              <g class="badge-outer">
                <circle cx="250" cy="250" r="205" fill="none" stroke="#1e2e48" stroke-width="2.5" stroke-dasharray="4 9" />
                <circle cx="250" cy="45" r="3.5" fill="#ff6b35" opacity=".85" class="badge-dot" />
                <circle cx="455" cy="250" r="3.5" fill="#ff6b35" opacity=".85" class="badge-dot" />
                <circle cx="250" cy="455" r="3.5" fill="#ff6b35" opacity=".85" class="badge-dot" />
                <circle cx="45" cy="250" r="3.5" fill="#ff6b35" opacity=".85" class="badge-dot" />
                <circle cx="395" cy="99" r="2" fill="#cc4a1a" opacity=".55" />
                <circle cx="395" cy="401" r="2" fill="#cc4a1a" opacity=".55" />
                <circle cx="105" cy="99" r="2" fill="#cc4a1a" opacity=".55" />
                <circle cx="105" cy="401" r="2" fill="#cc4a1a" opacity=".55" />
              </g>

              <g class="badge-inner">
                <circle cx="250" cy="250" r="172" fill="none" stroke="#1a2840" stroke-width="1.5" stroke-dasharray="2 13" />
              </g>

              <circle cx="250" cy="250" r="184" fill="none" stroke="#3a2818" stroke-width="3" class="badge-rim" />
              <circle cx="250" cy="250" r="179" fill="none" stroke="#ff6b35" stroke-width="2" opacity=".35" class="badge-rim" />

              <circle cx="250" cy="250" r="156" fill="url(#badge-disk)" />
              <circle cx="250" cy="250" r="156" fill="none" stroke="#263040" stroke-width="2" />
              <circle cx="250" cy="250" r="149" fill="none" stroke="#1a2030" stroke-width="1.5" />

              <path d="M 250 94 A 156 156 0 0 1 406 250" fill="none" stroke="#2a3040" stroke-width="1.5" />
              <path d="M 250 406 A 156 156 0 0 1 94 250" fill="none" stroke="#2a3040" stroke-width="1.5" />
              <circle cx="250" cy="250" r="90" fill="#ff6b35" opacity=".04" />

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
              <span class="px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-500 text-[10px] font-extrabold tracking-wider border border-brand-500/30 uppercase">
                Live Tracker
              </span>
            </div>
            <p class="text-[11px] sm:text-xs text-gray-400 font-medium">Daily High-Safety Predictions & Performance Analytics</p>
          </div>
        </div>

        <!-- Mobile Action Buttons -->
        <div class="flex items-center space-x-2 md:hidden">
          <button id="btnUpdateScoresMob" onclick="updateLiveScores()" class="p-2.5 rounded-xl bg-dark-surface hover:bg-gray-800 border border-dark-border text-xs text-gray-200 transition" title="Settle & Live Scores">
            <i class="fa-solid fa-arrows-rotate text-xs text-accent-500"></i>
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
        <button id="btnUpdateScores" onclick="updateLiveScores()" class="px-3.5 py-2 rounded-xl bg-dark-surface hover:bg-gray-800 border border-dark-border text-xs font-semibold transition flex items-center space-x-2 text-gray-200 hover:text-white">
          <i class="fa-solid fa-arrows-rotate text-xs text-accent-500"></i>
          <span>Settle & Live Scores</span>
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
      <!-- STATS OVERVIEW CARDS (2-column on mobile, 4-column on desktop) -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-5">
        <div class="glass-card rounded-2xl p-3.5 sm:p-5 border border-dark-border">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[10px] sm:text-xs font-semibold text-gray-400 uppercase tracking-wider">Matches</span>
            <i class="fa-solid fa-calendar-check text-brand-500 text-xs sm:text-base"></i>
          </div>
          <div id="statTotalFixtures" class="text-2xl sm:text-3xl font-extrabold text-white">53</div>
          <div class="text-[10px] sm:text-xs text-gray-500 mt-1 truncate">Today from Statarea</div>
        </div>

        <div class="glass-card rounded-2xl p-3.5 sm:p-5 border border-dark-border">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[10px] sm:text-xs font-semibold text-gray-400 uppercase tracking-wider">H2H Data</span>
            <i class="fa-solid fa-clock-rotate-left text-accent-500 text-xs sm:text-base"></i>
          </div>
          <div id="statH2HCount" class="text-2xl sm:text-3xl font-extrabold text-white">688+</div>
          <div class="text-[10px] sm:text-xs text-gray-500 mt-1 truncate">>= 2023 recency</div>
        </div>

        <div class="glass-card rounded-2xl p-3.5 sm:p-5 border border-brand-500/30 glow-orange">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[10px] sm:text-xs font-semibold text-brand-400 uppercase tracking-wider">Banker Odds</span>
            <i class="fa-solid fa-shield-halved text-brand-500 text-xs sm:text-base"></i>
          </div>
          <div id="statBankerOdds" class="text-2xl sm:text-3xl font-extrabold text-brand-400">4.59x</div>
          <div id="statBankerLegs" class="text-[10px] sm:text-xs text-brand-500/80 mt-1 font-semibold truncate">6 Ultra-Safe Legs</div>
        </div>

        <div class="glass-card rounded-2xl p-3.5 sm:p-5 border border-accent-500/30 glow-blue">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[10px] sm:text-xs font-semibold text-accent-400 uppercase tracking-wider">Value Odds</span>
            <i class="fa-solid fa-chart-line text-accent-500 text-xs sm:text-base"></i>
          </div>
          <div id="statValueOdds" class="text-2xl sm:text-3xl font-extrabold text-accent-400">4.55x</div>
          <div id="statValueLegs" class="text-[10px] sm:text-xs text-accent-400/80 mt-1 font-semibold truncate">6 Diversified Legs</div>
        </div>
      </div>

      <!-- ACCUMULATOR SLIPS SECTION -->
      <div class="space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 class="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center space-x-2">
              <span>🛡️ Onítẹ́tẹ́ High-Safety 5-Odds Slips</span>
            </h2>
            <p class="text-xs sm:text-sm text-gray-400">Conservative multi-market algorithms with dynamic H2H recency and safety filters.</p>
          </div>
          <div>
            <button onclick="copySlipText()" class="w-full sm:w-auto px-4 py-2 rounded-xl bg-dark-surface hover:bg-gray-800 text-xs font-semibold text-gray-300 border border-dark-border transition flex items-center justify-center space-x-2">
              <i class="fa-regular fa-copy text-brand-500"></i>
              <span>Copy Banker Ticket</span>
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6" id="slipsContainer">
          <!-- Banker Ticket Card -->
          <div class="glass-card rounded-2xl p-4 sm:p-6 border border-brand-500/30 flex flex-col justify-between relative overflow-hidden">
            <div class="absolute top-0 right-0 px-3 sm:px-4 py-1 bg-brand-500/20 border-b border-l border-brand-500/30 text-brand-400 text-[10px] sm:text-xs font-bold rounded-bl-xl uppercase tracking-wider">
              Primary Banker
            </div>
            <div>
              <div class="flex items-center space-x-3 mb-3 pr-24">
                <div class="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-brand-500/20 text-brand-500 flex items-center justify-center font-bold border border-brand-500/30 flex-shrink-0">
                  <i class="fa-solid fa-lock text-xs sm:text-sm"></i>
                </div>
                <div>
                  <h3 class="text-base sm:text-lg font-bold text-white" id="bankerTitle">High-Safety 5-Odds Banker Slip</h3>
                  <p class="text-[11px] sm:text-xs text-gray-400" id="bankerDesc">Ultra-conservative multi-market slip</p>
                </div>
              </div>

              <div class="grid grid-cols-3 py-2 px-3 rounded-xl bg-dark-surface/80 border border-dark-border my-3 text-center">
                <div>
                  <span class="text-[10px] sm:text-xs text-gray-400 block">Total Odds</span>
                  <span class="text-sm sm:text-base font-extrabold text-brand-400" id="bankerTotalOdds">4.59x</span>
                </div>
                <div class="border-x border-dark-border">
                  <span class="text-[10px] sm:text-xs text-gray-400 block">Avg Conf</span>
                  <span class="text-sm sm:text-base font-extrabold text-white" id="bankerAvgConf">73.0%</span>
                </div>
                <div>
                  <span class="text-[10px] sm:text-xs text-gray-400 block">Total Legs</span>
                  <span class="text-sm sm:text-base font-extrabold text-gray-200" id="bankerLegsCount">6</span>
                </div>
              </div>

              <!-- Legs List -->
              <div class="space-y-2.5 sm:space-y-3 mt-3" id="bankerLegsList"></div>
            </div>
          </div>

          <!-- Value Ticket Card -->
          <div class="glass-card rounded-2xl p-4 sm:p-6 border border-accent-500/30 flex flex-col justify-between relative overflow-hidden">
            <div class="absolute top-0 right-0 px-3 sm:px-4 py-1 bg-accent-500/20 border-b border-l border-accent-500/30 text-accent-400 text-xs font-bold rounded-bl-xl uppercase tracking-wider">
              Diversified Value
            </div>
            <div>
              <div class="flex items-center space-x-3 mb-3 pr-24">
                <div class="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-accent-500/20 text-accent-400 flex items-center justify-center font-bold border border-accent-500/30 flex-shrink-0">
                  <i class="fa-solid fa-scale-balanced text-xs sm:text-sm"></i>
                </div>
                <div>
                  <h3 class="text-base sm:text-lg font-bold text-white" id="valueTitle">Conservative Multi-Market Value Slip</h3>
                  <p class="text-[11px] sm:text-xs text-gray-400" id="valueDesc">Diversified low-risk ticket</p>
                </div>
              </div>

              <div class="grid grid-cols-3 py-2 px-3 rounded-xl bg-dark-surface/80 border border-dark-border my-3 text-center">
                <div>
                  <span class="text-[10px] sm:text-xs text-gray-400 block">Total Odds</span>
                  <span class="text-sm sm:text-base font-extrabold text-accent-400" id="valueTotalOdds">4.55x</span>
                </div>
                <div class="border-x border-dark-border">
                  <span class="text-[10px] sm:text-xs text-gray-400 block">Avg Conf</span>
                  <span class="text-sm sm:text-base font-extrabold text-white" id="valueAvgConf">72.9%</span>
                </div>
                <div>
                  <span class="text-[10px] sm:text-xs text-gray-400 block">Total Legs</span>
                  <span class="text-sm sm:text-base font-extrabold text-gray-200" id="valueLegsCount">6</span>
                </div>
              </div>

              <!-- Legs List -->
              <div class="space-y-2.5 sm:space-y-3 mt-3" id="valueLegsList"></div>
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

          <!-- Timeframe Selector (Responsive Grid/Flex) -->
          <div class="grid grid-cols-2 sm:flex items-center bg-dark-surface p-1 rounded-xl border border-dark-border gap-1 w-full sm:w-auto">
            <button id="tfSlipsBtn" onclick="switchTimeframe('slips')" class="px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-brand-500 transition text-center">Detailed Slips</button>
            <button id="tfDailyBtn" onclick="switchTimeframe('daily')" class="px-3 py-1.5 rounded-lg text-xs font-bold text-gray-400 hover:text-white transition text-center">Daily</button>
            <button id="tfWeeklyBtn" onclick="switchTimeframe('weekly')" class="px-3 py-1.5 rounded-lg text-xs font-bold text-gray-400 hover:text-white transition text-center">Weekly</button>
            <button id="tfMonthlyBtn" onclick="switchTimeframe('monthly')" class="px-3 py-1.5 rounded-lg text-xs font-bold text-gray-400 hover:text-white transition text-center">Monthly</button>
          </div>
        </div>

        <!-- Ledger Container -->
        <div id="ledgerContainer" class="space-y-3 sm:space-y-4">
          <!-- Dynamically populated depending on selected timeframe -->
        </div>
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
        <span>Automated Daily Predictions • Real-Time Score Settlement • Multi-Timeframe Records</span>
      </div>
    </div>
  </footer>

  <!-- TOAST NOTIFICATION -->
  <div id="toast" class="fixed bottom-6 right-6 px-4 py-3 rounded-xl bg-dark-surface border border-dark-border text-white text-sm font-semibold shadow-2xl transition transform translate-y-20 opacity-0 flex items-center space-x-2 z-50">
    <i id="toastIcon" class="fa-solid fa-circle-check text-brand-500"></i>
    <span id="toastMsg">Action completed</span>
  </div>

  <!-- JAVASCRIPT LOGIC -->
  <script>
    let rawSlips = null;
    let rawFixtures = [];
    let rawAnalytics = null;
    let activeTab = 'predictions';
    let activeTimeframe = 'slips';

    async function loadData() {
      try {
        const [slipsRes, fixturesRes, analyticsRes] = await Promise.all([
          fetch('/api/slips'),
          fetch('/api/fixtures'),
          fetch('/api/analytics')
        ]);
        rawSlips = await slipsRes.json();
        rawFixtures = await fixturesRes.json();
        rawAnalytics = await analyticsRes.json();

        renderSlips(rawSlips);
        renderFixtures(rawFixtures);
        renderAnalytics(rawAnalytics);
        updateStats();
      } catch (err) {
        console.error("Error loading data:", err);
        showToast("Error loading daily data", "error");
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

    function switchTimeframe(tf) {
      activeTimeframe = tf;
      ['slips', 'daily', 'weekly', 'monthly'].forEach(key => {
        const btn = document.getElementById(`tf${key.charAt(0).toUpperCase() + key.slice(1)}Btn`);
        if (key === tf) {
          btn.className = "px-3 py-1 rounded-lg text-xs font-bold text-white bg-brand-500 transition";
        } else {
          btn.className = "px-3 py-1 rounded-lg text-xs font-bold text-gray-400 hover:text-white transition";
        }
      });
      renderTimeframeContent();
    }

    function renderSlips(data) {
      if (!data) return;
      
      const banker = data.banker_ticket;
      if (banker) {
        document.getElementById('bankerTotalOdds').innerText = `${banker.total_odds}x`;
        document.getElementById('bankerAvgConf').innerText = `${banker.average_confidence}%`;
        document.getElementById('bankerLegsCount').innerText = banker.legs_count;
        document.getElementById('statBankerOdds').innerText = `${banker.total_odds}x`;
        document.getElementById('statBankerLegs').innerText = `${banker.legs_count} Ultra-Safe Legs`;

        const list = document.getElementById('bankerLegsList');
        list.innerHTML = banker.legs.map(leg => createLegCard(leg, 'brand')).join('');
      }

      const value = data.value_ticket;
      if (value) {
        document.getElementById('valueTotalOdds').innerText = `${value.total_odds}x`;
        document.getElementById('valueAvgConf').innerText = `${value.average_confidence}%`;
        document.getElementById('valueLegsCount').innerText = value.legs_count;
        document.getElementById('statValueOdds').innerText = `${value.total_odds}x`;
        document.getElementById('statValueLegs').innerText = `${value.legs_count} Diversified Legs`;

        const list = document.getElementById('valueLegsList');
        list.innerHTML = value.legs.map(leg => createLegCard(leg, 'accent')).join('');
      }
    }

    function createLegCard(leg, theme) {
      const isBrand = theme === 'brand';
      const badgeBg = isBrand ? 'bg-brand-500/15 text-brand-500 border-brand-500/30' : 'bg-accent-500/15 text-accent-400 border-accent-500/30';
      const oddsColor = isBrand ? 'text-brand-500' : 'text-accent-400';

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
          scoreBadge = `<span class="px-2 py-0.5 rounded-md font-mono font-bold text-[10px] sm:text-[11px] bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center space-x-1 animate-pulse whitespace-nowrap"><i class="fa-solid fa-circle-dot text-[9px]"></i><span>${leg.home_goals} - ${leg.away_goals} (LIVE)</span></span>`;
        } else {
          scoreBadge = `<span class="px-2 py-0.5 rounded-md font-mono font-semibold text-[10px] sm:text-[11px] bg-gray-800 text-gray-300 border border-gray-700 whitespace-nowrap">${leg.home_goals} - ${leg.away_goals}</span>`;
        }
      } else {
        scoreBadge = `<span class="px-2 py-0.5 rounded-md font-mono text-[10px] sm:text-[11px] bg-dark-bg text-gray-500 border border-dark-border/60 whitespace-nowrap">Scheduled</span>`;
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
      document.getElementById('statTotalFixtures').innerText = rawFixtures.length;
    }

    async function updateLiveScores() {
      const btn = document.getElementById('btnUpdateScores');
      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-xs"></i> <span>Updating...</span>`;
      showToast("Fetching live scores and settling bets...", "info");

      try {
        const res = await fetch('/api/update-scores', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          showToast("Live scores updated & bets settled!", "success");
          loadData();
        } else {
          showToast(data.message || "Failed to update live scores", "error");
        }
      } catch (err) {
        showToast("Error updating live scores", "error");
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-arrows-rotate text-xs text-accent-500"></i> <span>Settle & Live Scores</span>`;
      }
    }

    async function rebuildSlips() {
      const btn = document.getElementById('btnRebuildSlips');
      if (!btn) return;
      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-xs"></i> <span>Analyzing...</span>`;

      try {
        const res = await fetch('/api/refresh-slips', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          rawSlips = data.slips;
          renderSlips(rawSlips);
          showToast("Onítẹ́tẹ́ slips re-analyzed successfully!", "success");
        } else {
          showToast(data.message || "Failed to re-analyze slips", "error");
        }
      } catch (err) {
        showToast("Network error re-analyzing slips", "error");
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-rotate text-xs text-brand-500"></i> <span>Re-Analyze</span>`;
      }
    }

    async function triggerScrape() {
      const btn = document.getElementById('btnTriggerScrape');
      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Scraping...</span>`;
      showToast("Live scraper triggered in background...", "info");

      try {
        const res = await fetch('/api/scrape', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          showToast("Scrape initiated! Updating in background...", "success");
          pollScraperStatus();
        } else {
          showToast(data.message || "Scraper already running", "info");
        }
      } catch (err) {
        showToast("Error triggering scraper", "error");
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-bolt"></i> <span>Scrape Today</span>`;
      }
    }

    function pollScraperStatus() {
      const interval = setInterval(async () => {
        try {
          const res = await fetch('/api/status');
          const status = await res.json();
          if (!status.is_running) {
            clearInterval(interval);
            loadData();
            showToast("Scraping completed! New predictions loaded.", "success");
          }
        } catch (err) {
          clearInterval(interval);
        }
      }, 3000);
    }

    function copySlipText() {
      if (!rawSlips || !rawSlips.banker_ticket) return;
      const banker = rawSlips.banker_ticket;
      let text = `⚽ ONÍTẸ́TẸ́ 5-ODDS BANKER TICKET (${banker.total_odds}x Odds)\\n`;
      text += `Avg Confidence: ${banker.average_confidence}% | Legs: ${banker.legs_count}\\n\\n`;
      banker.legs.forEach(l => {
        text += `• ${l.time} | ${l.home_team} vs ${l.away_team} -> [${l.selection}] @ ${l.estimated_odds}x\\n`;
      });
      text += `\\nGenerated by Onítẹ́tẹ́ AI Engine`;

      navigator.clipboard.writeText(text);
      showToast("Onítẹ́tẹ́ Banker ticket copied to clipboard!", "success");
    }

    function showToast(msg, type = "success") {
      const toast = document.getElementById('toast');
      const toastMsg = document.getElementById('toastMsg');
      const toastIcon = document.getElementById('toastIcon');

      toastMsg.innerText = msg;
      if (type === 'error') {
        toastIcon.className = "fa-solid fa-circle-exclamation text-rose-500";
      } else if (type === 'info') {
        toastIcon.className = "fa-solid fa-circle-info text-blue-500";
      } else {
        toastIcon.className = "fa-solid fa-circle-check text-brand-500";
      }

      toast.classList.remove('translate-y-20', 'opacity-0');
      toast.classList.add('translate-y-0', 'opacity-100');

      setTimeout(() => {
        toast.classList.remove('translate-y-0', 'opacity-100');
        toast.classList.add('translate-y-20', 'opacity-0');
      }, 3500);
    }

    window.addEventListener('DOMContentLoaded', loadData);
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


def _run_scraper_job():
    """Background scraper execution job."""
    global SCRAPER_STATE
    SCRAPER_STATE["is_running"] = True
    SCRAPER_STATE["status"] = "Scraping fixtures and H2H data..."
    SCRAPER_STATE["error"] = None

    try:
        scraper = StatareaScraper(output_dir=OUTPUT_DIR)
        results = scraper.run(export=True)
        SCRAPER_STATE["total_fixtures"] = len(results)
        SCRAPER_STATE["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
        SCRAPER_STATE["status"] = "Completed successfully"
    except Exception as e:
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

    thread = threading.Thread(target=_run_scraper_job, daemon=True)
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
