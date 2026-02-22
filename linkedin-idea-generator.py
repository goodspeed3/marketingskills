#!/usr/bin/env python3
"""
LinkedIn Content Idea Generator for ArcPrime
=============================================
Researches timely IP/patent topics via web search APIs,
then combines them with ArcPrime's product-marketing-context
to generate LinkedIn content ideas for Jonathan Liu.

Usage:
    python linkedin-idea-generator.py [--count 5] [--product-context] [--output ideas.md]

Requirements:
    pip install anthropic requests feedparser

Environment:
    ANTHROPIC_API_KEY - Required for Claude API (idea generation)
"""

import argparse
import json
import os
import sys
import textwrap
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. CONFIG
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
CONTEXT_PATH = SCRIPT_DIR / ".claude" / "product-marketing-context.md"
TOP_POSTS_PATH = SCRIPT_DIR / ".claude" / "top-performing-posts.md"

# News / research sources to scrape via RSS or web search
RSS_FEEDS = {
    # Direct IP sources
    "IPWatchdog": "https://ipwatchdog.com/feed/",
    "PatentlyO": "https://patentlyo.com/feed",
    "Ars Technica (Tech Policy)": "https://feeds.arstechnica.com/arstechnica/technology-lab",
    # Indirect — leadership, legal profession, AI impact
    "Above the Law": "https://abovethelaw.com/feed/",
    "Harvard Business Review": "https://hbr.org/feed",
    "Artificial Lawyer": "https://www.artificiallawyer.com/feed/",
    "Corporate Counsel": "https://www.law.com/corpcounsel/feed/",
}

# Search queries — organized by direct vs indirect topics
SEARCH_QUERIES = {
    # Direct IP/patent topics
    "direct": [
        "patent litigation trends {year}",
        "AI patent eligibility USPTO {year}",
        "patent portfolio pruning cost savings",
        "PTAB IPR changes {year} corporate impact",
        "patent renewal fees rising {year}",
        "Section 101 patent reform {year}",
        "AI tools patent management corporate",
        "patent assertion entity NPE trends {year}",
        "continuation patents strategy value",
        "in-house patent counsel challenges {year}",
    ],
    # Indirect — career, leadership, industry dynamics
    "indirect": [
        "head of IP career path in-house counsel {year}",
        "in-house patent team structure best practices",
        "AI replacing patent attorneys jobs {year}",
        "patent counsel burnout legal profession {year}",
        "justifying IP budget to CFO executives",
        "general counsel expectations IP team {year}",
        "outside counsel management in-house patent teams",
        "legal ops technology adoption resistance {year}",
        "patent attorney hiring market salary trends {year}",
        "junior associates AI impact law firm {year}",
        "in-house counsel influence engineering product teams",
        "legal department KPIs metrics {year}",
        "specialist vs generalist career legal technology",
        "imposter syndrome lawyers legal professionals",
        "managing up as in-house counsel",
    ],
}

# ---------------------------------------------------------------------------
# ICP INTERESTS — Direct product pain points AND indirect professional concerns
# ---------------------------------------------------------------------------
#
# "Direct" = problems ArcPrime solves (cost, quality, time)
# "Indirect" = things the ICP *person* cares about that aren't product problems
#   but make them trust you, follow you, and think of you when they ARE ready to buy.
#
# The indirect topics are often what drives the highest-engagement posts because
# they're relatable to a wider audience and tap into emotions, not just logic.
# ---------------------------------------------------------------------------

