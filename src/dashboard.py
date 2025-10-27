"""
Dashboard com visão geral e estatísticas dos logs.
"""

from datetime import datetime
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer, Grid
from textual.widgets import Static, Label, DataTable, Button
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

        # Erros por localização no código
        yield ErrorsByLocation(self.all_entries)

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


class DashboardHeader(Container):
    """Header do dashboard moderno."""

    DEFAULT_CSS = """
    DashboardHeader {
        height: auto;
        padding: 1 2;
        background: $primary;
        border: heavy $accent;
        margin-bottom: 1;
    }

    DashboardHeader .dashboard-title {
        text-align: center;
        text-style: bold;
        color: $text;
        content-align: center middle;
    }

    DashboardHeader .stats-grid {
        height: auto;
        grid-size: 2;
        grid-gutter: 1;
        padding: 1;
    }

    DashboardHeader .stat-card {
        height: 3;
        border: solid $accent;
        background: $panel;
        padding: 0 1;
        text-align: center;
        content-align: center middle;
    }
    """

    def __init__(self, num_files: int, num_entries: int, **kwargs):
        super().__init__(**kwargs)
        self.num_files = num_files
        self.num_entries = num_entries

    def compose(self) -> ComposeResult:
        """Compõe o header moderno."""
        yield Label("📊 LOG ANALYZER DASHBOARD", classes="dashboard-title")
        with Grid(classes="stats-grid"):
            yield Label(f"📁 {self.num_files}\nFiles", classes="stat-card")
            yield Label(f"📝 {self.num_entries:,}\nTotal Entries", classes="stat-card")


class StatsOverview(Container):
    """Visão geral das estatísticas com DataTable moderna."""

    DEFAULT_CSS = """
    StatsOverview {
        height: auto;
        border: solid $accent;
        background: $panel;
        margin-bottom: 1;
        padding: 1;
    }

    StatsOverview > Label {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    StatsOverview > DataTable {
        height: auto;
        max-height: 20;
    }
    """

    def __init__(self, stats: dict, **kwargs):
        super().__init__(**kwargs)
        self.stats = stats

    def compose(self) -> ComposeResult:
        """Compõe a tabela de estatísticas."""
        yield Label("📈 OVERALL STATISTICS")

        table = DataTable(zebra_stripes=True)
        table.add_columns("Metric", "Value", "Visual")

        # Total
        total = self.stats['total']
        table.add_row("Total Log Entries", f"{total:,}", "")

        # Por nível com barra visual
        by_level = self.stats.get('by_level', {})

        # Define ícones e símbolos por nível
        level_icons = {
            'CRITICAL': '🔴',
            'ERROR': '❌',
            'WARNING': '⚠️',
            'WARN': '⚠️',
            'INFO': 'ℹ️',
            'SUCCESS': '✅',
            'DEBUG': '🐛',
        }

        for level in ['CRITICAL', 'ERROR', 'WARNING', 'WARN', 'INFO', 'SUCCESS', 'DEBUG']:
            if level in by_level:
                count = by_level[level]
                percentage = (count / total * 100) if total > 0 else 0
                bar_length = int(percentage / 3)  # Max ~33 chars
                bar = "█" * bar_length

                icon = level_icons.get(level, '•')
                table.add_row(
                    f"{icon} {level} Logs",
                    f"{count:,}",
                    f"{bar} {percentage:.1f}%"
                )

        # Outros stats
        table.add_row("─" * 20, "─" * 10, "─" * 30)
        table.add_row(
            "⏰ With Timestamp",
            f"{self.stats.get('with_timestamp', 0):,}",
            ""
        )

        tracebacks = self.stats.get('tracebacks', 0)
        if tracebacks > 0:
            table.add_row(
                "🔥 Tracebacks Detected",
                f"{tracebacks:,}",
                "!" * min(tracebacks, 20)
            )

        yield table


