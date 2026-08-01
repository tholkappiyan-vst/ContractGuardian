"""Contract-aware text splitting: splits on clause boundaries, not arbitrary chunks."""
import re
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.ai_engine.config import get_ai_settings


# Patterns that indicate clause boundaries in legal documents (priority order)
CLAUSE_SEPARATORS = [
    # Article/Section headers
    r"\n(?=ARTICLE\s+[IVXLCDM\d]+)",
    r"\n(?=SECTION\s+\d+)",
    r"\n(?=CLAUSE\s+\d+)",
    # Numbered sections: "1.", "1.1", "1.1.1"
    r"\n(?=\d+\.\d+\.\d+[\.\)]\s)",
    r"\n(?=\d+\.\d+[\.\)]\s)",
    r"\n(?=\d+[\.\)]\s+[A-Z])",
    # Lettered subsections
    r"\n(?=\([a-z]\)\s)",
    r"\n(?=\([ivx]+\)\s)",
    # ALL CAPS headings (likely section titles)
    r"\n(?=[A-Z][A-Z\s]{10,}\n)",
    # Double newlines (paragraph boundary)
    "\n\n",
    # Single newline
    "\n",
    # Space (last resort)
    " ",
]


class ContractTextSplitter:
    """Splits contract text respecting clause boundaries."""

    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        settings = get_ai_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        self._splitter = RecursiveCharacterTextSplitter(
            separators=CLAUSE_SEPARATORS,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            is_separator_regex=True,
        )

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Split documents into clause-aware chunks."""
        chunks = self._splitter.split_documents(documents)

        # Enrich metadata with chunk position info
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["chunk_total"] = len(chunks)
            # Detect if this chunk starts with a section number
            section = self._detect_section_number(chunk.page_content)
            if section:
                chunk.metadata["section_number"] = section

        return chunks

    def split_text(self, text: str) -> list[str]:
        """Split raw text into chunks."""
        return self._splitter.split_text(text)

    def _detect_section_number(self, text: str) -> str | None:
        """Extract section number from start of chunk if present."""
        patterns = [
            r"^(ARTICLE\s+[IVXLCDM\d]+)",
            r"^(SECTION\s+\d+(?:\.\d+)*)",
            r"^(\d+(?:\.\d+)*)[.\)]\s",
        ]
        for pattern in patterns:
            match = re.match(pattern, text.strip(), re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None


class ClauseSegmenter:
    """Higher-level segmentation: splits contract into individual clauses for classification."""

    SECTION_PATTERN = re.compile(
        r"(?:^|\n)("
        r"(?:ARTICLE|SECTION|CLAUSE)\s+[IVXLCDM\d]+[.:]\s*.*?"
        r"|"
        r"\d+(?:\.\d+)*[.)]\s+[A-Z].*?"
        r"|"
        r"[A-Z][A-Z\s]{10,}"
        r")(?=\n)",
        re.MULTILINE,
    )

    def segment(self, text: str) -> list[dict]:
        """Segment full contract text into individual clauses.

        Returns list of {"index": int, "title": str|None, "section_number": str|None, "body": str}
        """
        # Find all section headers
        matches = list(self.SECTION_PATTERN.finditer(text))

        if not matches:
            # No clear structure — split on double newlines
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            return [
                {"index": i, "title": None, "section_number": None, "body": p}
                for i, p in enumerate(paragraphs)
            ]

        clauses = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            header = match.group(1).strip()

            section_num = self._extract_section_number(header)
            title = self._extract_title(header, section_num)

            clauses.append({
                "index": i,
                "title": title,
                "section_number": section_num,
                "body": body,
            })

        return clauses

    def _extract_section_number(self, header: str) -> str | None:
        num_match = re.match(r"(?:ARTICLE|SECTION|CLAUSE)\s+([IVXLCDM\d]+)", header, re.IGNORECASE)
        if num_match:
            return num_match.group(1)
        num_match = re.match(r"(\d+(?:\.\d+)*)", header)
        if num_match:
            return num_match.group(1)
        return None

    def _extract_title(self, header: str, section_num: str | None) -> str | None:
        # Remove section prefix to get title
        cleaned = re.sub(r"^(?:ARTICLE|SECTION|CLAUSE)\s+[IVXLCDM\d]+[.:]\s*", "", header, flags=re.IGNORECASE)
        cleaned = re.sub(r"^\d+(?:\.\d+)*[.)]\s*", "", cleaned)
        return cleaned.strip() if cleaned.strip() else None
