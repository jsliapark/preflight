from dotenv import load_dotenv
load_dotenv()

from core.diff_parser import parse_diff
from agents.diff_analyzer import analyze_diff
from agents.review_agent import (
    run_correctness_pass,
    run_security_pass,
    run_style_pass,
    run_performance_pass,
)

# ────────BACKEND-SPECIFIC BAD DIFF─────────────
# - Correctness: null dereference on user.name
# - Security:    SQL injection + hardcoded API key
# - Style:       function name 'f', magic number
# - Performance: N+1 query inside a loop
# ─────────────────────────────────────────────

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

# ────────FRONTEND-SPECIFIC BAD DIFF─────────────
# - Correctness: x.ids[0].name crashes if ids is empty
# - Correctness: stale closure — data never updates correctly
# - Correctness: missing useEffect dependency on x.ids
# - Correctness: missing key prop in data.map()
# - Security:    hardcoded API key in k
# - Style:       meaningless names f, x, k, d, r
# - Performance: one fetch per user id — N+1 network requests
# ───────────────────────────────────────────────
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
+
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

def _print_result(result):
    """Helper to print review results."""
    print(f"Pass: {result.pass_name}")
    print(f"Summary: {result.summary}")
    for comment in result.comments:
        print(f"\n  [{comment.severity.value.upper()}] {comment.file}:{comment.line}")
        print(f"  {comment.message}")
        if comment.suggested_fix:
            print(f"  → {comment.suggested_fix}")


def test_correctness_backend():
    print("\nRunning correctness pass (backend)...")
    changeset = parse_diff(BACKEND_BAD_DIFF)
    result = run_correctness_pass(changeset)
    _print_result(result)


def test_correctness_frontend():
    print("\nRunning correctness pass (frontend)...")
    changeset = parse_diff(FRONTEND_BAD_DIFF)
    result = run_correctness_pass(changeset)
    _print_result(result)


def test_security_backend():
    print("\nRunning security pass (backend)...")
    changeset = parse_diff(BACKEND_BAD_DIFF)
    result = run_security_pass(changeset)
    _print_result(result)


def test_security_frontend():
    print("\nRunning security pass (frontend)...")
    changeset = parse_diff(FRONTEND_BAD_DIFF)
    result = run_security_pass(changeset)
    _print_result(result)


def test_style_backend():
    print("\nRunning style pass (backend)...")
    changeset = parse_diff(BACKEND_BAD_DIFF)
    result = run_style_pass(changeset)
    _print_result(result)


def test_style_frontend():
    print("\nRunning style pass (frontend)...")
    changeset = parse_diff(FRONTEND_BAD_DIFF)
    result = run_style_pass(changeset)
    _print_result(result)


def test_performance_backend():
    print("\nRunning performance pass (backend)...")
    changeset = parse_diff(BACKEND_BAD_DIFF)
    result = run_performance_pass(changeset)
    _print_result(result)


def test_performance_frontend():
    print("\nRunning performance pass (frontend)...")
    changeset = parse_diff(FRONTEND_BAD_DIFF)
    result = run_performance_pass(changeset)
    _print_result(result)


if __name__ == "__main__":
    test_correctness_backend()
    test_correctness_frontend()
    test_security_backend()
    test_security_frontend()
    test_style_backend()
    test_style_frontend()
    test_performance_backend()
    test_performance_frontend()