class FilesOverview(Container):
    """Visão geral dos arquivos com DataTable moderna."""

    DEFAULT_CSS = """
    FilesOverview {
        height: auto;
        border: solid $accent;
        background: $panel;
        margin-bottom: 1;
        padding: 1;
    }

    FilesOverview > Label {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    FilesOverview > DataTable {
        height: auto;
        max-height: 15;
    }
    """

    def __init__(self, files_data: Dict[str, List[LogEntry]], **kwargs):
        super().__init__(**kwargs)
        self.files_data = files_data

    def compose(self) -> ComposeResult:
        """Compõe a tabela de arquivos."""
        yield Label("📁 FILES OVERVIEW")

        table = DataTable(zebra_stripes=True, cursor_type="row")
        table.add_columns("File", "Entries", "Errors", "Warnings", "Status")

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

            # Define status com ícone
            if errors > 0:
                status = "❌ Issues"
            elif warnings > 0:
                status = "⚠️ Warnings"
            else:
                status = "✅ OK"

            table.add_row(
                f"📄 {file_name}",
                f"{len(entries):,}",
                f"{errors:,}" if errors > 0 else "-",
                f"{warnings:,}" if warnings > 0 else "-",
                status
            )

        yield table


class RecentErrors(Container):
    """Lista dos erros mais recentes com DataTable moderna."""

    DEFAULT_CSS = """
    RecentErrors {
        height: auto;
        border: heavy $error;
        background: $panel;
        margin-bottom: 1;
        padding: 1;
    }

    RecentErrors > Label {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }

    RecentErrors > DataTable {
        height: auto;
        max-height: 15;
    }
    """

    def __init__(self, errors: List[LogEntry], **kwargs):
        super().__init__(**kwargs)
        self.errors = errors

    def compose(self) -> ComposeResult:
        """Compõe a tabela de erros recentes."""
        yield Label("🔥 RECENT ERRORS")

        table = DataTable(zebra_stripes=True, cursor_type="row")
        table.add_columns("Time", "Level", "Message")

        for error in self.errors:
            time_str = error.timestamp.strftime("%Y-%m-%d %H:%M:%S") if error.timestamp else "N/A"
            message = error.message[:80] + "..." if len(error.message) > 80 else error.message

            # Ícone baseado no level
            level_icon = "🔴" if error.level == LogLevel.CRITICAL else "❌"

            table.add_row(
                f"⏰ {time_str}",
                f"{level_icon} {error.level.value}",
                message
            )

        yield table


class ErrorsByLocation(Container):
    """Tabela mostrando erros agrupados por localização no código."""

    DEFAULT_CSS = """
    ErrorsByLocation {
        height: auto;
        border: solid $warning;
        background: $panel;
        margin-bottom: 1;
        padding: 1;
    }

    ErrorsByLocation > Label {
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }

    ErrorsByLocation > DataTable {
        height: auto;
        max-height: 18;
    }
    """

    def __init__(self, entries: List[LogEntry], **kwargs):
        super().__init__(**kwargs)
        self.entries = entries

    def compose(self) -> ComposeResult:
        """Compõe a tabela de erros por localização."""
        from collections import Counter

        yield Label("📍 ERRORS BY CODE LOCATION")

        table = DataTable(zebra_stripes=True, cursor_type="row")

        # Filtra apenas erros e críticos que tem localização
        errors_with_location = [
            e for e in self.entries
            if e.level in [LogLevel.ERROR, LogLevel.CRITICAL] and e.location
        ]

        if not errors_with_location:
            table.add_columns("Message")
            table.add_row("No errors with location info")
            yield table
            return

        # Conta erros por localização
        location_counter = Counter(e.location for e in errors_with_location)

        table.add_columns("Location", "Module", "Function", "Line", "Count")

        # Adiciona as top 15 localizações com mais erros
        for location, count in location_counter.most_common(15):
            # Encontra um entry com essa localização para pegar detalhes
            entry = next((e for e in errors_with_location if e.location == location), None)
            if entry:
                table.add_row(
                    f"📌 {location}",
                    entry.module or "-",
                    entry.function or "-",
                    str(entry.code_line) if entry.code_line else "-",
                    f"🔢 {count}"
                )

        yield table


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
