from dotenv import load_dotenv
load_dotenv()

import uuid
import chromadb
from core.diff_parser import parse_diff
from core.models import ReviewResult, Severity
from agents.review_agent import run_security_pass, run_correctness_pass
from agents.standards_agent import run_standards_pass
from agents.diff_analyzer import analyze_diff
from agents.pr_description import generate_pr_description

# ────────SQL INJECTION DIFF──────────────────────────
# Violations: f-string SQL query, hardcoded key, function named "f"
# ────────────────────────────────────────────────────
SQL_INJECTION_DIFF = """diff --git a/auth.py b/auth.py
--- a/auth.py
+++ b/auth.py
@@ -1,0 +1,10 @@
+API_KEY = "sk-prod-1234567890abcdef"
+
+def f(user_id):
+    user = db.query(f"SELECT * FROM users WHERE id = {user_id}")
+    order = db.query(f"SELECT * FROM orders WHERE user_id = {user_id}")
+    return user
"""

# ────────CLEAN PYTHON DIFF──────────────────────────
# No violations — well-written Python
# ───────────────────────────────────────────────────
CLEAN_PYTHON_DIFF = """diff --git a/users/service.py b/users/service.py
--- a/users/service.py
+++ b/users/service.py
@@ -1,0 +1,12 @@
+import logging
+from db import session
+
+logger = logging.getLogger(__name__)
+
+def get_user_by_id(user_id: int) -> dict | None:
+    try:
+        return session.query("SELECT id, name FROM users WHERE id = %s", (user_id,))
+    except Exception as e:
+        logger.error("Failed to fetch user %s: %s", user_id, e)
+        return None
"""

# ────────N+1 QUERY DIFF─────────────────────────────
# Violation: DB query inside a loop
# ───────────────────────────────────────────────────
N_PLUS_ONE_DIFF = """diff --git a/reports.py b/reports.py
--- a/reports.py
+++ b/reports.py
@@ -1,0 +1,10 @@
+def get_order_summaries(user_ids):
+    summaries = []
+    for user_id in user_ids:
+        orders = db.query("SELECT * FROM orders WHERE user_id = %s", (user_id,))
+        total = sum(o.amount for o in orders)
+        summaries.append({"user_id": user_id, "total": total})
+    return summaries
"""

SEED_PATTERNS = [
    "Functions use snake_case naming: get_user, create_order, validate_token",
    "Error handling always wraps DB calls in try/except with logger.error()",
    "Imports follow order: stdlib → third-party → internal core modules",
]


def _seed_collection() -> chromadb.Collection:
    client = chromadb.EphemeralClient()
    collection = client.create_collection(name=f"repo_patterns_{uuid.uuid4().hex[:8]}")
    collection.add(ids=["p1", "p2", "p3"], documents=SEED_PATTERNS)
    return collection


def _print_result(result: ReviewResult):
    print(f"  pass:    {result.pass_name}")
    print(f"  summary: {result.summary}")
    for comment in result.comments:
        print(f"\n  [{comment.severity.value.upper()}] {comment.file}:{comment.line}")
        print(f"  {comment.message}")


# ── Security ──────────────────────────────────────

def test_security_catches_sql_injection():
    print("\n[eval] security catches SQL injection...")
    result = run_security_pass(parse_diff(SQL_INJECTION_DIFF))

    assert isinstance(result, ReviewResult)
    critical_comments = [c for c in result.comments if c.severity == Severity.CRITICAL]
    assert len(critical_comments) >= 1, "Expected at least 1 CRITICAL comment for SQL injection"

    _print_result(result)


def test_security_no_false_positive_clean_code():
    print("\n[eval] security no false positive on clean code...")
    result = run_security_pass(parse_diff(CLEAN_PYTHON_DIFF))

    assert isinstance(result, ReviewResult)
    critical_comments = [c for c in result.comments if c.severity == Severity.CRITICAL]
    assert len(critical_comments) == 0, f"Expected 0 CRITICAL comments for clean code, got {len(critical_comments)}"

    _print_result(result)


# ── Correctness ───────────────────────────────────

def test_correctness_catches_n_plus_one():
    print("\n[eval] correctness catches N+1 query...")
    result = run_correctness_pass(parse_diff(N_PLUS_ONE_DIFF))

    assert isinstance(result, ReviewResult)
    assert len(result.comments) >= 1, "Expected at least 1 comment for N+1 query pattern"

    _print_result(result)


def test_correctness_no_false_positive_clean_code():
    print("\n[eval] correctness no false positive on clean code...")
    result = run_correctness_pass(parse_diff(CLEAN_PYTHON_DIFF))

    assert isinstance(result, ReviewResult)
    assert isinstance(result.summary, str) and len(result.summary) > 0

    _print_result(result)


# ── Standards ─────────────────────────────────────

def test_standards_catches_bad_naming():
    print("\n[eval] standards catches bad naming (function 'f')...")
    collection = _seed_collection()
    result = run_standards_pass(parse_diff(SQL_INJECTION_DIFF), collection)

    assert isinstance(result, ReviewResult)
    assert len(result.comments) >= 1, "Expected at least 1 comment for non-snake_case function name"

    _print_result(result)


def test_standards_severity_never_critical():
    print("\n[eval] standards severity is never CRITICAL...")
    collection = _seed_collection()
    result = run_standards_pass(parse_diff(SQL_INJECTION_DIFF), collection)

    assert isinstance(result, ReviewResult)
    critical_comments = [c for c in result.comments if c.severity == Severity.CRITICAL]
    assert len(critical_comments) == 0, "Standards pass must never use CRITICAL severity"

    _print_result(result)


# ── PR Description ────────────────────────────────

def test_pr_description_title_length():
    print("\n[eval] PR description title ≤ 72 chars...")
    changeset = analyze_diff(parse_diff(CLEAN_PYTHON_DIFF))
    result = generate_pr_description(changeset)

    assert len(result.title) <= 72, f"Title too long: {len(result.title)} chars — '{result.title}'"
    print(f"  title ({len(result.title)} chars): {result.title}")

if __name__ == "__main__":
    test_security_catches_sql_injection()
    test_security_no_false_positive_clean_code()
    test_correctness_catches_n_plus_one()
    test_correctness_no_false_positive_clean_code()
    test_standards_catches_bad_naming()
    test_standards_severity_never_critical()
    test_pr_description_title_length()
