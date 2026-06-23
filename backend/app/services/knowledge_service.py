import asyncio
import logging

from openai import AsyncOpenAI

from app.config import ZHIPU_API_KEY, ZHIPU_BASE_URL, ZHIPU_EMBEDDING_MODEL, CHROMA_PERSIST_DIR

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(
    api_key=ZHIPU_API_KEY,
    base_url=ZHIPU_BASE_URL,
)

_chroma_client = None
_collection = None
_lock = asyncio.Lock()


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = _chroma_client.get_or_create_collection(
            name="mistakes",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _make_document(mistake) -> str:
    return (
        f"题目: {mistake.question_text}\n"
        f"学生答案: {mistake.student_answer}\n"
        f"正确答案: {mistake.correct_answer}\n"
        f"知识点: {mistake.topic or ''}\n"
        f"讲解: {mistake.explanation or ''}"
    )


async def _embed(texts: list[str]) -> list[list[float]]:
    resp = await _client.embeddings.create(
        model=ZHIPU_EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in resp.data]


async def add_mistake_to_kb(mistake) -> None:
    doc = _make_document(mistake)
    embeddings = await _embed([doc])

    async with _lock:
        col = _get_collection()
        col.upsert(
            ids=[f"mistake_{mistake.id}"],
            embeddings=embeddings,
            documents=[doc],
            metadatas=[{
                "user_id": mistake.user_id,
                # 多孩子隔离：0 表示无建档孩子（兼容旧数据）
                "student_id": mistake.student_id or 0,
                "subject": mistake.subject,
                "topic": mistake.topic or "",
                "mastery": mistake.mastery,
            }],
        )


async def update_mistake_in_kb(mistake) -> None:
    await add_mistake_to_kb(mistake)


async def remove_mistake_from_kb(mistake_id: int, user_id: int) -> None:
    async with _lock:
        col = _get_collection()
        col.delete(ids=[f"mistake_{mistake_id}"])


async def search_relevant_mistakes(
    user_id: int,
    query: str,
    subject: str | None = None,
    n_results: int = 5,
    student_id: int | None = None,
) -> list[dict]:
    query_embeddings = await _embed([query])

    # chromadb 1.x：单条件用扁平 dict，多条件必须用 $and 包裹
    conditions = [{"user_id": user_id}]
    if student_id is not None:
        conditions.append({"student_id": student_id})
    if subject:
        conditions.append({"subject": subject})
    where_filter = conditions[0] if len(conditions) == 1 else {"$and": conditions}

    col = _get_collection()
    results = col.query(
        query_embeddings=query_embeddings,
        n_results=n_results,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    items = []
    if results and results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            items.append({
                "id": int(doc_id.replace("mistake_", "")),
                "document": results["documents"][0][i],
                "distance": results["distances"][0][i],
                "question_text": "",
                "student_answer": "",
                "correct_answer": "",
                "topic": meta.get("topic", ""),
                "mastery": meta.get("mastery", 0),
            })
    return items
