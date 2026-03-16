import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

import click
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

# Must be called before importing modules that read environment variables (e.g., Anthropic API key)
load_dotenv()

from core.diff_parser import parse_diff
from agents.diff_analyzer import analyze_diff
from agents.review_agent import (
    run_correctness_pass,
    run_security_pass,
    run_style_pass,
    run_performance_pass,
)
from agents.pr_description import generate_pr_description
from core.models import PRDescription, ReviewResult, Severity

console = Console()

# Maximum characters to show in PR preview panel
PR_PREVIEW_MAX_LENGTH = 400

# Timeout in seconds for subprocess and API operations
GIT_TIMEOUT = 30
GH_CLI_TIMEOUT = 60
REVIEW_PASS_TIMEOUT = 120

# Fallback sort order for unknown pass names (ensures they appear last)
UNKNOWN_PASS_SORT_ORDER = 99

# Valid git branch name pattern (alphanumeric, dash, underscore, slash, dot)
BRANCH_NAME_PATTERN = re.compile(r"^[\w./-]+$")

SEVERITY_COLORS = {
    Severity.CRITICAL: "bold red",
    Severity.WARNING: "yellow",
    Severity.SUGGESTION: "blue",
}


@click.group()
def main():
    """Preflight — AI code review before you open a PR."""
    pass


@main.command()
@click.option("--base", default="main", help="Base branch to diff against (default: main)")
def review(base):
    """Run all review passes on the current branch diff."""
    _validate_branch_name(base)
    
    diff = _get_diff(base)
    if diff is None:
        return
    if not diff.strip():
        console.print(f"[yellow]No changes found against {base}.[/yellow]")
        return

    with console.status("[bold]Analyzing diff...[/bold]"):
        changeset = analyze_diff(parse_diff(diff))

    console.print(f"\n[dim]Intent: {changeset.intent.value} · {len(changeset.files)} file(s) changed[/dim]\n")

    # Run all passes concurrently since they are independent
    pass_funcs = [
        run_correctness_pass,
        run_security_pass,
        run_style_pass,
        run_performance_pass,
    ]

    # Execute all passes concurrently and collect results
    with console.status("[bold]Running review passes...[/bold]"):
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_func = {executor.submit(pass_func, changeset): pass_func for pass_func in pass_funcs}
            results = []
            for future in as_completed(future_to_func):
                pass_func = future_to_func[future]
                pass_name = _get_pass_name(pass_func)
                try:
                    results.append(future.result(timeout=REVIEW_PASS_TIMEOUT))
                except TimeoutError:
                    console.print(f"[yellow]Warning: {pass_name} pass timed out[/yellow]")
                except Exception as e:
                    console.print(f"[yellow]Warning: {pass_name} pass failed: {e}[/yellow]")
    
    if not results:
        console.print("[yellow]All review passes failed to complete. Check your API key and network connection.[/yellow]")
        return
    
    # Sort results to maintain consistent output order (failed passes are omitted)
    pass_order = {"correctness": 0, "security": 1, "style": 2, "performance": 3}
    results.sort(key=lambda r: pass_order.get(r.pass_name, UNKNOWN_PASS_SORT_ORDER))
    
    for result in results:
        _print_result(result)


@main.command()
@click.option("--base", default="main", help="Base branch to diff against (default: main)")
@click.option("--title", default=None, help="Override generated title")
def pr(base, title):
    """Generate a PR description and open a PR via gh CLI."""
    _validate_branch_name(base)
    
    diff = _get_diff(base)
    if diff is None:
        return
    if not diff.strip():
        console.print(f"[yellow]No changes found against {base}.[/yellow]")
        return

    with console.status("[bold]Generating PR description...[/bold]"):
        changeset = analyze_diff(parse_diff(diff))
        desc = generate_pr_description(changeset)

    pr_title = title or desc.title
    body = _format_pr_body(desc)

    preview_body = body[:PR_PREVIEW_MAX_LENGTH] + "..." if len(body) > PR_PREVIEW_MAX_LENGTH else body
    console.print(Panel(f"[bold]{pr_title}[/bold]\n\n{preview_body}", title="PR Preview", border_style="blue"))

    if click.confirm("\nCreate PR?"):
        try:
            # Use --body-file with stdin to safely pass body content
            subprocess.run(
                ["gh", "pr", "create", "--title", pr_title, "--body-file", "-"],
                input=body,
                text=True,
                check=True,
                timeout=GH_CLI_TIMEOUT,
            )
        except FileNotFoundError:
            console.print("[red]Error: 'gh' CLI not found. Install it from https://cli.github.com/[/red]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error creating PR: {e}[/red]")
        except subprocess.TimeoutExpired:
            console.print("[red]Error: PR creation timed out. Check your network connection.[/red]")
    else:
        console.print("[dim]PR not created.[/dim]")


def _validate_branch_name(branch: str) -> None:
    """Validates branch name to prevent command injection."""
    if not BRANCH_NAME_PATTERN.match(branch):
        raise click.BadParameter(
            f"Invalid branch name '{branch}'. Use only alphanumeric characters, dashes, underscores, slashes, and dots."
        )


def _get_pass_name(pass_func) -> str:
    """Extracts a clean pass name from a pass function (e.g., run_security_pass -> security)."""
    return pass_func.__name__.replace("run_", "").replace("_pass", "")


def _get_diff(base: str) -> str | None:
    """Returns the git diff against the base branch, or None on error."""
    try:
        result = subprocess.run(
            ["git", "diff", base],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        console.print("[red]Git error: diff command timed out[/red]")
        return None
    
    if result.returncode != 0:
        error_msg = result.stderr.strip() or "Unknown git error"
        console.print(f"[red]Git error: {error_msg}[/red]")
        return None
    return result.stdout


def _format_pr_body(desc: PRDescription) -> str:
    """
    Formats a PRDescription into markdown body text.
    
    Each field is rendered as a ## header followed by its content.
    Fields are output in order: Summary, Motivation, Approach, Testing Notes, Risks, TODOs.
    Empty fields are omitted.
    """
    fields = [
        ("Summary", desc.summary),
        ("Motivation", desc.motivation),
        ("Approach", desc.approach),
        ("Testing Notes", desc.testing_notes),
        ("Risks", desc.risks),
        ("TODOs", desc.todos),
    ]
    parts = [f"## {name}\n{value}" for name, value in fields if value]
    return "\n\n".join(parts)


def _print_result(result: ReviewResult) -> None:
    """Prints a single ReviewResult to the console with colored severity indicators."""
    pass_label = result.pass_name.upper()
    color = "red" if any(c.severity == Severity.CRITICAL for c in result.comments) else "green"

    console.print(f"\n[bold {color}]── {pass_label} ──[/bold {color}]")
    console.print(f"[dim]{result.summary}[/dim]")

    for comment in result.comments:
        sev_color = SEVERITY_COLORS.get(comment.severity, "white")
        location = f"{comment.file}:{comment.line}" if comment.line else comment.file
        console.print(f"\n  [{sev_color}][{comment.severity.value.upper()}][/{sev_color}] [bold]{location}[/bold]")
        console.print(f"  {comment.message}")
        if comment.suggested_fix:
            console.print(f"  [dim]→ {comment.suggested_fix}[/dim]")
