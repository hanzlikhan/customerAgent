"""LangGraph agentic core for DukaanAI (Phase 2).

State machine:
  ingest -> detect_language -> retrieve -> GATE1 -> abstain | answer
  answer -> verifier -> GATE2 -> abstain | respond   (abstain/respond terminal)

The two gates are the product:
  GATE1: retrieval similarity below threshold  -> no evidence, abstain.
  GATE2: model emitted NEED_ABSTAIN, or any cited claim fails the
         entailment check                        -> do not trust, abstain.
"""

import json
import re
from typing import TypedDict

from langgraph.graph import END, StateGraph

from . import config, db, index, llm

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    business_id: int
    business_name: str
    user_text: str
    customer_ref: str | None
    lang: str                       # "en" | "ur" | "mixed"
    chunks: list                    # retrieve() output: text/metadata/similarity
    max_score: float
    draft_answer: str
    cited_claims: list              # [{claim, chunk_idx}]
    verdicts: list                  # [{claim, chunk_idx, verdict}]
    final_reply: str
    abstained: bool
    escalation_id: int | None
    conversation_id: int | None


# ---------------------------------------------------------------------------
# Language detection (rule-based: fast, free, no LLM call)
# ---------------------------------------------------------------------------

_URDU_TOKENS = {
    "nahi", "nahin", "nai", "ni", "hai", "hein", "hain", "kya", "kia",
    "kitne", "kitna", "kitni", "ka", "ki", "ke", "ko", "mein", "me",
    "apki", "apka", "aap", "dukan", "kapra", "kapde", "kapday",
    "keemat", "qeemat", "timing", "batao", "bataen", "bataein",
    "chahiye", "wala", "wali", "walay", "mujhe", "hum", "tum", "aur",
    "kahan", "kidhar", "kese", "kaise", "kab", "kaun", "kitnay", "rupay",
    "rupy", "paisay", "sasta", "mehnga", "acha", "achi", "achay",
}

def _has_urdu_script(text: str) -> bool:
    return any(0x0600 <= ord(ch) <= 0x06FF for ch in text)


def detect_lang(text: str) -> str:
    """Return 'en', 'ur', or 'mixed' for a customer message."""
    if _has_urdu_script(text):
        return "ur"
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    hits = sum(1 for t in tokens if t in _URDU_TOKENS)
    if hits >= 2:
        return "ur"
    if hits == 1:
        return "mixed"
    return "en"


_LANG_INSTRUCTION = {
    "en": "English",
    "ur": "Roman Urdu, exactly as Pakistanis type it on WhatsApp",
    "mixed": "the same mix of English and Roman Urdu the customer used",
}

_ABSTAIN_TEXT = {
    "en": ("I don't have verified information on this, so I won't guess "
           "— the shop owner will confirm shortly."),
    "ur": ("Mujhe is baare mein tasdeeq shuda maloomat nahi hain, is liye "
           "main andaza nahi lagaunga — dukan ke malik jald tasdeeq kar ke "
           "jawab dein ge."),
    "mixed": ("Mujhe is ki verified maloomat nahi hain so I won't guess — "
              "shop owner jald confirm kar ke jawab dein ge."),
}

# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def n_ingest(state: AgentState) -> dict:
    text = (state["user_text"] or "").strip()
    biz = db.get_business(state["business_id"])
    if biz is None:
        raise ValueError(f"Unknown business_id={state['business_id']}")
    return {"user_text": text, "business_name": biz["name"]}


def n_detect_language(state: AgentState) -> dict:
    return {"lang": detect_lang(state["user_text"])}


def n_retrieve(state: AgentState) -> dict:
    chunks = index.retrieve(state["business_id"], state["user_text"], k=5)
    max_score = max((c["similarity"] for c in chunks), default=0.0)
    return {"chunks": chunks, "max_score": round(max_score, 4)}


def route_gate1(state: AgentState) -> str:
    if state["max_score"] < config.SIMILARITY_THRESHOLD:
        return "abstain"
    return "answer"


def _numbered_context(chunks: list) -> str:
    return "\n\n".join(
        f"[{i+1}] {c['text']}" for i, c in enumerate(chunks)
    )


def n_answer(state: AgentState) -> dict:
    system = (
        f"You are the WhatsApp receptionist for {state['business_name']}, "
        "a shop in Faisalabad. Answer the customer using ONLY the numbered "
        "context chunks below.\n"
        "Rules:\n"
        "1. Every factual claim (price, timing, product detail) MUST end "
        "with [n] citing the chunk number it came from. Use plain ASCII "
        "square brackets like [1] — never any other bracket style.\n"
        "2. Use ONLY information present in the chunks. Never infer, round, "
        "or invent anything.\n"
        "3. If the chunks do not contain the answer, reply with exactly: "
        "NEED_ABSTAIN and nothing else.\n"
        f"4. Reply in {_LANG_INSTRUCTION[state['lang']]}.\n"
        "5. Keep it short, like a WhatsApp message."
    )
    user = (
        f"Context:\n{_numbered_context(state['chunks'])}\n\n"
        f"Customer: {state['user_text']}"
    )
    draft = llm.chat(user, system_prompt=system, max_tokens=600)
    return {"draft_answer": draft}


_CITE_GROUP_RE = re.compile(r"((?:\[\s*\d+\s*\](?:\s*[,/&]|and)?\s*)+)")


