# Preflight

Instant senior-level AI code review before you open a PR.

Preflight analyzes your git diff through 4 focused AI review passes—each a separate Claude API call for higher quality than a single giant prompt. Get actionable feedback on correctness, security, style, and performance issues before your code even reaches human reviewers.

## Features

- **4 Focused Review Passes** — Correctness, Security, Style, and Performance checks run concurrently for fast, thorough analysis
- **Smart Diff Analysis** — Automatically extracts modified functions/classes and classifies intent (feature, bugfix, refactor)
- **PR Description Generation** — Creates complete PR writeups with summary, motivation, approach, and testing notes
- **Severity-Based Output** — Color-coded findings (critical, warning, suggestion) with specific line references and suggested fixes
- **Repo Standards Learning** — Optional ChromaDB integration to learn patterns from your merged PRs
- **CLI-First Design** — Simple commands that integrate into your existing workflow

## Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.11+ |
| AI | Anthropic Claude API |
| CLI | Click |
| Output | Rich |
| Data Validation | Pydantic v2 |
| Vector DB | ChromaDB |
| GitHub API | PyGithub |
| Config | python-dotenv |

## Prerequisites

- **Python 3.11 or higher**
- **Git** — Must be run from within a git repository
- **Anthropic API key** — Get one at [console.anthropic.com](https://console.anthropic.com/)
- **GitHub CLI** (optional) — Required for `preflight pr` to create PRs directly. Install from [cli.github.com](https://cli.github.com/)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/your-username/preflight.git
cd preflight
```

2. Install the package:

```bash
pip install -e .
```

For development (includes pytest):

```bash
pip install -e ".[dev]"
```

## Configuration

Create a `.env` file in the project root (or copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```
ANTHROPIC_API_KEY=your-anthropic-api-key-here
GITHUB_TOKEN=ghp_your-github-token-here
GITHUB_REPO=owner/repo-name
```

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key for Claude |
| `GITHUB_TOKEN` | No | GitHub token for Standards Indexer (repo pattern learning) |
| `GITHUB_REPO` | No | Repository in `owner/repo` format for Standards Indexer |

## Usage

### Code Review

Run all 4 review passes on your current branch's diff against `main`:

```bash
preflight review
```

Diff against a different base branch:

```bash
preflight review --base develop
```

Example output:

```
Intent: feature · 3 file(s) changed

── CORRECTNESS ──
No issues found.

── SECURITY ──
[WARNING] src/auth.py:45
  Potential SQL injection vulnerability in user query
  → Use parameterized queries instead of string formatting

── STYLE ──
[SUGGESTION] src/utils.py:12
  Magic number 86400 should be a named constant
  → Define SECONDS_PER_DAY = 86400

── PERFORMANCE ──
No issues found.
```

### PR Description Generation

Generate a PR description and create a PR via GitHub CLI:

```bash
preflight pr
```

Options:

```bash
# Diff against a different branch
preflight pr --base develop

# Override the generated title
preflight pr --title "Add user authentication"

# Copy to clipboard instead of creating PR
preflight pr --copy
```

When you run `preflight pr`, it will:
1. Generate a title, summary, motivation, approach, testing notes, and TODOs
2. Show a preview panel
3. Prompt for confirmation
4. Push your branch and create the PR via `gh pr create`

## Project Structure

```
preflight/
├── core/
│   ├── cli.py              # Main CLI entry point (Click commands)
│   ├── diff_parser.py      # Parses raw git diff into ChangeSet
│   └── models.py           # Pydantic models (ChangeSet, ReviewResult, etc.)
├── agents/
│   ├── diff_analyzer.py    # Extracts intent and function/class changes
│   ├── review_agent.py     # 4 review passes (correctness, security, style, performance)
│   ├── pr_description.py   # PR description generation
│   ├── standards_agent.py  # Reviews against repo-specific patterns
│   └── standards_indexer.py # Indexes merged PRs into ChromaDB
├── prompts/
│   ├── diff_analyzer.md
│   ├── correctness_review.md
│   ├── security_review.md
│   ├── style_review.md
│   ├── performance_review.md
│   ├── pr_description.md
│   └── standards_review.md
├── test_*.py               # Test files
├── pyproject.toml          # Package configuration
├── .env.example            # Example environment variables
└── SAFETY.md               # Safety considerations and limitations
```

## Review Passes

Each pass focuses on a specific category:

| Pass | What It Catches |
|------|-----------------|
| **Correctness** | Logic bugs, null dereferences, off-by-one errors, unhandled exceptions, race conditions |
| **Security** | SQL/command injection, hardcoded secrets, auth issues, sensitive data exposure |
| **Style** | Readability, naming conventions, magic numbers, dead code, missing docstrings |
| **Performance** | N+1 queries, unbounded memory, missing caching opportunities, sync vs async issues |

## Running Tests

```bash
# Run all tests
pytest

# Run specific test files
python test_diff_parser.py
python test_diff_analyzer.py
python test_agent.py
python test_evals.py
```

## Safety & Limitations

Preflight is **advisory only**—it does not block merges or execute any code.

- Diffs are sent to Anthropic's API; no external storage of your code
- Large diffs may be truncated to fit context limits
- The Security pass flags potential hardcoded secrets
- Standards Agent quality depends on the quality of indexed PRs

See [SAFETY.md](SAFETY.md) for full details.

## Contributing

Contributions are welcome! To get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m "Add your feature"`)
6. Push to the branch (`git push origin feature/your-feature`)
7. Open a Pull Request

