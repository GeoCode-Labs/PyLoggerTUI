"""
Widgets customizados para o Log Analyzer TUI.
"""

from textual.app import ComposeResult
from textual.widgets import Static, Label, RichLog
from textual.containers import Container, Vertical, Horizontal
from rich.text import Text
from rich.table import Table
from typing import List, Optional
from .parser import LogEntry, LogLevel


class LogLine(Static):
    """Widget para exibir uma linha de log com syntax highlighting."""

    LEVEL_COLORS = {
        LogLevel.DEBUG: "dim cyan",
        LogLevel.INFO: "blue",
        LogLevel.SUCCESS: "green",
        LogLevel.WARNING: "yellow",
        LogLevel.WARN: "yellow",
        LogLevel.ERROR: "red",
        LogLevel.CRITICAL: "bold red",
        LogLevel.UNKNOWN: "white",
    }

    def __init__(self, entry: LogEntry, **kwargs):
        self.entry = entry
        super().__init__(**kwargs)

    def render(self) -> Text:
        """Renderiza a linha com cores apropriadas."""
        text = Text()

        # Line number (dim)
        text.append(f"{self.entry.line_number:5d} ", style="dim")

        # Timestamp
        if self.entry.timestamp:
            text.append(
                f"[{self.entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] ",
                style="cyan"
            )

        # Level com cor
        level_color = self.LEVEL_COLORS.get(self.entry.level, "white")
        text.append(f"{self.entry.level.value:8s} ", style=level_color)

        # Separator
        text.append("| ", style="dim")

        # Message
        if self.entry.is_traceback:
            text.append(self.entry.message, style="red italic")
        else:
            text.append(self.entry.message)

        return text


class LogViewer(RichLog):
    """Widget principal para visualizar logs."""

    def __init__(self, **kwargs):
        super().__init__(
            highlight=True,
            markup=True,
            wrap=False,
            auto_scroll=False,
            **kwargs
        )
        self.entries: List[LogEntry] = []
        self.filtered_entries: List[LogEntry] = []
        self.current_filter: Optional[LogLevel] = None
        self.sort_order: Optional[str] = None  # None, 'asc', 'desc'

    def load_entries(self, entries: List[LogEntry]):
        """Carrega entradas de log."""
        self.entries = entries
        self.filtered_entries = entries
        self.refresh_display()

    def apply_filter(self, level: Optional[LogLevel] = None):
        """Aplica filtro por nível de log."""
        self.current_filter = level

        if level is None:
            self.filtered_entries = self.entries
        else:
            self.filtered_entries = [
                entry for entry in self.entries
                if entry.level == level
            ]

        self.refresh_display()

    def search(self, query: str):
        """Busca nas entradas."""
        if not query:
            self.filtered_entries = self.entries
        else:
            query_lower = query.lower()
            self.filtered_entries = [
                entry for entry in self.entries
                if query_lower in entry.raw_line.lower()
            ]

        self.refresh_display()

    def toggle_sort_by_date(self) -> str:
        """
        Alterna entre ordenação por data.
        Ciclo: None -> Ascending (antigo->novo) -> Descending (novo->antigo) -> None

        Retorna o estado atual de ordenação para feedback ao usuário.
        """
        from datetime import datetime

        if self.sort_order is None:
            # Ativa ordenação ascendente (mais antigo primeiro)
            self.sort_order = 'asc'
            self._apply_sort()
            return "Sorted: Oldest → Newest"
        elif self.sort_order == 'asc':
            # Ativa ordenação descendente (mais novo primeiro)
            self.sort_order = 'desc'
            self._apply_sort()
            return "Sorted: Newest → Oldest"
        else:
            # Desativa ordenação (ordem original)
            self.sort_order = None
            self._apply_sort()
            return "Sort: OFF (original order)"

    def _apply_sort(self):
        """Aplica a ordenação atual às entradas filtradas."""
        if self.sort_order is None:
            # Restaura ordem original (por linha)
            self.filtered_entries = sorted(self.filtered_entries, key=lambda e: e.line_number)
        elif self.sort_order == 'asc':
            # Ordena por timestamp ascendente (antigo -> novo)
            # Entradas sem timestamp vão para o fim
            from datetime import datetime
            self.filtered_entries = sorted(
                self.filtered_entries,
                key=lambda e: e.timestamp if e.timestamp else datetime.max
            )
        elif self.sort_order == 'desc':
            # Ordena por timestamp descendente (novo -> antigo)
            # Entradas sem timestamp vão para o fim
            from datetime import datetime
            self.filtered_entries = sorted(
                self.filtered_entries,
                key=lambda e: e.timestamp if e.timestamp else datetime.min,
                reverse=True
            )

        self.refresh_display()

    def refresh_display(self):
        """Atualiza a exibição dos logs."""
        self.clear()

        for entry in self.filtered_entries:
            self._write_entry(entry)

    def _write_entry(self, entry: LogEntry):
        """Escreve uma entrada no log viewer."""
        text = Text()

        # Line number
        text.append(f"{entry.line_number:5d} ", style="dim")

        # Timestamp
        if entry.timestamp:
            text.append(
                f"[{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] ",
                style="cyan"
            )

        # Level
        level_color = self._get_level_color(entry.level)
        text.append(f"{entry.level.value:8s} ", style=level_color)

        # Separator
        text.append("| ", style="dim")

        # Message
        if entry.is_traceback:
            text.append(entry.message, style="red italic")
        else:
            text.append(entry.message)

        self.write(text)

    @staticmethod
    def _get_level_color(level: LogLevel) -> str:
        """Retorna a cor para um nível de log."""
        colors = {
            LogLevel.DEBUG: "dim cyan",
            LogLevel.INFO: "blue",
            LogLevel.SUCCESS: "green",
            LogLevel.WARNING: "yellow",
            LogLevel.WARN: "yellow",
            LogLevel.ERROR: "red",
            LogLevel.CRITICAL: "bold red",
            LogLevel.UNKNOWN: "white",
        }
        return colors.get(level, "white")