def _extract_claims(draft: str, n_chunks: int, cap: int = 4) -> list:
    """One {claim, chunk_idx, chunk_indices} per cited segment in the draft.

    Handles:
      - ASCII [n] and full-width CJK brackets 【n】
      - Spaces inside brackets [ 1 ]
      - Adjacent/compound citations like [1][2], [1], [2], or [1] and [2]
    """
    draft = draft.replace("\u3010", "[").replace("\u3011", "]")
    draft = re.sub(r"\[\s*(\d+)\s*\]", r"[\1]", draft)
    parts = _CITE_GROUP_RE.split(draft)
    claims = []
    for i in range(1, len(parts), 2):
        cite_str = parts[i]
        prev_text = parts[i - 1].strip()
        seg = prev_text.split("\n")[-1].strip(" .!?,-;۔")
        indices = [
            int(n) for n in re.findall(r"\[\s*(\d+)\s*\]", cite_str)
            if 1 <= int(n) <= n_chunks
        ]
        if indices and seg:
            claims.append({
                "claim": seg,
                "chunk_idx": indices[0],
                "chunk_indices": indices,
            })
        if len(claims) >= cap:
            break
    return claims


_JUDGE_SYSTEM = (
    "You are a strict fact-checker for a bilingual (English / Roman Urdu) "
    "shop catalog. Treat standard English and Roman Urdu equivalents as "
    "matching (e.g. Peer = Monday, Jumma = Friday, rupay = PKR, dukan = shop). "
    "Reply with exactly one word: SUPPORTED, CONTRADICTED, or UNVERIFIABLE."
)


def n_verifier(state: AgentState) -> dict:
    claims = _extract_claims(
        state.get("draft_answer", ""), len(state["chunks"])
    )
    verdicts = []
    for item in claims:
        chunk_indices = item.get("chunk_indices", [item["chunk_idx"]])
        chunk_text = "\n\n".join(
            state["chunks"][i - 1]["text"] for i in chunk_indices
        )
        raw = llm.chat(
            f"Claim: {item['claim']}\n\nSource chunk:\n{chunk_text}\n\n"
            "Does the source support the claim? One word only.",
            system_prompt=_JUDGE_SYSTEM,
            max_tokens=100,  # gpt-oss spends tokens on reasoning; 20 starves it
        )
        m = re.search(r"\b(SUPPORTED|CONTRADICTED|UNVERIFIABLE)\b", raw.upper())
        verdict = m.group(1) if m else "UNVERIFIABLE"
        verdicts.append({
            "claim": item["claim"],
            "chunk_idx": item["chunk_idx"],
            "verdict": verdict,
        })
    return {"cited_claims": claims, "verdicts": verdicts}


def route_gate2(state: AgentState) -> str:
    draft = (state.get("draft_answer") or "").strip()
    if not draft:
        return "abstain"
    if "need_abstain" in draft.lower() or "need abstain" in draft.lower():
        return "abstain"
    verdicts = state.get("verdicts", [])
    if not verdicts:
        # Zero verified claims: do not pass ungrounded hallucination
        return "abstain"
    bad = [v for v in verdicts
           if v["verdict"] in ("CONTRADICTED", "UNVERIFIABLE")]
    if bad:
        return "abstain"
    return "respond"


def n_abstain(state: AgentState) -> dict:
    reply = _ABSTAIN_TEXT.get(state["lang"], _ABSTAIN_TEXT["en"])
    conv_id = db.add_conversation(
        state["business_id"],
        customer_ref=state.get("customer_ref") or "phase2-test",
        language=state["lang"],
    )
    db.add_message(conv_id, "in", state["user_text"],
                   retrieved_chunk_ids=[
                       c["metadata"].get("ref_id") for c in state["chunks"]
                   ])
    db.add_message(conv_id, "out", reply, verdict="ABSTAINED")
    esc_id = db.add_escalation(
        state["business_id"], state["user_text"], conversation_id=conv_id
    )
    return {"final_reply": reply, "abstained": True,
            "escalation_id": esc_id, "conversation_id": conv_id}


def n_respond(state: AgentState) -> dict:
    reply = state["draft_answer"].replace("NEED_ABSTAIN", "").strip()
    conv_id = db.add_conversation(
        state["business_id"],
        customer_ref=state.get("customer_ref") or "phase2-test",
        language=state["lang"],
    )
    db.add_message(conv_id, "in", state["user_text"],
                   retrieved_chunk_ids=[
                       c["metadata"].get("ref_id") for c in state["chunks"]
                   ])
    db.add_message(conv_id, "out", reply,
                   verdict=json.dumps(state.get("verdicts", []),
                                      ensure_ascii=False))
    return {"final_reply": reply, "abstained": False,
            "escalation_id": None, "conversation_id": conv_id}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_graph():
    g = StateGraph(AgentState)
    g.add_node("ingest", n_ingest)
    g.add_node("detect_language", n_detect_language)
    g.add_node("retrieve", n_retrieve)
    g.add_node("answer", n_answer)
    g.add_node("verifier", n_verifier)
    g.add_node("abstain", n_abstain)
    g.add_node("respond", n_respond)
    g.set_entry_point("ingest")
    g.add_edge("ingest", "detect_language")
    g.add_edge("detect_language", "retrieve")
    g.add_conditional_edges(
        "retrieve", route_gate1, {"abstain": "abstain", "answer": "answer"}
    )
    g.add_edge("answer", "verifier")
    g.add_conditional_edges(
        "verifier", route_gate2, {"abstain": "abstain", "respond": "respond"}
    )
    g.add_edge("abstain", END)
    g.add_edge("respond", END)
    return g.compile()


_GRAPH = None


def run_agent(business_id: int, user_text: str,
              customer_ref: str | None = None) -> dict:
    """Run one customer message through the agent. Returns full state."""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return dict(_GRAPH.invoke({
        "business_id": business_id,
        "user_text": user_text,
        "customer_ref": customer_ref,
    }))
