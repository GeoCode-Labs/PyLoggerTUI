"""
Log Analyzer - TUI Application
Aplicação principal do visualizador de logs interativo.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane, Input, Static, Label, ProgressBar
from textual.containers import Container, Vertical, Horizontal, Center
from textual.binding import Binding
from textual.screen import Screen
from textual.worker import Worker, WorkerState
from rich.text import Text

from .parser import LogParser, LogEntry, LogLevel
from .widgets import LogViewer, StatsBar
from .dashboard import DashboardView


class LoadingScreen(Screen):
    """Tela de loading durante carregamento dos arquivos."""

    CSS = """
    LoadingScreen {
        align: center middle;
    }

    #loading-container {
        width: 60;
        height: 15;
        border: heavy $primary;
        background: $surface;
        padding: 2;
    }

    #loading-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #loading-status {
        text-align: center;
        color: $text;
        margin-top: 1;
        margin-bottom: 1;
    }

    #loading-details {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }

    ProgressBar {
        margin-top: 1;
    }
    """

    def __init__(self, total_files: int, **kwargs):
        super().__init__(**kwargs)
        self.total_files = total_files
        self.current_file = 0

    def compose(self) -> ComposeResult:
        """Compõe a tela de loading."""
        with Center(id="loading-container"):
            with Vertical():
                yield Label("📊 PyLoggerTUI", id="loading-title")
                yield Label("Loading log files...", id="loading-status")
                yield ProgressBar(total=100, show_eta=False, id="loading-progress")
                yield Label("", id="loading-details")

    def update_progress(self, current: int, total: int, filename: str = ""):
        """Atualiza o progresso."""
        self.current_file = current
        progress_pct = int((current / total) * 100) if total > 0 else 0

        # Atualiza barra de progresso
        progress_bar = self.query_one("#loading-progress", ProgressBar)
        progress_bar.update(progress=progress_pct)

        # Atualiza status
        status_label = self.query_one("#loading-status", Label)
        status_label.update(f"Loading file {current}/{total}...")

        # Atualiza detalhes
        details_label = self.query_one("#loading-details", Label)
        if filename:
            short_name = filename[-40:] if len(filename) > 40 else filename
            details_label.update(f"📄 {short_name}")


class SearchScreen(Screen):
    """Tela de busca."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]

    def __init__(self, log_viewer: LogViewer, **kwargs):
        super().__init__(**kwargs)
        self.log_viewer = log_viewer

    def compose(self) -> ComposeResult:
        """Compõe a tela de busca."""
        with Vertical():
            yield Static("Search in logs (ESC to close):", classes="search-header")
            yield Input(placeholder="Type to search...", id="search-input")

    def on_mount(self):
        """Quando a tela é montada."""
        input_widget = self.query_one("#search-input", Input)
        input_widget.focus()

    def on_input_changed(self, event: Input.Changed):
        """Quando o texto de busca muda."""
        query = event.value
        self.log_viewer.search(query)

    def action_close(self):
        """Fecha a tela de busca."""
        self.app.pop_screen()


