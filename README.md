# Composio App Intelligence Research Agent

Autonomous SaaS research pipeline and verification case study analyzing application capabilities, authorization methods, and Model Context Protocol (MCP) server availability for AI agent tool integration.

## 1. Executive Summary

This repository implements an autonomous product research operator designed to audit SaaS applications for AI-agent readiness. Instead of relying on static spreadsheets, we built a multi-stage execution pipeline. First, the agent searches developer documentation and GitHub, downloads and structures raw evidence, and generates standardized Pydantic records with confidence ratings. Second, a verification engine extracts stratified evaluation samples, collects human ground-truth feedback via a resumable CLI, and maps pipeline inaccuracies to a specific error taxonomy. 

While free-tier API rate limits (Gemini API 15 RPM and daily search quotas) originally throttled runs to 32 apps, we resolved this constraint by building a dynamic **multi-model rate-limit cascade**. The pipeline automatically cycles through `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, and `gemini-3.1-flash-lite` as quotas exhaust, safely completing all **100 target applications** with zero manual fabrication and achieving a verified **88.8% ground-truth accuracy** (validated on a 20-app sample). Results are rendered in a high-fidelity interactive dashboard that runs completely client-side.


---

## 2. Architecture & Pipeline Flow

The research and verification pipeline follows a structured, multi-tier flow from raw seeds to the final verified dashboard dataset:

```text
+-----------------------------------------------------------------------------------+
|                                  RESEARCH PIPELINE                                 |
+-----------------------------------------------------------------------------------+
|  [apps.json]                                                                      |
|       |                                                                           |
|       v                                                                           |
|  [src/batch.py] (Batch Runner) ---------------------+                             |
|       |                                             | (Parallel, Concurrency=3)   |
|       v                                             v                             |
|  [src/research.py] (Search Tool) ----> [src/research.py] (LLM Extractor)          |
|       |                                             | (Pydantic Schema Parser)     |
|       v                                             v                             |
|  [data/pass_1.json] (Raw NDJSON Output) <-----------+                             |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                              VERIFICATION & ANALYSIS                              |
+-----------------------------------------------------------------------------------+
|  [src/verify.py] (Stratified Sampler)                                             |
|       |                                                                           |
|       v                                                                           |
|  [data/verification_sample.json] (20 Diverse Apps)                                |
|       |                                                                           |
|       v                                                                           |
|  [src/verify.py] (Interactive Human CLI) <--- Inputs y/n & override values       |
|       |                                                                           |
|       v                                                                           |
|  [data/ground_truth.json] (Resumable Progress Logs)                               |
|       |                                                                           |
|       v                                                                           |
|  [src/analyze.py] (Aggregator & Quadrant Classifier)                              |
|       |                                                                           |
|       v                                                                           |
|  [data/analysis.json] (Structured Metrics & Insights)                             |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                                 WEB DASHBOARD                                     |
+-----------------------------------------------------------------------------------+
|  [site/index.html] (Interactive Case Study Dashboard)                             |
|       |                                                                           |
|       +--> Dynamic fetches to data/ files (HTTP)                                  |
|       +--> Self-contained fallback constants (CORS/file:// local execution)       |
+-----------------------------------------------------------------------------------+
```

---

## 3. Setup & Environment Configuration

### Prerequisites
- **Python Version**: `3.10` or higher recommended.
- **Git**

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/composiohq/composio-product-research-agent.git
   cd composio-product-research-agent
   ```
2. Set up virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Configure environment keys:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and configure your API keys:
   - `GEMINI_API_KEY`: Required for LLM extraction and validation.
   - `COMPOSIO_API_KEY`: Optional; used for enhanced web tool searches.
   - `SERPER_API_KEY` / `TAVILY_API_KEY`: Optional fallback web search tokens.
   - `BATCH_CONCURRENCY`: Default `5` (can reduce to `3` to stay safely within free-tier rate limits).

---

## 4. Execution & Pipeline Commands

To run the complete data pipeline, execute the following commands in order:

### Step 1: Execute Pass 1 Research Batch
Run the parallel research agent across the input seed applications list:
```bash
python -m src.batch --config data/apps.json --output data/pass_1.json
```
*Note: To run a quick test on the first 3 apps, append `--dry-run`.*

### Step 2: Generate Stratified Verification Sample
Select a diverse subset of 20 apps (covering varying categories, confidence levels, and MCP settings) to review:
```bash
python -m src.verify --sample
```

### Step 3: Run Interactive Ground-Truth Verifier
Start the CLI flow to human-audit the 20-app sample. The CLI will display fields side-by-side, request `y/n` answers, capture correction overrides, and map error reasons to a taxonomy. You can stop (`Ctrl+C`) and resume anytime:
```bash
python -m src.verify --run
```

### Step 4: Finalize & Copy Dataset
Copy the processed raw records to the final dashboard path:
```bash
cp data/pass_1.json data/final.json
```

### Step 5: Compute Analysis & Generate Dashboard Data
Compute overall metrics, 2x2 matrix placements, blocker distributions, and 5 candidate findings insights:
```bash
python -m src.analyze
```

### Step 6: Serve the HTML Dashboard Locally
Serve the static case study page over HTTP (or simply double-click `site/index.html` since the page includes a bulletproof embedded dataset fallback):
```bash
python3 -m http.server 8000 --directory site/
```
Open [http://localhost:8000](http://localhost:8000) in your web browser.

---

## 5. Next Horizon: What I'd Do With Another Day

If granted an extra development cycle, I would focus on these specific improvements:
1. **Dynamic HTML to Markdown Pruning**: Our HTML crawler fetches entire documentation pages, often including heavy navigation headers, footers, and scripts that eat up LLM context. I would build a DOM-distance tree-pruning heuristic to extract only the central `<article>` or `<main>` content blocks.
2. **Multi-Agent Consensus Verification**: To further improve extraction quality, implement a debate protocol where two independent research agent instances extract data from different search indices (e.g. Google Search vs Exa), highlight conflicting claims, and output a validated consensus.
3. **Registry Check Integration**: Instead of relying solely on LLM search parameters to find community MCP servers, query the official modelcontextprotocol.org registry and Smithery.ai API programmatically to eliminate MCP false negatives.
4. **Vector-Grounded Claims Verification**: Store the raw documentation snippets inside a temporary in-memory ChromaDB vector instance, allowing the validator to perform exact cosine similarity checks to bind evidence claims to text coordinates.


---

## 6. Live Case Study Dashboard

View the deployed case study interactive report here:
👉 **[Composio App Intelligence Live Case Study](https://ishaanpgujaran.github.io/composio-product-research-agent/site/index.html)**
