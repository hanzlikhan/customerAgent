"""Vector index for DukaanAI (Phase 1).

One Chroma collection per business: ``business_<id>``, persisted under
<repo>/data/chroma/. Embeddings come from the multilingual
sentence-transformer in config (local, free, CPU).

Every catalog item and policy is indexed TWICE: one English chunk, one
Roman-Urdu chunk. Each chunk is self-contained (carries its own price /
facts) so retrieval never needs to join chunks.

Chroma returns cosine *distance*; we convert to similarity (1 - distance)
so the 0.40 SIMILARITY_THRESHOLD in config reads naturally.
"""

import json
import shutil
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction,
)

from . import config, db

REPO_ROOT = Path(__file__).resolve().parent.parent
CHROMA_DIR = REPO_ROOT / "data" / "chroma"

_embedding_fn = None


def _get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=config.EMBEDDING_MODEL
        )
    return _embedding_fn


def _get_client() -> chromadb.PersistentClient:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _collection_name(business_id: int) -> str:
    return f"business_{business_id}"


def _fmt_price(price: float) -> str:
    # "3,450" style formatting used identically in EN and UR chunks.
    return f"{price:,.0f}"


def _item_chunks(item) -> list[tuple[str, dict]]:
    """Two chunks (EN + UR) for one catalog item row."""
    try:
        variants = json.loads(item["variants_json"] or "{}")
    except (json.JSONDecodeError, TypeError):
        variants = {}
    colors_en = variants.get("en", "")
    colors_ur = variants.get("ur", "")
    en = (
        f"PRODUCT: {item['name_en']}. "
        f"Price: {_fmt_price(item['price'])} PKR {item['unit']}. "
        f"Colors: {colors_en}. Category: {item['category']}."
    )
    ur = (
        f"PRODUCT (Urdu): {item['name_ur_roman']}. "
        f"Keemat: {_fmt_price(item['price'])} rupay {item['unit']}. "
        f"Rang: {colors_ur}. Category: {item['category']}."
    )
    meta_base = {
        "business_id": item["business_id"],
        "ref_id": item["id"],
        "kind": "item",
    }
    return [
        (en, {**meta_base, "lang": "en"}),
        (ur, {**meta_base, "lang": "ur"}),
    ]


def _policy_chunks(policy) -> list[tuple[str, dict]]:
    en = f"SHOP POLICY ({policy['type']}): {policy['text_en']}"
    ur = f"DUKAN POLICY ({policy['type']}): {policy['text_ur_roman']}"
    meta_base = {
        "business_id": policy["business_id"],
        "ref_id": policy["id"],
        "kind": "policy",
    }
    return [
        (en, {**meta_base, "lang": "en"}),
        (ur, {**meta_base, "lang": "ur"}),
    ]


def build_index(business_id: int) -> int:
    """(Re)build the vector index for a business. Returns chunk count."""
    client = _get_client()
    name = _collection_name(business_id)
    try:
        client.delete_collection(name)
    except Exception:
        pass  # fresh start is fine

    collection = client.get_or_create_collection(
        name=name, embedding_function=_get_embedding_fn()
    )

    chunks: list[tuple[str, dict]] = []
    for item in db.list_catalog_items(business_id):
        chunks.extend(_item_chunks(item))
    for policy in db.list_policies(business_id):
        chunks.extend(_policy_chunks(policy))

    ids = [f"{c[1]['kind']}_{c[1]['ref_id']}_{c[1]['lang']}" for c in chunks]
    collection.add(
        ids=ids,
        documents=[c[0] for c in chunks],
        metadatas=[c[1] for c in chunks],
    )
    return len(chunks)


def count_chunks(business_id: int) -> int:
    """Chunks in the persisted index; 0 when the collection is missing."""
    try:
        client = _get_client()
        collection = client.get_collection(
            name=_collection_name(business_id),
            embedding_function=_get_embedding_fn(),
        )
        return collection.count()
    except Exception:
        return 0


def retrieve(business_id: int, query: str, k: int = 5) -> list[dict]:
    """Return top-k chunks as {text, metadata, similarity} (similarity 0..1)."""
    client = _get_client()
    collection = client.get_collection(
        name=_collection_name(business_id),
        embedding_function=_get_embedding_fn(),
    )
    res = collection.query(query_texts=[query], n_results=k)
    out = []
    for text, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        out.append({
            "text": text,
            "metadata": meta,
            "similarity": round(1.0 - float(dist), 4),
        })
    return out


def wipe_index() -> None:
    """Delete all persisted vector data (used by the seed script)."""
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
