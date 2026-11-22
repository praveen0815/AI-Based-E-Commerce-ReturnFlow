"""Knowledge document upload, processing, and tenant isolation."""

from __future__ import annotations

import io
import time
import zipfile

import pytest
from fastapi.testclient import TestClient

from tests.auth_helpers import auth_headers, create_store, register
from tests.commerce_helpers import setup_customer

pytestmark = pytest.mark.usefixtures("isolated_auth")

_TEXT = b"# Return policy\n\nItems may be returned within 30 days.\n"
_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<<>>endobj\n"
    b"2 0 obj<</Length 44>>stream\n"
    b"BT /F1 12 Tf 100 700 Td (Return within 30 days) Tj ET\n"
    b"endstream\nendobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 2 0 R>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n"
    b"trailer<</Root 1 0 R/Size 4>>\nstartxref\n9\n%%EOF\n"
)


def _minimal_docx(text: str = "Return within 30 days") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "word/document.xml",
            f'<?xml version="1.0"?>'
            f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>",
        )
        archive.writestr("[Content_Types].xml", "<Types></Types>")
    return buffer.getvalue()


def _wait_processed(client: TestClient, token: str, store_id: str, document_id: str) -> dict:
    for _ in range(60):
        response = client.get(
            f"/api/v1/stores/current/knowledge/documents/{document_id}",
            headers=auth_headers(token, store_id),
        )
        assert response.status_code == 200, response.text
        payload = response.json()["data"]
        if payload["processing_status"] in {"PROCESSED", "FAILED"}:
            return payload
        time.sleep(0.05)
    raise AssertionError("Document did not finish processing")


def test_upload_list_and_delete_txt(client: TestClient) -> None:
    setup = register(client, "knowledge-owner@example.com", "Owner")
    store = create_store(client, setup["token"]["access_token"], "Knowledge Store")
    token = setup["token"]["access_token"]
    store_id = store["id"]

    upload = client.post(
        "/api/v1/stores/current/knowledge/documents",
        headers=auth_headers(token, store_id),
        files={"file": ("policy.md", _TEXT, "text/markdown")},
        data={"document_type": "RETURN_POLICY"},
    )
    assert upload.status_code == 201, upload.text
    document_id = upload.json()["data"]["id"]

    processed = _wait_processed(client, token, store_id, document_id)
    assert processed["processing_status"] == "PROCESSED"
    assert "30 days" in (processed["extracted_text"] or "")

    listing = client.get(
        "/api/v1/stores/current/knowledge/documents",
        headers=auth_headers(token, store_id),
    )
    assert listing.status_code == 200
    assert listing.json()["data"]["total"] == 1
    assert listing.json()["data"]["items"][0]["original_filename"] == "policy.md"

    deleted = client.delete(
        f"/api/v1/stores/current/knowledge/documents/{document_id}",
        headers=auth_headers(token, store_id),
    )
    assert deleted.status_code == 200
    assert client.get(
        f"/api/v1/stores/current/knowledge/documents/{document_id}",
        headers=auth_headers(token, store_id),
    ).status_code == 404


def test_rejects_invalid_extension_and_content(client: TestClient) -> None:
    setup = register(client, "invalid-knowledge@example.com", "Owner")
    store = create_store(client, setup["token"]["access_token"], "Invalid Files")
    headers = auth_headers(setup["token"]["access_token"], store["id"])

    bad_ext = client.post(
        "/api/v1/stores/current/knowledge/documents",
        headers=headers,
        files={"file": ("policy.exe", b"data", "application/octet-stream")},
        data={"document_type": "CUSTOM"},
    )
    assert bad_ext.status_code == 400
    assert bad_ext.json()["error"]["code"] == "unsupported_format"

    fake_pdf = client.post(
        "/api/v1/stores/current/knowledge/documents",
        headers=headers,
        files={"file": ("policy.pdf", b"NOTPDF", "application/pdf")},
        data={"document_type": "CUSTOM"},
    )
    assert fake_pdf.status_code == 400
    assert fake_pdf.json()["error"]["code"] == "invalid_file_content"