ICP_PAIN_POINTS = {
    # ---- DIRECT (product-related) ----
    "cost": [
        "Reducing IP spend without increasing risk",
        "Outside counsel costs spiraling",
        "Renewal fees on low-value patents draining budget",
        "No visibility into what patents actually cost to maintain",
        "Overfunding low-ROI assets",
    ],
    "quality": [
        "Improving patent quality while reducing effort",
        "Can't tell which patents are strong vs weak",
        "Draft quality depends on associate you get",
        "No data-driven way to evaluate patent strength",
        "Continuation strategy is ad-hoc, not systematic",
    ],
    "time": [
        "Manual IDF process is a bottleneck",
        "Inventors constantly asking about status",
        "Workflow tracking is manual and error-prone",
        "No time to do deep analysis on each case",
        "Pruning reviews happen once a year at best",
    ],
    # ---- INDIRECT (professional / human concerns) ----
    "career": [
        "How to grow from patent attorney to Head of IP",
        "Feeling stuck in a niche — is IP a dead-end career?",
        "Staying relevant as AI reshapes the patent profession",
        "Transitioning from law firm to in-house (and back)",
        "Building a personal brand as an IP professional",
        "The loneliness of being a deep specialist in a generalist world",
    ],
    "leadership": [
        "Managing a patent team when budgets are flat or shrinking",
        "Hiring and retaining good patent counsel in a tight market",
        "Getting your team to adopt new tools and processes",
        "Balancing being a player-coach — still doing patent work while managing",
        "Setting team KPIs when patent value is hard to measure",
        "Dealing with underperforming outside counsel without burning bridges",
    ],
    "influence": [
        "Justifying IP budget to a CFO who sees patents as a cost center",
        "Getting a seat at the table with product and engineering leadership",
        "Explaining patent strategy to non-lawyers (executives, board, inventors)",
        "Making IP visible and valued inside the company",
        "Navigating internal politics around patent committees and filing decisions",
        "Convincing R&D teams that the IDF process is worth their time",
    ],
    "peer_challenges": [
        "What other Heads of IP are dealing with right now",
        "How top IP teams are structured at 500+ patent companies",
        "The unspoken tension between IP teams and outside counsel",
        "Why most patent committees are theater, not strategy",
        "The gap between how IP leaders talk about patents and how execs hear it",
        "Imposter syndrome in a field where feedback takes 5-10 years",
    ],
    "ai_and_future": [
        "Will AI replace patent attorneys or make them 10x more effective?",
        "How to evaluate AI tools when every vendor claims to use AI",
        "The fear of adopting AI too early vs. too late",
        "What happens to junior associates when AI handles first drafts?",
        "AI is making other legal functions faster — why is IP so slow to adopt?",
        "The ethics of AI-assisted patent prosecution",
    ],
    "craft": [
        "What separates a good patent from a great one",
        "The art of writing claims that actually hold up in litigation",
        "Learning to think like an inventor when you're a lawyer",
        "Why the best patent counsel are also great teachers",
        "The difference between being thorough and being strategic",
        "How to give feedback on a patent draft without demoralizing the associate",
    ],
}

# Content formats that perform well (based on top posts analysis)
# Tagged with "direct" or "indirect" to help balance the content mix.
CONTENT_FORMATS = [
    # ---- Formats that work best for DIRECT (IP/product) topics ----
    {
        "name": "Data-Driven Insight",
        "description": "Original data analysis with surprising findings",
        "example_post": "Post #1 (16.6K impressions) - Asserted patents analysis",
        "hook_style": "Lead with the data point, then explain why it matters",
        "topic_affinity": ["direct"],
    },
    {
        "name": "Contrarian Take",
        "description": "Challenge a widely-held belief in patent practice",
        "example_post": "Post #4 (8.5K) - Patent attorneys are hoarders",
        "hook_style": "State the contrarian position in the first sentence",
        "topic_affinity": ["direct", "indirect"],
    },
    {
        "name": "Simple Framework",
        "description": "Distill a complex patent strategy into a clear mental model",
        "example_post": "Post #15 (1.9K) - Patent strategy is simple",
        "hook_style": "Make the complex sound obvious",
        "topic_affinity": ["direct"],
    },
    # ---- Formats that work best for INDIRECT (human/career) topics ----
    {
        "name": "Insider War Story",
        "description": "Personal experience from patent counsel career that reveals a systemic problem",
        "example_post": "Post #2 (9.9K) - Facebook patent team problem",
        "hook_style": "Start with a personal moment, then zoom out to the industry problem",
        "topic_affinity": ["indirect", "direct"],
    },
    {
        "name": "Craft / Career Reflection",
        "description": "Insight about the practice of patent law or building a career in IP",
        "example_post": "Post #6 (7K) - Outside counsel associates",
        "hook_style": "Specific moment → universal truth",
        "topic_affinity": ["indirect"],
    },
    {
        "name": "Uncomfortable Truth",
        "description": "Say the quiet part out loud about IP team dynamics, politics, or career realities",
        "example_post": "Post #18 (1.8K) - Patent portfolio politics",
        "hook_style": "Name the elephant in the room in sentence one",
        "topic_affinity": ["indirect"],
    },
    {
        "name": "Peer Benchmark / 'How Others Do It'",
        "description": "Share how top IP teams structure, decide, or operate — based on observation or data",
        "example_post": "Post #12 (3K) - Facebook patent learning",
        "hook_style": "Open with curiosity: 'I wanted to know how X actually worked at...'",
        "topic_affinity": ["indirect", "direct"],
    },
    {
        "name": "Founder Vulnerability",
        "description": "Honest reflection on building a company, making hard choices, or personal growth",
        "example_post": "Post #5 (8.2K) - Hello world / lurking for 20 years",
        "hook_style": "Admit something most people wouldn't say publicly",
        "topic_affinity": ["indirect"],
    },
    {
        "name": "The Analogy Post",
        "description": "Explain an IP concept by comparing it to something unexpected from another domain",
        "example_post": "Post #4 (8.5K) - Roth IRA / patent renewals compound cost analogy",
        "hook_style": "Start with the non-IP analogy, then make the connection",
        "topic_affinity": ["direct", "indirect"],
    },
]

