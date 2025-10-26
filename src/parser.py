"""
Parser de logs com suporte a múltiplos formatos e detecção de tracebacks.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pathlib import Path


class LogLevel(Enum):
    """Níveis de log suportados."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    SUCCESS = "SUCCESS"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_string(cls, level_str: str) -> "LogLevel":
        """Converte string para LogLevel."""
        level_upper = level_str.upper()
        for level in cls:
            if level.value == level_upper:
                return level
        return cls.UNKNOWN


@dataclass
class LogEntry:
    """Representa uma entrada de log parseada."""
    raw_line: str
    line_number: int
    timestamp: Optional[datetime] = None
    level: LogLevel = LogLevel.UNKNOWN
    message: str = ""
    is_traceback: bool = False
    traceback_lines: List[str] = None
    file_path: Optional[str] = None

    def __post_init__(self):
        if self.traceback_lines is None:
            self.traceback_lines = []


class LogParser:
    """Parser inteligente de logs com múltiplos formatos."""

    # Padrões de regex para diferentes formatos de log
    PATTERNS = [
        # [2025-10-24 14:09:25] INFO | Message
        re.compile(
            r'\[(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s*'
            r'(?P<level>\w+)\s*[\|\:]\s*(?P<message>.*)'
        ),
        # 2025-10-24 14:09:25 - INFO - Message
        re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*-\s*'
            r'(?P<level>\w+)\s*-\s*(?P<message>.*)'
        ),
        # INFO: Message (simples)
        re.compile(
            r'(?P<level>DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|SUCCESS)\s*[\:\|]\s*'
            r'(?P<message>.*)'
        ),
        # Timestamp ISO: 2025-10-24T14:09:25.123Z INFO Message
        re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)\s+'
            r'(?P<level>\w+)\s+(?P<message>.*)'
        ),
    ]

    # Padrões para detectar tracebacks Python
    TRACEBACK_START = re.compile(r'Traceback \(most recent call last\):')
    TRACEBACK_LINE = re.compile(r'\s+File "(?P<file>.*)", line (?P<line>\d+), in (?P<func>.*)')
    TRACEBACK_ERROR = re.compile(r'^(?P<error>\w+Error|Exception):')

    @staticmethod
    def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp de diferentes formatos."""
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%fZ",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str.split('+')[0].split('Z')[0], fmt)
            except ValueError:
                continue
        return None

    @classmethod
    def parse_line(cls, line: str, line_number: int) -> LogEntry:
        """Parse uma linha de log."""
        line = line.rstrip('\n')

        # Detecta início de traceback
        if cls.TRACEBACK_START.search(line):
            return LogEntry(
                raw_line=line,
                line_number=line_number,
                level=LogLevel.ERROR,
                message="Traceback detected",
                is_traceback=True
            )

        # Detecta linha de traceback
        if cls.TRACEBACK_LINE.search(line):
            return LogEntry(
                raw_line=line,
                line_number=line_number,
                level=LogLevel.ERROR,
                message=line.strip(),
                is_traceback=True
            )

        # Tenta parsear com cada padrão
        for pattern in cls.PATTERNS:
            match = pattern.search(line)
            if match:
                groups = match.groupdict()

                timestamp = None
                if 'timestamp' in groups and groups['timestamp']:
                    timestamp = cls.parse_timestamp(groups['timestamp'])

                level = LogLevel.from_string(groups.get('level', 'UNKNOWN'))
                message = groups.get('message', '').strip()

                return LogEntry(
                    raw_line=line,
                    line_number=line_number,
                    timestamp=timestamp,
                    level=level,
                    message=message
                )

        # Se não match nenhum padrão, retorna entrada simples
        return LogEntry(
            raw_line=line,
            line_number=line_number,
            message=line
        )

    @classmethod
    def parse_file(cls, file_path: Path) -> List[LogEntry]:
        """Parse um arquivo de log completo."""
        entries = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    entry = cls.parse_line(line, line_num)
                    entry.file_path = str(file_path)
                    entries.append(entry)
        except Exception as e:
            # Retorna entrada de erro se falhar
            entries.append(LogEntry(
                raw_line=f"Error reading file: {e}",
                line_number=0,
                level=LogLevel.ERROR,
                message=f"Error reading file: {e}"
            ))

        return entries

    @classmethod
    def get_log_stats(cls, entries: List[LogEntry]) -> dict:
        """Calcula estatísticas dos logs."""
        stats = {
            'total': len(entries),
            'by_level': {},
            'with_timestamp': 0,
            'tracebacks': 0
        }

        for entry in entries:
            # Conta por nível
            level_name = entry.level.value
            stats['by_level'][level_name] = stats['by_level'].get(level_name, 0) + 1

            # Conta entradas com timestamp
            if entry.timestamp:
                stats['with_timestamp'] += 1

            # Conta tracebacks
            if entry.is_traceback:
                stats['tracebacks'] += 1

        return stats

    @classmethod
    def filter_by_level(cls, entries: List[LogEntry], level: LogLevel) -> List[LogEntry]:
        """Filtra entradas por nível de log."""
        return [entry for entry in entries if entry.level == level]

    @classmethod
    def search(cls, entries: List[LogEntry], query: str, regex: bool = False) -> List[LogEntry]:
        """Busca nos logs."""
        results = []

        if regex:
            try:
                pattern = re.compile(query, re.IGNORECASE)
            except re.error:
                return results

            for entry in entries:
                if pattern.search(entry.raw_line):
                    results.append(entry)
        else:
            query_lower = query.lower()
            for entry in entries:
                if query_lower in entry.raw_line.lower():
                    results.append(entry)

        return results
