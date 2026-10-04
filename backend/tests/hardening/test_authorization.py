"""
Authorization: candidate B must never read, modify or delete candidate A's
resources. A foreign id must look exactly like a missing one (404), so the
API is not an existence oracle.
"""
import uuid

import pytest
from sqlalchemy import text


async def _seed_alice_resources(client, act_as, alice, db_factory):
    act_as(alice)
    project = (await client.post("/projects", json={"name": "Search engine", "summary": "Built BM25"})).json()
    session = (await client.post("/sessions", json={"focus_area": "backend"})).json()
    app_ = (await client.post("/applications", json={"company": "Acme", "role": "SWE"})).json()
    item = (await client.post("/study/items", json={"topic": "Heaps", "prompt": "Explain heapify"})).json()
    job = (await client.post("/jobs", json={"company": "Acme", "role_title": "SWE", "description": "Build distributed systems in Go."})).json()
    files = {"file": ("cv.txt", b"Alice Example\nPython, Go, Kubernetes\n", "text/plain")}
    resume = (await client.post("/resumes", files=files)).json()

    # A resume claim + debrief row so nested endpoints have something to leak.
    async with db_factory() as s:
        version_id = str(uuid.uuid4())
        await s.execute(
            text("INSERT INTO resume_versions (id, resume_id, version_number) VALUES (:v, :r, 1)"),
            {"v": version_id, "r": resume["id"]},
        )
        claim_id = str(uuid.uuid4())
        await s.execute(
            text("INSERT INTO resume_claims (id, resume_version_id, claim_text, claim_type, verified_by_user) "
                 "VALUES (:c, :v, 'Python', 'skill', false)"),
            {"c": claim_id, "v": version_id},
        )
        await s.execute(
            text("INSERT INTO session_debriefs (id, session_id, strengths, weaknesses) VALUES (:d, :s, '[\"x\"]', '[]')"),
            {"d": str(uuid.uuid4()), "s": session["id"]},
        )
        await s.commit()
    return {
        "project": project["id"],
        "session": session["id"],
        "application": app_["id"],
        "study_item": item["id"],
        "job": job["id"],
        "resume": resume["id"],
        "claim": claim_id,
    }


@pytest.mark.asyncio
async def test_cross_candidate_access_is_denied_everywhere(api, alice, bob, db_factory):
    client, act_as = api
    ids = await _seed_alice_resources(client, act_as, alice, db_factory)

    act_as(bob)
    attempts = [
        ("GET", f"/projects/{ids['project']}", None),
        ("PATCH", f"/projects/{ids['project']}", {"name": "pwned"}),
        ("DELETE", f"/projects/{ids['project']}", None),
        ("GET", f"/sessions/{ids['session']}", None),
        ("GET", f"/sessions/{ids['session']}/turns", None),
        ("GET", f"/sessions/{ids['session']}/debrief", None),
        ("POST", f"/sessions/{ids['session']}/end", None),
        ("GET", f"/applications/{ids['application']}", None),
        ("PATCH", f"/applications/{ids['application']}", {"status": "rejected"}),
        ("DELETE", f"/applications/{ids['application']}", None),
        ("POST", f"/study/items/{ids['study_item']}/review", {"quality": 5}),
        ("GET", f"/jobs/{ids['job']}", None),
        ("DELETE", f"/jobs/{ids['job']}", None),
        ("GET", f"/resumes/{ids['resume']}", None),
        ("GET", f"/resumes/{ids['resume']}/facts", None),
        ("POST", f"/resumes/{ids['resume']}/facts/{ids['claim']}/confirm", None),
        ("PATCH", f"/resumes/{ids['resume']}/facts/{ids['claim']}", {"content": "pwned"}),
        ("POST", f"/resumes/{ids['resume']}/facts/{ids['claim']}/reject", None),
    ]
    for method, url, body in attempts:
        resp = await client.request(method, url, json=body)
        assert resp.status_code == 404, f"{method} {url} -> {resp.status_code} {resp.text}"
        assert resp.json()["code"] in ("not_found",), resp.json()

    # Bob cannot reference Alice's job when creating his own session/application.
    resp = await client.post("/sessions", json={"job_id": ids["job"]})
    assert resp.status_code == 404
    resp = await client.post("/applications", json={"company": "X", "role": "Y", "job_id": ids["job"]})
    assert resp.status_code == 404

    # Bob's list endpoints never include Alice's rows.
    for url in ("/projects", "/sessions", "/applications", "/study/items", "/jobs", "/resumes"):
        resp = await client.get(url)
        assert resp.status_code == 200, url
        assert resp.json()["items"] == [], f"{url} leaked {resp.json()['items']}"

    # Nothing of Alice's was modified or deleted by Bob's attempts.
    act_as(alice)
    project = (await client.get(f"/projects/{ids['project']}")).json()
    assert project["name"] == "Search engine"
    facts = (await client.get(f"/resumes/{ids['resume']}/facts")).json()
    assert [f["content"] for f in facts] == ["Python"] and facts[0]["verified_by_user"] is False
    assert (await client.get(f"/applications/{ids['application']}")).json()["status"] == "applied"
    assert (await client.get(f"/jobs/{ids['job']}")).status_code == 200


@pytest.mark.asyncio
async def test_owner_can_access_own_resources(api, alice, db_factory):
    client, act_as = api
    ids = await _seed_alice_resources(client, act_as, alice, db_factory)
    act_as(alice)
    assert (await client.get(f"/sessions/{ids['session']}")).status_code == 200
    resp = await client.post(f"/resumes/{ids['resume']}/facts/{ids['claim']}/confirm")
    assert resp.status_code == 200 and resp.json()["verified_by_user"] is True
    assert (await client.delete(f"/projects/{ids['project']}")).status_code == 204
    assert (await client.get(f"/projects/{ids['project']}")).status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_requests_are_rejected(api):
    client, act_as = api
    act_as(None)
    for url in ("/projects", "/sessions", "/resumes", "/study/items", "/applications", "/jobs", "/analytics/dashboard"):
        resp = await client.get(url)
        assert resp.status_code == 401, url
        assert resp.json()["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_malformed_ids_are_404_or_422_not_500(api, alice):
    client, act_as = api
    act_as(alice)
    assert (await client.get("/projects/not-a-uuid")).status_code == 422
    assert (await client.get(f"/projects/{uuid.uuid4()}")).status_code == 404
    resp = await client.get("/projects", params={"cursor": "garbage"})
    assert resp.status_code == 400 and resp.json()["code"] == "invalid_cursor"