# Voice guidelines for Jonathan Liu
VOICE_GUIDE = """
VOICE: Jonathan Liu (CEO, ArcPrime)
- Writing style: Like Paul Graham and Patrick Collison — clear thinking, plain language,
  substance over style. Concise. Never "I'm so insightful" tone.
- Sentence length: Mix short and long. Short for impact, long for nuance.
- Hooks: Short and punchy. Lead with the point, not the preamble.
- Tone: Quietly disruptive, strategic, precise, confident.
  Professional, expert-led, credible. Disruption that's thoughtful, not loud.
- NEVER: Hype-driven, emoji-heavy, LinkedIn-bro motivational, hashtag spam.
- CTA style: Soft. Ask a question or invite perspective. Never "Like if you agree!"
"""


# ---------------------------------------------------------------------------
# 2. RESEARCH MODULE — Gather timely topics
# ---------------------------------------------------------------------------

def fetch_rss_headlines(max_per_feed: int = 5) -> list[dict]:
    """Fetch recent headlines from IP/patent RSS feeds."""
    articles = []
    try:
        import feedparser
    except ImportError:
        print("  [!] feedparser not installed — skipping RSS feeds")
        return articles

    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_feed]:
                articles.append({
                    "source": source,
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:300],
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                })
        except Exception as e:
            print(f"  [!] Error fetching {source}: {e}")

    return articles


def search_web_topics(
    query_set: str = "both",
    max_results: int = 3,
) -> list[dict]:
    """
    Search for timely IP topics using available search methods.
    Falls back to curated topics if no API is available.

    Args:
        query_set: "direct", "indirect", or "both"
        max_results: max results per query
    """
    year = datetime.now().year
    results = []

    queries_to_use = []
    if query_set in ("direct", "both"):
        queries_to_use.extend(SEARCH_QUERIES.get("direct", []))
    if query_set in ("indirect", "both"):
        queries_to_use.extend(SEARCH_QUERIES.get("indirect", []))

    for query in queries_to_use:
        formatted = query.format(year=year)
        results.append({
            "query": formatted,
            "title": formatted,
            "snippet": f"Search topic: {formatted}",
        })

    return results


