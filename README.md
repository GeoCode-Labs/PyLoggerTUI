# PyLoggerTUI - Visualizador Profissional de Logs

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Visualizador de logs interativo no terminal com suporte a múltiplos arquivos, análise em tempo real, gráficos e estatísticas profissionais.

![PyLoggerTUI Demo](https://via.placeholder.com/800x400?text=PyLoggerTUI+Demo)

## Características

- **Múltiplos Arquivos**: Abra uma pasta inteira de logs com navegação por tabs
- **Gráficos e Estatísticas**: Visualização de distribuição de logs ao longo do tempo usando plotext
- **Busca Avançada**: Busca em tempo real com suporte a regex
- **Syntax Highlighting**: Cores diferenciadas por nível de log (INFO, WARNING, ERROR, etc)
- **Dashboard Interativo**: Visão geral de todos os logs com métricas agregadas
- **Performance Otimizada**: Suporta arquivos grandes com carregamento eficiente
- **Traceback Parser**: Detecta e formata automaticamente tracebacks Python
- **Interface Moderna**: Construído com Textual para uma experiência TUI profissional

## Instalação

### Requisitos

- Python 3.8 ou superior
- [uv](https://docs.astral.sh/uv/) - Gerenciador de pacotes Python ultra-rápido

### Instalar uv

Se você ainda não tem o `uv` instalado:

```bash
# No Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# No Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Ou via pip
pip install uv
```

### Instalar PyLoggerTUI

```bash
# Clone o repositório
git clone https://github.com/GeoCode-Labs/PyLoggerTUI.git
cd PyLoggerTUI

# Sincronizar dependências com uv (cria ambiente virtual automaticamente)
uv sync

# Ativar o ambiente virtual
source .venv/bin/activate  # Linux/macOS
# ou
.venv\Scripts\activate     # Windows

# Ou executar diretamente com uv (sem ativar venv)
uv run python -m src.main /caminho/para/logs
```

### Instalação Alternativa (pip tradicional)

```bash
# Clone o repositório
git clone https://github.com/GeoCode-Labs/PyLoggerTUI.git
cd PyLoggerTUI

# Instale as dependências
pip install -r requirements.txt
```

### Dependências

- `textual>=0.47.0` - Framework TUI moderno
- `plotext>=5.2.8` - Gráficos no terminal
- `rich>=13.7.0` - Formatação de texto rica
- `pyyaml>=6.0.3` - Leitura de arquivos de configuração YAML

## Uso

### Exemplos Básicos

```bash
# Com uv (recomendado)
# Abrir uma pasta de logs (carrega todos os .log)
uv run python -m src.main /caminho/para/pasta/logs

# Abrir arquivo único
uv run python -m src.main arquivo.log

# Abrir múltiplos arquivos
uv run python -m src.main app.log error.log debug.log

# Modo watch (auto-refresh - em desenvolvimento)
uv run python -m src.main /caminho/logs --watch

# Se você ativou o ambiente virtual
source .venv/bin/activate
python -m src.main /caminho/para/logs
```

### Exemplos Avançados

```bash
# Analisar logs de produção
uv run python -m src.main /var/log/myapp/*.log

# Abrir logs com caminhos relativos
uv run python -m src.main ./logs/

# Ver ajuda completa
uv run python -m src.main --help
```

## Configuração Customizada

PyLoggerTUI suporta formatos de log customizados através de um arquivo `config.yml` na mesma pasta dos logs.

### Exemplo de config.yml

```yaml
# Formato do log com placeholders
format: "[ {time} | process: {process.id} | {level: <8}] {module}.{function}:{line} {message}"

# Formato de data (opcional)
date_format: "%Y-%m-%d %H:%M:%S"
```

### Placeholders Suportados

- `{time}` ou `{timestamp}` - Data/hora do log
- `{level}` - Nível do log (INFO, ERROR, etc)
- `{message}` - Mensagem do log
- `{module}` - Nome do módulo
- `{function}` - Nome da função
- `{line}` - Número da linha
- `{process.id}` / `{process.name}` - Informações do processo
- `{thread.id}` / `{thread.name}` - Informações da thread

### Arquivos de Configuração

O PyLoggerTUI procura automaticamente por:
1. `config.yml` na pasta dos logs
2. `config.yaml` na pasta dos logs
3. `.loggerconfig.yml` na pasta dos logs
4. `logger.yml` na pasta dos logs

Se nenhum arquivo for encontrado, usa os formatos padrão.

## Atalhos de Teclado

| Atalho | Ação |
|--------|------|
| `Ctrl+F` | Abrir busca |
| `Ctrl+R` | Recarregar arquivos |
| `Ctrl+D` | Mostrar Dashboard |
| `S` | Ordenar por data (OFF → Antigo→Novo → Novo→Antigo → OFF) |
| `E` | Filtrar apenas ERRORs |
| `W` | Filtrar apenas WARNINGs |
| `I` | Filtrar apenas INFOs |
| `A` | Mostrar todos os níveis |
| `Tab` | Próxima aba |
| `Shift+Tab` | Aba anterior |
| `Q` ou `Ctrl+Q` | Sair |

## Estrutura do Projeto

```
PyLoggerTUI/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Entry point para python -m src
│   ├── main.py              # Aplicação principal TUI
│   ├── parser.py            # Parser de logs multi-formato
│   ├── config.py            # Carregador de configurações YAML
│   ├── widgets.py           # Widgets Textual customizados
│   ├── dashboard.py         # Dashboard com estatísticas
│   └── charts.py            # Geração de gráficos com plotext
├── examples/
│   ├── config.yml           # Exemplo de configuração customizada
│   ├── example_app.log      # Logs de exemplo
│   └── example_errors.log   # Logs de erro de exemplo
├── tests/
│   ├── __init__.py
│   └── test_parser.py       # Testes do parser
├── requirements.txt         # Dependências Python
└── README.md               # Este arquivo
```

## Formatos de Log Suportados

O parser reconhece automaticamente vários formatos de log:

### Formato 1: Timestamp em colchetes
```
[2025-10-24 14:09:25] INFO | Server started successfully
[2025-10-24 14:09:26] ERROR | Connection failed
```

### Formato 2: Formato Python logging
```
2025-10-24 14:09:25 - INFO - Server started
2025-10-24 14:09:26 - ERROR - Connection failed
```

### Formato 3: Simples
```
INFO: Application initialized
ERROR: Database connection timeout
```

### Formato 4: ISO timestamp
```
2025-10-24T14:09:25.123Z INFO Server started
2025-10-24T14:09:26.456Z ERROR Connection failed
```

## Dashboard

O dashboard fornece uma visão geral completa:

- **Estatísticas Gerais**: Total de entradas, erros, warnings, etc
- **Distribuição por Nível**: Visualização com barras de porcentagem
- **Análise por Arquivo**: Métricas individuais de cada arquivo
- **Erros Recentes**: Lista dos últimos erros detectados
- **Gráficos Timeline**: Distribuição temporal de logs
- **Heatmaps**: Padrões por dia da semana e hora

## Features Detalhadas

### Parser Inteligente

O parser detecta automaticamente:
- Múltiplos formatos de timestamp
- Níveis de log (DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL)
- Tracebacks Python com destaque especial
- Mensagens multi-linha

### Visualização de Logs

Cada linha de log é exibida com:
- Número da linha (para referência)
- Timestamp formatado (se disponível)
- Nível de log com cor apropriada
- Mensagem completa

### Sistema de Filtros

Filtre rapidamente por:
- Nível de log (teclas E, W, I)
- Busca textual (Ctrl+F)
- Busca com regex (suportado)

### Gráficos

Visualizações disponíveis:
- **Timeline**: Distribuição horária de logs
- **Level Distribution**: Contagem por nível
- **Error Timeline**: Apenas erros e warnings ao longo do tempo
- **Day of Week**: Distribuição por dia da semana

## Desenvolvimento

### Configurar Ambiente de Desenvolvimento

```bash
# Instalar dependências de desenvolvimento
uv sync --extra dev

# Ou adicionar dependências de dev manualmente
uv add --dev pytest pytest-cov textual-dev
```

### Executar Testes

```bash
# Com uv
# Todos os testes
uv run pytest tests/

# Testes específicos
uv run pytest tests/test_parser.py

# Com coverage
uv run pytest --cov=src tests/

# Se o ambiente virtual estiver ativado
pytest tests/
```

### Modo Desenvolvimento com Hot-Reload

```bash
# Requer textual-dev (incluído nas dependências de dev)
uv run textual run --dev src/main.py /caminho/logs

# Ou com venv ativado
textual run --dev src/main.py /caminho/logs
```

### Gerenciar Dependências

```bash
# Adicionar nova dependência
uv add nome-do-pacote

# Adicionar dependência de desenvolvimento
uv add --dev nome-do-pacote

# Remover dependência
uv remove nome-do-pacote

# Atualizar todas as dependências
uv sync --upgrade

# Gerar requirements.txt atualizado
uv pip compile pyproject.toml -o requirements.txt
```

### Estrutura de Classes

#### LogParser
- `parse_line()` - Parse uma linha individual
- `parse_file()` - Parse arquivo completo
- `get_log_stats()` - Calcula estatísticas
- `filter_by_level()` - Filtra por nível
- `search()` - Busca com regex ou texto

#### LogAnalyzerApp
- Aplicação principal Textual
- Gerencia tabs de arquivos
- Coordena widgets e screens
- Implementa ações e bindings

#### Widgets Customizados
- `LogViewer` - Visualizador principal de logs
- `StatsBar` - Barra de estatísticas no rodapé
- `DashboardView` - Dashboard completo

## Roadmap

- [x] Parser multi-formato
- [x] Interface TUI com Textual
- [x] Múltiplos arquivos com tabs
- [x] Sistema de busca
- [x] Filtros por nível
- [x] Dashboard com estatísticas
- [x] Gráficos com plotext
- [x] Detecção de tracebacks
- [x] Configuração via arquivo YAML (formatos customizados)
- [ ] Auto-refresh (watch mode)
- [ ] Export de relatórios (HTML, JSON)
- [ ] Temas customizáveis
- [ ] Plugin system
- [ ] Suporte a logs comprimidos (.gz, .zip)
- [ ] Integração com syslog
- [ ] Alertas em tempo real

## Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### Guidelines

- Siga PEP 8 para estilo de código Python
- Adicione testes para novas funcionalidades
- Atualize a documentação conforme necessário
- Mantenha mensagens de commit claras e descritivas

## Troubleshooting

### Problema: "No module named 'textual'"

```bash
# Solução com uv: Sincronize as dependências
uv sync

# Ou com pip tradicional
pip install -r requirements.txt
```

### Problema: uv não encontrado

```bash
# Instale o uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Ou via pip
pip install uv

# Verifique a instalação
uv --version
```

### Problema: Caracteres estranhos no terminal

```bash
# Solução: Use um terminal com suporte a Unicode
# Recomendados: Windows Terminal, iTerm2, Alacritty
```

### Problema: Performance lenta com arquivos grandes

```bash
# Solução: O parser é otimizado, mas arquivos > 100MB podem demorar
# Considere filtrar ou dividir o arquivo primeiro
grep "ERROR" huge.log > errors.log
python -m src.main errors.log
```

## Licença

Este projeto está licenciado sob a MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes.

## Autores

- **Log Analyzer Team** - *Trabalho Inicial*

## Agradecimentos

- [Textual](https://github.com/Textualize/textual) - Framework TUI incrível
- [Plotext](https://github.com/piccolomo/plotext) - Gráficos no terminal
- [Rich](https://github.com/Textualize/rich) - Formatação de texto rica
- Comunidade Python open source

## Links

- [Documentação Textual](https://textual.textualize.io/)
- [Plotext Documentation](https://github.com/piccolomo/plotext)
- [Report Issues](https://github.com/yourusername/PyLoggerTUI/issues)

---

**Desenvolvido com Python e muito café**
