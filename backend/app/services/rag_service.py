import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import chromadb
import httpx
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT, settings
from app.models.medical_record import MedicalRecord
from app.services.blockchain_service import blockchain_service
from app.services.pinata_service import download_from_ipfs

logger = logging.getLogger(__name__)

COLLECTION_NAME = "medical_records"


class RagError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass
class RetrievedRecord:
    record: MedicalRecord
    score: float
    excerpt: str
    blockchain_verified: bool
    source: str


class RagService:
    def __init__(self) -> None:
        self._embedding_model: SentenceTransformer | None = None
        self._chroma_client: chromadb.PersistentClient | None = None

    def index_record(self, record: MedicalRecord, pdf_content: bytes) -> None:
        text = self._extract_pdf_text(pdf_content)
        document = self._build_document(record.diagnosis, text)
        embedding = self._encode(document)

        collection = self._get_collection()
        collection.upsert(
            ids=[str(record.id)],
            documents=[document],
            embeddings=[embedding],
            metadatas=[
                {
                    "record_id": record.id,
                    "patient_id": record.patient_id,
                    "diagnosis": record.diagnosis,
                    "record_hash": record.record_hash,
                    "ipfs_cid": record.ipfs_cid or "",
                }
            ],
        )
        logger.info("Indexed medical record %s in ChromaDB", record.id)

    async def search(
        self,
        db: Session,
        query: str,
        top_k: int | None = None,
    ) -> tuple[str, list[dict]]:
        limit = top_k or settings.RAG_TOP_K
        query = query.strip()
        if not query:
            raise RagError("Search query cannot be empty")

        query_embedding = self._encode(query)
        collection = self._get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )

        if not results["ids"] or not results["ids"][0]:
            return "No relevant medical records were found.", []

        retrieved = await self._process_search_results(db, results)
        if not retrieved:
            return "No blockchain-verified records were available for this query.", []

        context = self._build_context(retrieved)
        answer = await self._generate_answer(query, context)
        citations = [self._to_citation(item) for item in retrieved]
        return answer, citations

    async def _process_search_results(
        self,
        db: Session,
        results: dict,
    ) -> list[RetrievedRecord]:
        retrieved: list[RetrievedRecord] = []

        for index, record_id_str in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][index]
            distance = results["distances"][0][index]
            document = results["documents"][0][index]
            score = 1 / (1 + distance)

            record = db.query(MedicalRecord).filter(MedicalRecord.id == int(metadata["record_id"])).first()
            if not record:
                logger.warning("Record %s missing from SQLite, skipping", metadata["record_id"])
                continue

            blockchain_verified = self._verify_on_chain(record)
            if blockchain_service.is_configured() and not blockchain_verified:
                logger.warning("Record %s failed blockchain verification, skipping", record.id)
                continue

            try:
                content, source = await self._fetch_record_content(record)
            except Exception as exc:
                logger.warning("Failed to fetch record %s content: %s", record.id, exc)
                continue

            excerpt = self._extract_pdf_text(content)[:500] if content else document[:500]

            retrieved.append(
                RetrievedRecord(
                    record=record,
                    score=score,
                    excerpt=excerpt.strip(),
                    blockchain_verified=blockchain_verified,
                    source=source,
                )
            )

        return retrieved

    def _verify_on_chain(self, record: MedicalRecord) -> bool:
        if not blockchain_service.is_configured():
            return True
        try:
            return blockchain_service.verify_record_hash(record.id, record.record_hash)
        except Exception as exc:
            logger.warning("Blockchain verification error for record %s: %s", record.id, exc)
            return False

    async def _fetch_record_content(self, record: MedicalRecord) -> tuple[bytes, str]:
        if record.ipfs_cid:
            try:
                content = await download_from_ipfs(record.ipfs_cid)
                return content, "pinata"
            except Exception as exc:
                logger.warning(
                    "Pinata download failed for record %s, falling back to local file: %s",
                    record.id,
                    exc,
                )

        local_path = PROJECT_ROOT / record.file_path
        if local_path.exists():
            return local_path.read_bytes(), "local"

        raise RagError(f"Unable to retrieve file content for record {record.id}")

    def _build_context(self, retrieved: list[RetrievedRecord]) -> str:
        sections: list[str] = []
        for item in retrieved:
            record = item.record
            sections.append(
                "\n".join(
                    [
                        f"[Record {record.id}]",
                        f"Patient ID: {record.patient_id}",
                        f"Diagnosis: {record.diagnosis}",
                        f"Source: {item.source}",
                        f"Blockchain verified: {item.blockchain_verified}",
                        f"Content excerpt:\n{item.excerpt}",
                    ]
                )
            )
        return "\n\n---\n\n".join(sections)

    async def _generate_answer(self, query: str, context: str) -> str:
        prompt = (
            "You are a medical records assistant. Answer the doctor's question using only "
            "the provided context from verified medical records. If the context is "
            "insufficient, clearly state that.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query}\n\n"
            "Answer:"
        )

        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise RagError("Ollama request timed out") from exc
        except httpx.HTTPError as exc:
            raise RagError(f"Ollama request failed: {exc}") from exc

        if response.status_code != 200:
            raise RagError(f"Ollama returned status {response.status_code}: {response.text}")

        data = response.json()
        answer = data.get("response", "").strip()
        if not answer:
            raise RagError("Ollama returned an empty response")
        return answer

    def _to_citation(self, item: RetrievedRecord) -> dict:
        record = item.record
        return {
            "record_id": record.id,
            "patient_id": record.patient_id,
            "diagnosis": record.diagnosis,
            "record_hash": record.record_hash,
            "ipfs_cid": record.ipfs_cid,
            "blockchain_verified": item.blockchain_verified,
            "score": round(item.score, 4),
            "excerpt": item.excerpt,
            "source": item.source,
        }

    def _get_embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return self._embedding_model

    def _encode(self, text: str) -> list[float]:
        model = self._get_embedding_model()
        return model.encode(text).tolist()

    def _get_chroma_client(self) -> chromadb.PersistentClient:
        if self._chroma_client is None:
            Path(settings.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        return self._chroma_client

    def _get_collection(self):
        client = self._get_chroma_client()
        return client.get_or_create_collection(name=COLLECTION_NAME)

    def _extract_pdf_text(self, content: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages).strip()
        except Exception as exc:
            logger.warning("PDF text extraction failed: %s", exc)
            return ""

    def _build_document(self, diagnosis: str, pdf_text: str) -> str:
        if pdf_text:
            return f"Diagnosis: {diagnosis}\n\n{pdf_text}"
        return f"Diagnosis: {diagnosis}"


rag_service = RagService()
