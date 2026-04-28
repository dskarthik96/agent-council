"""
Live terminal UI — shows agent status and token usage in real time using Rich.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from skills.base import SkillResponse

_STATUS_ICON = {
    "waiting":  ("○", "dim"),
    "routing":  ("⟳ routing...", "yellow"),
    "thinking": ("● thinking...", "yellow"),
    "judging":  ("⚖ judging...", "cyan"),
    "done":     ("✓", "green"),
    "skipped":  ("–", "dim"),
}


class CouncilUI:
    """
    Real-time display panel. Call update() as agents progress;
    use as a context manager to wrap a decide() call.

    with CouncilUI(agents, question) as ui:
        leader.ui = ui
        result = leader.decide(question)
    """

    def __init__(self, agent_names: list[str], question: str) -> None:
        self.question = question
        self.console = Console()
        self._state: dict[str, dict] = {
            name: {"status": "waiting", "model": "", "tokens": "", "cached": ""}
            for name in ["leader"] + agent_names
        }
        self._live: Live | None = None

    # ── context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "CouncilUI":
        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=8,
            transient=False,
        )
        self._live.__enter__()
        return self

    def __exit__(self, *args) -> None:
        if self._live:
            self._live.update(self._render())
            self._live.__exit__(*args)

    # ── updates ───────────────────────────────────────────────────────────────

    def update(self, agent: str, status: str, response: "SkillResponse | None" = None) -> None:
        if agent not in self._state:
            self._state[agent] = {"status": "waiting", "model": "", "tokens": "", "cached": ""}
        self._state[agent]["status"] = status
        if response:
            self._state[agent]["model"] = response.model.split("-")[1] if "-" in response.model else response.model
            self._state[agent]["tokens"] = str(response.total_tokens)
            cached = response.cache_read_tokens
            self._state[agent]["cached"] = str(cached) if cached else ""
        if self._live:
            self._live.update(self._render())

    # ── rendering ─────────────────────────────────────────────────────────────

    def _render(self) -> Panel:
        table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1), expand=False)
        table.add_column("Agent", style="bold", min_width=12)
        table.add_column("Status", min_width=16)
        table.add_column("Model", style="dim", min_width=10)
        table.add_column("Tokens", justify="right", min_width=7)
        table.add_column("Cached ↩", justify="right", style="green", min_width=8)

        for name, data in self._state.items():
            icon, style = _STATUS_ICON.get(data["status"], ("?", ""))
            table.add_row(
                name,
                Text(icon, style=style),
                data["model"],
                data["tokens"],
                data["cached"],
            )

        q = self.question[:72] + ("…" if len(self.question) > 72 else "")
        return Panel(table, title=f"[bold]Council[/bold]  [dim]{q}[/dim]", border_style="dim")

    # ── summary print (called after live ends) ────────────────────────────────

    def print_result(self, result: "object") -> None:  # CouncilResult
        self.console.print()
        for name, resp in result.perspectives.items():
            self.console.rule(f"[bold]{name.title()}[/bold]", style="dim")
            self.console.print(resp.text.strip())
        self.console.rule("[bold cyan]Leader — Final Decision[/bold cyan]")
        self.console.print(result.decision.text.strip())
        self.console.print()
        self.console.print(
            f"[dim]Total tokens: {result.total_tokens} "
            f"({result.total_cached} read from cache)[/dim]"
        )
        self.console.print()