class LogAnalyzerApp(App):
    """Aplicação principal do Log Analyzer."""

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $primary;
        color: $text;
    }

    Footer {
        background: $panel;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 0;
    }

    LogViewer {
        height: 1fr;
        border: solid $primary;
    }

    StatsBar {
        dock: bottom;
        height: 1;
        background: $panel;
        color: $text;
    }

    .search-header {
        height: 1;
        padding: 1;
        background: $primary;
        color: $text;
    }

    #search-input {
        margin: 1;
    }

    DashboardView {
        height: 1fr;
        padding: 1;
    }

    .dashboard-empty {
        height: 100%;
        content-align: center middle;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+f", "search", "Search"),
        Binding("ctrl+r", "reload", "Reload"),
        Binding("ctrl+d", "show_dashboard", "Dashboard"),
        Binding("s", "sort_by_date", "Sort by Date"),
        Binding("e", "filter_errors", "Errors"),
        Binding("w", "filter_warnings", "Warnings"),
        Binding("i", "filter_info", "Info"),
        Binding("a", "filter_all", "All"),
        Binding("tab", "next_tab", "Next Tab"),
        Binding("shift+tab", "prev_tab", "Prev Tab"),
    ]

    TITLE = "Log Analyzer - Professional Log Viewer"

    def __init__(self, paths: List[Path], watch: bool = False):
        super().__init__()
        self.watch = watch
        self.files_data: Dict[str, List[LogEntry]] = {}
        self.log_viewers: Dict[str, LogViewer] = {}
        self.stats_bar: Optional[StatsBar] = None
        self.dashboard: Optional[DashboardView] = None

        # Expande diretórios para arquivos .log
        self.paths = self._expand_paths(paths)

    def _expand_paths(self, paths: List[Path]) -> List[Path]:
        """Expande diretórios para incluir todos os arquivos .log."""
        expanded = []
        for path in paths:
            if path.is_file():
                expanded.append(path)
            elif path.is_dir():
                # Adiciona todos os .log do diretório
                log_files = sorted(path.glob("*.log"))
                if log_files:
                    expanded.extend(log_files)
                else:
                    # Se não encontrar .log, avisa mas não quebra
                    print(f"Warning: No .log files found in {path}")
        return expanded

    def compose(self) -> ComposeResult:
        """Compõe a interface."""
        yield Header()

        # TabbedContent com os arquivos
        with TabbedContent(id="tabs"):
            # Dashboard tab
            with TabPane("Dashboard", id="dashboard-tab"):
                self.dashboard = DashboardView()
                yield self.dashboard

            # Tabs para cada arquivo
            for path in self.paths:
                file_name = path.name
                # Cria ID válido (sem pontos, que não são permitidos)
                safe_id = f"file-{file_name.replace('.', '_')}"
                with TabPane(file_name, id=safe_id):
                    log_viewer = LogViewer()
                    self.log_viewers[str(path)] = log_viewer
                    yield log_viewer

        # Barra de estatísticas
        self.stats_bar = StatsBar()
        yield self.stats_bar

        yield Footer()

    def on_mount(self):
        """Quando a aplicação é montada."""
        # Mostra tela de loading e inicia carregamento em background
        if self.paths:
            self.loading_screen = LoadingScreen(total_files=len(self.paths))
            self.push_screen(self.loading_screen)
            # Inicia worker para carregar arquivos
            self.load_files_worker = self.run_worker(self.load_all_files_async(), exclusive=True)

    @staticmethod
    def load_single_file(path: Path, max_lines: Optional[int]) -> tuple[str, List[LogEntry]]:
        """Carrega um único arquivo (executado em thread separada)."""
        parser, config = LogParser.create_parser(path)

        # Se tem config, usa as opções de performance
        if max_lines is None and config:
            max_lines = config.max_lines

        smart_sample = config.smart_sample if config else False

        # Parse arquivo com limite de linhas e amostragem
        entries = parser.parse_file(path, max_lines=max_lines, smart_sample=smart_sample)
        return (str(path), entries)

    async def load_all_files_async(self):
        """Carrega todos os arquivos de forma assíncrona."""
        total = len(self.paths)

        for idx, path in enumerate(self.paths, 1):
            # Atualiza progress na tela de loading
            if hasattr(self, 'loading_screen'):
                self.loading_screen.update_progress(idx, total, path.name)

            # Carrega arquivo (bloqueia essa thread mas não a UI)
            path_str, entries = await self.run_in_thread(
                self.load_single_file, path, None
            )

            # Armazena dados
            self.files_data[path_str] = entries

            # Carrega no viewer correspondente
            if path_str in self.log_viewers:
                self.log_viewers[path_str].load_entries(entries)

        # Atualiza dashboard
        if self.dashboard:
            self.dashboard.load_data(self.files_data)

        # Atualiza stats bar
        self.update_stats_bar()

        # Fecha tela de loading
        if hasattr(self, 'loading_screen'):
            self.pop_screen()

    def update_stats_bar(self):
        """Atualiza a barra de estatísticas."""
        # Combina todas as entradas
        all_entries = []
        for entries in self.files_data.values():
            all_entries.extend(entries)

        if all_entries:
            stats = LogParser.get_log_stats(all_entries)
            if self.stats_bar:
                self.stats_bar.update_stats(stats)

    def get_current_viewer(self) -> Optional[LogViewer]:
        """Retorna o viewer atualmente ativo."""
        try:
            tabs = self.query_one("#tabs", TabbedContent)
            active_tab_id = tabs.active

            # Se é o dashboard, retorna None
            if active_tab_id == "dashboard-tab":
                return None

            # Encontra o viewer correspondente
            for path, viewer in self.log_viewers.items():
                file_name = Path(path).name
                safe_id = f"file-{file_name.replace('.', '_')}"
                if active_tab_id == safe_id:
                    return viewer

        except Exception:
            pass

        return None

    def action_search(self):
        """Abre a tela de busca."""
        viewer = self.get_current_viewer()
        if viewer:
            self.push_screen(SearchScreen(viewer))

    def action_reload(self):
        """Recarrega os arquivos."""
        self.load_all_files()
        self.notify("Files reloaded!")

    def action_show_dashboard(self):
        """Mostra o dashboard."""
        try:
            tabs = self.query_one("#tabs", TabbedContent)
            tabs.active = "dashboard-tab"
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def action_sort_by_date(self):
        """Alterna ordenação por data (None -> Asc -> Desc -> None)."""
        viewer = self.get_current_viewer()
        if viewer:
            status_msg = viewer.toggle_sort_by_date()
            self.notify(status_msg)
        else:
            self.notify("Sort by date only works on log tabs", severity="warning")

    def action_filter_errors(self):
        """Filtra apenas erros."""
        viewer = self.get_current_viewer()
        if viewer:
            viewer.apply_filter(LogLevel.ERROR)
            self.notify("Showing only ERRORS")

    def action_filter_warnings(self):
        """Filtra apenas warnings."""
        viewer = self.get_current_viewer()
        if viewer:
            viewer.apply_filter(LogLevel.WARNING)
            self.notify("Showing only WARNINGS")

    def action_filter_info(self):
        """Filtra apenas info."""
        viewer = self.get_current_viewer()
        if viewer:
            viewer.apply_filter(LogLevel.INFO)
            self.notify("Showing only INFO")

    def action_filter_all(self):
        """Mostra todos os logs."""
        viewer = self.get_current_viewer()
        if viewer:
            viewer.apply_filter(None)
            self.notify("Showing ALL logs")

    def action_next_tab(self):
        """Próxima tab."""
        try:
            tabs = self.query_one("#tabs", TabbedContent)
            # Textual TabbedContent não tem método next() direto
            # Mas podemos usar Tab key binding nativo
        except Exception:
            pass

    def action_prev_tab(self):
        """Tab anterior."""
        try:
            tabs = self.query_one("#tabs", TabbedContent)
            # Similar ao next_tab
        except Exception:
            pass


