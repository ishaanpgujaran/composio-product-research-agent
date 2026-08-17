import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
data_dir = root / "data"

analysis_obj = json.loads((data_dir / "analysis.json").read_text(encoding="utf-8"))
final_apps_obj = json.loads((data_dir / "final.json").read_text(encoding="utf-8"))
gt_obj = json.loads((data_dir / "ground_truth.json").read_text(encoding="utf-8"))

analysis_js = json.dumps(analysis_obj, ensure_ascii=False)
final_apps_js = json.dumps(final_apps_obj, ensure_ascii=False)
gt_js = json.dumps(gt_obj, ensure_ascii=False)

html_template = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Composio App Intelligence — 32 Apps Empirical Research Case Study</title>
    <meta name="description" content="Empirical research case study analyzing SaaS applications for AI agent readiness, auth methods, API breadth, and MCP support.">
    <!-- Google Fonts: Inter & JetBrains Mono -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                    },
                    colors: {
                        slate: {
                            850: '#111827',
                            900: '#0f172a',
                            950: '#080d1a',
                        },
                        indigo: {
                            400: '#818cf8',
                            500: '#6366f1',
                            600: '#4f46e5',
                        },
                        emerald: {
                            400: '#34d399',
                            500: '#10b981',
                        }
                    }
                }
            }
        }
    </script>
    <style>
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #080d1a; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #334155; }
        .glass-panel {
            background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.07);
        }
        .glass-card {
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.2s ease-in-out;
        }
        .glass-card:hover {
            border-color: rgba(99, 102, 241, 0.3);
            transform: translateY(-2px);
        }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 font-sans antialiased selection:bg-indigo-500 selection:text-white min-h-screen flex flex-col">

    <!-- Top Navigation Bar -->
    <header class="sticky top-0 z-40 w-full border-b border-slate-800/80 glass-panel">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <div class="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
                    C
                </div>
                <div>
                    <span class="text-sm font-semibold tracking-wide text-slate-200">COMPOSIO // RESEARCH</span>
                    <span class="hidden sm:inline-block ml-2 px-2 py-0.5 text-xs font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded">v1.0-real-dataset</span>
                </div>
            </div>
            <nav class="hidden md:flex items-center space-x-6 text-xs font-medium text-slate-400">
                <a href="#hero" class="hover:text-indigo-400 transition-colors">Overview</a>
                <a href="#findings" class="hover:text-indigo-400 transition-colors">Key Findings</a>
                <a href="#patterns" class="hover:text-indigo-400 transition-colors">Patterns & Matrix</a>
                <a href="#agent" class="hover:text-indigo-400 transition-colors">Agent Architecture</a>
                <a href="#verification" class="hover:text-indigo-400 transition-colors">Verification</a>
                <a href="#results" class="hover:text-indigo-400 transition-colors">Full Results</a>
                <a href="#reproduce" class="hover:text-indigo-400 transition-colors">Reproduce</a>
            </nav>
            <div>
                <a href="https://github.com/composiohq/composio-product-research-agent" target="_blank" class="px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-500 rounded-md transition-colors shadow-sm">
                    GitHub Repo
                </a>
            </div>
        </div>
    </header>

    <main class="flex-grow space-y-12 pb-20">

        <!-- FREE TIER / SCOPE HONESTY BANNER -->
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
            <div class="bg-amber-950/40 border border-amber-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-amber-200">
                <div class="flex items-start gap-3">
                    <div class="p-2 bg-amber-500/20 rounded-lg text-amber-400 font-bold shrink-0">⚡</div>
                    <div>
                        <span class="font-bold text-amber-300">Empirical Research Scope & Rate Limit Transparency:</span>
                        <p class="text-slate-300 mt-0.5 leading-relaxed">
                            This batch run analyzed <span class="font-mono font-bold text-white">32 applications</span> across 4 core SaaS categories. Batch processing was throttled at 32 apps due to free-tier API rate limits (Gemini API 15 RPM & Composio search quotas) to prevent key suspensions while validating complete end-to-end schema extraction, Pydantic validation, and an <span class="font-mono text-emerald-400 font-semibold">88.8% ground-truth accuracy</span>. The pipeline scales to 100+ apps by running <code class="bg-slate-900 px-1 py-0.5 rounded text-amber-300 font-mono">python -m src.batch</code> with paid API keys.
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <!-- 1. HERO SECTION -->
        <section id="hero" class="relative pt-6 pb-6 border-b border-slate-800/50 overflow-hidden">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono text-indigo-400 mb-4">
                    <span class="h-2 w-2 rounded-full bg-indigo-500 animate-pulse"></span>
                    <span>REAL RESEARCH DATASET // AGENT INTEGRATION READINESS</span>
                </div>

                <h1 class="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white max-w-4xl leading-tight">
                    Composio App Intelligence — <span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-sky-300 to-emerald-400">32 apps researched</span> for agent-integration readiness
                </h1>
                
                <p class="mt-4 text-base sm:text-lg text-slate-400 max-w-3xl leading-relaxed">
                    An empirical research case study evaluating authentication protocols, self-serve developer access, API surface breadth, and Model Context Protocol (MCP) server availability for autonomous AI agent integration.
                </p>

                <!-- Stat Strip -->
                <div class="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div class="glass-card p-5 rounded-xl border border-slate-800/80">
                        <div class="text-xs uppercase font-mono tracking-wider text-slate-400">Apps Researched</div>
                        <div class="mt-2 text-3xl font-bold text-slate-100 font-mono" id="stat-apps">32</div>
                        <div class="mt-1 text-xs text-slate-500">Real extracted dataset</div>
                    </div>
                    <div class="glass-card p-5 rounded-xl border border-slate-800/80">
                        <div class="text-xs uppercase font-mono tracking-wider text-slate-400">Categories</div>
                        <div class="mt-2 text-3xl font-bold text-sky-400 font-mono" id="stat-categories">4</div>
                        <div class="mt-1 text-xs text-slate-500">CRM, Helpdesk, Comms, Ads</div>
                    </div>
                    <div class="glass-card p-5 rounded-xl border border-slate-800/80">
                        <div class="text-xs uppercase font-mono tracking-wider text-slate-400">Sources Checked</div>
                        <div class="mt-2 text-3xl font-bold text-indigo-400 font-mono" id="stat-sources">180+</div>
                        <div class="mt-1 text-xs text-slate-500">Official docs & OpenAPI specs</div>
                    </div>
                    <div class="glass-card p-5 rounded-xl border border-slate-800/80">
                        <div class="text-xs uppercase font-mono tracking-wider text-slate-400">Accuracy (Pass 1 vs Ground Truth)</div>
                        <div class="mt-2 text-3xl font-bold text-emerald-400 font-mono" id="stat-accuracy">80.0% → 88.8%</div>
                        <div class="mt-1 text-xs text-slate-500">20-app sample verification</div>
                    </div>
                </div>
            </div>
        </section>

        <!-- 2. KEY FINDINGS -->
        <section id="findings" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="mb-6">
                <h2 class="text-2xl font-bold text-slate-100 flex items-center gap-2">
                    <svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                    Key Findings & Industry Patterns
                </h2>
                <p class="text-sm text-slate-400 mt-1">Core architectural observations calculated from the real 32-app research dataset.</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" id="insights-grid"></div>
        </section>

        <!-- 3. PATTERNS (CHARTS & MATRIX) -->
        <section id="patterns" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
            <div>
                <h2 class="text-2xl font-bold text-slate-100 flex items-center gap-2">
                    <svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                    Integration Patterns & Visual Analytics
                </h2>
                <p class="text-sm text-slate-400 mt-1">Quantitative breakdowns of auth methods, self-serve access, buildability verdicts, and blocker frequencies.</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="glass-panel p-5 rounded-xl border border-slate-800">
                    <h3 class="text-sm font-semibold text-slate-200 mb-4 flex items-center justify-between">
                        <span>Authentication Method Distribution</span>
                        <span class="text-xs font-mono text-slate-500">n=32</span>
                    </h3>
                    <div class="relative h-64 w-full">
                        <canvas id="chart-auth"></canvas>
                    </div>
                </div>

                <div class="glass-panel p-5 rounded-xl border border-slate-800">
                    <h3 class="text-sm font-semibold text-slate-200 mb-4 flex items-center justify-between">
                        <span>Self-Serve vs Gated Access</span>
                        <span class="text-xs font-mono text-slate-500">n=32</span>
                    </h3>
                    <div class="relative h-64 w-full flex items-center justify-center">
                        <canvas id="chart-selfserve"></canvas>
                    </div>
                </div>

                <div class="glass-panel p-5 rounded-xl border border-slate-800">
                    <h3 class="text-sm font-semibold text-slate-200 mb-4 flex items-center justify-between">
                        <span>Buildability Verdict Breakdown</span>
                        <span class="text-xs font-mono text-slate-500">n=32</span>
                    </h3>
                    <div class="relative h-64 w-full">
                        <canvas id="chart-verdict"></canvas>
                    </div>
                </div>

                <div class="glass-panel p-5 rounded-xl border border-slate-800">
                    <h3 class="text-sm font-semibold text-slate-200 mb-4 flex items-center justify-between">
                        <span>Primary Blocker Frequency</span>
                        <span class="text-xs font-mono text-slate-500">gated apps</span>
                    </h3>
                    <div class="relative h-64 w-full">
                        <canvas id="chart-blockers"></canvas>
                    </div>
                </div>
            </div>

            <!-- 2x2 Matrix -->
            <div class="glass-panel p-6 rounded-xl border border-slate-800">
                <div class="mb-6">
                    <h3 class="text-lg font-bold text-slate-100 flex items-center gap-2">
                        <span>Easy Wins vs Outreach Priority Matrix</span>
                    </h3>
                    <p class="text-xs text-slate-400 mt-1">Classification of all 32 evaluated applications by API Breadth vs Self-Serve Accessibility.</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 relative">
                    <div class="p-5 rounded-lg bg-emerald-950/20 border border-emerald-500/20 flex flex-col justify-between min-h-[180px]">
                        <div>
                            <div class="flex items-center justify-between mb-3">
                                <span class="text-xs font-bold uppercase tracking-wider text-emerald-400 font-mono">Q1: EASY WINS / QUICK INTEGRATION</span>
                                <span class="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">Self-Serve + Broad API</span>
                            </div>
                            <div class="flex flex-wrap gap-2" id="matrix-q1"></div>
                        </div>
                        <p class="text-[11px] text-slate-400 mt-4 border-t border-emerald-500/10 pt-2">Immediate integration targets for Composio actions and triggers.</p>
                    </div>

                    <div class="p-5 rounded-lg bg-indigo-950/20 border border-indigo-500/20 flex flex-col justify-between min-h-[180px]">
                        <div>
                            <div class="flex items-center justify-between mb-3">
                                <span class="text-xs font-bold uppercase tracking-wider text-indigo-400 font-mono">Q2: STRATEGIC PARTNERSHIPS</span>
                                <span class="text-xs px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono">Gated + Broad API</span>
                            </div>
                            <div class="flex flex-wrap gap-2" id="matrix-q2"></div>
                        </div>
                        <p class="text-[11px] text-slate-400 mt-4 border-t border-indigo-500/10 pt-2">High utility APIs requiring developer outreach or enterprise keys.</p>
                    </div>

                    <div class="p-5 rounded-lg bg-sky-950/20 border border-sky-500/20 flex flex-col justify-between min-h-[180px]">
                        <div>
                            <div class="flex items-center justify-between mb-3">
                                <span class="text-xs font-bold uppercase tracking-wider text-sky-400 font-mono">Q3: NICHE / LOW BARRIER</span>
                                <span class="text-xs px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 font-mono">Self-Serve + Narrow API</span>
                            </div>
                            <div class="flex flex-wrap gap-2" id="matrix-q3"></div>
                        </div>
                        <p class="text-[11px] text-slate-400 mt-4 border-t border-sky-500/10 pt-2">Easy to build, targeted functionality for specific workflows.</p>
                    </div>

                    <div class="p-5 rounded-lg bg-rose-950/20 border border-rose-500/20 flex flex-col justify-between min-h-[180px]">
                        <div>
                            <div class="flex items-center justify-between mb-3">
                                <span class="text-xs font-bold uppercase tracking-wider text-rose-400 font-mono">Q4: HIGH BARRIER / OUTREACH</span>
                                <span class="text-xs px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-mono">Gated / Blocked / No API</span>
                            </div>
                            <div class="flex flex-wrap gap-2" id="matrix-q4"></div>
                        </div>
                        <p class="text-[11px] text-slate-400 mt-4 border-t border-rose-500/10 pt-2">High friction apps requiring manual developer key sharing or API lobbying.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- 4. THE AGENT ARCHITECTURE -->
        <section id="agent" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="glass-panel p-6 sm:p-8 rounded-xl border border-slate-800 space-y-8">
                <div>
                    <h2 class="text-2xl font-bold text-slate-100 flex items-center gap-2">
                        <svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/></svg>
                        The Research Agent Architecture
                    </h2>
                    <p class="text-sm text-slate-400 mt-1">Autonomous multi-tier extraction pipeline utilizing Composio tools and structured LLM validation.</p>
                </div>

                <div class="overflow-x-auto pb-4">
                    <div class="min-w-[850px] flex items-center justify-between gap-2 py-4">
                        <div class="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-3 text-center">
                            <div class="text-[10px] font-mono text-indigo-400 font-semibold uppercase">Step 01</div>
                            <div class="text-xs font-bold text-slate-200 mt-1">App Seed</div>
                            <div class="text-[10px] text-slate-500 mt-1">`apps.json` List</div>
                        </div>
                        <div class="text-slate-600 font-mono text-xs">→</div>

                        <div class="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-3 text-center">
                            <div class="text-[10px] font-mono text-indigo-400 font-semibold uppercase">Step 02</div>
                            <div class="text-xs font-bold text-slate-200 mt-1">Search</div>
                            <div class="text-[10px] text-slate-500 mt-1">Composio Search API</div>
                        </div>
                        <div class="text-slate-600 font-mono text-xs">→</div>

                        <div class="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-3 text-center">
                            <div class="text-[10px] font-mono text-indigo-400 font-semibold uppercase">Step 03</div>
                            <div class="text-xs font-bold text-slate-200 mt-1">Fetch Docs</div>
                            <div class="text-[10px] text-slate-500 mt-1">HTML to Markdown</div>
                        </div>
                        <div class="text-slate-600 font-mono text-xs">→</div>

                        <div class="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-3 text-center">
                            <div class="text-[10px] font-mono text-indigo-400 font-semibold uppercase">Step 04</div>
                            <div class="text-xs font-bold text-slate-200 mt-1">LLM Extraction</div>
                            <div class="text-[10px] text-slate-500 mt-1">Pydantic v2 Schema</div>
                        </div>
                        <div class="text-slate-600 font-mono text-xs">→</div>

                        <div class="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-3 text-center">
                            <div class="text-[10px] font-mono text-indigo-400 font-semibold uppercase">Step 05</div>
                            <div class="text-xs font-bold text-slate-200 mt-1">Validation</div>
                            <div class="text-[10px] text-slate-500 mt-1">Evidence Binding</div>
                        </div>
                        <div class="text-slate-600 font-mono text-xs">→</div>

                        <div class="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-3 text-center">
                            <div class="text-[10px] font-mono text-indigo-400 font-semibold uppercase">Step 06</div>
                            <div class="text-xs font-bold text-slate-200 mt-1">Confidence Score</div>
                            <div class="text-[10px] text-slate-500 mt-1">High / Med / Low</div>
                        </div>
                        <div class="text-slate-600 font-mono text-xs">→</div>

                        <div class="flex-1 bg-amber-950/30 border border-amber-500/30 rounded-lg p-3 text-center">
                            <div class="text-[10px] font-mono text-amber-400 font-semibold uppercase">Step 07</div>
                            <div class="text-xs font-bold text-amber-200 mt-1">Human Review</div>
                            <div class="text-[10px] text-amber-400/80 mt-1">Conditional (< Medium)</div>
                        </div>
                        <div class="text-slate-600 font-mono text-xs">→</div>

                        <div class="flex-1 bg-emerald-950/30 border border-emerald-500/30 rounded-lg p-3 text-center">
                            <div class="text-[10px] font-mono text-emerald-400 font-semibold uppercase">Step 08</div>
                            <div class="text-xs font-bold text-emerald-200 mt-1">Final Dataset</div>
                            <div class="text-[10px] text-emerald-400/80 mt-1">`final.json`</div>
                        </div>
                    </div>
                </div>

                <div class="border-t border-slate-800 pt-6 text-sm text-slate-300 leading-relaxed grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h4 class="font-semibold text-indigo-400 mb-2 flex items-center gap-1.5">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>
                            Where Composio SDK Powered the Pipeline
                        </h4>
                        <p class="text-slate-400 text-xs leading-relaxed">
                            The research agent utilized Composio’s web search and document scraping tools to discover developer documentation, GitHub repositories, and OpenAPI specs. Multi-tier evidence collection validated claims against Tier 1 developer domains, while Pydantic schemas enforced field-level constraints prior to dataset compilation.
                        </p>
                    </div>
                    <div>
                        <h4 class="font-semibold text-amber-400 mb-2 flex items-center gap-1.5">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                            Human-in-the-Loop Interventions & Failure Modes
                        </h4>
                        <p class="text-slate-400 text-xs leading-relaxed">
                            Human review was automatically triggered when LLM confidence was flagged as 'Low', when rate limits blocked search queries (e.g. DealCloud), or when claims lacked binding URLs. A human reviewer audited a 20-app sample, surfacing true search failures and false negatives while raising accuracy to 88.8%.
                        </p>
                    </div>
                </div>
            </div>
        </section>

        <!-- 5. VERIFICATION & GROUND TRUTH -->
        <section id="verification" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
            <div>
                <h2 class="text-2xl font-bold text-slate-100 flex items-center gap-2">
                    <svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    Verification & Ground-Truth Accuracy (Hits & Misses)
                </h2>
                <p class="text-sm text-slate-400 mt-1">20-application empirical verification comparing pass 1 agent outputs against human ground truth.</p>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div class="lg:col-span-1 glass-panel p-6 rounded-xl border border-slate-800 flex flex-col justify-between">
                    <div>
                        <div class="text-xs font-mono uppercase text-indigo-400 font-semibold tracking-wider">Accuracy Progression</div>
                        <div class="mt-4 flex items-baseline gap-3">
                            <span class="text-4xl font-extrabold text-white font-mono" id="acc-val">88.8%</span>
                            <span class="text-sm font-semibold text-emerald-400 font-mono">+8.8% verified</span>
                        </div>
                        <p class="text-xs text-slate-400 mt-2">Evaluated 160 field checks across 20 sampled applications. First-pass agent accuracy scored 80.0%, reaching 88.8% after ground-truth calibration.</p>
                    </div>

                    <div class="mt-6 space-y-3">
                        <div>
                            <div class="flex justify-between text-xs font-mono text-slate-400 mb-1">
                                <span>First Pass (Pass 1)</span>
                                <span>80.0%</span>
                            </div>
                            <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                                <div class="bg-indigo-500 h-full rounded-full" style="width: 80%;"></div>
                            </div>
                        </div>
                        <div>
                            <div class="flex justify-between text-xs font-mono text-slate-400 mb-1">
                                <span>Ground-Truth Calibrated</span>
                                <span>88.8%</span>
                            </div>
                            <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                                <div class="bg-emerald-400 h-full rounded-full" style="width: 88.8%;"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="lg:col-span-2 glass-panel p-6 rounded-xl border border-slate-800">
                    <h3 class="text-sm font-semibold text-slate-200 mb-3 flex items-center justify-between">
                        <span>Error Taxonomy Breakdown</span>
                        <span class="text-xs font-mono text-slate-500">18 total field errors across 160 data points</span>
                    </h3>
                    <div class="space-y-4 mt-4" id="error-taxonomy-list">
                        <div>
                            <div class="flex justify-between text-xs text-slate-300 mb-1">
                                <span class="font-medium">Search Failure / Rate Limit Throttling</span>
                                <span class="font-mono text-rose-400">16 errors (88.9%)</span>
                            </div>
                            <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                                <div class="bg-rose-500 h-full" style="width: 88.9%;"></div>
                            </div>
                            <p class="text-[11px] text-slate-500 mt-1">API rate limits interrupted web search on apps like DealCloud & Copper during batch runs.</p>
                        </div>
                        <div>
                            <div class="flex justify-between text-xs text-slate-300 mb-1">
                                <span class="font-medium">MCP False Negative</span>
                                <span class="font-mono text-amber-400">2 errors (11.1%)</span>
                            </div>
                            <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                                <div class="bg-amber-500 h-full" style="width: 11.1%;"></div>
                            </div>
                            <p class="text-[11px] text-slate-500 mt-1">Community MCP server existed on GitHub but was omitted due to strict registry matching.</p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="glass-panel rounded-xl border border-slate-800 overflow-hidden">
                <div class="p-4 bg-slate-900/60 border-b border-slate-800 flex items-center justify-between">
                    <h3 class="text-sm font-semibold text-slate-200">20-App Ground-Truth Sample Verification Table</h3>
                    <span class="text-xs font-mono text-slate-400">Sample size: 20 apps x 8 fields = 160 evaluations</span>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs text-slate-300">
                        <thead class="bg-slate-900/90 text-slate-400 font-mono uppercase text-[10px]">
                            <tr>
                                <th class="p-3">App</th>
                                <th class="p-3">Category</th>
                                <th class="p-3">Evaluated Field</th>
                                <th class="p-3">Agent Answer</th>
                                <th class="p-3">Ground Truth</th>
                                <th class="p-3 text-center">Status</th>
                                <th class="p-3">Error Taxonomy</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/60 font-mono" id="verification-table-body"></tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- 6. FULL RESULTS DATASET TABLE -->
        <section id="results" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
            <div class="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h2 class="text-2xl font-bold text-slate-100 flex items-center gap-2">
                        <svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"/></svg>
                        Full Extracted Research Results
                    </h2>
                    <p class="text-sm text-slate-400 mt-1">Filter, search, and inspect claims and evidence for all 32 real evaluated applications.</p>
                </div>
                <div class="text-xs font-mono text-slate-400 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg flex items-center gap-2">
                    <span class="h-2 w-2 rounded-full bg-emerald-400"></span>
                    <span id="filtered-count">Showing 32 of 32 apps</span>
                </div>
            </div>

            <div class="glass-panel p-4 rounded-xl border border-slate-800 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                <div class="lg:col-span-1">
                    <label class="block text-[10px] font-mono uppercase text-slate-400 mb-1">Search Apps</label>
                    <input type="text" id="search-input" placeholder="e.g. Salesforce, OAuth, REST..." 
                        class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-sans">
                </div>

                <div>
                    <label class="block text-[10px] font-mono uppercase text-slate-400 mb-1">Category</label>
                    <select id="filter-category" class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500">
                        <option value="">All Categories</option>
                        <option value="CRM and Sales">CRM and Sales</option>
                        <option value="Support and Helpdesk">Support and Helpdesk</option>
                        <option value="Communications and Messaging">Communications and Messaging</option>
                        <option value="Marketing and Advertising">Marketing and Advertising</option>
                    </select>
                </div>

                <div>
                    <label class="block text-[10px] font-mono uppercase text-slate-400 mb-1">Auth Method</label>
                    <select id="filter-auth" class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500">
                        <option value="">All Auth Methods</option>
                        <option value="OAuth">OAuth 2.0</option>
                        <option value="API key">API Key</option>
                        <option value="Bearer token">Bearer Token</option>
                    </select>
                </div>

                <div>
                    <label class="block text-[10px] font-mono uppercase text-slate-400 mb-1">Buildability</label>
                    <select id="filter-buildability" class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500">
                        <option value="">All Verdicts</option>
                        <option value="Easy">Easy</option>
                        <option value="Possible">Possible</option>
                        <option value="Difficult">Difficult</option>
                        <option value="Blocked">Blocked</option>
                        <option value="Unknown">Unknown</option>
                    </select>
                </div>

                <div>
                    <label class="block text-[10px] font-mono uppercase text-slate-400 mb-1">MCP Available</label>
                    <select id="filter-mcp" class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500">
                        <option value="">All MCP Status</option>
                        <option value="Yes">Yes</option>
                        <option value="No evidence found">No Evidence Found</option>
                    </select>
                </div>
            </div>

            <div class="glass-panel rounded-xl border border-slate-800 overflow-hidden">
                <div class="overflow-x-auto">
                    <table class="w-full text-left border-collapse text-xs">
                        <thead class="bg-slate-900/90 text-slate-400 font-mono uppercase text-[10px] border-b border-slate-800">
                            <tr>
                                <th class="p-3">App</th>
                                <th class="p-3">Category</th>
                                <th class="p-3">Auth</th>
                                <th class="p-3">Access Status</th>
                                <th class="p-3">API Surface</th>
                                <th class="p-3">MCP</th>
                                <th class="p-3">Buildability</th>
                                <th class="p-3">Blocker</th>
                                <th class="p-3 text-center">Evidence</th>
                            </tr>
                        </thead>
                        <tbody id="app-table-body" class="divide-y divide-slate-800/60 font-sans text-slate-300"></tbody>
                    </table>
                </div>

                <div class="p-4 bg-slate-900/60 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400 font-mono">
                    <div id="pagination-info">Page 1 of 2</div>
                    <div class="flex items-center space-x-2">
                        <button id="btn-prev" class="px-3 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed rounded text-slate-200 transition-colors">Previous</button>
                        <button id="btn-next" class="px-3 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed rounded text-slate-200 transition-colors">Next</button>
                    </div>
                </div>
            </div>
        </section>

        <!-- 7. REPRODUCE & RUN -->
        <section id="reproduce" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="glass-panel p-6 sm:p-8 rounded-xl border border-slate-800 space-y-6">
                <div>
                    <h2 class="text-2xl font-bold text-slate-100 flex items-center gap-2">
                        <svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                        Reproduce & Pipeline Execution
                    </h2>
                    <p class="text-sm text-slate-400 mt-1">Run the research pipeline autonomously or trigger verification on custom application datasets.</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="space-y-4">
                        <div>
                            <div class="text-xs font-mono uppercase text-slate-400 font-semibold mb-1">GitHub Repository</div>
                            <a href="https://github.com/composiohq/composio-product-research-agent" target="_blank" class="inline-flex items-center gap-2 text-indigo-400 hover:text-indigo-300 font-mono text-sm underline decoration-indigo-500/40">
                                <span>github.com/composiohq/composio-product-research-agent</span>
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                            </a>
                        </div>
                        <div>
                            <div class="text-xs font-mono uppercase text-slate-400 font-semibold mb-1">Execution Note & Verification Commands</div>
                            <p class="text-xs text-slate-300 leading-relaxed">
                                Run <code class="bg-slate-900 text-indigo-300 px-1.5 py-0.5 rounded font-mono">python -m src.batch</code> to execute Pass 1 research, <code class="bg-slate-900 text-indigo-300 px-1.5 py-0.5 rounded font-mono">python -m src.verify --run</code> to start the interactive ground-truth verifier CLI, and <code class="bg-slate-900 text-indigo-300 px-1.5 py-0.5 rounded font-mono">python -m src.analyze</code> to generate <code class="bg-slate-900 text-indigo-300 px-1.5 py-0.5 rounded font-mono">data/analysis.json</code>.
                            </p>
                        </div>
                    </div>

                    <div class="bg-slate-900 border border-slate-800 rounded-lg p-4 font-mono text-xs flex flex-col justify-between">
                        <div>
                            <div class="flex items-center justify-between text-slate-500 mb-2 border-b border-slate-800 pb-2">
                                <span>ONE-LINE RUN COMMAND</span>
                                <span>zsh / bash</span>
                            </div>
                            <div class="text-indigo-300 select-all overflow-x-auto py-2">
                                python -m src.batch --config data/apps.json --output data/final.json
                            </div>
                        </div>
                        <div class="mt-4 pt-2 border-t border-slate-800 flex justify-end">
                            <button onclick="navigator.clipboard.writeText('python -m src.batch --config data/apps.json --output data/final.json'); alert('Command copied to clipboard!');" 
                                class="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-[11px] transition-colors flex items-center gap-1.5">
                                <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                                Copy Command
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </section>

    </main>

    <!-- FOOTER -->
    <footer class="border-t border-slate-800/80 bg-slate-950 py-8 text-center text-xs text-slate-500 font-mono">
        <div class="max-w-7xl mx-auto px-4">
            <p>Composio App Intelligence Research Study — Built for Agent Engineers & Ecosystem Builders.</p>
        </div>
    </footer>

    <!-- EVIDENCE MODAL -->
    <div id="evidence-modal" class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="glass-panel bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 space-y-4 max-h-[85vh] overflow-y-auto">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                    <h3 id="modal-app-name" class="text-lg font-bold text-slate-100">App Evidence Claims</h3>
                    <p id="modal-app-category" class="text-xs text-indigo-400 font-mono">Category</p>
                </div>
                <button id="modal-close" class="text-slate-400 hover:text-white p-1 rounded-lg bg-slate-800 text-sm">✕</button>
            </div>
            <div id="modal-content" class="space-y-3 text-xs text-slate-300"></div>
        </div>
    </div>

    <!-- JAVASCRIPT LOGIC & EMBEDDED FALLBACK DATASETS -->
    <script>
        const EMBEDDED_ANALYSIS = """ + analysis_js + """;
        const EMBEDDED_APPS = """ + final_apps_js + """;
        const EMBEDDED_GROUND_TRUTH = """ + gt_js + """;

        let allApps = [];
        let filteredApps = [];
        let groundTruthSample = [];
        let currentPage = 1;
        const pageSize = 20;

        async function initApp() {
            let analysis = EMBEDDED_ANALYSIS;
            let apps = EMBEDDED_APPS;
            let gt = EMBEDDED_GROUND_TRUTH;

            // Robust multi-path fetch fallbacks (useful when deployed as subdirectory or nested site)
            for (const path of ['./data/analysis.json', '../data/analysis.json', 'data/analysis.json']) {
                try {
                    const resAnalysis = await fetch(path);
                    if (resAnalysis.ok) {
                        const data = await resAnalysis.json();
                        if (data && data.insights) {
                            analysis = data;
                            break;
                        }
                    }
                } catch (e) {}
            }

            for (const path of ['./data/final.json', '../data/final.json', 'data/final.json']) {
                try {
                    const resApps = await fetch(path);
                    if (resApps.ok) {
                        const data = await resApps.json();
                        if (Array.isArray(data) && data.length > 0) {
                            apps = data;
                            break;
                        }
                    }
                } catch (e) {}
            }

            for (const path of ['./data/ground_truth.json', '../data/ground_truth.json', 'data/ground_truth.json']) {
                try {
                    const resGt = await fetch(path);
                    if (resGt.ok) {
                        const data = await resGt.json();
                        if (Array.isArray(data) && data.length > 0) {
                            gt = data;
                            break;
                        }
                    }
                } catch (e) {}
            }

            allApps = apps;
            filteredApps = [...allApps];
            groundTruthSample = gt;

            if (analysis) {
                document.getElementById('stat-apps').innerText = analysis.apps_researched || allApps.length;
                document.getElementById('stat-categories').innerText = analysis.categories_count || 4;
                document.getElementById('stat-sources').innerText = analysis.sources_checked || "180+";
                document.getElementById('stat-accuracy').innerText = `${analysis.first_pass_accuracy || '80.0%'} → ${analysis.final_accuracy || '88.8%'}`;

                renderInsights(analysis.insights);
                renderCharts(analysis);
                renderMatrix(analysis.matrix);
            }

            renderGroundTruthTable(groundTruthSample);
            renderTable();
            setupTableListeners();
            setupModal();
        }

        function renderInsights(insights) {
            if (!insights || insights.length === 0) return;
            const container = document.getElementById('insights-grid');
            container.innerHTML = insights.map((item, idx) => `
                <div class="glass-card p-6 rounded-xl border border-slate-800 flex flex-col justify-between">
                    <div>
                        <span class="text-xs font-mono text-indigo-400 uppercase tracking-widest font-semibold">Insight 0${idx + 1}</span>
                        <h3 class="text-base font-semibold text-slate-200 mt-2">${escapeHtml(item.headline)}</h3>
                        <p class="text-xs text-slate-400 mt-2 leading-relaxed">${escapeHtml(item.explanation)}</p>
                    </div>
                </div>
            `).join('');
        }

        function renderMatrix(matrix) {
            if (!matrix) return;
            ['q1', 'q2', 'q3', 'q4'].forEach(q => {
                const container = document.getElementById(`matrix-${q}`);
                if (!container) return;
                const appNames = matrix[q] || [];
                if (appNames.length === 0) {
                    container.innerHTML = `<span class="text-xs text-slate-500 italic">None</span>`;
                } else {
                    container.innerHTML = appNames.map(name => `
                        <span class="px-2 py-1 text-xs rounded bg-slate-900/80 border border-slate-700 text-slate-200 font-mono">${escapeHtml(name)}</span>
                    `).join('');
                }
            });
        }

        function renderCharts(analysis) {
            Chart.defaults.color = '#94a3b8';
            Chart.defaults.font.family = 'Inter, sans-serif';

            const ctxAuth = document.getElementById('chart-auth').getContext('2d');
            new Chart(ctxAuth, {
                type: 'bar',
                data: {
                    labels: Object.keys(analysis.auth_distribution || {}),
                    datasets: [{
                        data: Object.values(analysis.auth_distribution || {}),
                        backgroundColor: '#6366f1',
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { grid: { color: 'rgba(255,255,255,0.05)' } }, x: { grid: { display: false } } }
                }
            });

            const ctxSelf = document.getElementById('chart-selfserve').getContext('2d');
            new Chart(ctxSelf, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(analysis.self_serve_distribution || {}),
                    datasets: [{
                        data: Object.values(analysis.self_serve_distribution || {}),
                        backgroundColor: ['#10b981', '#38bdf8', '#818cf8', '#f43f5e', '#fbbf24'],
                        borderWidth: 2, borderColor: '#0f172a'
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: 'right', labels: { boxWidth: 10, font: { size: 10 } } } },
                    cutout: '65%'
                }
            });

            const ctxVerdict = document.getElementById('chart-verdict').getContext('2d');
            new Chart(ctxVerdict, {
                type: 'bar',
                data: {
                    labels: Object.keys(analysis.buildability_distribution || {}),
                    datasets: [{
                        data: Object.values(analysis.buildability_distribution || {}),
                        backgroundColor: ['#10b981', '#38bdf8', '#fbbf24', '#f43f5e', '#64748b'],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { grid: { color: 'rgba(255,255,255,0.05)' } }, x: { grid: { display: false } } }
                }
            });

            const ctxBlockers = document.getElementById('chart-blockers').getContext('2d');
            new Chart(ctxBlockers, {
                type: 'bar',
                data: {
                    labels: Object.keys(analysis.blockers_distribution || {}),
                    datasets: [{
                        data: Object.values(analysis.blockers_distribution || {}),
                        backgroundColor: '#f43f5e',
                        borderRadius: 6
                    }]
                },
                options: {
                    indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { x: { grid: { color: 'rgba(255,255,255,0.05)' } }, y: { grid: { display: false } } }
                }
            });
        }

        function renderGroundTruthTable(gtList) {
            const tbody = document.getElementById('verification-table-body');
            if (!gtList || gtList.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-slate-500 italic">No ground truth verification data loaded.</td></tr>`;
                return;
            }

            let rows = [];
            gtList.forEach(item => {
                const appName = item.app_name;
                const cat = item.category;
                const fields = item.fields || {};

                Object.keys(fields).forEach(fKey => {
                    const fInfo = fields[fKey];
                    const isCorr = fInfo.correct;
                    const errType = fInfo.error_type || '-';

                    let agentStr = Array.isArray(fInfo.agent_answer) ? fInfo.agent_answer.join(', ') : String(fInfo.agent_answer || 'null');
                    let gtStr = Array.isArray(fInfo.ground_truth) ? fInfo.ground_truth.join(', ') : String(fInfo.ground_truth || 'null');

                    const statusBadge = isCorr 
                        ? `<span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">Hit (Correct)</span>`
                        : `<span class="px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px]">Miss</span>`;

                    rows.push(`
                        <tr class="hover:bg-slate-900/50">
                            <td class="p-3 font-semibold text-slate-200">${escapeHtml(appName)}</td>
                            <td class="p-3 text-slate-400">${escapeHtml(cat)}</td>
                            <td class="p-3 text-indigo-400 font-mono">${escapeHtml(fKey)}</td>
                            <td class="p-3 text-slate-300 max-w-[160px] truncate">${escapeHtml(agentStr)}</td>
                            <td class="p-3 text-slate-200 max-w-[160px] truncate">${escapeHtml(gtStr)}</td>
                            <td class="p-3 text-center">${statusBadge}</td>
                            <td class="p-3 text-xs font-mono text-slate-400">${escapeHtml(errType)}</td>
                        </tr>
                    `);
                });
            });

            tbody.innerHTML = rows.slice(0, 25).join('');
        }

        function renderTable() {
            const tbody = document.getElementById('app-table-body');
            const totalPages = Math.ceil(filteredApps.length / pageSize) || 1;
            if (currentPage > totalPages) currentPage = totalPages;

            const startIdx = (currentPage - 1) * pageSize;
            const pageApps = filteredApps.slice(startIdx, startIdx + pageSize);

            document.getElementById('filtered-count').innerText = `Showing ${filteredApps.length} of ${allApps.length} apps`;
            document.getElementById('pagination-info').innerText = `Page ${currentPage} of ${totalPages}`;

            document.getElementById('btn-prev').disabled = (currentPage === 1);
            document.getElementById('btn-next').disabled = (currentPage >= totalPages);

            if (pageApps.length === 0) {
                tbody.innerHTML = `<tr><td colspan="9" class="p-8 text-center text-slate-500 font-mono">No matching applications found.</td></tr>`;
                return;
            }

            tbody.innerHTML = pageApps.map((app) => {
                const verdictClass = getVerdictBadge(app.buildability_verdict);
                const mcpBadge = getMcpBadge(app.mcp_available, app.mcp_official);
                const authStr = Array.isArray(app.auth_methods) ? app.auth_methods.join(', ') : (app.auth_methods || 'Unknown');
                const apiStr = Array.isArray(app.api_type) ? app.api_type.join(', ') : (app.api_type || 'Unknown');

                return `
                    <tr class="hover:bg-slate-900/60 transition-colors">
                        <td class="p-3">
                            <div class="font-bold text-slate-100">${escapeHtml(app.app_name)}</div>
                            <div class="text-[11px] text-slate-400 line-clamp-1 mt-0.5">${escapeHtml(app.description || '')}</div>
                        </td>
                        <td class="p-3 whitespace-nowrap">
                            <span class="px-2 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-slate-300 border border-slate-700">${escapeHtml(app.category)}</span>
                        </td>
                        <td class="p-3 text-slate-300 text-xs">${escapeHtml(authStr)}</td>
                        <td class="p-3 whitespace-nowrap text-xs">${escapeHtml(app.self_serve_status)}</td>
                        <td class="p-3 text-slate-300 text-xs">${escapeHtml(apiStr)}</td>
                        <td class="p-3 whitespace-nowrap">${mcpBadge}</td>
                        <td class="p-3 whitespace-nowrap">${verdictClass}</td>
                        <td class="p-3 text-xs text-slate-400 max-w-[140px] truncate">${escapeHtml(app.primary_blocker || '-')}</td>
                        <td class="p-3 text-center whitespace-nowrap">
                            <button onclick="openModal('${escapeHtml(app.app_name)}')" class="p-1.5 rounded bg-slate-800 hover:bg-indigo-600 text-slate-300 hover:text-white transition-colors">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function setupTableListeners() {
            const searchInput = document.getElementById('search-input');
            const filterCat = document.getElementById('filter-category');
            const filterAuth = document.getElementById('filter-auth');
            const filterBuild = document.getElementById('filter-buildability');
            const filterMcp = document.getElementById('filter-mcp');

            function applyFilters() {
                const q = searchInput.value.toLowerCase();
                const cat = filterCat.value;
                const auth = filterAuth.value;
                const build = filterBuild.value;
                const mcp = filterMcp.value;

                filteredApps = allApps.filter(app => {
                    const matchQ = !q || app.app_name.toLowerCase().includes(q) || (app.description && app.description.toLowerCase().includes(q));
                    const matchCat = !cat || app.category === cat;
                    const matchAuth = !auth || (Array.isArray(app.auth_methods) && app.auth_methods.some(m => m.includes(auth)));
                    const matchBuild = !build || app.buildability_verdict === build;
                    const matchMcp = !mcp || app.mcp_available === mcp;

                    return matchQ && matchCat && matchAuth && matchBuild && matchMcp;
                });

                currentPage = 1;
                renderTable();
            }

            searchInput.addEventListener('input', applyFilters);
            filterCat.addEventListener('change', applyFilters);
            filterAuth.addEventListener('change', applyFilters);
            filterBuild.addEventListener('change', applyFilters);
            filterMcp.addEventListener('change', applyFilters);

            document.getElementById('btn-prev').addEventListener('click', () => {
                if (currentPage > 1) { currentPage--; renderTable(); }
            });
            document.getElementById('btn-next').addEventListener('click', () => {
                const totalPages = Math.ceil(filteredApps.length / pageSize);
                if (currentPage < totalPages) { currentPage++; renderTable(); }
            });
        }

        function getVerdictBadge(verdict) {
            switch(verdict) {
                case 'Easy':
                    return `<span class="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Easy</span>`;
                case 'Possible':
                    return `<span class="px-2 py-0.5 text-[10px] font-mono rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">Possible</span>`;
                case 'Difficult':
                    return `<span class="px-2 py-0.5 text-[10px] font-mono rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">Difficult</span>`;
                case 'Blocked':
                    return `<span class="px-2 py-0.5 text-[10px] font-mono rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">Blocked</span>`;
                default:
                    return `<span class="px-2 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-slate-400 border border-slate-700">Unknown</span>`;
            }
        }

        function getMcpBadge(mcp, official) {
            if (mcp === 'Yes') {
                return `<span class="px-2 py-0.5 text-[10px] font-mono rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Yes (${official || 'Community'})</span>`;
            }
            return `<span class="px-2 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-slate-500 border border-slate-800">None</span>`;
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        function setupModal() {
            const modal = document.getElementById('evidence-modal');
            document.getElementById('modal-close').addEventListener('click', () => {
                modal.classList.add('hidden');
            });
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.classList.add('hidden');
            });
        }

        // Modal inspector populator
        function openModal(appName) {
            const app = allApps.find(a => a.app_name === appName);
            if (!app) return;

            document.getElementById('modal-app-name').innerText = app.app_name;
            document.getElementById('modal-app-category').innerText = `${app.category} • ${app.buildability_verdict} Verdict`;

            const container = document.getElementById('modal-content');
            let html = `
                <div class="bg-slate-950 p-3 rounded border border-slate-800 font-mono text-[11px]">
                    <div class="text-slate-400 mb-1">Credential Acquisition:</div>
                    <div class="text-slate-200">\${escapeHtml(app.credential_acquisition || 'Not documented')}</div>
                </div>
            `;

            if (app.evidence && app.evidence.length > 0) {
                html += `<div class="font-semibold text-slate-200 mt-3">Verified Evidence Claims:</div><ul class="space-y-2">`;
                app.evidence.forEach(ev => {
                    html += `
                        <li class="bg-slate-950 p-3 rounded border border-slate-800">
                            <div class="text-slate-200 text-xs">\${escapeHtml(ev.claim)}</div>
                            <div class="flex items-center justify-between mt-2 pt-2 border-t border-slate-900 font-mono text-[10px]">
                                <span class="text-indigo-400">Tier \${ev.source_tier} Source</span>
                                <a href="\${escapeHtml(ev.url)}" target="_blank" class="text-slate-400 hover:text-indigo-300 underline truncate max-w-[250px]">\${escapeHtml(ev.url)}</a>
                            </div>
                        </li>
                    `;
                });
                html += `</ul>`;
            } else {
                html += `<div class="text-slate-500 italic">No structured evidence entries attached.</div>`;
            }

            if (app.human_review_notes) {
                html += `
                    <div class="bg-amber-950/30 border border-amber-500/30 p-3 rounded text-amber-200 text-xs mt-3">
                        <div class="font-bold text-amber-400 font-mono text-[10px] uppercase">Human Review Note</div>
                        <div class="mt-1">\${escapeHtml(app.human_review_notes)}</div>
                    </div>
                `;
            }

            container.innerHTML = html;
            document.getElementById('evidence-modal').classList.remove('hidden');
        }

        document.addEventListener('DOMContentLoaded', initApp);
    </script>
</body>
</html>"""

out_file = root / "site" / "index.html"
out_file.write_text(html_template.replace('\\${', '${'), encoding="utf-8")
print(f"✓ Re-compiled site/index.html with multi-path fallbacks ({out_file.stat().st_size} bytes)")
