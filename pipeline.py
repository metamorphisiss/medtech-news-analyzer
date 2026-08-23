# pipeline.py
# Direct LLM pipeline — replaces CrewAI agents/tasks.
# Uses Groq as primary provider (fast, generous free tier) with
# OpenRouter as automatic fallback if Groq rate-limits.
#
# Total API calls per pipeline run: ~10 (2 scouts + 8 stories combined)
# vs CrewAI's ~18+ calls per run.

import os
import json
import time
from openai import OpenAI


# ---------------------------------------------------------------------------
# Provider Config
# ---------------------------------------------------------------------------

GROQ_MODELS = {
    "fast":    "openai/gpt-oss-20b",      # Scout: fast, large context
    "quality": "openai/gpt-oss-120b",     # Analyst+Coach: strong reasoning
}

OPENROUTER_MODELS = {
    "fast":    "nvidia/nemotron-3-super-120b-a12b:free",
    "quality": "nvidia/nemotron-3-super-120b-a12b:free",
}


# ---------------------------------------------------------------------------
# Core LLM caller with auto-fallback
# ---------------------------------------------------------------------------

def _call_llm(prompt: str, tier: str = "quality", log_fn=None) -> str:
    """
    Call LLM with provider fallback chain: Groq → OpenRouter.
    - Retries with exponential backoff on 429s within each provider.
    - Falls through to the next provider if all retries are exhausted.
    Raises RuntimeError if all providers fail.
    """
    groq_key = os.environ.get("GROQ_API_KEY", "")
    or_key   = os.environ.get("OPENROUTER_API_KEY", "")

    providers = []

    if groq_key:
        providers.append({
            "name":   "Groq",
            "client": OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1"),
            "model":  GROQ_MODELS[tier],
        })

    if or_key:
        providers.append({
            "name":   "OpenRouter",
            "client": OpenAI(api_key=or_key, base_url="https://openrouter.ai/api/v1"),
            "model":  OPENROUTER_MODELS[tier],
        })

    if not providers:
        raise RuntimeError("No API keys set. Add GROQ_API_KEY or OPENROUTER_API_KEY to secrets.")

    last_error = None
    for provider in providers:
        for attempt in range(3):
            try:
                if log_fn and attempt > 0:
                    log_fn(f"LLM — retrying on {provider['name']} (attempt {attempt + 1})")
                resp = provider["client"].chat.completions.create(
                    model=provider["model"],
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=3000,
                    timeout=30,
                )
                return resp.choices[0].message.content
            except Exception as e:
                last_error = e
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower():
                    if attempt < 2:
                        wait = 2 ** attempt  # 1s, 2s, 4s
                        if log_fn:
                            log_fn(f"LLM — {provider['name']} rate-limited, waiting {wait}s...")
                        time.sleep(wait)
                        continue
                    if log_fn:
                        log_fn(f"LLM — {provider['name']} exhausted, trying next provider...")
                    break  # try next provider
                else:
                    # Non-rate-limit error — don't retry on same provider
                    if log_fn:
                        log_fn(f"LLM — {provider['name']} error: {str(e)[:60]}")
                    break

    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _extract_json(raw: str):
    """Robustly extract the first valid JSON array or object from LLM output."""
    raw = raw.strip()

    # Try extracting array first, then object
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start = raw.find(start_char)
        end   = raw.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass

    # Strip markdown fences and try again
    cleaned = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(cleaned)


# ---------------------------------------------------------------------------
# Scout — Regional news filter (pure Python, zero API calls)
# ---------------------------------------------------------------------------

