"""Smoke tests for the question bank API routes."""
import pytest


def test_domains_requires_auth(test_client):
    resp = test_client.get("/api/v1/questions/domains")
    assert resp.status_code in (401, 403)


def test_questions_requires_auth(test_client):
    resp = test_client.get("/api/v1/questions")
    assert resp.status_code in (401, 403)


def test_readiness_requires_auth(test_client):
    resp = test_client.get("/api/v1/readiness")
    assert resp.status_code in (401, 403)


def test_readiness_plan_requires_auth(test_client):
    resp = test_client.get("/api/v1/readiness/plan")
    assert resp.status_code in (401, 403)


def test_create_question_requires_auth(test_client):
    resp = test_client.post("/api/v1/questions", json={
        "domain_code": "DSA",
        "difficulty": "medium",
        "title": "Two Sum",
        "body": "Given an array, return two indices that add to target.",
    })
    assert resp.status_code in (401, 403)
