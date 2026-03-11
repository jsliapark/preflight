from dotenv import load_dotenv
load_dotenv()

import uuid
import chromadb
from core.diff_parser import parse_diff
from core.models import ReviewResult
from agents.standards_agent import run_standards_pass

# ────────BACKEND BAD DIFF────────────────────────
# Violations: function named "f" (breaks snake_case),
# SQL built with f-string (no try/except around DB call)
# ─────────────────────────────────────────────────
BACKEND_BAD_DIFF = """diff --git a/auth.py b/auth.py
--- a/auth.py
+++ b/auth.py
@@ -1,0 +1,20 @@
+API_KEY = "sk-prod-1234567890abcdef"
+
+def f(user_ids):
+    orders = []
+    for user_id in user_ids:
+        user = db.query(f"SELECT * FROM users WHERE id = {user_id}")
+        order = db.query(f"SELECT * FROM orders WHERE user_id = {user_id}")
+        if user:
+            orders.append(user.name * 1.08)
+    return orders
"""

# ────────FRONTEND BAD DIFF───────────────────────
# Violations: function named "f", variable "k", "x", "d", "r"
# ─────────────────────────────────────────────────
FRONTEND_BAD_DIFF = """diff --git a/UserProfile.jsx b/UserProfile.jsx
--- /dev/null
+++ b/UserProfile.jsx
@@ -0,0 +1,20 @@
+const k = "AIzaSyB-1234567890abcdef";
+
+function f(x) {
+  const [data, setData] = useState([]);
+
+  useEffect(() => {
+    for (let i = 0; i < x.ids.length; i++) {
+      fetch(`/api/user/${x.ids[i]}`)
+        .then(r => r.json())
+        .then(d => setData([...data, d]));
+    }
+  }, []);

+  return (
+    <div>
+      {data.map(user => (
+        <div>{user.name}</div>
+      ))}
+      <div>{x.ids[0].name}</div>
+    </div>
+  );
+}
"""

# Seeded patterns — inserted directly into in-memory ChromaDB, no GitHub needed
SEED_PATTERNS = [
    "Functions use snake_case naming: get_user, create_order, validate_token",
    "Error handling always wraps DB calls in try/except with logger.error()",
    "Imports follow order: stdlib → third-party → internal core modules",
]


def _seed_collection() -> chromadb.Collection:
    """Creates a fresh in-memory ChromaDB collection with seeded patterns."""
    client = chromadb.EphemeralClient()
    collection = client.create_collection(name=f"repo_patterns_{uuid.uuid4().hex[:8]}")
    collection.add(
        ids=["p1", "p2", "p3"],
        documents=SEED_PATTERNS,
    )
    return collection


def _print_result(result: ReviewResult):
    print(f"  pass:    {result.pass_name}")
    print(f"  summary: {result.summary}")
    for comment in result.comments:
        print(f"\n  [{comment.severity.value.upper()}] {comment.file}:{comment.line}")
        print(f"  {comment.message}")
        if comment.suggested_fix:
            print(f"  → {comment.suggested_fix}")


def test_standards_pass_backend():
    print("\nTesting standards pass (backend)...")
    collection = _seed_collection()
    changeset = parse_diff(BACKEND_BAD_DIFF)
    result = run_standards_pass(changeset, collection)

    assert isinstance(result, ReviewResult)
    assert isinstance(result.comments, list)
    assert isinstance(result.summary, str) and len(result.summary) > 0
    assert result.pass_name == "standards"

    _print_result(result)


def test_standards_pass_frontend():
    print("\nTesting standards pass (frontend)...")
    collection = _seed_collection()
    changeset = parse_diff(FRONTEND_BAD_DIFF)
    result = run_standards_pass(changeset, collection)

    assert isinstance(result, ReviewResult)
    assert isinstance(result.comments, list)
    assert isinstance(result.summary, str) and len(result.summary) > 0
    assert result.pass_name == "standards"

    _print_result(result)


def test_standards_result_structure():
    """Structural guard: ReviewResult fields are always the right types."""
    print("\nTesting standards result structure...")
    collection = _seed_collection()
    result = run_standards_pass(parse_diff(BACKEND_BAD_DIFF), collection)

    assert isinstance(result.comments, list)
    assert isinstance(result.summary, str)
    assert result.pass_name == "standards"


def test_standards_finds_violations():
    """Semantic guard: backend diff violates snake_case — at least 1 comment expected."""
    print("\nTesting standards violation detection...")
    collection = _seed_collection()
    result = run_standards_pass(parse_diff(BACKEND_BAD_DIFF), collection)

    assert len(result.comments) > 0, "Expected at least 1 standards violation for function named 'f'"

    _print_result(result)


if __name__ == "__main__":
    test_standards_pass_backend()
    test_standards_pass_frontend()
    test_standards_result_structure()
    test_standards_finds_violations()
