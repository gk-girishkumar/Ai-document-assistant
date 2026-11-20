"""Integration tests for conversations, messages, and cross-user isolation."""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_conversations(client: AsyncClient, test_user):
    user, token = test_user
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post(
        "/api/conversations",
        headers=headers,
        json={"title": "Test Chat"},
    )
    assert create_resp.status_code == 201
    convo_id = create_resp.json()["id"]

    list_resp = await client.get("/api/conversations", headers=headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(c["id"] == convo_id for c in items)


@pytest.mark.asyncio
async def test_cross_user_conversation_isolation(client: AsyncClient, test_user, test_user_2):
    user1, token1 = test_user
    user2, token2 = test_user_2

    # User 1 creates conversation
    create_resp = await client.post(
        "/api/conversations",
        headers={"Authorization": f"Bearer {token1}"},
        json={"title": "Private Discussion"},
    )
    convo_id = create_resp.json()["id"]

    # User 2 attempts to view User 1's conversation -> 403
    get_resp = await client.get(
        f"/api/conversations/{convo_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert get_resp.status_code == 403

    # User 2 attempts to post message to User 1's conversation -> 403
    msg_resp = await client.post(
        f"/api/conversations/{convo_id}/messages",
        headers={"Authorization": f"Bearer {token2}"},
        json={"content": "Unauthorized intrusion attempt"},
    )
    assert msg_resp.status_code == 403
