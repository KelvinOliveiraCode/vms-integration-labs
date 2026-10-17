# vms-integration-labs

<img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License">

Integração simulada entre CFTV e controle de acesso: normaliza eventos de dois sistemas com relógios diferentes, correlaciona, aplica quatro regras de incidente e constrói uma trilha de auditoria com hash encadeado.

> **Nada aqui é real.** Dois sistemas simulados geram eventos com relógios diferentes. Nenhuma câmera, porta ou nuvem é tocada.

## Problema / Por que existe

Dois sistemas de segurança registram a mesma manhã, cada um na sua língua e no seu relógio. O VMS carimba em segundos desde a época; o controle de acesso carimba em texto `AAAA-MM-DDTHH:MM:SS`. Pior: o relógio de acesso anda 47 segundos adiantado em relação ao VMS. Sem alinhar, a correlação chega a conclusões opostas sobre o mesmo fato — "a câmera viu antes do cartão passar" versus o contrário — e 47 segundos não são arredondamento.

Integração entre sistemas de segurança é o que diferencia instalador de integrador. O problema real não é ler dois formatos: é que os relógios não andam juntos, e estimar o desvio a partir dos próprios eventos que se quer correlacionar é raciocínio circular.

## O que faz

- Carrega 12 eventos VMS e 9 eventos de controle de acesso em JSONL.
- Normaliza cada evento para um formato canônico com tempo em segundos desde a época (UTC), já alinhado.
- Aplica o deslocamento conhecido de 47 segundos no relógio de acesso, lido na normalização, nunca na correlação.
- Correla movimento de câmera e acesso por proximidade temporal (janela de 120 segundos).
- Detecta quatro incidentes pelas regras do `regras-incidente.yaml`: badge-clonado, porta-forcada, fora-de-horario, camera-offline.
- Constrói uma trilha de auditoria append-only de 21 registros, cada um amarrado ao hash SHA-256 do anterior.
- Verifica a cadeia: alterar 1 byte invalida a trilha a partir dali.

## Stack

- Python 3.10+
- PyYAML>=6.0 (única dependência de execução)
- pytest>=7.4, pytest-cov>=4.1 (dependências de desenvolvimento)
- Biblioteca padrão apenas: `json`, `hashlib`, `datetime`, `argparse`, `dataclasses`, `pathlib`

## Como funciona

O pipeline tem quatro estágios:

1. **Normalização** (`src/vmslabs/eventos.py`): lê cada JSONL, converte o timestamp do sistema de origem para segundos desde a época e subtrai os 47 segundos do relógio de acesso. Campos obrigatórios ausentes geram `ErroDeEvento` com o número da linha; nada é descartado em silêncio.
2. **Correlação** (`src/vmslabs/correlacao.py`): junta movimento de câmera e acesso que aconteceram próximos no tempo. Não exige chave compartilhada — VMS fala em câmeras, acesso fala em cartões e portas, e não existe mapeamento porta-camera nos dados. O significado do par vem das regras, não do correlacionador.
3. **Detecção de incidentes** (`src/vmslabs/incidentes.py`): aplica as quatro regras carregadas do YAML (janela e severidade vêm do dado, não do código). Porta forçada não exige ator; a ausência de cartão é o próprio sinal.
4. **Auditoria** (`src/vmslabs/auditoria.py`): monta a trilha em ordem de tempo e encadeia SHA-256. `verificar` recalcula toda a cadeia e reporta o índice da primeira quebra.

A CLI expõe dois comandos: `correlacionar` lista incidentes com código de saída 1 quando há incidente, e `auditar` verifica a cadeia com código de saída 0 quando íntegra. Integração que acha problema e passa é pior do que integração que não procura.

## Como rodar

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
python -m pytest tests/ -q
python -m vmslabs --help
```

Fluxo principal:

```powershell
python -m vmslabs correlacionar dados/eventos-vms.jsonl dados/eventos-acesso.jsonl --regras dados/regras-incidente.yaml
```

Saída esperada:

```
eventos: 12 VMS, 9 acesso
incidentes: 4

[alta] badge-clonado
  cartao C-100 em PORTA-A e PORTA-B com 90s de diferenca
  eventos: a-010, a-011
[alta] porta-forcada
  PORTA-C abriu sem cartao antes
  eventos: a-020
[media] fora-de-horario
  C-103 em PORTA-A as 03:00, fora de 06:00-22:00
  eventos: a-030
[media] camera-offline
  C-104 em PORTA-B com CAM-07 offline ha 40s
  eventos: a-040
```

Auditoria da trilha:

```powershell
python -m vmslabs auditar dados/eventos-vms.jsonl dados/eventos-acesso.jsonl
```

```
registros: 21
cadeia integra: nenhum registro adulterado
```

Rodar sem instalar (útil para conferência rápida):

```powershell
$env:PYTHONPATH="$PWD\src"; python -m vmslabs correlacionar dados/eventos-vms.jsonl dados/eventos-acesso.jsonl --regras dados/regras-incidente.yaml
```

Provas de aceite:

```powershell
python tools/verificar_aceite.py     # 4 incidentes + cadeia valida e quebrada
python tools/verificar_encoding.py   # nenhum caractere corrompido
```

## Estrutura do projeto

```
vms-integration-labs/
  README.md
  pyproject.toml
  requirements.txt
  LICENSE
  dados/
    eventos-vms.jsonl       # 12 eventos do VMS
    eventos-acesso.jsonl    # 9 eventos de controle de acesso
    regras-incidente.yaml    # 4 regras com janela e severidade
  docs/
    fluxo-de-evento-entre-sistemas.md
    trilha-de-auditoria.md
  exemplos/
    incidentes-detectados.md
  src/vmslabs/
    __init__.py
    __main__.py              # permite `python -m vmslabs`
    cli.py                   # comandos `correlacionar` e `auditar`
    eventos.py               # normalizacao e alinhamento de eventos
    correlacao.py            # cruzamento por proximidade temporal
    incidentes.py            # regras de incidente a partir do YAML
    auditoria.py             # trilha com hash encadeado SHA-256
  tests/
    test_eventos.py
    test_correlacao.py
    test_auditoria.py
    test_cli.py
  tools/
    gerar_eventos.py         # regenera dados/regras de forma deterministica
    verificar_aceite.py      # prova de aceite do laboratorio
    verificar_encoding.py    # conferencia de encoding dos arquivos
```

## Trade-offs e decisões

- Deslocamento conhecido (47 segundos) aplicado na normalização, não na correlação. Realinhar na correlação aplicaria o desvio duas vezes e desloca tudo para o lado errado.
- Sem chave compartilhada entre sistemas. A correlação usa apenas o tempo; exigir coincidência de porta e câmera paralisaria o correlacionador porque não existe mapeamento nos dados.
- Porta forçada não exige ator. Exigir cartão transformaria o incidente mais importante em erro de validação.
- Regras e janelas no YAML, não no código. Mudar uma janela é ajuste de dado, não deploy de código.
- A trilha é ordenada pelo campo tempo, nunca pela ordem de chegada.
- Código de saída 1 quando há incidente ou quando a cadeia quebrou.

## Limitações conhecidas

- Sem mapeamento de zona entre porta e câmera; a correlação é temporal apenas.
- Deslocamento fixo de 47 segundos. Um relógio real deriva; aqui o desvio é constante.
- Janelas definidas no YAML, não aprendidas. Outra rotina precisaria de outros valores.
- Trilha em memória: sem persistência, rotação ou backup.
- Simulado: não acessa câmeras, portas ou serviços de nuvem.

## Licença

MIT.

## Autor

Kelvin Oliveira.