def get_curated_indirect_topics() -> list[dict]:
    """
    Curated list of INDIRECT topics — career, leadership, peer dynamics, AI impact.
    These are things the ICP *person* cares about that aren't directly about patents,
    but build trust, relatability, and thought-leader positioning.
    """
    return [
        {
            "topic": "The Head of IP is becoming a strategic executive — but most orgs still treat it as a cost center",
            "summary": "GCs and CFOs increasingly expect IP leaders to tie patent portfolios to revenue, "
                       "competitive positioning, and M&A strategy. Yet IP teams still report through legal ops "
                       "with no direct line to the C-suite. The role is evolving faster than the org chart.",
            "relevance": "influence",
            "category": "indirect",
            "timeliness": "2026-Q1",
            "source_url": "",
        },
        {
            "topic": "Junior patent associates are about to have an identity crisis",
            "summary": "AI can now draft patent applications, summarize prior art, and generate office action "
                       "responses. The traditional 'learn by doing grunt work' associate model is breaking. "
                       "Firms that don't rethink training will produce attorneys who can prompt but can't think.",
            "relevance": "ai_and_future",
            "category": "indirect",
            "timeliness": "2026-Q1",
            "source_url": "",
        },
        {
            "topic": "Why most patent committees are performance theater",
            "summary": "Patent committee meetings at large companies often rubber-stamp decisions already "
                       "made by individual counsel. The committee structure gives the appearance of rigor "
                       "but rarely changes outcomes. Teams that replaced committees with data-driven scoring "
                       "report faster decisions and better portfolio alignment.",
            "relevance": "peer_challenges",
            "category": "indirect",
            "timeliness": "evergreen",
            "source_url": "",
        },
        {
            "topic": "The hardest conversation in IP: telling an inventor their idea isn't worth patenting",
            "summary": "Inventors have emotional attachment to their ideas. Saying 'no' risks damaging the "
                       "relationship between IP and R&D. Many counsel avoid the conversation entirely and "
                       "just file everything — which is how portfolios bloat. The best IP leaders reframe "
                       "'no' as redirection.",
            "relevance": "influence",
            "category": "indirect",
            "timeliness": "evergreen",
            "source_url": "",
        },
        {
            "topic": "The 'do more with less' mandate is hitting IP teams harder than anyone admits",
            "summary": "Flat budgets + growing patent portfolios + rising renewal fees = IP teams stretched "
                       "thin. Many Heads of IP are quietly burning out while maintaining the appearance of "
                       "control. The ones surviving are ruthlessly prioritizing and automating admin work.",
            "relevance": "leadership",
            "category": "indirect",
            "timeliness": "2026-Q1",
            "source_url": "",
        },
        {
            "topic": "How to explain patent strategy to your CEO in 5 minutes",
            "summary": "Most IP leaders over-explain when presenting to executives. CEOs want to know: "
                       "what are we protected from, what are we exposed to, and what does it cost. "
                       "The best IP communicators speak in business risk, not legal nuance.",
            "relevance": "influence",
            "category": "indirect",
            "timeliness": "evergreen",
            "source_url": "",
        },
        {
            "topic": "The imposter syndrome problem in patent law is uniquely bad",
            "summary": "Patent counsel operate in a field where feedback loops are 5-10 years long. "
                       "You file something today and won't know if it was good until it's litigated or "
                       "licensed years later. That ambiguity breeds chronic self-doubt, especially in "
                       "counsel who care about quality.",
            "relevance": "career",
            "category": "indirect",
            "timeliness": "evergreen",
            "source_url": "",
        },
        {
            "topic": "The real reason your IP team resists new tools (it's not the tech)",
            "summary": "Tool adoption failure in IP teams is rarely about the software. It's about workflow "
                       "disruption fear, loss of control over quality, and the unspoken belief that 'my way "
                       "works fine.' Change management in IP requires addressing identity, not just features.",
            "relevance": "leadership",
            "category": "indirect",
            "timeliness": "evergreen",
            "source_url": "",
        },
        {
            "topic": "The unspoken tension between in-house counsel and outside counsel",
            "summary": "In-house counsel manage budgets and strategy. Outside counsel do the work and bill "
                       "for it. The incentives are fundamentally misaligned: one wants efficiency, the other "
                       "bills by the hour. AI is about to blow this dynamic wide open.",
            "relevance": "peer_challenges",
            "category": "indirect",
            "timeliness": "2026-Q1",
            "source_url": "",
        },
        {
            "topic": "Hiring patent counsel in 2026: the market is bifurcating",
            "summary": "Demand for AI-literate patent counsel is surging while traditional prosecution-only "
                       "roles are flat. The attorneys who can bridge technical AI understanding with legal "
                       "strategy command premium compensation. Those who can't are seeing fewer opportunities.",
            "relevance": "career",
            "category": "indirect",
            "timeliness": "2026-Q1",
            "source_url": "",
        },
        {
            "topic": "What I wish someone told me before going in-house",
            "summary": "The transition from law firm to in-house changes everything: billing pressure "
                       "disappears but gets replaced by budget pressure. You go from deep specialist to "
                       "broad strategist overnight. The skill that matters most isn't legal — it's influence.",
            "relevance": "career",
            "category": "indirect",
            "timeliness": "evergreen",
            "source_url": "",
        },
        {
            "topic": "The best Heads of IP are not the best patent attorneys",
            "summary": "Technical excellence gets you to senior counsel. But leading an IP function requires "
                       "an entirely different skill set: budget negotiation, cross-functional influence, "
                       "executive communication, team development. The promotion often catches people off guard.",
            "relevance": "leadership",
            "category": "indirect",
            "timeliness": "evergreen",
            "source_url": "",
        },
    ]


