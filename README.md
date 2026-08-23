# Healthcare Intelligence Co-Pilot (GDPI)

## Overview
An automated pipeline that generates executive-level healthcare intelligence briefings and MBA interview prep. Built with a responsive brutalist UI, it processes live RSS feeds and synthesizes complex medical and operational data into an intuitive dashboard.

## Features
* Pure Python Scout Agent: Zero-API keyword-scoring engine to filter and rank regional news efficiently.
* Single-Pass Analysis Pipeline: Analyst and Coach outputs are generated in a single LLM call to optimize speed and minimize API requests.
* Resilient LLM Fallback Mechanism: Primary inference via Groq for high-speed processing, with automatic exponential backoff and fallback routing to OpenRouter (Nvidia Nemotron) on rate limits.
* Brutalist Dashboard: Custom-styled Streamlit interface featuring a 60/40 split layout, dynamic typography, and live terminal progress visualization.
* GD/PI Prep Engine: Automatically generates realistic group discussion topics, personal interview probes, and structured 30-second model answers for every story.
* Interactive Visualizations: Policy radar, company watchlists, and conceptual data containers for quick data comprehension.

## Technology Stack
* Frontend: Streamlit (with custom Brutalist CSS)
* LLM Pipeline Providers: Groq (Primary), OpenRouter (Fallback)
* Models: `openai/gpt-oss-120b` (Primary), `nvidia/nemotron-3-super-120b-a12b` (Fallback)
* Backend / Database: Python, Supabase (PostgreSQL)
"# medtech-news-analyzer" 
