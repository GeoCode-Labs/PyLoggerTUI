"""
Configuration loader for custom log formats.
"""

import re
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LogConfig:
    """Configuração de formato de log."""
    format: str
    date_format: Optional[str] = None

    def to_regex(self) -> re.Pattern:
        """
        Converte o formato para regex.

        Formato suportado:
        - {time} ou {timestamp} -> timestamp
        - {level} -> nível do log
        - {message} -> mensagem
        - {module}, {function}, {line}, {process.id}, etc -> ignorados no parse básico

        Exemplo:
        "[ {time} | process: {process.id} | {level: <8}] {module}.{function}:{line} {message}"
        """
        # Escapa caracteres especiais do regex
        pattern = re.escape(self.format)

        # Substitui os placeholders por grupos de captura
        replacements = {
            # Timestamp - vários formatos possíveis
            r'\{time\}': r'(?P<timestamp>[^\|\]]+)',
            r'\{timestamp\}': r'(?P<timestamp>[^\|\]]+)',
            r'\{time:[^\}]+\}': r'(?P<timestamp>[^\|\]]+)',

            # Level - pode ter formatação como {level: <8}
            r'\{level\}': r'(?P<level>\w+)',
            r'\{level:[^\}]+\}': r'(?P<level>\w+)',

            # Message - captura tudo até o final
            r'\{message\}': r'(?P<message>.*)',

            # Outros campos - captura até o próximo separador
            r'\{module\}': r'(?P<module>[^\.\s\]]+)',
            r'\{function\}': r'(?P<function>[^\:\s\]]+)',
            r'\{line\}': r'(?P<line>\d+)',
            r'\{process\.id\}': r'(?P<process_id>\d+)',
            r'\{process\.name\}': r'(?P<process_name>[^\|\s\]]+)',
            r'\{thread\.id\}': r'(?P<thread_id>\d+)',
            r'\{thread\.name\}': r'(?P<thread_name>[^\|\s\]]+)',
            r'\{name\}': r'(?P<name>[^\s\]]+)',
            r'\{file\}': r'(?P<file>[^\s\]]+)',
        }

        for placeholder, regex_group in replacements.items():
            pattern = re.sub(placeholder, regex_group, pattern)

        # Remove escapes desnecessários dos grupos de captura
        pattern = pattern.replace(r'\(', '(').replace(r'\)', ')')
        pattern = pattern.replace(r'\?', '?')
        pattern = pattern.replace(r'\<', '<').replace(r'\>', '>')
        pattern = pattern.replace(r'\|', '|')

        try:
            return re.compile(pattern)
        except re.error as e:
            # Se falhar, retorna None e usa padrões padrão
            print(f"Warning: Failed to compile custom format regex: {e}")
            return None


class ConfigLoader:
    """Carregador de configurações de log."""

    @staticmethod
    def load_from_file(config_path: Path) -> Optional[LogConfig]:
        """Carrega configuração de um arquivo YAML."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                return None

            # Suporta tanto 'format' quanto 'log_format'
            log_format = data.get('format') or data.get('log_format')
            if not log_format:
                return None

            date_format = data.get('date_format') or data.get('time_format')

            return LogConfig(
                format=log_format,
                date_format=date_format
            )

        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            return None

    @staticmethod
    def find_config(log_path: Path) -> Optional[LogConfig]:
        """
        Procura por config.yml na mesma pasta do arquivo de log.

        Ordem de busca:
        1. config.yml no mesmo diretório do arquivo de log
        2. .loggerconfig.yml no mesmo diretório
        3. logger.yml no mesmo diretório
        """
        if log_path.is_file():
            directory = log_path.parent
        else:
            directory = log_path

        config_names = ['config.yml', 'config.yaml', '.loggerconfig.yml', 'logger.yml']

        for config_name in config_names:
            config_path = directory / config_name
            if config_path.exists():
                config = ConfigLoader.load_from_file(config_path)
                if config:
                    return config

        return None
