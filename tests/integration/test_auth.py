"""Integration tests for user registration, authentication, login, logout, and token security."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    payload = {
        "email": "newuser@example.com",
        "password": "SecurePassword123!",
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user):
    user, _ = test_user
    payload = {
        "email": user.email,
        "password": "AnotherPassword123!",
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    payload = {
        "email": "weak@example.com",
        "password": "weak",
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    user, _ = test_user
    payload = {
        "email": user.email,
        "password": "StrongP@ssw0rd!",
    }
    response = await client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    user, _ = test_user
    payload = {
        "email": user.email,
        "password": "WrongPassword123!",
    }
    response = await client.post("/api/auth/login", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, test_user):
    user, token = test_user
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user.email


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/api/users/me")
    assert response.status_code == 401
