import json
from itertools import islice

from anthropic import Anthropic
from dotenv import load_dotenv
import os
import chromadb
from core.models import ChangeSet, ReviewComment, ReviewResult, Severity

load_dotenv()
client = Anthropic()

# Maximum number of comments to process from model response
MAX_COMMENTS = 100


def run_standards_pass(changeset: ChangeSet, collection: chromadb.Collection) -> ReviewResult:
    prompt = _load_prompt("standards_review")
    context = _build_context(changeset, collection)

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=prompt,
        messages=[
            {"role": "user", "content": f"Review this diff for standards violations:\n\n{context}"}
        ]
    )

    if not response.content:
        return ReviewResult(comments=[], summary="No response from model.", pass_name="standards")

    raw_response = response.content[0].text.strip()

    if raw_response.startswith("```"):
        start = raw_response.find("\n") + 1
        end = raw_response.rfind("```")
        raw_response = raw_response[start:end].strip()

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        return ReviewResult(comments=[], summary="Failed to parse model response.", pass_name="standards")

    comments = []
    for comment_data in islice(parsed.get("comments", []), MAX_COMMENTS):
        # Skip comments missing required fields
        file_path = comment_data.get("file")
        message = comment_data.get("message")
        if not file_path or not message:
            continue
        
        try:
            severity = Severity(comment_data.get("severity", "warning"))
        except ValueError:
            severity = Severity.WARNING
        
        comments.append(ReviewComment(
            file=file_path,
            line=comment_data.get("line"),
            severity=severity,
            category="standards",
            message=message,
            suggested_fix=comment_data.get("suggested_fix"),
        ))

    return ReviewResult(
        comments=comments,
        summary=parsed.get("summary", ""),
        pass_name="standards",
    )


def _build_context(changeset: ChangeSet, collection: chromadb.Collection) -> str:
    """
    Builds context string with similar patterns from the collection and the diff.
    
    Args:
        changeset: The parsed changeset containing files and diff.
        collection: ChromaDB collection of code patterns from merged PRs.
    
    Returns:
        Context string combining relevant patterns and the diff for the prompt.
    """
    # Query with fixed n_results; ChromaDB handles cases where fewer results exist
    similar = collection.query(
        query_texts=[changeset.raw_diff[:2000]],
        n_results=5,
    )

    pattern_lines = []
    if similar and similar["documents"] and similar["documents"][0]:
        for doc in similar["documents"][0]:
            pattern_lines.append(f"- {doc}")

    patterns_section = "\n".join(pattern_lines) if pattern_lines else "- No patterns available"

    return f"Repo patterns (from merged PRs):\n{patterns_section}\n\nDiff to review:\n{changeset.raw_diff}"


def _load_prompt(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", f"{name}.md")
    with open(path) as f:
        return f.read()
