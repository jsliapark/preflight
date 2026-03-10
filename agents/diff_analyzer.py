import json
from anthropic import Anthropic
from dotenv import load_dotenv
import os
from core.models import ChangeSet, ChangeIntent, FileChange

load_dotenv()
client = Anthropic()


def analyze_diff(changeset: ChangeSet) -> ChangeSet:
    """
    Enriches a ChangeSet with:
    - intent classification (feature / bugfix / refactor / unknown)
    - function and class level changes extracted by Claude
    """
    prompt = _load_prompt("diff_analyzer")

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=prompt,
        messages=[
            {"role": "user", "content": f"Analyze this diff:\n\n{changeset.raw_diff}"}
        ]
    )

    raw = response.content[0].text.strip()

    if raw.startswith("```"):
        start = raw.find("\n") + 1
        end = raw.rfind("```")
        raw = raw[start:end].strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        print("WARNING: diff analyzer could not parse Claude response, using defaults")
        return changeset

    # Classify intent
    try:
        intent = ChangeIntent(parsed.get("intent", "unknown"))
    except ValueError:
        intent = ChangeIntent.UNKNOWN

    # Enrich each file with extracted functions and classes
    updated_files = []
    for f in changeset.files:
        updated_files.append(f.model_copy(update={
            "functions_added": parsed.get("functions_added", []),
            "functions_modified": parsed.get("functions_modified", []),
            "functions_deleted": parsed.get("functions_deleted", []),
            "classes_added": parsed.get("classes_added", []),
            "classes_modified": parsed.get("classes_modified", []),
            "classes_deleted": parsed.get("classes_deleted", []),
        }))

    return changeset.model_copy(update={
        "intent": intent,
        "files": updated_files,
    })


def _load_prompt(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", f"{name}.md")
    with open(path) as f:
        return f.read()