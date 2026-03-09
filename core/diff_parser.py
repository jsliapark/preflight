from core.models import ChangeSet, FileChange, Hunk, ChangeType

def parse_diff(raw_diff: str) -> ChangeSet:
    files = []
    current_file = None
    current_hunks = []
    current_hunk_lines = []
    current_hunk_start = 0

    for line in raw_diff.splitlines():

        # New file detected: "diff --git a/foo.py b/foo.py"
        if line.startswith("diff --git"):
            # [Flush pattern] Before starting the new file, save the previous one
            if current_file:
                _flush_hunk(current_hunk_lines, current_hunks, current_hunk_start)
                files.append(FileChange(
                    path=current_file,
                    change_type=_detect_change_type(current_hunks),
                    hunks=current_hunks,
                ))
            current_file = _extract_path(line)
            current_hunks = []
            current_hunk_lines = []

        # Hunk header: "@@ -3,7 +3,7 @@"
        elif line.startswith("@@"):
            _flush_hunk(current_hunk_lines, current_hunks, current_hunk_start)
            current_hunk_start = _extract_start_line(line)
            current_hunk_lines = []

        # Actual changed lines (+ added, - removed, context)
        elif current_file and (line.startswith("+")
                               or line.startswith("-")
                               or line.startswith(" ")):
            if not line.startswith("+++") and not line.startswith("---"):
                current_hunk_lines.append(line)

    # Append Last file 
    if current_file:
        _flush_hunk(current_hunk_lines, current_hunks, current_hunk_start)
        files.append(FileChange(
            path=current_file,
            change_type=_detect_change_type(current_hunks),
            hunks=current_hunks,
        ))

    return ChangeSet(files=files, raw_diff=raw_diff)


# --- Helpers ---

def _flush_hunk(lines, hunks, start_line):
    """Save the current hunk if it has content."""
    if lines:
        hunks.append(Hunk(start_line=start_line, lines=lines))


def _extract_path(line: str) -> str:
    """Extract 'foo.py' from 'diff --git a/foo.py b/foo.py'"""
    parts = line.split(" ")
    return parts[-1].replace("b/", "", 1)


def _extract_start_line(line: str) -> int:
    """Extract 198 from '@@ -198,6 +198,8 @@'"""
    try:
        new_file_part = line.split("+")[1].split(",")[0]
        return int(new_file_part)
    except (IndexError, ValueError):
        return 0


def _detect_change_type(hunks: list) -> ChangeType:
    """Infer whether a file was added, deleted, or modified."""
    all_lines = [l for h in hunks for l in h.lines]
    has_additions = any(l.startswith("+") for l in all_lines)
    has_deletions = any(l.startswith("-") for l in all_lines)

    if has_additions and not has_deletions:
        return ChangeType.ADDED
    if has_deletions and not has_additions:
        return ChangeType.DELETED
    return ChangeType.MODIFIED