# Importance-weighted keyword sets for scoring headlines
INDIA_HIGH = {
    # Regulators & schemes
    "cdsco", "ayushman", "abdm", "dpco", "pli", "nppa", "nhm", "pmjay",
    "cghs", "esi", "irdai health", "national health mission",
    "central drugs standard", "drugs controller",
    # Hospital chains
    "apollo", "fortis", "max healthcare", "narayana", "manipal", "medanta",
    "aster", "rainbow", "yatharth", "global hospitals", "hcg",
    # Pharma companies
    "sun pharma", "cipla", "dr reddy", "lupin", "biocon", "serum institute",
    "cadila", "zydus", "aurobindo", "glenmark", "ipca", "alkem",
    "torrent pharma", "mankind pharma", "abbott india", "pfizer india",
    # Medtech / devices
    "skanray", "trivitron", "agappe", "siemens healthineers india",
    # Geography + policy signals
    "india pharma", "india health", "india medtech", "india hospital",
    "india drug", "india medical", "india biotech", "india vaccine",
    "india clinical trial", "india fdi", "india export", "india import",
    "make in india health", "startup health india", "healthtech india",
}
INDIA_MED = {
    "india", "indian", "delhi", "mumbai", "bangalore", "hyderabad",
    "chennai", "kolkata", "pune", "ahmedabad",
    "rupee", "crore", "lakh", "niti aayog", "ministry of health",
    "health ministry", "nhp", "msme health", "irdai",
    "generic drug", "biosimilar", "jan aushadhi",
}
GLOBAL_HIGH = {
    # Regulators
    "fda", "ema", "who", "cdc", "nice", "mhra", "anvisa", "pmda",
    "510k", "pma", "breakthrough therapy", "fast track", "orphan drug",
    "accelerated approval", "priority review",
    # Trial milestones
    "phase 3", "phase iii", "phase 2", "phase ii", "phase 1",
    "clinical trial", "randomized controlled", "pivotal trial",
    "primary endpoint", "overall survival", "progression-free",
    # Deal signals
    "merger", "acquisition", "ipo", "spinoff", "divestiture",
    "partnership", "licensing deal", "collaboration",
    # Companies
    "pfizer", "johnson & johnson", "j&j", "roche", "novartis", "abbvie",
    "merck", "astrazeneca", "moderna", "biontech", "bristol myers",
    "eli lilly", "sanofi", "bayer", "gsk", "amgen", "gilead",
    "regeneron", "biogen", "vertex", "illumina", "danaher",
    "medtronic", "boston scientific", "stryker", "edwards lifesciences",
    "becton dickinson", "abbott", "zimmer biomet",
    # Dollar amounts are important
    "billion", "million",
}
GLOBAL_MED = {
    "drug", "therapy", "treatment", "vaccine", "biotech", "pharma",
    "hospital", "health", "medical", "device", "diagnostics",
    "insurance", "policy", "regulation", "patient", "clinical",
    "cancer", "oncology", "diabetes", "cardiology", "neurology",
    "rare disease", "gene therapy", "cell therapy", "immunotherapy",
    "ai health", "digital health", "wearable", "telehealth",
    "supply chain", "shortage", "recall", "warning letter",
}

DISCARD = {
    "cricket", "football", "ipl", "bollywood", "fashion", "stock tip",
    "recipe", "weather", "horoscope", "celebrity", "film", "movie",
    "entertainment", "lifestyle", "travel", "real estate", "astrology",
}


def _score_entry(title: str, keyword_high: set, keyword_med: set) -> int:
    t = title.lower()
    if any(k in t for k in DISCARD):
        return -1
    score = 0
    score += sum(3 for k in keyword_high if k in t)
    score += sum(1 for k in keyword_med if k in t)
    return score


def run_scout(entries: list[dict], region: str, log_fn=None) -> list[dict]:
    """
    Filter and rank entries for a region using keyword scoring — no LLM call.
    Returns exactly 4 stories (or fewer if not enough entries).
    """
    if not entries:
        return []

    high = INDIA_HIGH if region == "India" else GLOBAL_HIGH
    med  = INDIA_MED  if region == "India" else GLOBAL_MED

    scored = []
    seen_titles = set()
    for e in entries:
        title = e.get("title", "").strip()
        if not title or len(title) < 10:
            continue
        # Deduplicate by first 6 words
        key = " ".join(title.lower().split()[:6])
        if key in seen_titles:
            continue
        seen_titles.add(key)
        s = _score_entry(title, high, med)
        if s >= 0:
            scored.append((s, e))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [e for _, e in scored[:4]]

    if log_fn:
        log_fn(f"SCOUT::{region.upper()} — scored {len(scored)} entries, selected {len(top)}")
    return top



# ---------------------------------------------------------------------------
# Analyst + Coach — Combined single call per story
# ---------------------------------------------------------------------------

