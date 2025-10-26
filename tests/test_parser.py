"""
Testes para o parser de logs.
"""

import unittest
from datetime import datetime
from pathlib import Path
import tempfile
import os

from src.parser import LogParser, LogEntry, LogLevel


class TestLogParser(unittest.TestCase):
    """Testes para o LogParser."""

    def test_parse_line_with_timestamp(self):
        """Testa parse de linha com timestamp."""
        line = "[2025-10-24 14:09:25] INFO | Server started successfully"
        entry = LogParser.parse_line(line, 1)

        self.assertEqual(entry.line_number, 1)
        self.assertEqual(entry.level, LogLevel.INFO)
        self.assertEqual(entry.message, "Server started successfully")
        self.assertIsNotNone(entry.timestamp)

    def test_parse_line_error(self):
        """Testa parse de linha com erro."""
        line = "[2025-10-24 14:09:25] ERROR | Connection failed"
        entry = LogParser.parse_line(line, 1)

        self.assertEqual(entry.level, LogLevel.ERROR)
        self.assertEqual(entry.message, "Connection failed")

    def test_parse_line_warning(self):
        """Testa parse de linha com warning."""
        line = "[2025-10-24 14:09:25] WARNING | Low memory"
        entry = LogParser.parse_line(line, 1)

        self.assertEqual(entry.level, LogLevel.WARNING)

    def test_parse_line_success(self):
        """Testa parse de linha com success."""
        line = "[2025-10-24 14:09:25] SUCCESS | Operation completed"
        entry = LogParser.parse_line(line, 1)

        self.assertEqual(entry.level, LogLevel.SUCCESS)

    def test_parse_line_no_timestamp(self):
        """Testa parse de linha sem timestamp."""
        line = "INFO: Simple log message"
        entry = LogParser.parse_line(line, 1)

        self.assertEqual(entry.level, LogLevel.INFO)
        self.assertIsNone(entry.timestamp)

    def test_parse_traceback(self):
        """Testa detecção de traceback."""
        line = "Traceback (most recent call last):"
        entry = LogParser.parse_line(line, 1)

        self.assertTrue(entry.is_traceback)
        self.assertEqual(entry.level, LogLevel.ERROR)

    def test_parse_file(self):
        """Testa parse de arquivo completo."""
        # Cria arquivo temporário
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("[2025-10-24 14:09:25] INFO | Line 1\n")
            f.write("[2025-10-24 14:09:26] ERROR | Line 2\n")
            f.write("[2025-10-24 14:09:27] WARNING | Line 3\n")
            temp_path = f.name

        try:
            entries = LogParser.parse_file(Path(temp_path))

            self.assertEqual(len(entries), 3)
            self.assertEqual(entries[0].level, LogLevel.INFO)
            self.assertEqual(entries[1].level, LogLevel.ERROR)
            self.assertEqual(entries[2].level, LogLevel.WARNING)

        finally:
            os.unlink(temp_path)

    def test_get_log_stats(self):
        """Testa cálculo de estatísticas."""
        entries = [
            LogEntry(raw_line="line1", line_number=1, level=LogLevel.INFO),
            LogEntry(raw_line="line2", line_number=2, level=LogLevel.ERROR),
            LogEntry(raw_line="line3", line_number=3, level=LogLevel.ERROR),
            LogEntry(raw_line="line4", line_number=4, level=LogLevel.WARNING),
        ]

        stats = LogParser.get_log_stats(entries)

        self.assertEqual(stats['total'], 4)
        self.assertEqual(stats['by_level']['INFO'], 1)
        self.assertEqual(stats['by_level']['ERROR'], 2)
        self.assertEqual(stats['by_level']['WARNING'], 1)

    def test_filter_by_level(self):
        """Testa filtro por nível."""
        entries = [
            LogEntry(raw_line="line1", line_number=1, level=LogLevel.INFO),
            LogEntry(raw_line="line2", line_number=2, level=LogLevel.ERROR),
            LogEntry(raw_line="line3", line_number=3, level=LogLevel.ERROR),
        ]

        filtered = LogParser.filter_by_level(entries, LogLevel.ERROR)

        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(e.level == LogLevel.ERROR for e in filtered))

    def test_search_simple(self):
        """Testa busca simples."""
        entries = [
            LogEntry(raw_line="Server started", line_number=1, level=LogLevel.INFO),
            LogEntry(raw_line="Connection error", line_number=2, level=LogLevel.ERROR),
            LogEntry(raw_line="Server stopped", line_number=3, level=LogLevel.INFO),
        ]

        results = LogParser.search(entries, "server")

        self.assertEqual(len(results), 2)

    def test_search_regex(self):
        """Testa busca com regex."""
        entries = [
            LogEntry(raw_line="Error 404", line_number=1, level=LogLevel.ERROR),
            LogEntry(raw_line="Error 500", line_number=2, level=LogLevel.ERROR),
            LogEntry(raw_line="Success 200", line_number=3, level=LogLevel.INFO),
        ]

        results = LogParser.search(entries, r"Error \d+", regex=True)

        self.assertEqual(len(results), 2)

    def test_parse_timestamp(self):
        """Testa parse de diferentes formatos de timestamp."""
        # Formato padrão
        ts1 = LogParser.parse_timestamp("2025-10-24 14:09:25")
        self.assertIsNotNone(ts1)
        self.assertEqual(ts1.year, 2025)

        # Com milissegundos
        ts2 = LogParser.parse_timestamp("2025-10-24 14:09:25.123")
        self.assertIsNotNone(ts2)

        # ISO format
        ts3 = LogParser.parse_timestamp("2025-10-24T14:09:25")
        self.assertIsNotNone(ts3)

    def test_parse_alternative_formats(self):
        """Testa parse de formatos alternativos de log."""
        # Formato com hífen
        line1 = "2025-10-24 14:09:25 - INFO - Message"
        entry1 = LogParser.parse_line(line1, 1)
        self.assertEqual(entry1.level, LogLevel.INFO)

        # Formato ISO
        line2 = "2025-10-24T14:09:25.123Z INFO Message here"
        entry2 = LogParser.parse_line(line2, 1)
        self.assertEqual(entry2.level, LogLevel.INFO)


if __name__ == '__main__':
    unittest.main()
