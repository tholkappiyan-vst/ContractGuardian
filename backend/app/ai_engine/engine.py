"""ContractAI Engine: orchestrates the full analysis pipeline.

Usage:
    engine = ContractAIEngine()

    # Full analysis
    result = await engine.analyze(content=pdf_bytes, file_type="pdf", filename="contract.pdf")

    # Chat (RAG)
    answer = await engine.chat(contract_id="...", question="Can I terminate early?", history=[])

    # Compare
    diff = await engine.compare(text_a="...", text_b="...", title_a="V1", title_b="V2")
"""
import json
import time
from dataclasses import dataclass, field

from app.ai_engine.loader import ContractLoader
from app.ai_engine.splitter import ContractTextSplitter, ClauseSegmenter
from app.ai_engine.vectorstore import ContractVectorStore
from app.ai_engine.chains import (
    run_clause_extraction,
    run_risk_analysis,
    run_simple_explanation,
    run_contract_summary,
    run_negotiation_advice,
    run_contract_comparison,
    run_contract_chat,
)


@dataclass
class AnalysisResult:
    """Complete analysis output."""
    contract_text: str
    clauses: list[dict]
    risks: dict
    explanations: dict
    summary: dict
    negotiations: dict
    metadata: dict = field(default_factory=dict)


class ContractAIEngine:
    """Main entry point for all AI operations."""

    def __init__(self):
        self.loader = ContractLoader()
        self.splitter = ContractTextSplitter()
        self.segmenter = ClauseSegmenter()
        self.vector_store = ContractVectorStore()

    # ─────────────────────────────────────────────────────────────────────
    # FULL ANALYSIS PIPELINE
    # ─────────────────────────────────────────────────────────────────────

    async def analyze(
        self,
        content: bytes,
        file_type: str,
        filename: str = "",
        contract_id: str | None = None,
        user_role: str = "the person signing",
    ) -> AnalysisResult:
        """Run the complete analysis pipeline on a contract.

        Steps:
        1. Load document → extract text
        2. Split into chunks → index in vector store
        3. Extract clauses (LLM)
        4. Risk analysis (LLM)
        5. Plain-language explanations (LLM)
        6. Summary (LLM)
        7. Negotiation advice for risky clauses (LLM)
        """
        start_time = time.time()

        # Step 1: Load and extract text
        documents = self.loader.load_from_bytes(content, file_type, filename)
        full_text = "\n\n".join(doc.page_content for doc in documents)

        # Step 2: Chunk and index for RAG
        chunks = self.splitter.split_documents(documents)
        if contract_id:
            self.vector_store.index_contract(contract_id, chunks)

        # Step 3: Extract clauses
        clauses = await run_clause_extraction(full_text)

        # Determine contract type from clauses or first-pass
        contract_type = self._infer_contract_type(clauses, full_text)
        clauses_json = json.dumps(clauses, indent=2)

        # Step 4: Risk analysis
        risks = await run_risk_analysis(
            clauses_json=clauses_json,
            contract_type=contract_type,
            user_role=user_role,
            context=full_text[:3000],  # first few pages for context
        )

        # Step 5: Plain-language explanations
        explanations = await run_simple_explanation(
            clauses_json=clauses_json,
            contract_type=contract_type,
            user_role=user_role,
        )

        # Step 6: Contract summary
        risk_context = json.dumps(risks.get("overall_risk", {}))
        summary = await run_contract_summary(
            contract_text=full_text,
            context=risk_context,
        )

        # Step 7: Negotiation advice (only for risky clauses)
        risky_clauses = [c for c in clauses if c.get("risk_score", 0) >= 6]
        # Also include clauses flagged by risk analysis
        risky_indices = {r["clause_index"] for r in risks.get("clause_risks", []) if r.get("score", 0) >= 6}
        risky_clauses += [c for c in clauses if c.get("index") in risky_indices and c not in risky_clauses]

        negotiations = {}
        if risky_clauses:
            counterparty = self._infer_counterparty(contract_type)
            power_dynamic = self._infer_power_dynamic(contract_type, user_role)

            negotiations = await run_negotiation_advice(
                clauses_json=json.dumps(risky_clauses, indent=2),
                contract_type=contract_type,
                user_role=user_role,
                counterparty_role=counterparty,
                power_dynamic=power_dynamic,
                risk_context=json.dumps(risks.get("clause_risks", [])),
            )

        elapsed_ms = int((time.time() - start_time) * 1000)

        return AnalysisResult(
            contract_text=full_text,
            clauses=clauses,
            risks=risks,
            explanations=explanations,
            summary=summary,
            negotiations=negotiations,
            metadata={
                "processing_ms": elapsed_ms,
                "page_count": len(documents),
                "word_count": len(full_text.split()),
                "chunk_count": len(chunks),
                "clause_count": len(clauses),
                "contract_type": contract_type,
            },
        )

    # ─────────────────────────────────────────────────────────────────────
    # RAG CHAT
    # ─────────────────────────────────────────────────────────────────────

    async def chat(
        self,
        contract_id: str,
        question: str,
        history: list[dict] | None = None,
        full_text: str | None = None,
    ) -> dict:
        """Answer a question about a contract using RAG.

        Args:
            contract_id: ID of the indexed contract
            question: User's question
            history: Previous messages [{"role": "user|assistant", "content": "..."}]
            full_text: Optional full contract text (used if vector store unavailable)

        Returns:
            {"answer": str, "sources": list[str]}
        """
        # Retrieve relevant chunks
        if self.vector_store.exists(contract_id):
            relevant_docs = self.vector_store.search(contract_id, question)
            context = "\n\n---\n\n".join(
                f"[Section: {doc.metadata.get('section_number', 'unknown')} | "
                f"Page: {doc.metadata.get('page', '?')}]\n{doc.page_content}"
                for doc in relevant_docs
            )
            sources = [
                {
                    "page": doc.metadata.get("page"),
                    "section": doc.metadata.get("section_number"),
                    "text": doc.page_content[:200],
                }
                for doc in relevant_docs
            ]
        elif full_text:
            # Fallback: use full text if it fits
            context = full_text[:50000]
            sources = []
        else:
            raise ValueError(f"No vector store found for contract {contract_id} and no full_text provided")

        # Format chat history
        chat_history = ""
        if history:
            chat_history = "\n".join(
                f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
                for m in history[-10:]  # last 10 messages for context
            )

        answer = await run_contract_chat(
            question=question,
            context=context,
            chat_history=chat_history,
        )

        return {"answer": answer, "sources": sources}

    # ─────────────────────────────────────────────────────────────────────
    # CONTRACT COMPARISON
    # ─────────────────────────────────────────────────────────────────────

    async def compare(
        self,
        text_a: str,
        text_b: str,
        title_a: str = "Contract A",
        title_b: str = "Contract B",
        user_role: str = "the person signing",
    ) -> dict:
        """Compare two contracts and return structured diff."""
        return await run_contract_comparison(
            contract_a_text=text_a,
            contract_b_text=text_b,
            title_a=title_a,
            title_b=title_b,
            user_role=user_role,
        )

    # ─────────────────────────────────────────────────────────────────────
    # INDIVIDUAL PIPELINE STAGES (for targeted re-runs)
    # ─────────────────────────────────────────────────────────────────────

    async def extract_clauses(self, text: str) -> list[dict]:
        """Run clause extraction only."""
        return await run_clause_extraction(text)

    async def analyze_risks(self, clauses: list[dict], contract_type: str, user_role: str, context: str = "") -> dict:
        """Run risk analysis only."""
        return await run_risk_analysis(
            clauses_json=json.dumps(clauses, indent=2),
            contract_type=contract_type,
            user_role=user_role,
            context=context,
        )

    async def explain_clauses(self, clauses: list[dict], contract_type: str, user_role: str) -> dict:
        """Run explanation generation only."""
        return await run_simple_explanation(
            clauses_json=json.dumps(clauses, indent=2),
            contract_type=contract_type,
            user_role=user_role,
        )

    async def summarize(self, text: str, context: str = "") -> dict:
        """Run summary generation only."""
        return await run_contract_summary(contract_text=text, context=context)

    async def negotiate(self, clauses: list[dict], contract_type: str, user_role: str, risk_context: str = "") -> dict:
        """Run negotiation advice only."""
        counterparty = self._infer_counterparty(contract_type)
        power_dynamic = self._infer_power_dynamic(contract_type, user_role)
        return await run_negotiation_advice(
            clauses_json=json.dumps(clauses, indent=2),
            contract_type=contract_type,
            user_role=user_role,
            counterparty_role=counterparty,
            power_dynamic=power_dynamic,
            risk_context=risk_context,
        )

    # ─────────────────────────────────────────────────────────────────────
    # VECTOR STORE MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────

    def index_document(self, contract_id: str, content: bytes, file_type: str, filename: str = "") -> int:
        """Index a document for RAG without running full analysis."""
        documents = self.loader.load_from_bytes(content, file_type, filename)
        chunks = self.splitter.split_documents(documents)
        return self.vector_store.index_contract(contract_id, chunks)

    def delete_index(self, contract_id: str):
        """Remove a contract's vector index."""
        self.vector_store.delete_contract(contract_id)

    # ─────────────────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────────────────────────────────────────────

    def _infer_contract_type(self, clauses: list[dict], text: str) -> str:
        """Infer contract type from extracted clauses and text patterns."""
        text_lower = text[:2000].lower()

        type_signals = {
            "employment": ["employee", "employer", "salary", "termination of employment", "work for hire"],
            "nda": ["confidential information", "non-disclosure", "receiving party", "disclosing party"],
            "lease": ["landlord", "tenant", "rent", "premises", "lease term"],
            "service_agreement": ["service provider", "deliverables", "scope of work", "statement of work"],
            "freelance": ["contractor", "independent contractor", "freelance", "project fees"],
            "saas": ["subscription", "software as a service", "user agreement", "terms of service"],
            "partnership": ["partners", "partnership", "profit sharing", "capital contribution"],
            "purchase": ["buyer", "seller", "purchase price", "closing date", "bill of sale"],
            "loan": ["lender", "borrower", "principal", "interest rate", "repayment"],
            "licensing": ["licensor", "licensee", "license grant", "royalt"],
        }

        scores = {}
        for contract_type, signals in type_signals.items():
            score = sum(1 for s in signals if s in text_lower)
            if score > 0:
                scores[contract_type] = score

        if scores:
            return max(scores, key=scores.get)
        return "general"

    def _infer_counterparty(self, contract_type: str) -> str:
        mapping = {
            "employment": "employer / HR department",
            "nda": "the other company's legal team",
            "lease": "landlord / property manager",
            "service_agreement": "the client's procurement team",
            "freelance": "the client",
            "saas": "the vendor (usually non-negotiable)",
            "partnership": "your potential partner",
            "purchase": "the seller",
            "loan": "the lender / bank",
            "licensing": "the licensor",
        }
        return mapping.get(contract_type, "the other party")

    def _infer_power_dynamic(self, contract_type: str, user_role: str) -> str:
        lower_power = {
            "employment": "They have more leverage (many candidates), but skilled workers can negotiate. Focus on non-standard terms.",
            "lease": "Landlord has leverage in competitive markets. Focus on terms that cost them nothing to change.",
            "saas": "Standard terms are usually non-negotiable for individuals. Enterprise plans can negotiate.",
            "loan": "Lender sets terms. You can shop around but rarely negotiate individual clauses.",
        }
        balanced = {
            "service_agreement": "Balanced — they need your service, you need the revenue. Both sides can push.",
            "freelance": "Relatively balanced. They chose you for a reason. Push on payment and liability.",
            "partnership": "Balanced — both parties need each other. Everything is negotiable.",
            "nda": "Usually balanced for mutual NDAs. One-way NDAs favor the discloser.",
        }
        if contract_type in lower_power:
            return lower_power[contract_type]
        if contract_type in balanced:
            return balanced[contract_type]
        return "Assess based on context — who needs this deal more?"
