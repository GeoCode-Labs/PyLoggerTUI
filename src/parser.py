"""
Parser de logs com suporte a múltiplos formatos e detecção de tracebacks.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Union, Tuple
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
    # Localização no código (para logs estruturados como Loguru)
    module: Optional[str] = None
    function: Optional[str] = None
    code_line: Optional[int] = None

    def __post_init__(self):
        if self.traceback_lines is None:
            self.traceback_lines = []

    @property
    def location(self) -> Optional[str]:
        """Retorna a localização formatada (module.function:line)."""
        if self.module and self.function and self.code_line:
            return f"{self.module}.{self.function}:{self.code_line}"
        elif self.module and self.function:
            return f"{self.module}.{self.function}"
        elif self.module:
            return self.module
        return None


class LogParser:
    """Parser inteligente de logs com múltiplos formatos."""

    def __init__(self, custom_pattern: Optional[re.Pattern] = None, date_format: Optional[str] = None):
        """
        Inicializa o parser.

        Args:
            custom_pattern: Padrão regex customizado (tem prioridade sobre padrões padrão)
            date_format: Formato de data customizado (ex: "%d/%m/%Y %H:%M:%S")
        """
        self.custom_pattern = custom_pattern
        self.custom_date_format = date_format

    # Padrões de regex para diferentes formatos de log
    DEFAULT_PATTERNS = [
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

    # Padrão para detectar localização no código (estilo Loguru)
    # Exemplo: src.config.mongo:_close:40 ou module.submodule:function:123
    LOCATION_PATTERN = re.compile(
        r'(?P<module>[\w\.]+):(?P<function>\w+):(?P<line>\d+)'
    )

    def parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp de diferentes formatos."""
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S.%f",
        ]

        # Se tem formato customizado, tenta primeiro
        if self.custom_date_format:
            try:
                return datetime.strptime(timestamp_str.strip(), self.custom_date_format)
            except ValueError:
                pass

        # Tenta formatos padrão
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str.split('+')[0].split('Z')[0].strip(), fmt)
            except ValueError:
                continue
        return None

    def _extract_location(self, message: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        """
        Extrai informações de localização no código da mensagem.

        Procura por padrões como:
        - src.config.mongo:_close:40
        - module.submodule:function:123

        Retorna: (module, function, line_number) ou (None, None, None)
        """
        match = self.LOCATION_PATTERN.search(message)
        if match:
            module = match.group('module')
            function = match.group('function')
            try:
                line = int(match.group('line'))
                return (module, function, line)
            except ValueError:
                return (module, function, None)

        return (None, None, None)

    def parse_line(self, line: str, line_number: int) -> LogEntry:
        """Parse uma linha de log."""
        line = line.rstrip('\n')

        # Detecta início de traceback
        if self.TRACEBACK_START.search(line):
            return LogEntry(
                raw_line=line,
                line_number=line_number,
                level=LogLevel.ERROR,
                message="Traceback detected",
                is_traceback=True
            )

        # Detecta linha de traceback
        if self.TRACEBACK_LINE.search(line):
            return LogEntry(
                raw_line=line,
                line_number=line_number,
                level=LogLevel.ERROR,
                message=line.strip(),
                is_traceback=True
            )

        # Tenta primeiro com padrão customizado se existir
        patterns_to_try = []
        if self.custom_pattern:
            patterns_to_try.append(self.custom_pattern)
        patterns_to_try.extend(self.DEFAULT_PATTERNS)

        # Tenta parsear com cada padrão
        for pattern in patterns_to_try:
            match = pattern.search(line)
            if match:
                groups = match.groupdict()

                timestamp = None
                if 'timestamp' in groups and groups['timestamp']:
                    timestamp = self.parse_timestamp(groups['timestamp'])

                level = LogLevel.from_string(groups.get('level', 'UNKNOWN'))
                message = groups.get('message', '').strip()

                # Extrai informações de localização (se presentes)
                module, function, code_line = self._extract_location(message)

                return LogEntry(
                    raw_line=line,
                    line_number=line_number,
                    timestamp=timestamp,
                    level=level,
                    message=message,
                    module=module,
                    function=function,
                    code_line=code_line
                )

        # Se não match nenhum padrão, retorna entrada simples
        return LogEntry(
            raw_line=line,
            line_number=line_number,
            message=line
        )

    def parse_file(self, file_path: Path) -> List[LogEntry]:
        """Parse um arquivo de log completo usando este parser."""
        entries = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    entry = self.parse_line(line, line_num)
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

    @staticmethod
    def create_parser(file_path: Path) -> 'LogParser':
        """
        Cria um parser apropriado para o arquivo.
        Procura por config.yml na mesma pasta do arquivo.
        """
        from .config import ConfigLoader

        config = ConfigLoader.find_config(file_path)
        if config:
            pattern = config.to_regex()
            return LogParser(custom_pattern=pattern, date_format=config.date_format)
        else:
            return LogParser()

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
