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
        # Primeiro substitui os placeholders por marcadores temporários
        # Isso evita problemas com escaping
        pattern = self.format

        # Ordem importa: substituir padrões mais específicos primeiro
        replacements = [
            # Timestamp com formatação
            (r'{time:[^}]+}', '__TIMESTAMP__'),
            (r'{time}', '__TIMESTAMP__'),
            (r'{timestamp}', '__TIMESTAMP__'),

            # Level com formatação (como {level: <8})
            (r'{level:[^}]+}', '__LEVEL__'),
            (r'{level}', '__LEVEL__'),

            # Message
            (r'{message}', '__MESSAGE__'),

            # Outros campos
            (r'{module}', '__MODULE__'),
            (r'{function}', '__FUNCTION__'),
            (r'{line}', '__LINE__'),
            (r'{process.id}', '__PROCESS_ID__'),
            (r'{process.name}', '__PROCESS_NAME__'),
            (r'{thread.id}', '__THREAD_ID__'),
            (r'{thread.name}', '__THREAD_NAME__'),
            (r'{name}', '__NAME__'),
            (r'{file}', '__FILE__'),
        ]

        # Substitui placeholders por marcadores
        for placeholder, marker in replacements:
            pattern = re.sub(re.escape(placeholder), marker, pattern)

        # Agora escapa o que sobrou (caracteres especiais de regex)
        pattern = re.escape(pattern)

        # Substitui marcadores por grupos regex
        pattern = pattern.replace('__TIMESTAMP__', r'(?P<timestamp>[^\|\]]+)')
        pattern = pattern.replace('__LEVEL__', r'(?P<level>\w+)')
        pattern = pattern.replace('__MESSAGE__', r'(?P<message>.*)')
        pattern = pattern.replace('__MODULE__', r'(?P<module>[^\.\s\]]+)')
        pattern = pattern.replace('__FUNCTION__', r'(?P<function>[^\:\s\]]+)')
        pattern = pattern.replace('__LINE__', r'(?P<line>\d+)')
        pattern = pattern.replace('__PROCESS_ID__', r'(?P<process_id>\d+)')
        pattern = pattern.replace('__PROCESS_NAME__', r'(?P<process_name>[^\|\s\]]+)')
        pattern = pattern.replace('__THREAD_ID__', r'(?P<thread_id>\d+)')
        pattern = pattern.replace('__THREAD_NAME__', r'(?P<thread_name>[^\|\s\]]+)')
        pattern = pattern.replace('__NAME__', r'(?P<name>[^\s\]]+)')
        pattern = pattern.replace('__FILE__', r'(?P<file>[^\s\]]+)')

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
