from dotenv import load_dotenv
load_dotenv()  # must be first — Anthropic client init happens at module import time

from core.diff_parser import parse_diff
from core.models import ChangeSet, ChangeIntent
from agents.diff_analyzer import analyze_diff

# ────────FEATURE DIFF─────────────────────────────
# Entirely new file with two new functions.
# Expected: intent=FEATURE, functions_added non-empty
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
+    return Transaction.objects.filter(user_id=user_id, status="completed").all()
"""

# ────────BUGFIX DIFF──────────────────────────────
# Existing function modified to fix two exception-safety holes.
# Expected: intent=BUGFIX, functions_modified non-empty
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
# Expected: intent=REFACTOR, functions_added and functions_modified both non-empty
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


def _print_analysis(result: ChangeSet):
    print(f"  Intent:             {result.intent.value}")
    for f in result.files:
        print(f"  File:               {f.path}")
        print(f"  functions_added:    {f.functions_added}")
        print(f"  functions_modified: {f.functions_modified}")
        print(f"  functions_deleted:  {f.functions_deleted}")
        print(f"  classes_added:      {f.classes_added}")
        print(f"  classes_modified:   {f.classes_modified}")
        print(f"  classes_deleted:    {f.classes_deleted}")


def test_feature_classification():
    print("\nTesting feature classification...")
    changeset = parse_diff(FEATURE_DIFF)
    result = analyze_diff(changeset)

    assert isinstance(result.intent, ChangeIntent)
    assert result.intent == ChangeIntent.FEATURE
    assert isinstance(result.files[0].functions_added, list)
    assert len(result.files[0].functions_added) > 0

    _print_analysis(result)


def test_bugfix_classification():
    print("\nTesting bugfix classification...")
    changeset = parse_diff(BUGFIX_DIFF)
    result = analyze_diff(changeset)

    assert isinstance(result.intent, ChangeIntent)
    assert result.intent == ChangeIntent.BUGFIX
    assert isinstance(result.files[0].functions_modified, list)
    assert len(result.files[0].functions_modified) > 0

    _print_analysis(result)


def test_refactor_classification():
    print("\nTesting refactor classification...")
    changeset = parse_diff(REFACTOR_DIFF)
    result = analyze_diff(changeset)

    assert isinstance(result.intent, ChangeIntent)
    assert result.intent == ChangeIntent.REFACTOR
    assert isinstance(result.files[0].functions_added, list)
    assert isinstance(result.files[0].functions_modified, list)
    assert len(result.files[0].functions_added) > 0
    assert len(result.files[0].functions_modified) > 0

    _print_analysis(result)


def test_output_types_feature_diff():
    """Structural guard: every symbol field is a list on the feature diff."""
    print("\nTesting output type safety (feature diff)...")
    result = analyze_diff(parse_diff(FEATURE_DIFF))
    f = result.files[0]
    assert isinstance(f.functions_added, list)
    assert isinstance(f.functions_modified, list)
    assert isinstance(f.functions_deleted, list)
    assert isinstance(f.classes_added, list)
    assert isinstance(f.classes_modified, list)
    assert isinstance(f.classes_deleted, list)


def test_output_types_bugfix_diff():
    """Structural guard: every symbol field is a list on the bugfix diff."""
    print("\nTesting output type safety (bugfix diff)...")
    result = analyze_diff(parse_diff(BUGFIX_DIFF))
    f = result.files[0]
    assert isinstance(f.functions_added, list)
    assert isinstance(f.functions_modified, list)
    assert isinstance(f.functions_deleted, list)
    assert isinstance(f.classes_added, list)
    assert isinstance(f.classes_modified, list)
    assert isinstance(f.classes_deleted, list)


def test_output_types_refactor_diff():
    """Structural guard: every symbol field is a list on the refactor diff."""
    print("\nTesting output type safety (refactor diff)...")
    result = analyze_diff(parse_diff(REFACTOR_DIFF))
    f = result.files[0]
    assert isinstance(f.functions_added, list)
    assert isinstance(f.functions_modified, list)
    assert isinstance(f.functions_deleted, list)
    assert isinstance(f.classes_added, list)
    assert isinstance(f.classes_modified, list)
    assert isinstance(f.classes_deleted, list)


if __name__ == "__main__":
    test_feature_classification()
    test_bugfix_classification()
    test_refactor_classification()
    test_output_types_feature_diff()
    test_output_types_bugfix_diff()
    test_output_types_refactor_diff()