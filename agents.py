import os
from crewai import Agent, LLM
import litellm

# This patch intercepts the LiteLLM call and strips it out before the API request.
original_completion = litellm.completion

def clean_messages(*args, **kwargs):
    if "messages" in kwargs:
        for msg in kwargs["messages"]:
            if isinstance(msg, dict):
                msg.pop("cache_breakpoint", None)
    return original_completion(*args, **kwargs)

litellm.completion = clean_messages

def _build_llm(model: str, temperature: float = 0.4) -> LLM:
    """
    Constructs an OpenRouter-hosted LLM instance.
    OPENROUTER_API_KEY must be set in os.environ before this is called.
    app.py handles that injection from st.secrets at startup.

    We pass api_key and base_url explicitly to bypass CrewAI's internal
    provider auto-detection, which incorrectly routes openrouter/ models
    through its native Gemini provider.
    """
    return LLM(
        model=model,
        temperature=temperature,
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        base_url="https://openrouter.ai/api/v1",
    )
 
FAST_MODEL = "openrouter/google/gemma-4-31b-it:free"
QUALITY_MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
 
 
def build_scout_agent(region: str) -> Agent:
    """
    Regional Scout Agent (India or Global).
    Input: pre-pulled, formatted RSS entries passed via task description.
    Job:   filter to healthcare relevance, collapse duplicates, rank by
           significance, return top 4 as a JSON array.
    No tools attached — this is a pure reasoning/ranking task.
    """
    if region == "India":
        focus_goal = "You MUST focus entirely on the Indian Healthcare Ecosystem (e.g., CDSCO regulation, Ayushman Bharat/ABDM, Indian pharma/biotech exports, PLI schemes, hospital chains like Apollo/Fortis/Max, DPCO pricing, or Indian healthtech)."
        role_name = "Healthcare News Scout (India Focus)"
    else:
        focus_goal = "You MUST focus entirely on major global health, FDA, EMA, CMS, or international pharma/medtech events."
        role_name = "Healthcare News Scout (Global Focus)"

    return Agent(
        role=role_name,
        goal=(
            "From a list of RSS feed entries, identify the 4 most significant "
            f"healthcare, pharma, medtech, hospital, insurance, or health-policy stories. "
            f"{focus_goal} "
            "Collapse duplicate coverage of the same event into single entries. "
            "Return a ranked JSON array — most significant story first — with no commentary outside the JSON."
        ),
        backstory=(
            "You are a chief news editor for top business schools curating daily healthcare intelligence for MBA candidates. "
            f"You specialize in {region} news. You know that candidates need a strong, authoritative grip on the most consequential stories. "
        ),
        llm=_build_llm(FAST_MODEL, temperature=0.2),
        max_iter=1,
        verbose=False,
        allow_delegation=False,
    )


def build_analyst_agent() -> Agent:
    """
    Analyst Agent.
    Input: one story title + full article text (pre-fetched by trafilatura in app.py).
    Job:   produce the extended MBA-lens analysis in structured JSON.
    """
    return Agent(
        role="Healthcare MBA Analyst (India & Global)",
        goal=(
            "Produce a rigorous, structured MBA-lens analysis of a single healthcare "
            "news story. Output must be valid JSON matching the extended schema exactly. "
            "For all stories—whether domestic or international—explicitly draw connections "
            "to implications for the Indian healthcare ecosystem, market, or policy where relevant."
        ),
        backstory=(
            "You are a healthcare strategy consultant advising leading Indian hospital groups, "
            "pharma giants (Sun, Dr. Reddy's, Cipla), medtech firms, and NITI Aayog policy panels. "
            "You possess an intimate understanding of both domestic Indian healthcare dynamics "
            "(Ayushman Bharat, CDSCO, PLI schemes, out-of-pocket expenditure) and global market shifts. "
            "You never invent data and you extract non-obvious, high-leverage strategic takeaways."
        ),
        llm=_build_llm(QUALITY_MODEL, temperature=0.3),
        max_iter=1,
        verbose=False,
        allow_delegation=False,
    )


def build_coach_agent() -> Agent:
    """
    Coach Agent.
    Input: the Analyst's extended JSON for one story.
    Job:   generate gd_question, pi_question, thirty_second_answer,
           policy_radar_entry, company_to_watch, concept_explained.
    """
    return Agent(
        role="GDPI Preparation Coach (India B-Schools)",
        goal=(
            "From the analyst's structured briefing for one story, generate a genuinely "
            "debatable GD question, a probing PI question, a 30-second spoken-format model "
            "answer, a policy radar entry, a company to watch, and a plain-English concept "
            "explanation. Output must be valid JSON with exactly six keys. "
            "Tailor all interview questions and answers to the expectations of Indian B-school "
            "panellists (IIM-A, IIM-B, IIM-C, XLRI, ISB, SPHRON, FMS, IIFT)."
        ),
        backstory=(
            "You coach candidates for Group Discussions and Personal Interviews at top Indian B-schools "
            "specifically for healthcare, pharma, and consulting roles. You know that Indian panellists "
            "test candidates on domestic health economics, trade-offs between public vs private healthcare, "
            "price control vs R&D innovation, and global regulatory standards. Your model answers are punchy, "
            "articulate, and grounded in real-world Indian and global context."
        ),
        llm=_build_llm(QUALITY_MODEL, temperature=0.6),
        max_iter=5,
        verbose=False,
        allow_delegation=False,
    )
 