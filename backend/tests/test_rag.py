"""RAG chunking, indexing, retrieval, and policy assistant."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.services.rag.chunking import chunk_document_text
from tests.auth_helpers import auth_headers, create_store, register

pytestmark = pytest.mark.usefixtures("isolated_auth")

_POLICY = (
    "Return policy\n\n"
    "Items may be returned within 30 days of delivery in original condition.\n"
    "Refunds are issued to the original payment method within 5 business days."
)


def _wait_processed(client: TestClient, token: str, store_id: str, document_id: str) -> None:
    for _ in range(60):
        response = client.get(
            f"/api/v1/stores/current/knowledge/documents/{document_id}",
            headers=auth_headers(token, store_id),
        )
        assert response.status_code == 200
        if response.json()["data"]["processing_status"] in {"PROCESSED", "FAILED"}:
            return
        time.sleep(0.05)
    raise AssertionError("processing timeout")


def _upload_processed(client: TestClient, token: str, store_id: str) -> str:
    upload = client.post(
        "/api/v1/stores/current/knowledge/documents",
        headers=auth_headers(token, store_id),
        files={"file": ("returns.txt", _POLICY.encode("utf-8"), "text/plain")},
        data={"document_type": "RETURN_POLICY"},
    )
    assert upload.status_code == 201
    document_id = upload.json()["data"]["id"]
    _wait_processed(client, token, store_id, document_id)
    return document_id


def test_chunking_overlap_and_metadata() -> None:
    text = "Alpha paragraph.\n\n" + ("Beta sentence. " * 40)
    chunks = chunk_document_text(text, chunk_size=120, chunk_overlap=20, page_count=2)
    assert len(chunks) > 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].section_label == "Section 1"
    assert chunks[0].page_hint is not None


def test_index_search_ask_and_citations(client: TestClient) -> None:
    setup = register(client, "rag-owner@example.com", "Owner")
    store = create_store(client, setup["token"]["access_token"], "RAG Store")
    token = setup["token"]["access_token"]
    store_id = store["id"]
    _upload_processed(client, token, store_id)

    indexed = client.post(
        "/api/v1/stores/current/knowledge/rag/reindex",
        headers=auth_headers(token, store_id),
        json={},
    )
    assert indexed.status_code == 200
    assert indexed.json()["data"]["indexed"] == 1

    search = client.post(
        "/api/v1/stores/current/knowledge/rag/search",
        headers=auth_headers(token, store_id),
        json={"query": "returned within 30 days", "top_k": 3},
    )
    assert search.status_code == 200
    hits = search.json()["data"]["hits"]
    assert hits
    assert hits[0]["citation"]["original_filename"] == "returns.txt"
    assert hits[0]["score"] >= 0

    ask = client.post(
        "/api/v1/stores/current/knowledge/rag/ask",
        headers=auth_headers(token, store_id),
        json={"question": "What is the return window?", "top_k": 3},
    )
    assert ask.status_code == 200
    body = ask.json()["data"]
    assert body["grounded"] is True
    assert body["citations"]
    assert "30 days" in body["citations"][0]["excerpt"] or "30 days" in body["answer"]
    assert body["model"] == "mock-policy-llm"


def test_tenant_isolation_for_retrieval(client: TestClient) -> None:
    owner_a = register(client, "rag-a@example.com", "A")
    store_a = create_store(client, owner_a["token"]["access_token"], "Store A")
    owner_b = register(client, "rag-b@example.com", "B")
    store_b = create_store(client, owner_b["token"]["access_token"], "Store B")
    _upload_processed(client, owner_a["token"]["access_token"], store_a["id"])
    client.post(
        "/api/v1/stores/current/knowledge/rag/reindex",
        headers=auth_headers(owner_a["token"]["access_token"], store_a["id"]),
        json={},
    )

    foreign = client.post(
        "/api/v1/stores/current/knowledge/rag/search",
        headers=auth_headers(owner_b["token"]["access_token"], store_b["id"]),
        json={"query": "30 days return", "top_k": 3},
    )
    assert foreign.status_code == 200
    assert foreign.json()["data"]["total"] == 0


def test_delete_index_and_uncertain_answer(client: TestClient) -> None:
    setup = register(client, "rag-del@example.com", "Owner")
    store = create_store(client, setup["token"]["access_token"], "Delete Store")
    token = setup["token"]["access_token"]
    store_id = store["id"]
    _upload_processed(client, token, store_id)
    client.post("/api/v1/stores/current/knowledge/rag/reindex", headers=auth_headers(token, store_id), json={})

    deleted = client.delete("/api/v1/stores/current/knowledge/rag/index", headers=auth_headers(token, store_id))
    assert deleted.status_code == 200

    ask = client.post(
        "/api/v1/stores/current/knowledge/rag/ask",
        headers=auth_headers(token, store_id),
        json={"question": "What is the return window?"},
    )
    assert ask.json()["data"]["grounded"] is False
    assert "could not find" in ask.json()["data"]["answer"].lower()


def test_feedback_saved(client: TestClient) -> None:
    setup = register(client, "rag-fb@example.com", "Owner")
    store = create_store(client, setup["token"]["access_token"], "Feedback Store")
    response = client.post(
        "/api/v1/stores/current/knowledge/rag/feedback",
        headers=auth_headers(setup["token"]["access_token"], store["id"]),
        json={"helpful": True, "question": "Window?", "answer_excerpt": "30 days"},
    )
    assert response.status_code == 201