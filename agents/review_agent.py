import os
import json
from core.models import ChangeSet, ReviewComment, ReviewResult, Severity
from core.anthropic_client import get_client

def _run_pass(changeset: ChangeSet, prompt_name: str, category: str) -> ReviewResult:
    prompt = _load_prompt(prompt_name)
    diff_content = _format_diff_for_review(changeset)
    
    response = get_client().messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=prompt,
        messages=[
            {"role": "user", "content": f"Please review this diff:\n\n{diff_content}"}
        ]
    )
    
    raw = response.content[0].text
    
    if raw.startswith("```"):
        start = raw.find("\n") + 1
        end = raw.rfind("```")
        raw = raw[start:end].strip()
    
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        print(f"ERROR: Failed to parse JSON response from Claude")
        print(f"Raw response:\n{raw}")
        raise
    
    comments = [ReviewComment(
        file=c["file"],
        line=c.get("line"),
        severity=Severity(c["severity"]),
        category=category,
        message=c["message"],
        suggested_fix=c.get("suggested_fix")
    ) for c in parsed["comments"]]
    
    return ReviewResult(
        comments=comments,
        summary=parsed["summary"],
        pass_name=category
    )


# Public API — one line each
def run_correctness_pass(changeset: ChangeSet) -> ReviewResult:
    return _run_pass(changeset, "correctness_review", "correctness")

def run_security_pass(changeset: ChangeSet) -> ReviewResult:
    return _run_pass(changeset, "security_review", "security")

def run_style_pass(changeset: ChangeSet) -> ReviewResult:
    return _run_pass(changeset, "style_review", "style")

def run_performance_pass(changeset: ChangeSet) -> ReviewResult:
    return _run_pass(changeset, "performance_review", "performance")

# Helper functions
def _load_prompt(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", f"{name}.md")
    with open(path) as f:
        return f.read()


def _format_diff_for_review(changeset: ChangeSet) -> str:
    return changeset.raw_diff