def main():
    """Entry point da aplicação."""
    parser = argparse.ArgumentParser(
        description="Log Analyzer - Professional TUI Log Viewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/logs/              # Open all .log files in directory
  %(prog)s application.log             # Open single file
  %(prog)s app.log error.log           # Open multiple files
  %(prog)s /path/to/logs/ --watch      # Auto-refresh mode

Keyboard Shortcuts:
  Ctrl+F    - Search
  Ctrl+R    - Reload files
  Ctrl+D    - Show Dashboard
  S         - Sort by date (toggle: OFF → Oldest→Newest → Newest→Oldest)
  E         - Filter Errors only
  W         - Filter Warnings only
  I         - Filter Info only
  A         - Show All logs
  Q         - Quit
        """
    )

    parser.add_argument(
        'paths',
        nargs='+',
        type=str,
        help='Log files or directories to analyze'
    )

    parser.add_argument(
        '--watch',
        action='store_true',
        help='Watch mode - auto-refresh on file changes'
    )

    args = parser.parse_args()

    # Converte paths para Path objects
    paths = [Path(p) for p in args.paths]

    # Valida paths
    valid_paths = []
    for path in paths:
        if path.exists():
            valid_paths.append(path)
        else:
            print(f"Warning: Path not found: {path}", file=sys.stderr)

    if not valid_paths:
        print("Error: No valid paths provided", file=sys.stderr)
        sys.exit(1)

    # Cria e roda a aplicação
    app = LogAnalyzerApp(valid_paths, watch=args.watch)

    try:
        app.run()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