class StatsBar(Static):
    """Barra de estatísticas no rodapé."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stats = {}

    def update_stats(self, stats: dict):
        """Atualiza as estatísticas exibidas."""
        self.stats = stats
        self.refresh()

    def render(self) -> Text:
        """Renderiza a barra de estatísticas."""
        text = Text()

        total = self.stats.get('total', 0)
        text.append(f" Total: {total} ", style="bold")

        # Stats por nível
        by_level = self.stats.get('by_level', {})

        if 'ERROR' in by_level or 'CRITICAL' in by_level:
            errors = by_level.get('ERROR', 0) + by_level.get('CRITICAL', 0)
            text.append(f"  Errors: {errors} ", style="bold red")

        if 'WARNING' in by_level or 'WARN' in by_level:
            warnings = by_level.get('WARNING', 0) + by_level.get('WARN', 0)
            text.append(f"  Warnings: {warnings} ", style="bold yellow")

        if 'INFO' in by_level:
            info = by_level.get('INFO', 0)
            text.append(f"  Info: {info} ", style="bold blue")

        if 'SUCCESS' in by_level:
            success = by_level.get('SUCCESS', 0)
            text.append(f"  Success: {success} ", style="bold green")

        # Tracebacks
        tracebacks = self.stats.get('tracebacks', 0)
        if tracebacks > 0:
            text.append(f"  Tracebacks: {tracebacks} ", style="bold red")

        return text


class FilterBar(Horizontal):
    """Barra com botões de filtro."""

    def compose(self) -> ComposeResult:
        """Compõe os botões de filtro."""
        yield Label("Filters: ", classes="filter-label")
        yield Label("[E] Errors", classes="filter-button")
        yield Label("[W] Warnings", classes="filter-button")
        yield Label("[I] Info", classes="filter-button")
        yield Label("[A] All", classes="filter-button")


class SearchBar(Horizontal):
    """Barra de busca."""

    def compose(self) -> ComposeResult:
        """Compõe a barra de busca."""
        from textual.widgets import Input
        yield Label("Search: ", classes="search-label")
        yield Input(placeholder="Type to search...", id="search-input")


class LogStats(Container):
    """Container com estatísticas detalhadas."""

    def __init__(self, stats: dict, **kwargs):
        super().__init__(**kwargs)
        self.stats = stats

    def compose(self) -> ComposeResult:
        """Compõe as estatísticas."""
        table = Table(title="Log Statistics", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Count", justify="right", style="green")

        # Total
        table.add_row("Total Lines", str(self.stats.get('total', 0)))

        # Por nível
        by_level = self.stats.get('by_level', {})
        for level, count in sorted(by_level.items()):
            table.add_row(f"{level} logs", str(count))

        # Com timestamp
        table.add_row(
            "With Timestamp",
            str(self.stats.get('with_timestamp', 0))
        )

        # Tracebacks
        table.add_row(
            "Tracebacks",
            str(self.stats.get('tracebacks', 0))
        )

        yield Static(table)
