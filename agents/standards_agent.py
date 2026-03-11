import json
from anthropic import Anthropic
from dotenv import load_dotenv
import os
import chromadb
from core.models import ChangeSet, ReviewComment, ReviewResult, Severity

load_dotenv()
client = Anthropic()


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

    raw = response.content[0].text.strip()

    if raw.startswith("```"):
        start = raw.find("\n") + 1
        end = raw.rfind("```")
        raw = raw[start:end].strip()

    parsed = json.loads(raw)

    comments = [
        ReviewComment(
            file=c["file"],
            line=c.get("line"),
            severity=Severity(c["severity"]),
            category="standards",
            message=c["message"],
            suggested_fix=c.get("suggested_fix"),
        )
        for c in parsed["comments"]
    ]

    return ReviewResult(
        comments=comments,
        summary=parsed["summary"],
        pass_name="standards",
    )


def _build_context(changeset: ChangeSet, collection: chromadb.Collection) -> str:
    similar = collection.query(
        query_texts=[changeset.raw_diff[:2000]],
        n_results=min(5, collection.count()),
    )

    pattern_lines = []
    if similar and similar["documents"]:
        for doc in similar["documents"][0]:
            pattern_lines.append(f"- {doc}")

    patterns_section = "\n".join(pattern_lines) if pattern_lines else "- No patterns available"

    return f"Repo patterns (from merged PRs):\n{patterns_section}\n\nDiff to review:\n{changeset.raw_diff}"


def _load_prompt(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", f"{name}.md")
    with open(path) as f:
        return f.read()
