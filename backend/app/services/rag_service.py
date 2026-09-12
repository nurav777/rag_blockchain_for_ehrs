from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import chromadb
import httpx
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.services.blockchain_service import (
    BlockchainError,
    blockchain_service,
)
from app.services.pinata_service import (
    PinataUploadError,
    download_from_ipfs,
)


logger = logging.getLogger(__name__)

COLLECTION_NAME = "medical_records"

DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 200


# ============================================================
# EXCEPTIONS
# ============================================================


class RagError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


# ============================================================
# RETRIEVED CHUNK
# ============================================================


@dataclass
class RetrievedChunk:
    record_hash: str
    ipfs_cid: str
    chunk_index: int
    score: float
    excerpt: str
    blockchain_verified: bool
    source: str


# ============================================================
# RAG SERVICE
# ============================================================


class RagService:
    def __init__(self) -> None:
        self._embedding_model: SentenceTransformer | None = None
        self._chroma_client: chromadb.PersistentClient | None = None

    # ========================================================
    # INDEX RECORD
    # ========================================================

    def index_record(
        self,
        record_hash: str,
        pdf_content: bytes,
    ) -> int:
        """
        Extract text from PDF and store embeddings in Chroma.

        Chroma stores:
        - embedding
        - record_hash
        - chunk_index

        Plaintext medical text is not stored in Chroma.
        """

        normalized_hash = self._normalize_record_hash(
            record_hash
        )

        text = self._extract_pdf_text(
            pdf_content
        )

        if not text:
            raise RagError(
                "No extractable text found in PDF"
            )

        chunks = self._chunk_text(
            text
        )

        if not chunks:
            raise RagError(
                "No chunks were generated from PDF"
            )

        model = self._get_embedding_model()

        embeddings = model.encode(
            chunks,
            convert_to_numpy=True,
        ).tolist()

        collection = self._get_collection()

        ids: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for index in range(len(chunks)):
            ids.append(
                self._build_chunk_id(
                    normalized_hash,
                    index,
                )
            )

            metadatas.append(
                {
                    "record_hash": normalized_hash,
                    "chunk_index": index,
                }
            )

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info(
            "Indexed %s chunks for record %s",
            len(chunks),
            normalized_hash,
        )

        return len(chunks)

    # ========================================================
    # CHECK IF RECORD ALREADY EXISTS
    # ========================================================

    def has_record(
        self,
        record_hash: str,
    ) -> bool:
        """
        Return True if at least one Chroma chunk already exists
        for the supplied record hash.
        """

        normalized_hash = self._normalize_record_hash(
            record_hash
        )

        collection = self._get_collection()

        try:
            result = collection.get(
                where={
                    "record_hash": normalized_hash
                },
                limit=1,
                include=["metadatas"],
            )

        except Exception as exc:
            raise RagError(
                f"Unable to inspect Chroma index: {exc}"
            ) from exc

        ids = result.get("ids")

        return bool(ids)

    # ========================================================
    # CLEAR INDEX
    # ========================================================

    def clear_index(self) -> None:
        """
        Delete the Chroma collection.

        Only intended for explicit full rebuilds.
        """

        client = self._get_chroma_client()

        try:
            client.delete_collection(
                COLLECTION_NAME
            )

        except Exception:
            pass

    # ========================================================
    # SEARCH
    # ========================================================

    async def search(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:

        normalized_query = query.strip()

        if not normalized_query:
            raise RagError(
                "Search query cannot be empty"
            )

        limit = (
            top_k
            if top_k is not None
            else settings.RAG_TOP_K
        )

        if limit <= 0:
            raise RagError(
                "top_k must be greater than zero"
            )

        model = self._get_embedding_model()

        query_embedding = model.encode(
            [normalized_query],
            convert_to_numpy=True,
        )[0].tolist()

        collection = self._get_collection()

        count = collection.count()

        if count == 0:
            return []

        result = collection.query(
            query_embeddings=[
                query_embedding
            ],
            n_results=min(
                limit,
                count,
            ),
            include=[
                "metadatas",
                "distances",
            ],
        )

        metadata_rows = (
            result.get("metadatas")
            or [[]]
        )

        distance_rows = (
            result.get("distances")
            or [[]]
        )

        if not metadata_rows:
            return []

        metadatas = (
            metadata_rows[0]
            or []
        )

        distances = (
            distance_rows[0]
            if distance_rows
            else []
        )

        retrieved: list[RetrievedChunk] = []

        record_cache: dict[
            str,
            tuple[
                str,
                list[str],
                bool,
            ],
        ] = {}

        for position, metadata in enumerate(
            metadatas
        ):
            if not metadata:
                continue

            record_hash = str(
                metadata.get(
                    "record_hash",
                    "",
                )
            ).strip()

            if not record_hash:
                continue

            try:
                chunk_index = int(
                    metadata.get(
                        "chunk_index",
                        -1,
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

            if chunk_index < 0:
                continue

            if record_hash not in record_cache:
                try:
                    (
                        ipfs_cid,
                        chunks,
                        verified,
                    ) = await self._retrieve_record_chunks(
                        record_hash
                    )

                except (
                    BlockchainError,
                    PinataUploadError,
                    RagError,
                ) as exc:
                    logger.warning(
                        "Unable to retrieve record %s: %s",
                        record_hash,
                        exc,
                    )

                    continue

                record_cache[
                    record_hash
                ] = (
                    ipfs_cid,
                    chunks,
                    verified,
                )

            (
                ipfs_cid,
                chunks,
                verified,
            ) = record_cache[
                record_hash
            ]

            if chunk_index >= len(chunks):
                logger.warning(
                    "Chunk %s for record %s no longer exists",
                    chunk_index,
                    record_hash,
                )

                continue

            distance = (
                float(
                    distances[position]
                )
                if position < len(distances)
                else 0.0
            )

            retrieved.append(
                RetrievedChunk(
                    record_hash=record_hash,
                    ipfs_cid=ipfs_cid,
                    chunk_index=chunk_index,
                    score=self._distance_to_score(
                        distance
                    ),
                    excerpt=chunks[
                        chunk_index
                    ],
                    blockchain_verified=verified,
                    source="ipfs",
                )
            )

        return retrieved

    # ========================================================
    # ANSWER
    # ========================================================

    async def answer(
        self,
        query: str,
        top_k: int | None = None,
    ) -> tuple[
        str,
        list[RetrievedChunk],
    ]:

        chunks = await self.search(
            query=query,
            top_k=top_k,
        )

        if not chunks:
            return (
                (
                    "I could not find relevant "
                    "medical-record evidence "
                    "for that query."
                ),
                [],
            )

        context_parts: list[str] = []

        for index, chunk in enumerate(
            chunks,
            start=1,
        ):
            context_parts.append(
                (
                    f"[Source {index}]\n"
                    f"Record hash: {chunk.record_hash}\n"
                    f"IPFS CID: {chunk.ipfs_cid}\n"
                    f"Chunk index: {chunk.chunk_index}\n"
                    f"Blockchain verified: "
                    f"{chunk.blockchain_verified}\n"
                    f"Content:\n"
                    f"{chunk.excerpt}"
                )
            )

        context = "\n\n".join(
            context_parts
        )

        prompt = (
            "You are a medical-record retrieval assistant.\n\n"
            "Answer the user's question using only the "
            "supplied record context.\n"
            "Do not invent facts that are not present "
            "in the context.\n"
            "If the context is insufficient, say that "
            "clearly.\n\n"
            f"Question:\n{query}\n\n"
            f"Context:\n{context}\n\n"
            "Answer:"
        )

        answer = await self._call_ollama(
            prompt
        )

        return (
            answer,
            chunks,
        )

    # ========================================================
    # BLOCKCHAIN -> IPFS RECORD RETRIEVAL
    # ========================================================

    async def _retrieve_record_chunks(
        self,
        record_hash: str,
    ) -> tuple[
        str,
        list[str],
        bool,
    ]:

        record = blockchain_service.get_record(
            record_hash
        )

        ipfs_cid = str(
            record["ipfs_cid"]
        ).strip()

        if not ipfs_cid:
            raise RagError(
                "Blockchain record does not contain an IPFS CID"
            )

        verified = (
            blockchain_service
            .verify_record_hash(
                record_hash
            )
        )

        pdf_content = await download_from_ipfs(
            ipfs_cid
        )

        text = self._extract_pdf_text(
            pdf_content
        )

        if not text:
            raise RagError(
                "Unable to extract text from IPFS PDF"
            )

        chunks = self._chunk_text(
            text
        )

        if not chunks:
            raise RagError(
                "No chunks could be reconstructed "
                "from the IPFS record"
            )

        return (
            ipfs_cid,
            chunks,
            verified,
        )

    # ========================================================
    # OLLAMA
    # ========================================================

    async def _call_ollama(
        self,
        prompt: str,
    ) -> str:

        url = (
            settings.OLLAMA_BASE_URL.rstrip("/")
            + "/api/generate"
        )

        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(
                timeout=settings.OLLAMA_TIMEOUT
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                )

        except httpx.TimeoutException as exc:
            raise RagError(
                "Ollama request timed out"
            ) from exc

        except httpx.HTTPError as exc:
            raise RagError(
                f"Unable to communicate with Ollama: {exc}"
            ) from exc

        if response.status_code != 200:
            raise RagError(
                (
                    "Ollama returned status "
                    f"{response.status_code}: "
                    f"{response.text}"
                )
            )

        try:
            response_payload = response.json()

        except ValueError as exc:
            raise RagError(
                "Ollama returned invalid JSON"
            ) from exc

        answer = str(
            response_payload.get(
                "response",
                "",
            )
        ).strip()

        if not answer:
            raise RagError(
                "Ollama returned an empty response"
            )

        return answer

    # ========================================================
    # EMBEDDING MODEL
    # ========================================================

    def _get_embedding_model(
        self,
    ) -> SentenceTransformer:

        if self._embedding_model is None:
            logger.info(
                "Loading embedding model: %s",
                settings.EMBEDDING_MODEL,
            )

            self._embedding_model = SentenceTransformer(
                settings.EMBEDDING_MODEL
            )

        return self._embedding_model

    # ========================================================
    # CHROMA CLIENT
    # ========================================================

    def _get_chroma_client(
        self,
    ) -> chromadb.PersistentClient:

        if self._chroma_client is None:
            PROJECT_ROOT = Path(__file__).resolve().parents[3]

            persist_path = Path(settings.CHROMA_PERSIST_DIR)

            if not persist_path.is_absolute():
                persist_path = PROJECT_ROOT / persist_path

            persist_path.mkdir(parents=True, exist_ok=True)

            logger.info(
                "Using ChromaDB persistence directory: %s",
                persist_path,
            )

            self._chroma_client = (
                chromadb.PersistentClient(
                    path=str(
                        persist_path
                    )
                )
            )

        return self._chroma_client

    def _get_collection(self):
        client = self._get_chroma_client()

        return client.get_or_create_collection(
            name=COLLECTION_NAME
        )

    # ========================================================
    # PDF EXTRACTION
    # ========================================================

    def _extract_pdf_text(
        self,
        content: bytes,
    ) -> str:

        try:
            reader = PdfReader(
                BytesIO(
                    content
                )
            )

            pages: list[str] = []

            for page in reader.pages:
                page_text = (
                    page.extract_text()
                    or ""
                ).strip()

                if page_text:
                    pages.append(
                        page_text
                    )

            extracted = "\n\n".join(
                pages
            ).strip()

            return self._redact_identity_lines(
                extracted
            )

        except Exception as exc:
            logger.warning(
                "PDF text extraction failed: %s",
                exc,
            )

            return ""

    # ========================================================
    # LEGACY PATIENT NAME REDACTION
    # ========================================================

    def _redact_identity_lines(
        self,
        text: str,
    ) -> str:
        """
        Redact legacy synthetic Patient: name lines before
        embedding or sending text to the LLM.

        Replacement keeps the same character count so old
        deterministic chunk positions remain stable.
        """

        pattern = re.compile(
            r"(?im)^(\s*Patient\s*:\s*)([^\r\n]*)"
        )

        def replace(
            match: re.Match[str],
        ) -> str:
            prefix = match.group(1)
            value = match.group(2)

            return (
                prefix
                + ("*" * len(value))
            )

        return pattern.sub(
            replace,
            text,
        )

    # ========================================================
    # CHUNKING
    # ========================================================

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> list[str]:

        normalized_text = text.strip()

        if not normalized_text:
            return []

        if chunk_size <= 0:
            raise RagError(
                "Chunk size must be greater than zero"
            )

        if overlap < 0:
            raise RagError(
                "Chunk overlap cannot be negative"
            )

        if overlap >= chunk_size:
            raise RagError(
                "Chunk overlap must be smaller than chunk size"
            )

        chunks: list[str] = []

        start = 0
        text_length = len(
            normalized_text
        )

        step = (
            chunk_size
            - overlap
        )

        while start < text_length:
            end = min(
                start + chunk_size,
                text_length,
            )

            chunk = normalized_text[
                start:end
            ].strip()

            if chunk:
                chunks.append(
                    chunk
                )

            if end >= text_length:
                break

            start += step

        return chunks

    # ========================================================
    # CHUNK ID
    # ========================================================

    def _build_chunk_id(
        self,
        record_hash: str,
        chunk_index: int,
    ) -> str:

        return (
            f"{record_hash}:"
            f"{chunk_index}"
        )

    # ========================================================
    # HASH NORMALIZATION
    # ========================================================

    def _normalize_record_hash(
        self,
        record_hash: str,
    ) -> str:

        normalized = (
            record_hash
            .strip()
            .lower()
            .removeprefix("0x")
        )

        if len(normalized) != 64:
            raise RagError(
                "Record hash must be a "
                "64-character SHA-256 hash"
            )

        try:
            bytes.fromhex(
                normalized
            )

        except ValueError as exc:
            raise RagError(
                "Record hash contains invalid "
                "hexadecimal characters"
            ) from exc

        return normalized

    # ========================================================
    # DISTANCE -> SCORE
    # ========================================================

    def _distance_to_score(
        self,
        distance: float,
    ) -> float:

        if distance < 0:
            distance = 0.0

        return (
            1.0
            / (
                1.0
                + distance
            )
        )


# ============================================================
# SHARED SERVICE INSTANCE
# ============================================================

rag_service = RagService()