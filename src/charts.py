"""
Geração de gráficos para visualização de logs usando plotext.
"""

from typing import List, Dict
from datetime import datetime, timedelta
from collections import defaultdict
import plotext as plt
from .parser import LogEntry, LogLevel


class LogCharts:
    """Gerador de gráficos para logs."""

    @staticmethod
    def create_timeline_chart(entries: List[LogEntry], width: int = 80, height: int = 20) -> str:
        """
        Cria gráfico de timeline mostrando distribuição de logs ao longo do tempo.
        """
        # Filtra apenas entradas com timestamp
        entries_with_time = [e for e in entries if e.timestamp]

        if not entries_with_time:
            return "No timestamp data available for timeline chart."

        # Agrupa por hora
        hourly_counts = defaultdict(int)

        for entry in entries_with_time:
            # Arredonda para hora
            hour_key = entry.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour_key] += 1

        # Ordena por timestamp
        sorted_hours = sorted(hourly_counts.keys())
        counts = [hourly_counts[hour] for hour in sorted_hours]
        labels = [hour.strftime("%H:%M") for hour in sorted_hours]

        # Cria gráfico
        plt.clf()
        plt.plot_size(width, height)
        plt.plot(labels, counts, marker="braille")
        plt.title("Log Timeline - Events per Hour")
        plt.xlabel("Time")
        plt.ylabel("Count")

        # Retorna como string
        return plt.build()

    @staticmethod
    def create_level_distribution(entries: List[LogEntry], width: int = 80, height: int = 20) -> str:
        """
        Cria gráfico de barras mostrando distribuição por nível de log.
        """
        # Conta por nível
        level_counts = defaultdict(int)

        for entry in entries:
            level_counts[entry.level.value] += 1

        # Ordena por contagem
        sorted_levels = sorted(level_counts.items(), key=lambda x: x[1], reverse=True)
        labels = [level for level, _ in sorted_levels]
        counts = [count for _, count in sorted_levels]

        # Cria gráfico de barras
        plt.clf()
        plt.plot_size(width, height)
        plt.bar(labels, counts, orientation="h")
        plt.title("Log Level Distribution")
        plt.xlabel("Count")

        return plt.build()

    @staticmethod
    def create_heatmap(entries: List[LogEntry], width: int = 80, height: int = 20) -> str:
        """
        Cria heatmap mostrando distribuição de logs por hora do dia e dia da semana.
        """
        entries_with_time = [e for e in entries if e.timestamp]

        if not entries_with_time:
            return "No timestamp data available for heatmap."

        # Matriz de contagens [dia da semana][hora]
        heatmap_data = [[0 for _ in range(24)] for _ in range(7)]

        for entry in entries_with_time:
            day_of_week = entry.timestamp.weekday()  # 0 = Monday
            hour = entry.timestamp.hour
            heatmap_data[day_of_week][hour] += 1

        # Cria visualização simplificada
        plt.clf()
        plt.plot_size(width, height)

        # Plotext não tem heatmap nativo, vamos usar uma representação alternativa
        # Vamos criar um gráfico de barras empilhadas por dia
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        totals = [sum(day_data) for day_data in heatmap_data]

        plt.bar(days, totals)
        plt.title("Log Distribution by Day of Week")
        plt.xlabel("Day")
        plt.ylabel("Count")

        return plt.build()

    @staticmethod
    def create_error_timeline(entries: List[LogEntry], width: int = 80, height: int = 20) -> str:
        """
        Cria timeline apenas de erros e warnings.
        """
        # Filtra apenas errors e warnings com timestamp
        error_entries = [
            e for e in entries
            if e.timestamp and e.level in [LogLevel.ERROR, LogLevel.CRITICAL, LogLevel.WARNING, LogLevel.WARN]
        ]

        if not error_entries:
            return "No errors or warnings with timestamp found."

        # Agrupa por hora
        hourly_errors = defaultdict(lambda: {'errors': 0, 'warnings': 0})

        for entry in error_entries:
            hour_key = entry.timestamp.replace(minute=0, second=0, microsecond=0)

            if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                hourly_errors[hour_key]['errors'] += 1
            else:
                hourly_errors[hour_key]['warnings'] += 1

        # Ordena por timestamp
        sorted_hours = sorted(hourly_errors.keys())
        error_counts = [hourly_errors[hour]['errors'] for hour in sorted_hours]
        warning_counts = [hourly_errors[hour]['warnings'] for hour in sorted_hours]
        labels = [hour.strftime("%H:%M") for hour in sorted_hours]

        # Cria gráfico com múltiplas linhas
        plt.clf()
        plt.plot_size(width, height)
        plt.plot(labels, error_counts, label="Errors", marker="braille")
        plt.plot(labels, warning_counts, label="Warnings", marker="braille")
        plt.title("Errors and Warnings Timeline")
        plt.xlabel("Time")
        plt.ylabel("Count")

        return plt.build()

    @staticmethod
    def create_summary_stats(entries: List[LogEntry]) -> str:
        """
        Cria sumário de estatísticas textuais.
        """
        from .parser import LogParser

        stats = LogParser.get_log_stats(entries)

        lines = []
        lines.append("=" * 60)
        lines.append(" LOG STATISTICS SUMMARY ".center(60))
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Total Entries: {stats['total']}")
        lines.append(f"With Timestamp: {stats['with_timestamp']}")
        lines.append(f"Tracebacks: {stats['tracebacks']}")
        lines.append("")
        lines.append("-" * 60)
        lines.append(" Distribution by Level ".center(60))
        lines.append("-" * 60)

        # Ordena por contagem
        by_level = stats.get('by_level', {})
        sorted_levels = sorted(by_level.items(), key=lambda x: x[1], reverse=True)

        for level, count in sorted_levels:
            percentage = (count / stats['total'] * 100) if stats['total'] > 0 else 0
            bar_length = int(percentage / 2)  # Escala para 50 chars max
            bar = "█" * bar_length
            lines.append(f"{level:12s} {count:6d} ({percentage:5.1f}%) {bar}")

        lines.append("=" * 60)

        return "\n".join(lines)

    @staticmethod
    def create_all_charts(entries: List[LogEntry], width: int = 100, height: int = 20) -> Dict[str, str]:
        """
        Cria todos os gráficos disponíveis.
        """
        charts = {}

        charts['timeline'] = LogCharts.create_timeline_chart(entries, width, height)
        charts['level_distribution'] = LogCharts.create_level_distribution(entries, width, height)
        charts['heatmap'] = LogCharts.create_heatmap(entries, width, height)
        charts['error_timeline'] = LogCharts.create_error_timeline(entries, width, height)
        charts['summary'] = LogCharts.create_summary_stats(entries)

        return charts