def get_curated_timely_topics() -> list[dict]:
    """
    Curated list of DIRECT timely IP topics based on recent research.
    Updated periodically — this is the fallback when web search isn't available.
    """
    return [
        {
            "topic": "USPTO proposes 'One Challenge' rule — IPR estoppel expansion",
            "summary": "The USPTO's proposed NPRM would force companies to choose between "
                       "IPR and district court invalidity defenses. Filing an IPR means forfeiting "
                       "all anticipation/obviousness arguments in litigation. Over 2,800 comments received.",
            "relevance": "cost,quality",
            "timeliness": "2026-Q1",
            "source_url": "https://federalnewsnetwork.com/commentary/2026/01/uspto-proposes-dramatic-restrictions-on-patent-challenges-through-inter-partes-review/",
        },
        {
            "topic": "Patent renewal fees rising 25%+ globally — UK IPO leads with April 2026 hike",
            "summary": "Companies projected to spend $10B+ on renewal fees in 2026 alone. "
                       "UK IPO raising fees ~25% in April 2026. Industry-wide pruning savings "
                       "could reach $527M in 2026 if companies aligned with aggressive pruners.",
            "relevance": "cost",
            "timeliness": "2026-Q1",
            "source_url": "https://www.iam-media.com/article/analysis-of-global-patent-pruning-strategies-highlights-how-companies-can-strengthen-portfolios",
        },
        {
            "topic": "Section 101 reform: Patent Eligibility Restoration Act introduced",
            "summary": "PERA (S. 1546 / H.R. 3152) would eliminate all judicial exceptions "
                       "to patent eligibility. Meanwhile, USPTO's Ex parte Desjardins decision "
                       "is now precedential — raising the bar for 101 rejections of AI patents.",
            "relevance": "quality",
            "timeliness": "2026-Q1",
            "source_url": "https://www.congress.gov/bill/119th-congress/senate-bill/1546/text",
        },
        {
            "topic": "Perfect storm for patent litigation in 2026",
            "summary": "Tighter PTAB access + rising AI patent allowances + more domestic "
                       "manufacturing targets = significant increase in district court patent cases. "
                       "NPEs making targeted AI patent acquisitions for future assertion.",
            "relevance": "cost,quality",
            "timeliness": "2026-Q1",
            "source_url": "https://www.bakerbotts.com/thought-leadership/publications/2025/november/a-perfect-storm-for-increased-patent-litigation-in-2026",
        },
        {
            "topic": "Corporate IP teams shifting from episodic reviews to continuous portfolio intelligence",
            "summary": "AI-driven patent management reduces search/analysis time by 60-80%. "
                       "Executives now expect IP teams to explain which patents protect revenue, "
                       "which justify maintenance costs, and where FTO risk exists.",
            "relevance": "cost,time,quality",
            "timeliness": "2026-Q1",
            "source_url": "https://www.deepip.ai/blog/corporate-ip-ai-2026-innovation-patentability-portfolio",
        },
        {
            "topic": "Asserted patents are disproportionately continuations and acquisitions",
            "summary": "Analysis of 9,700 asserted patents shows 50% were continuations (vs 20% baseline) "
                       "and ~55% were acquired. Even filtering out NPEs, 42% of operating company "
                       "litigated patents were acquired.",
            "relevance": "quality,cost",
            "timeliness": "evergreen",
            "source_url": "https://asserted.office",
        },
        {
            "topic": "AI invention disclosure capture is going continuous and embedded",
            "summary": "Modern systems integrate with R&D workflows to identify potential inventions "
                       "as work progresses, replacing static IDF forms. AI structures early technical "
                       "insights into legally meaningful disclosures automatically.",
            "relevance": "time,quality",
            "timeliness": "2026-Q1",
            "source_url": "https://patentlawyermagazine.com/the-corporate-ip-tech-stack-2026-what-in-house-teams-should-demand-from-ai-tools/",
        },
        {
            "topic": "Portfolio bloat: companies can save $200K/quarter by not renewing just 5% of patents",
            "summary": "PA Consulting finds companies who review patents often discover 10-20% can be abandoned. "
                       "Honda, Fujitsu, HP eliminated ~60% of lowest-decile families. "
                       "Letting 10-15 families lapse can save $670K-1M+.",
            "relevance": "cost",
            "timeliness": "evergreen",
            "source_url": "https://www.paconsulting.com/insights/why-it-pays-to-prune-patents",
        },
        {
            "topic": "AI patent vulnerability: recently issued AI/software patents face new eligibility challenges",
            "summary": "USPTO's rescission of Biden-era guidance + Recentive Analytics decision means "
                       "AI patents that merely automate existing methods are prime targets for early "
                       "motions to dismiss. Generic ML on conventional computing = vulnerable.",
            "relevance": "quality",
            "timeliness": "2026-Q1",
            "source_url": "https://www.venable.com/insights/publications/2025/12/the-101-reset-for-2026",
        },
        {
            "topic": "Pro-patent policy shift under Director Squires creates new strategic calculus",
            "summary": "Director Squires centralized IPR institution decisions, tightened discretionary "
                       "denials, and made PTAB less accessible. Patent challengers flowing toward "
                       "ex parte reexamination as alternative. IPR is no longer reflexive.",
            "relevance": "cost,quality",
            "timeliness": "2026-Q1",
            "source_url": "https://news.bloomberglaw.com/us-law-week/ip-policy-shifts-are-promising-for-patent-owners-in-high-tech",
        },
    ]


# ---------------------------------------------------------------------------
# 3. IDEA GENERATION MODULE — Combine research + ICP context
# ---------------------------------------------------------------------------

def load_product_context() -> str:
    """Load the product marketing context file."""
    if CONTEXT_PATH.exists():
        return CONTEXT_PATH.read_text()
    print(f"  [!] Product context not found at {CONTEXT_PATH}")
    return ""


def load_top_posts() -> str:
    """Load top performing posts for style reference."""
    if TOP_POSTS_PATH.exists():
        return TOP_POSTS_PATH.read_text()
    return ""


