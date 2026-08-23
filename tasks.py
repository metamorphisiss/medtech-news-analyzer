# tasks.py
# Task prompt definitions for Scout, Analyst, and Coach agents.
# Implements the full schemas from Section 5 of the build spec, extended with the dashboard data fields
import json
from crewai import Task


def make_scout_task(agent, feed_entries: list[dict], region: str) -> Task:
    """
    Regional Scout task: filter, dedupe, and rank pre-pulled RSS entries.

    feed_entries is a list of dicts, each with keys:
        title, link, source, published

    These are pulled from feedparser in app.py (Python, no LLM call).
    The Scout's job is pure reasoning: relevance filtering, deduplication,
    ranking, and selection of the top 4 stories for the region.
    """
    # Cap at 120 entries to stay within token budget.
    entries_to_show = feed_entries[:120]
    lines = []
    for i, e in enumerate(entries_to_show, start=1):
        lines.append(
            f"[{i}] Title: {e.get('title', '').strip()}\n"
            f"    Source: {e.get('source', '')}\n"
            f"    Link: {e.get('link', '')}\n"
            f"    Date: {e.get('published', '')}"
        )
    entries_block = "\n\n".join(lines)

    return Task(
        description=f"""
You are given {len(entries_to_show)} RSS feed entries pre-fetched from validated healthcare news sources.

ENTRIES:
{entries_block}

Your job — work through this list carefully:

1. FILTER & GEOGRAPHIC BALANCE (CRITICAL):
   - You MUST select EXACTLY 4 stories that directly relate to {region} healthcare, policy, or business.
   - Discard: sports, entertainment, pure finance, lifestyle, unrelated tech, generic science.

2. DEDUPLICATE: Identify entries that cover the exact same underlying news event
   from different outlets. Collapse them into one. Use the most informative title.
   In the "link" field, put the primary source link.

3. RANK: Order surviving stories by significance. Prioritise:
   - Major regulatory decisions or policy shifts
   - Large funding rounds, acquisitions, or market exits
   - Down-rank: routine quarterly results, minor product updates, human-interest pieces

4. FINAL OUTPUT FORMAT (STRICT):
Output format — return a valid JSON array only. Each element must have exactly these keys:
- "title" (string)
- "link" (string)
- "source" (string)
- "published_date" (string)

Return EXACTLY 4 stories. Do not include markdown blocks, just the pure JSON string.
""",
        agent=agent,
        expected_output=(
            "A pure JSON array of exactly 4 story objects, each with keys: "
            "title, link, source, published_date."
        ),
    )


def make_analyst_task(agent, story: dict, full_text: str) -> Task:
    """
    Analyst task: full MBA-lens analysis of a single story.
    Output is forced JSON — never free text.

    Extended schema includes:
      key_facts, key_numbers, companies_mentioned,
      policies_mentioned, key_concepts, one_opinion
    These fields feed the Daily Snapshot aggregation in the dashboard.
    """
    return Task(
        description=f"""
You are analyzing a healthcare/pharma/medtech/policy news story through an MBA lens.

STORY TITLE: {story.get("title", "")}
SOURCE: {story.get("source", "")}
URL: {story.get("link", "")}

ARTICLE TEXT:
{full_text}

Produce a structured JSON analysis. Follow these rules without exception:
- Only include a field if it genuinely applies to THIS specific story.
- Do not hallucinate. If no regulatory angle exists, omit "regulatory_implications" entirely.
- Be precise and non-generic. Avoid observations that could apply to any healthcare story.
- Write for an MBA candidate who will cite this in a Group Discussion.
- Every list must contain actual names, figures, or entities — never placeholder text.

FIELD DEFINITIONS (include only those that apply):

"what_happened"
  2-3 factual sentences. Who did what, when, and what changed. No opinions.

"why_it_matters"
  The business significance and the health-system significance. Keep these distinct.
  2-4 sentences total.

"stakeholders"
  JSON array of strings. Name the specific groups, companies, or institutions
  genuinely affected — not generic categories like "patients" or "the public."
  Example: ["Apollo Hospitals", "IRDAI", "rural PHC networks", "Sun Pharma generics division"]

"business_implications"
  Revenue streams, margin dynamics, pricing power, competitive positioning, or
  market structure effects. Be specific — which segments, which players, what direction.

"regulatory_implications"
  Which specific regulator, which regulation or pathway is invoked, and what the
  practical effect is for companies in scope. Omit if not applicable.

"health_system_implications"
  Effects on access, affordability, care quality, or system capacity. Quantify where
  the article provides data.

"counterargument"
  The strongest reasonable opposing view or key caveat. 1-3 sentences. Must be
  a position a thoughtful person could actually hold, not a strawman.

"key_facts"
  JSON array of 2-4 strings. Short, standalone factual statements that would work
  as bullet points in a briefing document. Each under 25 words.

"key_numbers"
  JSON array of objects. Include only figures explicitly stated in the article.
  Each object: {{"figure": "string", "context": "string"}}
  Example: {{"figure": "$2.3B", "context": "valuation of the acquisition"}}

"companies_mentioned"
  JSON array of company/organisation names that appear in the article with
  meaningful context (not just passing mentions).

"policies_mentioned"
  JSON array of named policies, acts, schemes, or regulations referenced
  in the article. Full names preferred.

"key_concepts"
  JSON array of 1-3 domain concepts central to understanding this story.
  Aim for terms an interviewer might ask you to explain.

"one_opinion"
  A single debatable but defensible position on this story — something a
  well-informed person could argue in a GD. 1-2 sentences.

Return ONLY a valid JSON object with the applicable fields from the list above.
No explanation, no preamble, no markdown fences.
""",
        agent=agent,
        expected_output=(
            "A JSON object with applicable MBA-lens fields: what_happened, why_it_matters, "
            "stakeholders, business_implications, regulatory_implications, "
            "health_system_implications, counterargument, key_facts, key_numbers, "
            "companies_mentioned, policies_mentioned, key_concepts, one_opinion."
        ),
    )


