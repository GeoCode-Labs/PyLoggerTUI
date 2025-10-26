"""
Dashboard com visão geral e estatísticas dos logs.
"""

from datetime import datetime
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Label
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from typing import Dict, List
from pathlib import Path
from .parser import LogEntry, LogParser, LogLevel
from .charts import LogCharts


class DashboardView(ScrollableContainer):
    """View principal do dashboard."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.all_entries: List[LogEntry] = []
        self.files_data: Dict[str, List[LogEntry]] = {}

    def load_data(self, files_data: Dict[str, List[LogEntry]]):
        """Carrega dados dos arquivos."""
        self.files_data = files_data
        self.all_entries = []

        # Combina todas as entradas
        for entries in files_data.values():
            self.all_entries.extend(entries)

        self.refresh_dashboard()

    def refresh_dashboard(self):
        """Atualiza o dashboard com novos dados."""
        # Limpa e reconstrói
        self.remove_children()
        self.mount_all(self.compose())

    def compose(self) -> ComposeResult:
        """Compõe o dashboard."""
        if not self.all_entries:
            yield Static("No log data loaded.", classes="dashboard-empty")
            return

        # Header
        yield DashboardHeader(len(self.files_data), len(self.all_entries))

        # Visão geral de estatísticas
        stats = LogParser.get_log_stats(self.all_entries)
        yield StatsOverview(stats)

        # Estatísticas por arquivo
        yield FilesOverview(self.files_data)

        # Últimos erros
        recent_errors = self._get_recent_errors()
        if recent_errors:
            yield RecentErrors(recent_errors)

        # Charts (se houver timestamps)
        if any(e.timestamp for e in self.all_entries):
            yield ChartsSection(self.all_entries)

    def _get_recent_errors(self, limit: int = 10) -> List[LogEntry]:
        """Retorna os erros mais recentes."""
        errors = [
            e for e in self.all_entries
            if e.level in [LogLevel.ERROR, LogLevel.CRITICAL]
        ]

        # Ordena por timestamp se disponível, senão por line number
        if any(e.timestamp for e in errors):
            errors.sort(key=lambda x: x.timestamp or datetime.min, reverse=True)
        else:
            errors.sort(key=lambda x: x.line_number, reverse=True)

        return errors[:limit]


class DashboardHeader(Static):
    """Header do dashboard."""

    def __init__(self, num_files: int, num_entries: int, **kwargs):
        super().__init__(**kwargs)
        self.num_files = num_files
        self.num_entries = num_entries

    def render(self) -> Text:
        """Renderiza o header."""
        text = Text()
        text.append("=" * 80 + "\n", style="bold blue")
        text.append(" LOG ANALYZER DASHBOARD ".center(80) + "\n", style="bold cyan")
        text.append("=" * 80 + "\n", style="bold blue")
        text.append(f"\n Files: {self.num_files}  |  Total Entries: {self.num_entries:,}\n\n", style="bold")
        return text


class StatsOverview(Static):
    """Visão geral das estatísticas."""

    def __init__(self, stats: dict, **kwargs):
        super().__init__(**kwargs)
        self.stats = stats

    def render(self) -> Table:
        """Renderiza tabela de estatísticas."""
        table = Table(
            title="Overall Statistics",
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
            expand=True
        )

        table.add_column("Metric", style="cyan", width=30)
        table.add_column("Value", justify="right", style="green", width=15)
        table.add_column("Visual", width=35)

        # Total
        total = self.stats['total']
        table.add_row("Total Log Entries", f"{total:,}", "")

        # Por nível com barra visual
        by_level = self.stats.get('by_level', {})

        # Define cores por nível
        level_colors = {
            'ERROR': 'red',
            'CRITICAL': 'bold red',
            'WARNING': 'yellow',
            'WARN': 'yellow',
            'INFO': 'blue',
            'SUCCESS': 'green',
            'DEBUG': 'cyan',
        }

        for level in ['CRITICAL', 'ERROR', 'WARNING', 'WARN', 'INFO', 'SUCCESS', 'DEBUG']:
            if level in by_level:
                count = by_level[level]
                percentage = (count / total * 100) if total > 0 else 0
                bar_length = int(percentage / 2)  # Max 50 chars
                bar = "█" * bar_length

                color = level_colors.get(level, 'white')
                table.add_row(
                    f"{level} Logs",
                    f"{count:,}",
                    f"[{color}]{bar}[/] {percentage:.1f}%"
                )

        # Outros stats
        table.add_row("", "", "")
        table.add_row(
            "With Timestamp",
            f"{self.stats.get('with_timestamp', 0):,}",
            ""
        )

        tracebacks = self.stats.get('tracebacks', 0)
        if tracebacks > 0:
            table.add_row(
                "Tracebacks Detected",
                f"{tracebacks:,}",
                f"[red]{'!' * min(tracebacks, 20)}[/]"
            )

        return table


class FilesOverview(Static):
    """Visão geral dos arquivos."""

    def __init__(self, files_data: Dict[str, List[LogEntry]], **kwargs):
        super().__init__(**kwargs)
        self.files_data = files_data

    def render(self) -> Table:
        """Renderiza tabela de arquivos."""
        table = Table(
            title="Files Overview",
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
            expand=True
        )

        table.add_column("File", style="cyan", width=40)
        table.add_column("Entries", justify="right", style="green", width=10)
        table.add_column("Errors", justify="right", style="red", width=10)
        table.add_column("Warnings", justify="right", style="yellow", width=10)

        for file_path, entries in self.files_data.items():
            file_name = Path(file_path).name

            # Conta erros e warnings
            errors = sum(
                1 for e in entries
                if e.level in [LogLevel.ERROR, LogLevel.CRITICAL]
            )
            warnings = sum(
                1 for e in entries
                if e.level in [LogLevel.WARNING, LogLevel.WARN]
            )

            table.add_row(
                file_name,
                f"{len(entries):,}",
                f"{errors:,}" if errors > 0 else "-",
                f"{warnings:,}" if warnings > 0 else "-"
            )

        return table


class RecentErrors(Static):
    """Lista dos erros mais recentes."""

    def __init__(self, errors: List[LogEntry], **kwargs):
        super().__init__(**kwargs)
        self.errors = errors

    def render(self) -> Table:
        """Renderiza tabela de erros recentes."""
        table = Table(
            title="Recent Errors",
            show_header=True,
            header_style="bold red",
            border_style="red",
            expand=True
        )

        table.add_column("Time", style="cyan", width=20)
        table.add_column("Level", style="red", width=10)
        table.add_column("Message", style="white")

        for error in self.errors:
            time_str = error.timestamp.strftime("%Y-%m-%d %H:%M:%S") if error.timestamp else "N/A"
            message = error.message[:80] + "..." if len(error.message) > 80 else error.message

            table.add_row(
                time_str,
                error.level.value,
                message
            )

        return table


class ChartsSection(Static):
    """Seção com gráficos."""

    def __init__(self, entries: List[LogEntry], **kwargs):
        super().__init__(**kwargs)
        self.entries = entries

    def render(self) -> Text:
        """Renderiza os gráficos."""
        text = Text()

        text.append("\n" + "=" * 80 + "\n", style="bold blue")
        text.append(" CHARTS & VISUALIZATIONS ".center(80) + "\n", style="bold cyan")
        text.append("=" * 80 + "\n\n", style="bold blue")

        # Cria gráficos
        try:
            # Timeline
            text.append("Log Timeline\n", style="bold yellow")
            text.append("-" * 80 + "\n", style="dim")
            timeline = LogCharts.create_timeline_chart(self.entries, width=78, height=15)
            text.append(timeline + "\n\n")

            # Level Distribution
            text.append("Level Distribution\n", style="bold yellow")
            text.append("-" * 80 + "\n", style="dim")
            dist = LogCharts.create_level_distribution(self.entries, width=78, height=15)
            text.append(dist + "\n\n")

            # Error Timeline
            text.append("Errors & Warnings Timeline\n", style="bold yellow")
            text.append("-" * 80 + "\n", style="dim")
            error_timeline = LogCharts.create_error_timeline(self.entries, width=78, height=15)
            text.append(error_timeline + "\n\n")

        except Exception as e:
            text.append(f"Error generating charts: {e}\n", style="red")

        return text