def generate_ideas_with_claude(
    topics: list[dict],
    product_context: str,
    count: int = 5,
    include_product_context: bool = True,
    focus: str = "mixed",
) -> str:
    """Use Claude API to generate LinkedIn content ideas.

    Args:
        focus: "direct" (IP/product topics only), "indirect" (career/leadership/peer),
               or "mixed" (balanced blend — default)
    """
    try:
        import anthropic
    except ImportError:
        print("  [!] anthropic package not installed. Using template-based generation.")
        return generate_ideas_template(topics, count, include_product_context, focus)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  [!] ANTHROPIC_API_KEY not set. Using template-based generation.")
        return generate_ideas_template(topics, count, include_product_context, focus)

    client = anthropic.Anthropic(api_key=api_key)

    # Separate topics by category for the prompt
    direct_topics = [t for t in topics if t.get("category") != "indirect"]
    indirect_topics = [t for t in topics if t.get("category") == "indirect"]

    topics_text = ""
    if focus in ("direct", "mixed") and direct_topics:
        topics_text += "\n### Direct IP/Patent Topics\n"
        topics_text += "\n".join(
            f"- **{t['topic']}** ({t.get('timeliness', 'recent')}): {t['summary']}"
            for t in direct_topics
        )
    if focus in ("indirect", "mixed") and indirect_topics:
        topics_text += "\n\n### Indirect Topics (Career, Leadership, Peer Dynamics)\n"
        topics_text += "\n".join(
            f"- **{t['topic']}** ({t.get('timeliness', 'recent')}): {t['summary']}"
            for t in indirect_topics
        )

    formats_text = "\n".join(
        f"- **{f['name']}** [{'/'.join(f.get('topic_affinity', ['any']))}]: "
        f"{f['description']} | Hook style: {f['hook_style']}"
        for f in CONTENT_FORMATS
    )

    # Group pain points by direct vs indirect
    direct_categories = ["cost", "quality", "time"]
    indirect_categories = [k for k in ICP_PAIN_POINTS if k not in direct_categories]

    pain_points_text = "\n### Direct Pain Points (product-related)\n"
    for theme in direct_categories:
        if theme in ICP_PAIN_POINTS:
            pain_points_text += f"  {theme.upper()}: " + "; ".join(ICP_PAIN_POINTS[theme]) + "\n"
    pain_points_text += "\n### Indirect Pain Points (professional/human concerns)\n"
    for theme in indirect_categories:
        if theme in ICP_PAIN_POINTS:
            pain_points_text += f"  {theme.upper()}: " + "; ".join(ICP_PAIN_POINTS[theme][:3]) + "\n"

    context_block = ""
    if include_product_context and product_context:
        context_block = f"""
## PRODUCT CONTEXT (use to inform ideas, but posts should NOT be product pitches)
{product_context[:3000]}
"""

    # Build focus-specific instructions
    focus_instructions = {
        "direct": (
            "Focus ALL ideas on direct IP/patent topics. "
            "Connect to cost, quality, or time pain points."
        ),
        "indirect": (
            "Focus ALL ideas on INDIRECT topics: career growth, team leadership, "
            "peer challenges, AI's impact on the profession, internal politics, craft. "
            "These posts should make IP leaders feel SEEN and build trust. "
            "Product tie-ins should be very light or absent — the goal is relatability."
        ),
        "mixed": (
            f"Generate a balanced mix: ~{max(1, count // 2)} ideas on direct IP/patent topics "
            f"and ~{count - max(1, count // 2)} on indirect topics (career, leadership, peer dynamics). "
            "The indirect posts build trust and audience; the direct posts establish expertise."
        ),
    }

    prompt = f"""You are a LinkedIn content strategist for Jonathan Liu, CEO of ArcPrime
(AI-powered patent lifecycle management platform).

{VOICE_GUIDE}

## TIMELY TOPICS FROM RESEARCH
{topics_text}

## ICP INTERESTS (Heads of IP / Patents at HW/SW companies with 500+ patents)
{pain_points_text}

## CONTENT FORMATS THAT PERFORM (based on top posts data)
{formats_text}

{context_block}

## TASK
Generate exactly {count} LinkedIn content ideas. {focus_instructions[focus]}

For each idea:

1. **HEADLINE** — The working title (not the post itself)
2. **TOPIC TYPE** — Direct (IP/patent) or Indirect (career/leadership/peer/craft)
3. **HOOK** — The exact opening 1-2 sentences of the post (this is what people see before "...see more")
4. **TIMELY ANGLE** — What current event/trend makes this relevant RIGHT NOW (for evergreen indirect topics, explain why it resonates now)
5. **ICP CONNECTION** — Which specific pain point or interest this addresses. For indirect topics, explain the EMOTIONAL resonance — why would a Head of IP stop scrolling for this?
6. **FORMAT** — Which content format from the list above
7. **KEY POINTS** — 3-4 bullet points the post would cover
8. **SOFT CTA** — How to end the post (question, invitation to discuss, etc.)
9. **PRODUCT TIE-IN (optional)** — If natural, how ArcPrime connects. For indirect posts, this can be "None — pure trust-building" and that's perfectly fine.

RULES:
- Each idea should use a DIFFERENT format from the list
- Match formats to topic type using the [direct/indirect] affinity tags
- At least 1 idea should be a contrarian or surprising take
- Ideas should feel like something a former Meta patent counsel turned founder would write
- NO LinkedIn-bro energy. NO "Here's what I learned" generic openers.
- Posts should provide genuine value to IP leaders, not just promote ArcPrime
- For indirect topics: tap into emotions (frustration, ambition, imposter syndrome, pride in craft, loneliness of leadership). These are the posts that get saved and shared.
- IMPORTANT: Indirect posts should still feel relevant to IP specifically — not generic "leadership advice" that could apply to any industry. Ground them in the specific realities of running an IP function.
"""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def generate_ideas_template(
    topics: list[dict],
    count: int = 5,
    include_product_context: bool = True,
    focus: str = "mixed",
) -> str:
    """
    Template-based idea generation (no API key needed).
    Combines timely topics with ICP pain points and content formats.
    """
    ideas = []
    used_formats = set()

    # Filter topics by focus
    if focus == "direct":
        filtered = [t for t in topics if t.get("category") != "indirect"]
    elif focus == "indirect":
        filtered = [t for t in topics if t.get("category") == "indirect"]
    else:  # mixed — interleave
        direct = [t for t in topics if t.get("category") != "indirect"]
        indirect = [t for t in topics if t.get("category") == "indirect"]
        filtered = []
        di, ii = 0, 0
        for i in range(count):
            if i % 2 == 0 and di < len(direct):
                filtered.append(direct[di])
                di += 1
            elif ii < len(indirect):
                filtered.append(indirect[ii])
                ii += 1
            elif di < len(direct):
                filtered.append(direct[di])
                di += 1

    for i in range(min(count, len(filtered))):
        topic = filtered[i]
        is_indirect = topic.get("category") == "indirect"

        # Pick format with matching affinity
        affinity = "indirect" if is_indirect else "direct"
        matching_formats = [
            f for f in CONTENT_FORMATS
            if affinity in f.get("topic_affinity", ["direct"])
            and f["name"] not in used_formats
        ]
        fmt = matching_formats[0] if matching_formats else CONTENT_FORMATS[i % len(CONTENT_FORMATS)]
        used_formats.add(fmt["name"])

        # Map relevance to pain points
        relevance = topic.get("relevance", "cost")
        pain_category = relevance.split(",")[0]
        pain_points = ICP_PAIN_POINTS.get(pain_category, ICP_PAIN_POINTS["cost"])

        topic_type = "Indirect (career/leadership/peer)" if is_indirect else "Direct (IP/patent)"

        idea = f"""
### Idea {i + 1}: {topic['topic']}

- **Topic type**: {topic_type}
- **Format**: {fmt['name']}
- **Timely angle**: {topic['summary'][:200]}
- **ICP interest**: {pain_points[0]}
- **Hook style**: {fmt['hook_style']}
- **Source**: {topic.get('source_url', 'N/A') or 'Observation / evergreen'}
- **Product tie-in**: {'Light — connects to ArcPrime ' + pain_category + ' value pillar' if include_product_context and not is_indirect else 'None — pure trust-building' if is_indirect else 'N/A'}
"""
        ideas.append(idea)

    return "\n".join(ideas)


