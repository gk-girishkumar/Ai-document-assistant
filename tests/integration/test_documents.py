"""Integration tests for document upload, listing, access control, and cross-user security."""

import io
import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_document(client: AsyncClient, test_user):
    user, token = test_user
    headers = {"Authorization": f"Bearer {token}"}

    file_content = b"This is a test document text content for upload verification."
    files = {"file": ("test_doc.txt", file_content, "text/plain")}

    response = await client.post("/api/documents", headers=headers, files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test_doc.txt"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_upload_unsupported_type(client: AsyncClient, test_user):
    user, token = test_user
    headers = {"Authorization": f"Bearer {token}"}

    files = {"file": ("script.sh", b"echo 'hack'", "application/x-sh")}
    response = await client.post("/api/documents", headers=headers, files=files)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient, test_user):
    user, token = test_user
    headers = {"Authorization": f"Bearer {token}"}

    files = {"file": ("sample.txt", b"Sample text content.", "text/plain")}
    await client.post("/api/documents", headers=headers, files=files)

    response = await client.get("/api/documents", headers=headers)
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) >= 1
    assert docs[0]["filename"] == "sample.txt"


@pytest.mark.asyncio
async def test_cross_user_document_isolation(client: AsyncClient, test_user, test_user_2):
    # User 1 uploads document
    user1, token1 = test_user
    user2, token2 = test_user_2

    files = {"file": ("user1_secret.txt", b"Confidential notes.", "text/plain")}
    upload_resp = await client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token1}"},
        files=files,
    )
    doc_id = upload_resp.json()["id"]

    # User 2 attempts to read User 1's document -> must be 403 Forbidden!
    resp = await client.get(
        f"/api/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 403

    # User 2 attempts to delete User 1's document -> must be 403 Forbidden!
    del_resp = await client.delete(
        f"/api/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert del_resp.status_code == 403
