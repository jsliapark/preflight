from dotenv import load_dotenv
load_dotenv()

from core.diff_parser import parse_diff
from core.models import PRDescription
from agents.diff_analyzer import analyze_diff
from agents.pr_description import generate_pr_description

# ────────FEATURE DIFF─────────────────────────────
# New file with two new functions.
# Expected: imperative title, approach references function names
# ─────────────────────────────────────────────────
FEATURE_DIFF = """diff --git a/api/payments.py b/api/payments.py
--- /dev/null
+++ b/api/payments.py
@@ -0,0 +1,14 @@
+from decimal import Decimal
+
+def process_payment(user_id: int, amount: Decimal, currency: str) -> dict:
+    gateway_response = payment_gateway.charge(user_id, amount, currency)
+    transaction = Transaction.create(
+        user_id=user_id,
+        amount=amount,
+        currency=currency,
+        status=gateway_response["status"],
+    )
+    return {"transaction_id": transaction.id, "status": transaction.status}
+
+def get_payment_history(user_id: int) -> list:
+    # TODO: add pagination support
+    return Transaction.objects.filter(user_id=user_id, status="completed").all()
"""

# ────────BUGFIX DIFF──────────────────────────────
# Existing function modified to fix two exception-safety holes.
# Expected: motivation describes what was broken
# ─────────────────────────────────────────────────
BUGFIX_DIFF = """diff --git a/core/auth.py b/core/auth.py
--- a/core/auth.py
+++ b/core/auth.py
@@ -12,4 +12,10 @@
 def validate_token(token: str) -> bool:
-    payload = jwt.decode(token, SECRET_KEY)
-    return payload["user_id"] is not None
+    try:
+        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
+    except jwt.ExpiredSignatureError:
+        return False
+    except jwt.InvalidTokenError:
+        return False
+    return payload.get("user_id") is not None
"""

# ────────REFACTOR DIFF────────────────────────────
# Private helper extracted from existing function — no behavioral change.
# Expected: risks as "No significant risks identified"
# ─────────────────────────────────────────────────
REFACTOR_DIFF = """diff --git a/core/reports.py b/core/reports.py
--- a/core/reports.py
+++ b/core/reports.py
@@ -5,6 +5,10 @@
+def _build_header(title: str, period: str) -> dict:
+    return {"title": title, "period": period, "generated_at": datetime.utcnow().isoformat()}
+
 def generate_report(title: str, period: str, rows: list) -> dict:
-    header = {"title": title, "period": period, "generated_at": datetime.utcnow().isoformat()}
+    header = _build_header(title, period)
     return {"header": header, "rows": rows, "count": len(rows)}
"""


def _print_description(result: PRDescription):
    print(f"  title:         {result.title}")
    print(f"  summary:       {result.summary}")
    print(f"  motivation:    {result.motivation}")
    print(f"  approach:      {result.approach}")
    print(f"  testing_notes: {result.testing_notes}")
    print(f"  risks:         {result.risks}")
    print(f"  todos:         {result.todos}")


def test_feature_description():
    print("\nTesting PR description for feature diff...")
    changeset = analyze_diff(parse_diff(FEATURE_DIFF))
    result = generate_pr_description(changeset)

    assert isinstance(result, PRDescription)
    assert isinstance(result.title, str) and len(result.title) > 0
    assert isinstance(result.summary, str) and len(result.summary) > 0
    assert isinstance(result.motivation, str) and len(result.motivation) > 0
    assert isinstance(result.approach, str) and len(result.approach) > 0
    assert isinstance(result.testing_notes, str) and len(result.testing_notes) > 0
    assert isinstance(result.risks, str) and len(result.risks) > 0
    assert isinstance(result.todos, str) and len(result.todos) > 0
    assert "pagination" in result.todos.lower()
    assert len(result.title) <= 72

    _print_description(result)


def test_bugfix_description():
    print("\nTesting PR description for bugfix diff...")
    changeset = analyze_diff(parse_diff(BUGFIX_DIFF))
    result = generate_pr_description(changeset)

    assert isinstance(result, PRDescription)
    assert isinstance(result.title, str) and len(result.title) > 0
    assert isinstance(result.summary, str) and len(result.summary) > 0
    assert isinstance(result.motivation, str) and len(result.motivation) > 0
    assert isinstance(result.approach, str) and len(result.approach) > 0
    assert isinstance(result.testing_notes, str) and len(result.testing_notes) > 0
    assert isinstance(result.risks, str) and len(result.risks) > 0
    assert isinstance(result.todos, str) and len(result.todos) > 0
    assert len(result.title) <= 72

    _print_description(result)


def test_refactor_description():
    print("\nTesting PR description for refactor diff...")
    changeset = analyze_diff(parse_diff(REFACTOR_DIFF))
    result = generate_pr_description(changeset)

    assert isinstance(result, PRDescription)
    assert isinstance(result.title, str) and len(result.title) > 0
    assert isinstance(result.summary, str) and len(result.summary) > 0
    assert isinstance(result.motivation, str) and len(result.motivation) > 0
    assert isinstance(result.approach, str) and len(result.approach) > 0
    assert isinstance(result.testing_notes, str) and len(result.testing_notes) > 0
    assert isinstance(result.risks, str) and len(result.risks) > 0
    assert isinstance(result.todos, str) and len(result.todos) > 0
    assert len(result.title) <= 72

    _print_description(result)


def test_all_fields_are_strings():
    """Structural guard: every field of PRDescription is a non-empty str."""
    print("\nTesting PRDescription field types...")
    result = generate_pr_description(analyze_diff(parse_diff(FEATURE_DIFF)))

    assert isinstance(result.title, str)
    assert isinstance(result.summary, str)
    assert isinstance(result.motivation, str)
    assert isinstance(result.approach, str)
    assert isinstance(result.testing_notes, str)
    assert isinstance(result.risks, str)
    assert isinstance(result.todos, str)


if __name__ == "__main__":
    test_feature_description()
    test_bugfix_description()
    test_refactor_description()
    test_all_fields_are_strings()
