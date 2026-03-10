## About

Preflight analyzes a git diff through 4 focused AI passes — each a separate Claude call for higher quality than one giant prompt.

## Agents

| Agent | Description | Status |
|-------|-------------|--------|
| **Diff Analyzer** | Extracts function/class changes and classifies intent (feature / bugfix / refactor) | ✅ |
| **Review Agent** | 4 passes: Correctness, Security, Style, Performance | ✅ |
| **PR Description Agent** | Generates full PR writeup: summary, motivation, approach, testing, risks | 🚧 |
| **Standards Agent** | Learns your repo's specific patterns via ChromaDB + GitHub API | 🚧 |

## Built With

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Claude](https://img.shields.io/badge/Anthropic-Claude-orange)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-green)
![Click](https://img.shields.io/badge/CLI-Click-white)
