import os
import chromadb
from github import Github
from dotenv import load_dotenv
from core.models import RepoPattern

load_dotenv()


def build_index(repo_name: str, token: str, n_prs: int = 50) -> chromadb.Collection:
    """
    Fetches the last n_prs merged PRs from a GitHub repo, extracts code patterns,
    and stores them in a local persistent ChromaDB collection.
    Returns the populated collection.
    """
    client = _chroma_client()
    collection = client.get_or_create_collection(name="repo_patterns")

    gh = Github(token)
    repo = gh.get_repo(repo_name)

    pulls = repo.get_pulls(state="closed", sort="updated", direction="desc")
    count = 0

    for pr in pulls:
        if not pr.merged_at:
            continue

        patterns = _extract_patterns(pr)
        for i, pattern in enumerate(patterns):
            doc_id = f"pr-{pr.number}-{i}"
            collection.upsert(
                ids=[doc_id],
                documents=[pattern.text],
                metadatas=[{
                    "category": pattern.category,
                    "source_file": pattern.source_file,
                    "pr_number": pattern.pr_number,
                    "pr_url": pattern.pr_url,
                }]
            )

        count += 1
        if count >= n_prs:
            break

    print(f"Indexed {count} PRs into ChromaDB.")
    return collection


def load_index() -> chromadb.Collection:
    """Loads the existing local ChromaDB collection (no GitHub API call)."""
    client = _chroma_client()
    try:
        return client.get_collection(name="repo_patterns")
    except chromadb.errors.NotFoundError as e:
        raise RuntimeError("Standards index not found. Run build_index() first.") from e


def _extract_patterns(pr) -> list[RepoPattern]:
    """Extracts code pattern candidates from a merged PR's changed files."""
    patterns = []
    try:
        files = pr.get_files()
    except Exception:
        return patterns

    for f in files:
        if not f.filename.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".go")):
            continue
        if not f.patch:
            continue

        added_lines = [
            line[1:].strip()
            for line in f.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]

        for line in added_lines:
            if not line or line.startswith("#"):
                continue

            category = _classify_line(line)
            if category:
                patterns.append(RepoPattern(
                    text=line,
                    category=category,
                    source_file=f.filename,
                    pr_number=pr.number,
                    pr_url=pr.html_url,
                ))

    return patterns


def _classify_line(line: str) -> str | None:
    """Returns the pattern category for a line, or None if not a meaningful pattern."""
    if line.startswith(("def ", "async def ", "function ", "const ", "class ")):
        return "naming"
    if line.startswith(("import ", "from ")):
        return "imports"
    if "try:" in line or "except " in line or "catch " in line:
        return "error_handling"
    if line.startswith(("class ", "interface ", "type ")):
        return "structure"
    return None


def _chroma_client() -> chromadb.Client:
    path = os.path.join(os.path.dirname(__file__), "..", ".chroma")
    return chromadb.PersistentClient(path=path)
