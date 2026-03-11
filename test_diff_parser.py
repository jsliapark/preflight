from core.diff_parser import parse_diff
from core.models import ChangeType


# ─────────────────────────────────────────────
# Fixtures — reusable raw diffs
# ─────────────────────────────────────────────

SINGLE_FILE_SINGLE_HUNK = """diff --git a/auth.py b/auth.py
--- a/auth.py
+++ b/auth.py
@@ -3,4 +3,4 @@
 def login(user, password):
-    if password == "admin123":
+    if check_password_hash(password):
     return True
"""

SINGLE_FILE_TWO_HUNKS = """diff --git a/auth.py b/auth.py
--- a/auth.py
+++ b/auth.py
@@ -3,4 +3,4 @@
 def login(user, password):
-    if password == "admin123":
+    if check_password_hash(password):
     return True
@@ -198,4 +198,6 @@
 def logout(user):
+    invalidate_session(user)
+    log_audit_event(user)
     return redirect("/")
"""

TWO_FILES = """diff --git a/auth.py b/auth.py
--- a/auth.py
+++ b/auth.py
@@ -3,4 +3,4 @@
 def login(user, password):
-    if password == "admin123":
+    if check_password_hash(password):
     return True
diff --git a/utils.py b/utils.py
--- a/utils.py
+++ b/utils.py
@@ -10,3 +10,4 @@
 def format_date(d):
+    if d is None: return ""
     return d.strftime("%Y-%m-%d")
"""

NEW_FILE_ONLY_ADDITIONS = """diff --git a/newfile.py b/newfile.py
--- /dev/null
+++ b/newfile.py
@@ -0,0 +1,4 @@
+def hello():
+    print("hello world")
+
+hello()
"""

DELETED_FILE_ONLY_REMOVALS = """diff --git a/old.py b/old.py
--- a/old.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def deprecated():
-    pass
-
"""

EMPTY_DIFF = ""


# ─────────────────────────────────────────────
# 1. Basic structure tests
# ─────────────────────────────────────────────

class TestBasicStructure:

    def test_single_file_is_parsed(self):
        result = parse_diff(SINGLE_FILE_SINGLE_HUNK)
        assert len(result.files) == 1

    def test_correct_file_path_extracted(self):
        result = parse_diff(SINGLE_FILE_SINGLE_HUNK)
        assert result.files[0].path == "auth.py"

    def test_two_files_parsed(self):
        result = parse_diff(TWO_FILES)
        assert len(result.files) == 2

    def test_two_file_paths(self):
        result = parse_diff(TWO_FILES)
        paths = [f.path for f in result.files]
        assert "auth.py" in paths
        assert "utils.py" in paths

    def test_raw_diff_preserved(self):
        result = parse_diff(SINGLE_FILE_SINGLE_HUNK)
        assert result.raw_diff == SINGLE_FILE_SINGLE_HUNK

    def test_empty_diff_returns_empty_changeset(self):
        result = parse_diff(EMPTY_DIFF)
        assert result.files == []
        assert result.raw_diff == ""


# ─────────────────────────────────────────────
# 2. Hunk tests
# ─────────────────────────────────────────────

class TestHunks:

    def test_single_hunk_detected(self):
        result = parse_diff(SINGLE_FILE_SINGLE_HUNK)
        assert len(result.files[0].hunks) == 1

    def test_two_hunks_in_one_file(self):
        result = parse_diff(SINGLE_FILE_TWO_HUNKS)
        assert len(result.files[0].hunks) == 2

    def test_hunk_start_line_extracted(self):
        result = parse_diff(SINGLE_FILE_SINGLE_HUNK)
        assert result.files[0].hunks[0].start_line == 3

    def test_second_hunk_start_line(self):
        result = parse_diff(SINGLE_FILE_TWO_HUNKS)
        assert result.files[0].hunks[1].start_line == 198

    def test_hunk_contains_lines(self):
        result = parse_diff(SINGLE_FILE_SINGLE_HUNK)
        hunk = result.files[0].hunks[0]
        assert len(hunk.lines) > 0

    def test_hunk_lines_include_added_line(self):
        result = parse_diff(SINGLE_FILE_SINGLE_HUNK)
        lines = result.files[0].hunks[0].lines
        assert any("check_password_hash" in l for l in lines)

    def test_hunk_lines_include_removed_line(self):
        result = parse_diff(SINGLE_FILE_SINGLE_HUNK)
        lines = result.files[0].hunks[0].lines
        assert any("admin123" in l for l in lines)

    def test_metadata_lines_excluded(self):
        """Lines starting with +++ or --- should not appear in hunk lines."""
        result = parse_diff(SINGLE_FILE_SINGLE_HUNK)
        lines = result.files[0].hunks[0].lines
        assert not any(l.startswith("+++") or l.startswith("---") for l in lines)


# ─────────────────────────────────────────────
# 3. Change type detection
# ─────────────────────────────────────────────

class TestChangeType:

    def test_modified_file(self):
        result = parse_diff(SINGLE_FILE_SINGLE_HUNK)
        assert result.files[0].change_type == ChangeType.MODIFIED

    def test_new_file_is_added(self):
        result = parse_diff(NEW_FILE_ONLY_ADDITIONS)
        assert result.files[0].change_type == ChangeType.ADDED

    def test_deleted_file(self):
        result = parse_diff(DELETED_FILE_ONLY_REMOVALS)
        assert result.files[0].change_type == ChangeType.DELETED


# ─────────────────────────────────────────────
# 4. Edge cases
# ─────────────────────────────────────────────

class TestEdgeCases:

    def test_new_file_path_correct(self):
        result = parse_diff(NEW_FILE_ONLY_ADDITIONS)
        assert result.files[0].path == "newfile.py"

    def test_deleted_file_path_correct(self):
        result = parse_diff(DELETED_FILE_ONLY_REMOVALS)
        assert result.files[0].path == "old.py"

    def test_new_file_hunk_start_line(self):
        """New files always start at line 1."""
        result = parse_diff(NEW_FILE_ONLY_ADDITIONS)
        assert result.files[0].hunks[0].start_line == 1

    def test_two_files_each_have_one_hunk(self):
        result = parse_diff(TWO_FILES)
        for f in result.files:
            assert len(f.hunks) == 1