def test_customer_cannot_upload_but_support_can_read(client: TestClient) -> None:
    owner = register(client, "k-cust-owner@example.com", "Owner")
    store = create_store(client, owner["token"]["access_token"], "Role Store")
    customer = setup_customer(client, owner["token"]["access_token"], store["id"], "k-cust")

    denied = client.post(
        "/api/v1/stores/current/knowledge/documents",
        headers=auth_headers(customer["token"], store["id"]),
        files={"file": ("sop.txt", b"Handle returns gently", "text/plain")},
        data={"document_type": "STORE_SOP"},
    )
    assert denied.status_code == 403

    owner_upload = client.post(
        "/api/v1/stores/current/knowledge/documents",
        headers=auth_headers(owner["token"]["access_token"], store["id"]),
        files={"file": ("sop.txt", b"Handle returns gently", "text/plain")},
        data={"document_type": "STORE_SOP"},
    )
    assert owner_upload.status_code == 201

    register(client, "k-support@example.com", "Support")
    added = client.post(
        "/api/v1/stores/current/members",
        headers=auth_headers(owner["token"]["access_token"], store["id"]),
        json={"email": "k-support@example.com", "role": "SUPPORT_AGENT"},
    )
    assert added.status_code == 201
    from tests.auth_helpers import login

    support = login(client, "k-support@example.com")
    listing = client.get(
        "/api/v1/stores/current/knowledge/documents",
        headers=auth_headers(support["token"]["access_token"], store["id"]),
    )
    assert listing.status_code == 200
    assert listing.json()["data"]["total"] == 1


def test_tenant_isolation(client: TestClient) -> None:
    owner_a = register(client, "tenant-a@example.com", "Owner A")
    store_a = create_store(client, owner_a["token"]["access_token"], "Store A")
    owner_b = register(client, "tenant-b@example.com", "Owner B")
    store_b = create_store(client, owner_b["token"]["access_token"], "Store B")

    upload = client.post(
        "/api/v1/stores/current/knowledge/documents",
        headers=auth_headers(owner_a["token"]["access_token"], store_a["id"]),
        files={"file": ("private.txt", b"Store A only", "text/plain")},
        data={"document_type": "CUSTOM"},
    )
    document_id = upload.json()["data"]["id"]

    foreign = client.get(
        f"/api/v1/stores/current/knowledge/documents/{document_id}",
        headers=auth_headers(owner_b["token"]["access_token"], store_b["id"]),
    )
    assert foreign.status_code == 404


def test_reprocess_after_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    setup = register(client, "reprocess@example.com", "Owner")
    store = create_store(client, setup["token"]["access_token"], "Reprocess Store")
    headers = auth_headers(setup["token"]["access_token"], store["id"])

    from app.services import knowledge as knowledge_service

    original = knowledge_service.extract_text

    def boom(_content: bytes, ext: str):
        raise ValueError("Simulated extractor failure")

    monkeypatch.setattr(knowledge_service, "extract_text", boom)

    upload = client.post(
        "/api/v1/stores/current/knowledge/documents",
        headers=headers,
        files={"file": ("notes.txt", b"Plain text", "text/plain")},
        data={"document_type": "CUSTOM"},
    )
    document_id = upload.json()["data"]["id"]
    failed = _wait_processed(client, setup["token"]["access_token"], store["id"], document_id)
    assert failed["processing_status"] == "FAILED"
    assert failed["error_message"]

    monkeypatch.setattr(knowledge_service, "extract_text", original)
    client.post(f"/api/v1/stores/current/knowledge/documents/{document_id}/reprocess", headers=headers)
    fixed = _wait_processed(client, setup["token"]["access_token"], store["id"], document_id)
    assert fixed["processing_status"] == "PROCESSED"
    assert "Plain text" in (fixed["extracted_text"] or "")


def test_docx_upload(client: TestClient) -> None:
    setup = register(client, "docx@example.com", "Owner")
    store = create_store(client, setup["token"]["access_token"], "Docx Store")
    headers = auth_headers(setup["token"]["access_token"], store["id"])

    upload = client.post(
        "/api/v1/stores/current/knowledge/documents",
        headers=headers,
        files={
            "file": (
                "warranty.docx",
                _minimal_docx("Warranty valid one year"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        data={"document_type": "WARRANTY"},
    )
    assert upload.status_code == 201
    document_id = upload.json()["data"]["id"]
    processed = _wait_processed(client, setup["token"]["access_token"], store["id"], document_id)
    assert processed["processing_status"] == "PROCESSED"
    assert "Warranty" in (processed["extracted_text"] or "")