# ---------------------------------------------------------------------------
# 4. OUTPUT MODULE
# ---------------------------------------------------------------------------

def format_output(ideas_text: str, topics: list[dict], timestamp: str) -> str:
    """Format the final output as markdown."""
    header = f"""# LinkedIn Content Ideas for Jonathan Liu / ArcPrime
**Generated**: {timestamp}
**Method**: Timely IP research × ICP pain points × Top-performing post formats

---

## Research Sources Used
"""
    sources = "\n".join(
        f"- [{t['topic'][:60]}...]({t.get('source_url', '#')})"
        for t in topics[:10]
    )

    return f"""{header}
{sources}

---

## Content Ideas

{ideas_text}

---

## How This Was Generated

1. **Research**: Pulled timely topics from RSS feeds, web searches, and curated sources
2. **ICP Mapping**: Cross-referenced with both DIRECT pain points (Cost, Quality, Time) and INDIRECT interests (career, leadership, peer dynamics, AI impact, craft)
3. **Format Selection**: Matched each idea to a proven content format based on top-performing posts, using topic affinity tags
4. **Voice Check**: Filtered through Jonathan Liu's writing voice guidelines

## Topic Categories

**Direct topics** build expertise and credibility:
- Patent strategy, portfolio management, litigation trends, AI tools, regulatory changes

**Indirect topics** build trust and relatability:
- Career growth as an IP leader, managing teams with shrinking budgets
- The politics of IP inside a corporation, justifying budget to executives
- Peer dynamics (what other Heads of IP deal with), outside counsel tensions
- AI's impact on the profession, imposter syndrome, craft and quality
- Founder journey and personal growth

## Next Steps
- Pick 1-2 ideas to develop into full posts
- For a balanced content calendar, alternate: direct → indirect → direct
- For data-driven posts, gather supporting data from ArcPrime's internal analysis
- Draft, sleep on it, edit for clarity (per Jonathan's proven writing process)
- Indirect posts often outperform direct posts in engagement — don't underestimate them
"""


