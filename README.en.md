# vms-integration-labs

<img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License">

Simulated integration between CCTV and access control: normalizes events from two systems with different clocks, correlates them, applies four incident rules, and builds an audit trail with chained hash.

> **Nothing here is real.** Two simulated systems generate events with different clocks. No camera, door, or cloud is touched.

## Problem / Why it exists

Two security systems record the same morning, each in its own language and its own clock. The VMS stamps seconds since the epoch; access control stamps text `AAAA-MM-DDTHH:MM:SS`. Worse: the access clock runs 47 seconds ahead of the VMS clock. Without alignment, correlation reaches opposite conclusions about the same fact — "the camera saw before the card passed" versus the reverse — and 47 seconds is not rounding.

Integration between security systems is what separates an installer from an integrator. The real problem is not reading two formats: it is that the clocks do not run together, and estimating the offset from the very events you want to correlate is circular reasoning.

## What it does

- Loads 12 VMS events and 9 access control events in JSONL.
- Normalizes each event into a canonical format with time in seconds since the epoch (UTC), already aligned.
- Applies the known 47-second offset on the access clock, read at normalization time, never at correlation time.
- Correlates camera movement and access by temporal proximity (120-second window).
- Detects four incidents per the rules in `regras-incidente.yaml`: badge-clonado, porta-forcada, fora-de-horario, camera-offline.
- Builds an append-only audit trail of 21 records, each chained to the SHA-256 hash of the previous one.
- Verifies the chain: altering 1 byte invalidates the trail from that point.

## Stack

- Python 3.10+
- PyYAML>=6.0 (only runtime dependency)
- pytest>=7.4, pytest-cov>=4.1 (development dependencies)
- Standard library only: `json`, `hashlib`, `datetime`, `argparse`, `dataclasses`, `pathlib`

## How it works

The pipeline has four stages:

1. **Normalization** (`src/vmslabs/eventos.py`): reads each JSONL, converts the source system's timestamp to seconds since the epoch, and subtracts the 47 seconds from the access clock. Missing mandatory fields raise `ErroDeEvento` with the line number; nothing is silently discarded.
2. **Correlation** (`src/vmslabs/correlacao.py`): joins camera movement and access events that happened close in time. It does not require a shared key — VMS speaks of cameras, access speaks of cards and doors, and no door-camera mapping exists in the data. The meaning of the pair comes from the rules, not from the correlator.
3. **Incident detection** (`src/vmslabs/incidentes.py`): applies the four rules loaded from YAML (window and severity come from data, not from code). Forced door does not require an actor; the absence of a card is itself the signal.
4. **Audit** (`src/vmslabs/auditoria.py`): builds the trail in time order and chains SHA-256. `verificar` recalculates the whole chain and reports the index of the first break.

The CLI exposes two commands: `correlacionar` lists incidents with exit code 1 when there is an incident, and `auditar` verifies the chain with exit code 0 when intact. Integration that finds a problem and passes is worse than integration that does not look.

## How to run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
python -m pytest tests/ -q
python -m vmslabs --help
```

Main flow:

```powershell
python -m vmslabs correlacionar dados/eventos-vms.jsonl dados/eventos-acesso.jsonl --regras dados/regras-incidente.yaml
```

Expected output:

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

Audit trail:

```powershell
python -m vmslabs auditar dados/eventos-vms.jsonl dados/eventos-acesso.jsonl
```

```
registros: 21
cadeia integra: nenhum registro adulterado
```

Run without installing (useful for a quick check):

```powershell
$env:PYTHONPATH="$PWD\src"; python -m vmslabs correlacionar dados/eventos-vms.jsonl dados/eventos-acesso.jsonl --regras dados/regras-incidente.yaml
```

Acceptance checks:

```powershell
python tools/verificar_aceite.py     # 4 incidentes + cadeia valida e quebrada
python tools/verificar_encoding.py   # nenhum caractere corrompido
```

## Project structure

```
vms-integration-labs/
  README.md
  README.en.md
  pyproject.toml
  requirements.txt
  LICENSE
  dados/
    eventos-vms.jsonl       # 12 VMS events
    eventos-acesso.jsonl    # 9 access control events
    regras-incidente.yaml    # 4 rules with window and severity
  docs/
    fluxo-de-evento-entre-sistemas.md
    trilha-de-auditoria.md
  exemplos/
    incidentes-detectados.md
  src/vmslabs/
    __init__.py
    __main__.py              # allows `python -m vmslabs`
    cli.py                   # `correlacionar` and `auditar` commands
    eventos.py               # event normalization and alignment
    correlacao.py            # temporal proximity crossing
    incidentes.py            # incident rules from YAML
    auditoria.py             # audit trail with chained SHA-256 hash
  tests/
    test_eventos.py
    test_correlacao.py
    test_auditoria.py
    test_cli.py
  tools/
    gerar_eventos.py         # deterministically regenerates data/rules
    verificar_aceite.py      # lab acceptance check
    verificar_encoding.py    # file encoding check
```

## Trade-offs and decisions

- Known offset (47 seconds) applied at normalization, not at correlation. Realigning at correlation would apply the deviation twice and shift everything to the wrong side.
- No shared key between systems. Correlation uses only time; requiring door-camera coincidence would stall the correlator because no mapping exists in the data.
- Forced door does not require an actor. Requiring a card would turn the most important incident into a validation error.
- Rules and windows in YAML, not in code. Changing a window is a data change, not a code deployment.
- The trail is ordered by the time field, never by arrival order.
- Exit code 1 when there is an incident or when the chain broke.

## Known limitations

- No zone mapping between door and camera; correlation is temporal only.
- Fixed 47-second offset. A real clock drifts; here the deviation is constant.
- Windows defined in YAML, not learned. Another routine would need other values.
- In-memory trail: no persistence, rotation, or backup.
- Simulated: does not access cameras, doors, or cloud services.

## License

MIT.

## Author

Kelvin Oliveira.