def make_coach_task(agent, analyst_json: dict, story: dict) -> Task:
    """
    Coach task: generate GDPI prep content + dashboard feature fields.

    Outputs (in JSON):
      gd_question, pi_question, thirty_second_answer
      policy_radar_entry, company_to_watch, concept_explained

    Dashboard section assembly (Top Stories, Snapshot, etc.) is a Python
    templating pass in app.py — not part of this LLM call.
    """
    analyst_str = json.dumps(analyst_json, indent=2)

    return Task(
        description=f"""
You are a GDPI preparation coach for MBA aspirants targeting healthcare,
pharma, and hospital management programs (IIMs, XLRI, IIFT, MICA, Symbiosis SPH).

STORY: {story.get("title", "")}

ANALYST BRIEFING:
{analyst_str}

Generate the following six outputs. Base every response strictly on the
analyst briefing — do not introduce facts that aren't in it.

---

1. "gd_question"
   A genuinely debatable group discussion prompt. Both sides must have
   legitimate arguments that a reasonable person could make.
   Do NOT write a leading question implying one correct answer.
   Format: a single question sentence ending with a question mark.

2. "pi_question"
   A personal interview question that tests depth of understanding —
   specifically the candidate's ability to connect this story to healthcare
   system design, business models, or policy trade-offs.
   Not a recall question ("What happened?"). A thinking question ("Given X,
   how would you...?" or "What does this imply for...?").

3. "thirty_second_answer"
   A spoken-format model answer to the gd_question.
   Exact structure:
     - Opening line: state your position clearly in one sentence.
     - Point 1: first supporting argument, 1-2 sentences.
     - Point 2: second supporting argument, 1-2 sentences.
     - Nuance: acknowledge the strongest counterpoint in one sentence.
     - Close: restate your position or offer a synthesis in one sentence.
   Must sound like a confident person speaking aloud, not a written essay.
   No jargon for its own sake. Target: 120-160 words.

4. "policy_radar_entry"
   If this story has a regulatory or policy angle, write 1-2 sentences
   suitable for a "Policy Radar" dashboard section — what changed, which
   body is involved, and the practical effect.
   If the story has no policy/regulatory angle, return an empty string "".

5. "company_to_watch"
   An object with two keys:
     "name": the single most strategically interesting company from this story.
     "why": one sentence explaining why this company is worth watching today
            specifically — not a generic company description.
   If no specific company stands out, return null.

6. "concept_explained"
   An object with two keys:
     "concept": the single most important domain concept a candidate must
                understand to discuss this story in an interview.
     "plain_english": a 2-3 sentence plain-English explanation of that concept.
                      No assumed background. Write as if explaining to a
                      smart person who hasn't studied healthcare.

---

Return ONLY a valid JSON object with exactly these six keys:
  "gd_question", "pi_question", "thirty_second_answer",
  "policy_radar_entry", "company_to_watch", "concept_explained"

No explanation, no preamble, no markdown fences.
""",
        agent=agent,
        expected_output=(
            "A JSON object with exactly six keys: gd_question, pi_question, "
            "thirty_second_answer, policy_radar_entry, company_to_watch, concept_explained."
        ),
    )
