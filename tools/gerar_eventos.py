"""Gera os eventos dos dois sistemas de forma deterministica.

Generate both systems' events deterministically.

Os dois arquivos contam a mesma manha, cada um na sua lingua e no seu
relogio. O VMS carimba em segundos desde a epoca; o acesso carimba em texto
e anda 47 segundos adiantado. O gerador escreve o tempo "verdadeiro" uma vez
e converte para cada formato, para que o alinhamento seja exato por
construcao - e nao aproximado por sorte.

## Os 4 incidentes plantados

Eles estao documentados aqui e nao escondidos, porque o criterio de aceite e
que a correlacao os detecte. Incidente que ninguem sabe onde esta nao e
criterio, e loteria.

1. **badge-clonado**: cartao C-100 na PORTA-A as 08:10:00 e na PORTA-B as
   08:11:30, 90 segundos depois, em zona diferente. Ninguem atravessa o
   predio nesse tempo a pe.
2. **porta-forcada**: PORTA-C registra abertura sem cartao anterior em 5
   minutos. Porta nao se abre sozinha.
3. **fora-de-horario**: cartao C-103 na PORTA-A as 03:14:00, fora da janela
   06:00-22:00. Madrugada nao e horario de visita.
4. **camera-offline**: CAM-07 cai as 08:20:00 e a PORTA-B abre as 08:20:40
   sem registro de camera. Coincidencia possivel, e por isso e so o quarto
   da lista: sozinho nao prova nada, junto com os outros conta historia.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VMS = RAIZ / "dados" / "eventos-vms.jsonl"
ACESSO = RAIZ / "dados" / "eventos-acesso.jsonl"
REGRAS = RAIZ / "dados" / "regras-incidente.yaml"

# 2026-10-01T08:00:00Z em segundos. A manha inteira e deslocamento disso.
BASE = int(datetime(2026, 10, 1, 8, 0, 0, tzinfo=timezone.utc).timestamp())

# O acesso anda adiantado; o gerador soma para que o arquivo reflita o
# relogio errado, e o normalizador subtraia de volta.
ADIANTAMENTO = 47


def _texto(segundos: int) -> str:
    """Segundos desde a epoca em texto de acesso, com o adiantamento.

    Args:
        segundos: O tempo verdadeiro.

    Returns:
        O texto como o relogio errado o escreveria.
    """
    momento = datetime.fromtimestamp(segundos + ADIANTAMENTO, tz=timezone.utc)
    return momento.strftime("%Y-%m-%dT%H:%M:%S")


def principal() -> int:
    """Gera os dois arquivos e as regras.

    Generate both files and the rules.

    Returns:
        Sempre 0.
    """
    vms: list[dict] = []
    acesso: list[dict] = []

    def vms_movimento(eid: str, camera: str, desloc: int) -> None:
        vms.append({
            "id": eid, "tipo": "movimento", "camera": camera,
            "timestamp": BASE + desloc,
        })

    def vms_status(eid: str, camera: str, estado: str, desloc: int) -> None:
        vms.append({
            "id": eid, "tipo": "status", "camera": camera,
            "estado": estado, "timestamp": BASE + desloc,
        })

    def acs(eid: str, cartao: str, porta: str, desloc: int, extra=None) -> None:
        item = {
            "id": eid, "tipo": "acesso", "cartao": cartao,
            "porta": porta, "datahora": _texto(BASE + desloc),
        }
        if extra:
            item.update(extra)
        acesso.append(item)

    # --- rotina normal da manha ---
    vms_movimento("v-001", "CAM-01", 300)
    acs("a-001", "C-101", "PORTA-A", 320)
    vms_movimento("v-002", "CAM-02", 900)
    acs("a-002", "C-102", "PORTA-A", 920)
    vms_status("v-003", "CAM-01", "online", 0)
    vms_status("v-004", "CAM-02", "online", 0)

    # --- 1. badge clonado: C-100 em dois lugares com 90s de diferenca ---
    acs("a-010", "C-100", "PORTA-A", 600)
    vms_movimento("v-010", "CAM-01", 610)
    acs("a-011", "C-100", "PORTA-B", 690)
    vms_movimento("v-011", "CAM-03", 700)

    # --- 2. porta forcada: PORTA-C abre sem cartao antes ---
    vms_movimento("v-020", "CAM-04", 1200)
    acesso.append({
        "id": "a-020", "tipo": "porta-forcada", "cartao": "",
        "porta": "PORTA-C", "datahora": _texto(BASE + 1210),
    })

    # --- 3. fora de horario: 03:14, fora da janela 06:00-22:00 ---
    noite = int(datetime(2026, 10, 1, 3, 14, 0, tzinfo=timezone.utc).timestamp())
    acesso.append({
        "id": "a-030", "tipo": "acesso", "cartao": "C-103",
        "porta": "PORTA-A", "datahora": _texto(noite),
    })
    vms.append({
        "id": "v-030", "tipo": "movimento", "camera": "CAM-01",
        "timestamp": noite,
    })

    # --- 4. camera offline durante incidente ---
    vms_status("v-040", "CAM-07", "offline", 1200)
    acesso.append({
        "id": "a-040", "tipo": "acesso", "cartao": "C-104",
        "porta": "PORTA-B", "datahora": _texto(BASE + 1240),
    })
    vms_status("v-041", "CAM-07", "online", 1800)

    # --- resto da rotina ---
    acs("a-050", "C-105", "PORTA-A", 2400)
    vms_movimento("v-050", "CAM-01", 2410)
    acs("a-051", "C-106", "PORTA-B", 3000)
    vms_movimento("v-051", "CAM-03", 3010)

    for caminho, linhas in ((VMS, vms), (ACESSO, acesso)):
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(
            "\n".join(json.dumps(l, ensure_ascii=True) for l in linhas) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    REGRAS.write_text(
        "# Regras de incidente do laboratorio.\n"
        "#\n"
        "# Cada regra tem janela em segundos e severidade. Janela curta demais\n"
        "# perde o incidente; longa demais junta o que nao tem a ver. Os numeros\n"
        "# abaixo sao os que separam os 4 plantados da rotina sem cruzar.\n"
        "\n"
        "janela_horario: [6, 22]\n"
        "\n"
        "regras:\n"
        "  - id: badge-clonado\n"
        "    descricao: mesmo cartao em dois lugares em menos de 120 segundos\n"
        "    janela_s: 120\n"
        "    severidade: alta\n"
        "  - id: porta-forcada\n"
        "    descricao: abertura sem cartao nos 5 minutos anteriores\n"
        "    janela_s: 300\n"
        "    severidade: alta\n"
        "  - id: fora-de-horario\n"
        "    descricao: acesso fora da janela 06:00-22:00\n"
        "    severidade: media\n"
        "  - id: camera-offline\n"
        "    descricao: acesso numa zona cuja camera esta offline\n"
        "    janela_s: 300\n"
        "    severidade: media\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"eventos gravados: {len(vms)} VMS, {len(acesso)} acesso")
    print("incidentes plantados: badge-clonado, porta-forcada, fora-de-horario, camera-offline")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())