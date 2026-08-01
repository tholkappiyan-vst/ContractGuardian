"""LangChain chains: each wraps a prompt + Gemini LLM + output parsing."""
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted

from app.ai_engine.config import get_ai_settings
from app.ai_engine.prompts import (
    CLAUSE_EXTRACTION_PROMPT,
    RISK_ANALYSIS_PROMPT,
    SIMPLE_EXPLANATION_PROMPT,
    CONTRACT_SUMMARY_PROMPT,
    NEGOTIATION_ADVICE_PROMPT,
    CONTRACT_COMPARISON_PROMPT,
    CONTRACT_CHAT_PROMPT,
)


def _get_llm(temperature: float = 0.1) -> ChatGoogleGenerativeAI:
    settings = get_ai_settings()
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=temperature,
        max_retries=settings.max_retries,
        timeout=settings.request_timeout,
    )


def _parse_json(text: str) -> dict | list:
    """Extract JSON from LLM response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ResourceExhausted, json.JSONDecodeError)),
)
async def run_clause_extraction(contract_text: str) -> list[dict]:
    """Extract clauses from contract text."""
    llm = _get_llm(temperature=0.0)
    chain = CLAUSE_EXTRACTION_PROMPT | llm | StrOutputParser()
    result = await chain.ainvoke({"contract_text": contract_text})
    return _parse_json(result)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ResourceExhausted, json.JSONDecodeError)),
)
async def run_risk_analysis(
    clauses_json: str,
    contract_type: str,
    user_role: str,
    context: str = "",
) -> dict:
    """Analyze risk for extracted clauses."""
    llm = _get_llm(temperature=0.1)
    chain = RISK_ANALYSIS_PROMPT | llm | StrOutputParser()
    result = await chain.ainvoke({
        "clauses_json": clauses_json,
        "contract_type": contract_type,
        "user_role": user_role,
        "context": context,
    })
    return _parse_json(result)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ResourceExhausted, json.JSONDecodeError)),
)
async def run_simple_explanation(
    clauses_json: str,
    contract_type: str,
    user_role: str,
) -> dict:
    """Generate plain-language explanations for clauses."""
    llm = _get_llm(temperature=0.3)
    chain = SIMPLE_EXPLANATION_PROMPT | llm | StrOutputParser()
    result = await chain.ainvoke({
        "clauses_json": clauses_json,
        "contract_type": contract_type,
        "user_role": user_role,
    })
    return _parse_json(result)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ResourceExhausted, json.JSONDecodeError)),
)
async def run_contract_summary(contract_text: str, context: str = "") -> dict:
    """Generate structured contract summary."""
    llm = _get_llm(temperature=0.2)
    chain = CONTRACT_SUMMARY_PROMPT | llm | StrOutputParser()
    result = await chain.ainvoke({
        "contract_text": contract_text,
        "context": context,
    })
    return _parse_json(result)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ResourceExhausted, json.JSONDecodeError)),
)
async def run_negotiation_advice(
    clauses_json: str,
    contract_type: str,
    user_role: str,
    counterparty_role: str,
    power_dynamic: str,
    risk_context: str = "",
) -> dict:
    """Generate negotiation suggestions for risky clauses."""
    llm = _get_llm(temperature=0.4)
    chain = NEGOTIATION_ADVICE_PROMPT | llm | StrOutputParser()
    result = await chain.ainvoke({
        "clauses_json": clauses_json,
        "contract_type": contract_type,
        "user_role": user_role,
        "counterparty_role": counterparty_role,
        "power_dynamic": power_dynamic,
        "risk_context": risk_context,
    })
    return _parse_json(result)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ResourceExhausted, json.JSONDecodeError)),
)
async def run_contract_comparison(
    contract_a_text: str,
    contract_b_text: str,
    title_a: str,
    title_b: str,
    user_role: str,
) -> dict:
    """Compare two contracts."""
    llm = _get_llm(temperature=0.1)
    chain = CONTRACT_COMPARISON_PROMPT | llm | StrOutputParser()
    result = await chain.ainvoke({
        "contract_a_text": contract_a_text,
        "contract_b_text": contract_b_text,
        "title_a": title_a,
        "title_b": title_b,
        "user_role": user_role,
    })
    return _parse_json(result)


async def run_contract_chat(
    question: str,
    context: str,
    chat_history: str = "",
) -> str:
    """RAG-powered Q&A about a contract. Returns natural language answer."""
    llm = _get_llm(temperature=0.2)
    chain = CONTRACT_CHAT_PROMPT | llm | StrOutputParser()
    result = await chain.ainvoke({
        "question": question,
        "context": context,
        "chat_history": chat_history,
    })
    return result