def run_analyst_and_coach(story: dict, full_text: str, log_fn=None) -> tuple[dict, dict]:
    """
    Run analyst and coach analysis in a SINGLE LLM call.
    Returns (analyst_dict, coach_dict).
    """
    title  = story.get("title", "")
    source = story.get("source", "")
    link   = story.get("link", "")
    text   = full_text[:4000] if full_text and not full_text.startswith("[FETCH") and not full_text.startswith("[ERROR") \
             else "(Full article text unavailable — analyse from the headline and source publication only)"

    prompt = f"""You are a senior healthcare industry analyst and MBA interview coach creating daily intelligence briefings for Indian MBA students preparing for GD/PI at top business schools (IIM, XLRI, IIFT, etc.).

STORY: {title}
SOURCE: {source}
URL: {link}

ARTICLE TEXT:
{text}

Produce a rich, detailed JSON object with exactly two top-level keys: "analyst" and "coach".
Write in confident, precise prose. Do NOT be sparse — every field should be substantive.

"analyst" must contain ALL of these fields:
  "what_happened": 3-4 sentence factual account. Cover WHO did WHAT, WHERE, WHEN, and the key numbers/scale involved.
  "why_it_matters": 2-3 sentences. Explain the strategic or systemic significance — why this matters to investors, payers, patients, or the industry at large.
  "stakeholders": A comma-separated string listing all key stakeholders — companies, regulators, patient groups, governments, payers, competitors.
  "business_implications": 3-4 sentences covering market impact, competitive dynamics, revenue or cost implications, and investment signals.
  "regulatory_implications": 2-3 sentences on how this affects the regulatory landscape — new precedents set, compliance burdens, policy signals.
  "health_system_implications": 2-3 sentences on what this means for access, affordability, care delivery, or public health outcomes.
  "counterargument": 2-3 sentences presenting a credible opposing perspective, risk, or reason why this development may not play out as expected.
  "key_facts": array of 4-6 specific, concrete facts with numbers or names (e.g. "Deal valued at $4.3B", "FDA granted priority review").
  "key_numbers": array of specific figures mentioned (percentages, dollar amounts, patient counts, timelines).
  "companies_mentioned": array of all company and organization names referenced.
  "policies_mentioned": array of specific policies, regulations, schemes, or Acts referenced.
  "key_concepts": array of 3-5 MBA/healthcare concepts this story illustrates (e.g. "Porter's Five Forces", "Value-Based Care", "Regulatory Arbitrage").
  "one_opinion": A nuanced, original perspective or contrarian take that a well-read analyst might offer (2-3 sentences).

"coach" must contain ALL of these fields:
  "gd_question": A realistic, provocative Group Discussion topic this story could generate (e.g. "Should India prioritize domestic pharma manufacturing over affordability?").
  "pi_question": A sharp Personal Interview question a panelist could ask based on this story (e.g. "If you were the CDSCO chief, how would you balance innovation with patient safety?").
  "thirty_second_answer": A strong, structured 3-4 sentence model answer to the PI question. Use the PREP framework (Point, Reason, Example, Point). This should sound like a confident, well-informed MBA candidate.
  "policy_radar_entry": 1-2 sentences on the specific regulatory or policy angle — what rule, scheme, or policy is implicated and what direction it signals.
  "company_to_watch": object with keys "name" (company name), "why" (1-2 sentences on why this company deserves attention), "signal" (1 sentence on the specific indicator — revenue, pipeline, M&A, regulatory win).
  "concept_explained": object with keys "term" (the concept), "plain_english" (2-3 sentence plain-language explanation), "why_it_matters" (1-2 sentences on why an MBA candidate must know this).

Return ONLY the JSON object. No markdown fences, no explanation, no preamble."""

    try:
        raw = _call_llm(prompt, tier="quality", log_fn=log_fn)
        result = _extract_json(raw)
        if isinstance(result, dict):
            return result.get("analyst", {}), result.get("coach", {})
    except Exception as e:
        if log_fn:
            log_fn(f"ANALYST/COACH — ERROR on '{title[:40]}': {str(e)}")

    return {"what_happened": "Analysis unavailable."}, {}
