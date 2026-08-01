import json
import time
from datetime import datetime, timezone
from anthropic import Anthropic
from app.core.config import get_settings

ANALYSIS_SYSTEM_PROMPT = """You are a senior contract analyst. Analyze the provided contract and return a JSON object with the following structure. Be thorough, accurate, and explain everything in plain language a non-lawyer can understand.

Output ONLY valid JSON matching this schema:
{
  "contract_type": {"type": "string", "confidence": 0.0-1.0},
  "parties": [{"name": "string", "role": "string", "type": "individual|corporate"}],
  "dates": {
    "effective": "ISO date or null",
    "expiration": "ISO date or null",
    "renewal": {"type": "auto|manual|none", "terms": "string"}
  },
  "payment_summary": {
    "total_value": {"amount": "number or null", "currency": "string"},
    "schedule": "string description"
  },
  "obligations": {
    "party_a": ["obligation strings"],
    "party_b": ["obligation strings"]
  },
  "clauses": [
    {
      "index": 0,
      "section_number": "string or null",
      "title": "string",
      "body": "original clause text",
      "category": "payment|termination|liability|confidentiality|ip_rights|data_privacy|non_compete|warranty|dispute_resolution|penalties|force_majeure|assignment|governing_law|definitions|other",
      "subcategory": "string or null",
      "confidence": 0.0-1.0,
      "risk_score": 1-10,
      "is_standard": true/false,
      "explanation": {
        "tldr": "one sentence",
        "what_it_means": "2-3 sentences, grade 8 reading level",
        "why_care": "1-2 sentences, personal stakes",
        "consequence": "worst case scenario, concrete",
        "negotiate": "actionable suggestion or null"
      }
    }
  ],
  "entities": [
    {
      "entity_type": "person|organization|date|money|percent|duration|payment_term|penalty|liability_term|obligation|termination_condition|deadline|restriction",
      "value": "canonical value",
      "original_text": "as in contract",
      "normalized": {"structured": "form"} or null,
      "confidence": 0.0-1.0,
      "role": "string or null",
      "clause_index": 0
    }
  ],
  "risks": [
    {
      "clause_index": 0,
      "scope": "clause",
      "score": 1-10,
      "label": "low|moderate|elevated|high|critical",
      "category": "financial_exposure|restrictive_terms|one_sided_obligations|missing_protections|unusual_language|compliance_risk|operational_risk",
      "explanation": "plain language",
      "consequence": "if X then Y, concrete",
      "affected_party": "string",
      "is_standard": true/false,
      "standard_note": "what standard would be, or null"
    }
  ],
  "overall_risk": {
    "score": 1-10,
    "label": "low|moderate|elevated|high|critical",
    "summary": "2-3 sentences"
  },
  "executive_summary": "3-5 sentences summarizing the contract for a non-lawyer",
  "top_risks": [
    {"rank": 1, "clause_index": 0, "summary": "one sentence", "score": 1-10}
  ],
  "action_items": {
    "negotiate": ["items"],
    "verify": ["items"],
    "acceptable": ["items"]
  },
  "negotiations": [
    {
      "clause_index": 0,
      "difficulty": "easy|medium|hard",
      "label": "short title",
      "original_text": "the risky clause text",
      "alternative_text": "suggested replacement language",
      "explanation": "why this is better",
      "talking_points": ["conversational points"],
      "likelihood": "high|medium|low"
    }
  ]
}

Rules:
- Score risk from the READER's perspective (they uploaded this, they're about to sign it)
- Use "you" and "they" in explanations
- Include SPECIFIC numbers/dates from the contract
- Never use legal jargon without immediate explanation
- For negotiations: only generate for clauses with risk_score >= 6
- Be concrete: "you could lose $X" not "financial implications"
"""

CHAT_SYSTEM_PROMPT = """You are a contract Q&A assistant. Answer questions ONLY based on the provided contract text.

Rules:
- ONLY reference content from the contract provided
- Quote specific sections that support your answer
- Say "this contract doesn't address that" when the answer isn't in the document
- Never provide legal advice — frame as "based on this document"
- Suggest one follow-up question at the end
- Use plain language, no legal jargon without explanation
"""

COMPARISON_SYSTEM_PROMPT = """You are a contract comparison analyst. Compare two contracts and identify differences that matter to the reader.

Output ONLY valid JSON:
{
  "summary": "3-5 sentences comparing the contracts",
  "recommendation": "A|B|neither",
  "confidence": 0.0-1.0,
  "risk_a": 1-10,
  "risk_b": 1-10,
  "differences": [
    {
      "category": "string",
      "significance": "critical|major|minor|cosmetic",
      "contract_a": "what A says",
      "contract_b": "what B says",
      "impact": "what this means for you",
      "favors": "A|B|neutral"
    }
  ],
  "unchanged": ["list of unchanged categories"],
  "subtle_changes": [
    {"clause": "reference", "change": "what changed", "significance": "why it matters"}
  ]
}
"""


def _get_client() -> Anthropic:
    return Anthropic(api_key=get_settings().anthropic_api_key)


async def analyze_contract(contract_text: str) -> dict:
    """Run full analysis on contract text. Returns structured analysis dict."""
    settings = get_settings()
    client = _get_client()

    start = time.time()
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=16000,
        system=ANALYSIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Analyze this contract:\n\n{contract_text}"}],
    )

    elapsed_ms = int((time.time() - start) * 1000)
    raw = response.content[0].text

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    result = json.loads(raw)
    result["_meta"] = {
        "model_used": settings.anthropic_model,
        "tokens_input": response.usage.input_tokens,
        "tokens_output": response.usage.output_tokens,
        "processing_ms": elapsed_ms,
    }
    return result


async def chat_about_contract(contract_text: str, messages: list[dict]) -> dict:
    """Answer a question about a contract given conversation history."""
    settings = get_settings()
    client = _get_client()

    system = f"{CHAT_SYSTEM_PROMPT}\n\nContract text:\n{contract_text}"

    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=4000,
        system=system,
        messages=messages,
    )

    return {
        "content": response.content[0].text,
        "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
        "model_used": settings.anthropic_model,
    }


async def compare_contracts(text_a: str, text_b: str) -> dict:
    """Compare two contracts and return structured diff."""
    settings = get_settings()
    client = _get_client()

    user_msg = f"Compare these two contracts from my perspective (I'm about to choose one to sign).\n\nCONTRACT A:\n{text_a}\n\n---\n\nCONTRACT B:\n{text_b}"

    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=8000,
        system=COMPARISON_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = response.content[0].text
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    return json.loads(raw)
