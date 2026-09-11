from __future__ import annotations

import logging
from dataclasses import dataclass
from io import BytesIO
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
    def __init__(
        self,
        message: str,
    ) -> None:
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
        self._embedding_model: (
            SentenceTransformer | None
        ) = None

        self._chroma_client: (
            chromadb.PersistentClient | None
        ) = None

    # ========================================================
    # INDEX RECORD
    # ========================================================

    def index_record(
        self,
        record_hash: str,
        pdf_content: bytes,
    ) -> None:
        """
        Index a medical record in ChromaDB.

        Chroma stores:

            embedding
            record_hash
            chunk_index

        Chroma does NOT store:

            PDF plaintext
            patient identity
            diagnosis
            IPFS CID
        """

        normalized_hash = (
            self._normalize_record_hash(
                record_hash
            )
        )

        text = self._extract_pdf_text(
            pdf_content
        )

        if not text:
            raise RagError(
                (
                    "No extractable text was "
                    "found in the PDF"
                )
            )

        chunks = self._chunk_text(
            text
        )

        if not chunks:
            raise RagError(
                (
                    "PDF did not produce any "
                    "indexable chunks"
                )
            )

        embeddings = self._encode_many(
            chunks
        )

        if len(embeddings) != len(chunks):
            raise RagError(
                (
                    "Embedding count does not "
                    "match chunk count"
                )
            )

        ids: list[str] = []

        metadatas: list[
            dict[str, Any]
        ] = []

        for chunk_index in range(
            len(chunks)
        ):
            ids.append(
                self._build_chunk_id(
                    record_hash=normalized_hash,
                    chunk_index=chunk_index,
                )
            )

            metadatas.append(
                {
                    "record_hash": (
                        normalized_hash
                    ),
                    "chunk_index": (
                        chunk_index
                    ),
                }
            )

        collection = (
            self._get_collection()
        )

        #
        # IMPORTANT:
        #
        # There is intentionally NO:
        #
        #     documents=...
        #
        # Plaintext medical text is not persisted
        # in ChromaDB.
        #
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info(
            (
                "Indexed %s chunks for "
                "medical record %s"
            ),
            len(chunks),
            normalized_hash,
        )

    # ========================================================
    # SEARCH
    # ========================================================

    async def search(
        self,
        query: str,
        top_k: int | None = None,
    ) -> tuple[
        str,
        list[dict[str, Any]],
    ]:
        """
        Semantic retrieval flow:

            query
                ↓
            query embedding
                ↓
            ChromaDB
                ↓
            record_hash + chunk_index
                ↓
            blockchain
                ↓
            IPFS CID
                ↓
            IPFS PDF
                ↓
            deterministic re-chunking
                ↓
            relevant plaintext chunk
                ↓
            Ollama
        """

        normalized_query = (
            query.strip()
        )

        if not normalized_query:
            raise RagError(
                "Search query cannot be empty"
            )

        requested_limit = (
            top_k
            if top_k is not None
            else settings.RAG_TOP_K
        )

        if requested_limit <= 0:
            raise RagError(
                (
                    "top_k must be greater "
                    "than zero"
                )
            )

        collection = (
            self._get_collection()
        )

        collection_size = (
            collection.count()
        )

        if collection_size == 0:
            return (
                (
                    "No indexed medical records "
                    "are currently available."
                ),
                [],
            )

        limit = min(
            requested_limit,
            collection_size,
        )

        query_embedding = (
            self._encode(
                normalized_query
            )
        )

        try:
            results = (
                collection.query(
                    query_embeddings=[
                        query_embedding
                    ],
                    n_results=limit,
                    include=[
                        "metadatas",
                        "distances",
                    ],
                )
            )

        except Exception as exc:
            raise RagError(
                (
                    "ChromaDB search failed: "
                    f"{exc}"
                )
            ) from exc

        result_ids = results.get(
            "ids"
        )

        if (
            not result_ids
            or not result_ids[0]
        ):
            return (
                (
                    "No relevant medical records "
                    "were found."
                ),
                [],
            )

        retrieved = (
            await self._process_search_results(
                results
            )
        )

        if not retrieved:
            return (
                (
                    "Relevant vector entries were "
                    "found, but no corresponding "
                    "blockchain-verified medical "
                    "records could be retrieved."
                ),
                [],
            )

        context = (
            self._build_context(
                retrieved
            )
        )

        answer = (
            await self._generate_answer(
                query=normalized_query,
                context=context,
            )
        )

        citations = [
            self._to_citation(
                item
            )
            for item in retrieved
        ]

        return (
            answer,
            citations,
        )

    # ========================================================
    # PROCESS VECTOR RESULTS
    # ========================================================

    async def _process_search_results(
        self,
        results: dict[str, Any],
    ) -> list[RetrievedChunk]:

        retrieved: list[
            RetrievedChunk
        ] = []

        ids = results.get(
            "ids",
            [[]],
        )[0]

        metadatas = results.get(
            "metadatas",
            [[]],
        )[0]

        distances = results.get(
            "distances",
            [[]],
        )[0]

        #
        # Request-local caches only.
        #
        # These prevent repeated network/PDF work when multiple
        # top-k chunks belong to the same medical record.
        #

        blockchain_cache: dict[
            str,
            dict[str, Any],
        ] = {}

        content_cache: dict[
            str,
            bytes,
        ] = {}

        chunks_cache: dict[
            str,
            list[str],
        ] = {}

        for result_position, result_id in enumerate(
            ids
        ):
            if result_position >= len(
                metadatas
            ):
                logger.warning(
                    (
                        "Chroma result %s is "
                        "missing metadata"
                    ),
                    result_id,
                )

                continue

            metadata = (
                metadatas[
                    result_position
                ]
            )

            if not metadata:
                logger.warning(
                    (
                        "Chroma result %s has "
                        "empty metadata"
                    ),
                    result_id,
                )

                continue

            raw_hash = metadata.get(
                "record_hash"
            )

            raw_chunk_index = (
                metadata.get(
                    "chunk_index"
                )
            )

            if raw_hash is None:
                logger.warning(
                    (
                        "Chroma result %s has no "
                        "record_hash"
                    ),
                    result_id,
                )

                continue

            if raw_chunk_index is None:
                logger.warning(
                    (
                        "Chroma result %s has no "
                        "chunk_index"
                    ),
                    result_id,
                )

                continue

            try:
                record_hash = (
                    self._normalize_record_hash(
                        str(raw_hash)
                    )
                )

                chunk_index = int(
                    raw_chunk_index
                )

            except (
                RagError,
                TypeError,
                ValueError,
            ) as exc:
                logger.warning(
                    (
                        "Invalid Chroma metadata "
                        "for %s: %s"
                    ),
                    result_id,
                    exc,
                )

                continue

            if chunk_index < 0:
                continue

            # ================================================
            # Blockchain resolution
            # ================================================

            try:
                if (
                    record_hash
                    in blockchain_cache
                ):
                    chain_record = (
                        blockchain_cache[
                            record_hash
                        ]
                    )

                else:
                    chain_record = (
                        blockchain_service
                        .get_record(
                            record_hash
                        )
                    )

                    blockchain_cache[
                        record_hash
                    ] = chain_record

            except BlockchainError as exc:
                logger.warning(
                    (
                        "Blockchain lookup failed "
                        "for %s: %s"
                    ),
                    record_hash,
                    exc.message,
                )

                continue

            returned_hash = (
                chain_record.get(
                    "record_hash",
                    "",
                )
            )

            try:
                returned_hash = (
                    self._normalize_record_hash(
                        str(returned_hash)
                    )
                )

            except RagError:
                logger.warning(
                    (
                        "Blockchain returned an "
                        "invalid hash for %s"
                    ),
                    record_hash,
                )

                continue

            if returned_hash != record_hash:
                logger.warning(
                    (
                        "Blockchain hash mismatch "
                        "for %s"
                    ),
                    record_hash,
                )

                continue

            ipfs_cid = str(
                chain_record.get(
                    "ipfs_cid",
                    "",
                )
            ).strip()

            if not ipfs_cid:
                logger.warning(
                    (
                        "Blockchain record %s "
                        "contains no IPFS CID"
                    ),
                    record_hash,
                )

                continue

            # ================================================
            # IPFS retrieval
            # ================================================

            try:
                if (
                    ipfs_cid
                    in content_cache
                ):
                    pdf_content = (
                        content_cache[
                            ipfs_cid
                        ]
                    )

                else:
                    pdf_content = (
                        await download_from_ipfs(
                            ipfs_cid
                        )
                    )

                    content_cache[
                        ipfs_cid
                    ] = pdf_content

            except PinataUploadError as exc:
                logger.warning(
                    (
                        "IPFS retrieval failed "
                        "for %s: %s"
                    ),
                    record_hash,
                    exc.message,
                )

                continue

            except Exception as exc:
                logger.warning(
                    (
                        "Unexpected IPFS retrieval "
                        "error for %s: %s"
                    ),
                    record_hash,
                    exc,
                )

                continue

            # ================================================
            # Recreate deterministic chunks
            # ================================================

            try:
                if (
                    record_hash
                    in chunks_cache
                ):
                    chunks = (
                        chunks_cache[
                            record_hash
                        ]
                    )

                else:
                    text = (
                        self._extract_pdf_text(
                            pdf_content
                        )
                    )

                    if not text:
                        logger.warning(
                            (
                                "Record %s contains "
                                "no extractable text"
                            ),
                            record_hash,
                        )

                        continue

                    chunks = (
                        self._chunk_text(
                            text
                        )
                    )

                    chunks_cache[
                        record_hash
                    ] = chunks

            except Exception as exc:
                logger.warning(
                    (
                        "Unable to recreate "
                        "chunks for %s: %s"
                    ),
                    record_hash,
                    exc,
                )

                continue

            if chunk_index >= len(
                chunks
            ):
                logger.warning(
                    (
                        "Chunk index %s is outside "
                        "record %s chunk range"
                    ),
                    chunk_index,
                    record_hash,
                )

                continue

            excerpt = (
                chunks[
                    chunk_index
                ].strip()
            )

            if not excerpt:
                continue

            # ================================================
            # Similarity score
            # ================================================

            distance = 0.0

            if (
                result_position
                < len(distances)
            ):
                try:
                    distance = float(
                        distances[
                            result_position
                        ]
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    distance = 0.0

            score = (
                self._distance_to_score(
                    distance
                )
            )

            retrieved.append(
                RetrievedChunk(
                    record_hash=record_hash,
                    ipfs_cid=ipfs_cid,
                    chunk_index=chunk_index,
                    score=score,
                    excerpt=excerpt,
                    blockchain_verified=True,
                    source="ipfs",
                )
            )

        return retrieved

    # ========================================================
    # CONTEXT
    # ========================================================

    def _build_context(
        self,
        retrieved: list[
            RetrievedChunk
        ],
    ) -> str:

        sections: list[str] = []

        for item in retrieved:
            section = "\n".join(
                [
                    (
                        "[Medical record "
                        f"{item.record_hash}]"
                    ),
                    (
                        "Chunk index: "
                        f"{item.chunk_index}"
                    ),
                    (
                        "Blockchain verified: "
                        f"{item.blockchain_verified}"
                    ),
                    "",
                    item.excerpt,
                ]
            )

            sections.append(
                section
            )

        return "\n\n---\n\n".join(
            sections
        )

    # ========================================================
    # OLLAMA
    # ========================================================

    async def _generate_answer(
        self,
        query: str,
        context: str,
    ) -> str:

        prompt = (
            "You are a medical-record retrieval assistant.\n\n"
            "Answer the doctor's question using ONLY the "
            "provided blockchain-verified medical-record "
            "context.\n\n"
            "Do not invent information that does not appear "
            "in the retrieved records.\n\n"
            "If the records do not contain enough information, "
            "say so clearly.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{query}\n\n"
            "Answer:"
        )

        payload = {
            "model": (
                settings.OLLAMA_MODEL
            ),
            "prompt": prompt,
            "stream": False,
        }

        endpoint = (
            f"{settings.OLLAMA_BASE_URL.rstrip('/')}"
            "/api/generate"
        )

        try:
            async with httpx.AsyncClient(
                timeout=(
                    settings.OLLAMA_TIMEOUT
                )
            ) as client:
                response = (
                    await client.post(
                        endpoint,
                        json=payload,
                    )
                )

        except httpx.TimeoutException as exc:
            raise RagError(
                "Ollama request timed out"
            ) from exc

        except httpx.HTTPError as exc:
            raise RagError(
                (
                    "Ollama request failed: "
                    f"{exc}"
                )
            ) from exc

        if response.status_code != 200:
            raise RagError(
                (
                    "Ollama returned HTTP "
                    f"{response.status_code}: "
                    f"{response.text}"
                )
            )

        try:
            payload = response.json()

        except ValueError as exc:
            raise RagError(
                (
                    "Ollama returned an "
                    "invalid JSON response"
                )
            ) from exc

        answer = str(
            payload.get(
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
    # CITATION
    # ========================================================

    def _to_citation(
        self,
        item: RetrievedChunk,
    ) -> dict[str, Any]:

        return {
            "record_hash": (
                item.record_hash
            ),
            "ipfs_cid": (
                item.ipfs_cid
            ),
            "chunk_index": (
                item.chunk_index
            ),
            "blockchain_verified": (
                item.blockchain_verified
            ),
            "score": round(
                item.score,
                4,
            ),
            "excerpt": (
                item.excerpt
            ),
            "source": (
                item.source
            ),
        }

    # ========================================================
    # EMBEDDINGS
    # ========================================================

    def _get_embedding_model(
        self,
    ) -> SentenceTransformer:

        if self._embedding_model is None:
            logger.info(
                (
                    "Loading embedding model: "
                    "%s"
                ),
                settings.EMBEDDING_MODEL,
            )

            self._embedding_model = (
                SentenceTransformer(
                    settings.EMBEDDING_MODEL
                )
            )

        return self._embedding_model

    def _encode(
        self,
        text: str,
    ) -> list[float]:

        model = (
            self._get_embedding_model()
        )

        embedding = (
            model.encode(
                text
            )
        )

        return embedding.tolist()

    def _encode_many(
        self,
        texts: list[str],
    ) -> list[
        list[float]
    ]:

        model = (
            self._get_embedding_model()
        )

        embeddings = (
            model.encode(
                texts
            )
        )

        return [
            embedding.tolist()
            for embedding
            in embeddings
        ]

    # ========================================================
    # CHROMA
    # ========================================================

    def _get_chroma_client(
        self,
    ) -> chromadb.PersistentClient:
        """
        Initialize Chroma relative to PROJECT_ROOT.

        Example:

            CHROMA_PERSIST_DIR=./data/chromadb

        always resolves to:

            <project-root>/data/chromadb

        rather than depending on the process working directory.
        """

        if self._chroma_client is None:
            persist_path = (
                settings.resolve_project_path(
                    settings.CHROMA_PERSIST_DIR
                )
            )

            persist_path.mkdir(
                parents=True,
                exist_ok=True,
            )

            logger.info(
                (
                    "Using ChromaDB persistence "
                    "directory: %s"
                ),
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

    def _get_collection(
        self,
    ):
        client = (
            self._get_chroma_client()
        )

        return (
            client.get_or_create_collection(
                name=COLLECTION_NAME
            )
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
                )

                page_text = (
                    page_text.strip()
                )

                if page_text:
                    pages.append(
                        page_text
                    )

            return "\n\n".join(
                pages
            ).strip()

        except Exception as exc:
            logger.warning(
                (
                    "PDF text extraction "
                    "failed: %s"
                ),
                exc,
            )

            return ""

    # ========================================================
    # DETERMINISTIC CHUNKING
    # ========================================================

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = (
            DEFAULT_CHUNK_SIZE
        ),
        overlap: int = (
            DEFAULT_CHUNK_OVERLAP
        ),
    ) -> list[str]:

        normalized_text = (
            text.strip()
        )

        if not normalized_text:
            return []

        if chunk_size <= 0:
            raise RagError(
                (
                    "Chunk size must be "
                    "greater than zero"
                )
            )

        if overlap < 0:
            raise RagError(
                (
                    "Chunk overlap cannot "
                    "be negative"
                )
            )

        if overlap >= chunk_size:
            raise RagError(
                (
                    "Chunk overlap must be "
                    "smaller than chunk size"
                )
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

            chunk = (
                normalized_text[
                    start:end
                ].strip()
            )

            if chunk:
                chunks.append(
                    chunk
                )

            if end >= text_length:
                break

            start += step

        return chunks

    # ========================================================
    # CHUNK IDENTIFIER
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
    # RECORD HASH
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
                (
                    "Record hash must be a "
                    "64-character SHA-256 hash"
                )
            )

        try:
            bytes.fromhex(
                normalized
            )

        except ValueError as exc:
            raise RagError(
                (
                    "Record hash contains "
                    "invalid hexadecimal "
                    "characters"
                )
            ) from exc

        return normalized

    # ========================================================
    # DISTANCE → DISPLAY SCORE
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


rag_service = RagService()