# ---------------------------------------------------------------------------
# 5. MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate LinkedIn content ideas for ArcPrime",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              # Default: 5 mixed ideas (direct + indirect)
              python linkedin-idea-generator.py

              # Focus on indirect topics (career, leadership, peer dynamics)
              python linkedin-idea-generator.py --focus indirect --count 7

              # Direct IP topics only, no product tie-ins
              python linkedin-idea-generator.py --focus direct --no-product-context

              # Generate 10 ideas focused on career and leadership
              python linkedin-idea-generator.py --focus indirect --count 10

            Focus modes:
              mixed    - Balanced blend of direct IP topics and indirect human topics (default)
              direct   - Only IP/patent/product-related topics
              indirect - Only career, leadership, peer dynamics, AI impact, craft topics
        """),
    )
    parser.add_argument(
        "--count", type=int, default=5,
        help="Number of ideas to generate (default: 5)",
    )
    parser.add_argument(
        "--focus",
        choices=["mixed", "direct", "indirect"],
        default="mixed",
        help=(
            "Topic focus: 'mixed' (default) balances direct IP topics with indirect "
            "human topics; 'direct' = only IP/patent; 'indirect' = only career, "
            "leadership, peer challenges, AI impact, craft"
        ),
    )
    parser.add_argument(
        "--product-context",
        action="store_true",
        default=True,
        help="Include product marketing context in idea generation (default: True)",
    )
    parser.add_argument(
        "--no-product-context",
        action="store_true",
        help="Exclude product marketing context",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file path (default: auto-generated with date)",
    )
    args = parser.parse_args()

    include_context = args.product_context and not args.no_product_context
    focus = args.focus
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    focus_labels = {
        "mixed": "Mixed (direct IP + indirect human topics)",
        "direct": "Direct (IP/patent topics only)",
        "indirect": "Indirect (career, leadership, peer dynamics, craft)",
    }

    print(f"\n{'='*60}")
    print(f"  ArcPrime LinkedIn Content Idea Generator")
    print(f"  {timestamp}")
    print(f"  Focus: {focus_labels[focus]}")
    print(f"{'='*60}\n")

    # Step 1: Gather research
    print("[1/4] Gathering topics...")
    rss_articles = fetch_rss_headlines()
    print(f"  Found {len(rss_articles)} RSS articles")

    all_topics = []
    if focus in ("direct", "mixed"):
        direct_topics = get_curated_timely_topics()
        # Tag them
        for t in direct_topics:
            t.setdefault("category", "direct")
        all_topics.extend(direct_topics)
        print(f"  Loaded {len(direct_topics)} direct IP topics")

    if focus in ("indirect", "mixed"):
        indirect_topics = get_curated_indirect_topics()
        all_topics.extend(indirect_topics)
        print(f"  Loaded {len(indirect_topics)} indirect topics")

    # Step 2: Load context
    print("[2/4] Loading product context...")
    product_context = ""
    if include_context:
        product_context = load_product_context()
        print(f"  Loaded {len(product_context)} chars of product context")
    else:
        print("  Skipped (--no-product-context)")

    # Step 3: Generate ideas
    print(f"[3/4] Generating {args.count} content ideas (focus={focus})...")
    ideas_text = generate_ideas_with_claude(
        topics=all_topics,
        product_context=product_context,
        count=args.count,
        include_product_context=include_context,
        focus=focus,
    )

    # Step 4: Format and output
    print("[4/4] Formatting output...")
    output = format_output(ideas_text, all_topics, timestamp)

    # Save to file
    output_path = args.output or str(
        SCRIPT_DIR / f"linkedin-ideas-{datetime.now().strftime('%Y%m%d')}.md"
    )
    Path(output_path).write_text(output)
    print(f"\n  Saved to: {output_path}")

    # Also print to stdout
    print(f"\n{'='*60}\n")
    print(output)

    return output


if __name__ == "__main__":
    main()
