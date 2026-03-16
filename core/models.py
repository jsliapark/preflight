from pydantic import BaseModel
from enum import Enum
from typing import List

# Enums
class ChangeType(str, Enum):
    ADDED = "added"
    DELETED = "deleted"
    MODIFIED = "modified"

class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"

# Diff / Input Models
# Hunk represents one contiguous block of changes within a file (a git diff can have multiple hunks per file)
class Hunk(BaseModel):
    start_line: int
    lines: List[str] # raw lines, "+" added, "-" removed

class FileChange(BaseModel):
    path: str
    change_type: ChangeType
    hunks: List[Hunk]
    functions_added: List[str] = []     
    functions_modified: List[str] = [] 
    functions_deleted: List[str] = []    
    classes_added: List[str] = []        
    classes_modified: List[str] = []     
    classes_deleted: List[str] = []

class ChangeIntent(str, Enum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    UNKNOWN = "unknown"


# Changeset is what the diff parser produces and what every agent receives as input
class ChangeSet(BaseModel):
    files: list[FileChange]
    raw_diff: str # full diff string from git
    intent: ChangeIntent = ChangeIntent.UNKNOWN  # filled in by diff analyzer agent

# --- Review / Output models ---
class ReviewComment(BaseModel):
    file: str
    line: int | None = None
    severity: Severity
    category: str
    message: str
    suggested_fix: str | None = None

class ReviewResult(BaseModel):
    comments: list[ReviewComment]
    summary: str
    pass_name: str

# --- Standards Agent models ---
class RepoPattern(BaseModel):
    text: str           # the code pattern (naming, structure, error handling, etc.)
    category: str       # "naming" | "structure" | "error_handling" | "imports" | "other"
    source_file: str    # file it came from
    pr_number: int      # PR it was merged in
    pr_url: str

# --- PR Description / Output models ---
class PRDescription(BaseModel):
    title: str
    summary: str
    motivation: str
    approach: str
    testing_notes: str
    todos: str