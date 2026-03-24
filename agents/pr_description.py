import json
import os
from core.models import ChangeSet, PRDescription
from core.anthropic_client import get_client


def generate_pr_description(changeset: ChangeSet) -> PRDescription:
    prompt = _load_prompt("pr_description")
    context = _build_context(changeset)

    response = get_client().messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        system=prompt,
        messages=[
            {"role": "user", "content": f"Generate a PR description for this change:\n\n{context}"}
        ]
    )

    raw = response.content[0].text.strip()

    if raw.startswith("```"):
        start = raw.find("\n") + 1
        end = raw.rfind("```")
        raw = raw[start:end].strip()

    parsed = json.loads(raw)

    return PRDescription(
        title=parsed["title"],
        summary=_to_string(parsed["summary"]),
        motivation=_to_string(parsed["motivation"]),
        approach=_to_string(parsed["approach"]),
        testing_notes=_to_string(parsed["testing_notes"]),
        todos=_to_string(parsed["todos"]),
    )


def _to_string(value) -> str:
    """Convert a value to string, joining list items with newlines if needed."""
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value)


def _build_context(changeset: ChangeSet) -> str:
    lines = [f"Intent: {changeset.intent.value}", "", "Files changed:"]

    for f in changeset.files:
        lines.append(f"- {f.path} ({f.change_type.value})")
        if f.functions_added:
            lines.append(f"  functions_added: {', '.join(f.functions_added)}")
        if f.functions_modified:
            lines.append(f"  functions_modified: {', '.join(f.functions_modified)}")
        if f.functions_deleted:
            lines.append(f"  functions_deleted: {', '.join(f.functions_deleted)}")
        if f.classes_added:
            lines.append(f"  classes_added: {', '.join(f.classes_added)}")
        if f.classes_modified:
            lines.append(f"  classes_modified: {', '.join(f.classes_modified)}")
        if f.classes_deleted:
            lines.append(f"  classes_deleted: {', '.join(f.classes_deleted)}")

    lines.append("")
    lines.append("Raw diff:")
    lines.append(changeset.raw_diff)

    return "\n".join(lines)


def _load_prompt(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", f"{name}.md")
    with open(path) as f:
        return f.read()