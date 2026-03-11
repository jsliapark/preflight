# Preflight

Instant senior-level AI code review before you open a PR.

## About

Preflight analyzes a git diff through 4 focused AI passes — each a separate Claude call for higher quality than one giant prompt.

## Agents

| Agent | Description | Status |
|---|---|---|
| Diff Analyzer | Extracts function/class changes and classifies intent (feature / bugfix / refactor) | ✅ |
| Review Agent | 4 passes: Correctness, Security, Style, Performance | ✅ |
| PR Description Agent | Generates full PR writeup: summary, motivation, approach, testing, risks | ✅ |
| Standards Agent | Learns your repo's specific patterns via ChromaDB + GitHub API | 🚧 |

## Built With

Python 3.11 · Anthropic SDK · Pydantic v2 · python-dotenv · pytest
