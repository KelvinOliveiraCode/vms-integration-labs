"""Normalizacao de evento entre sistemas.

Cross-system event normalization.

Dois sistemas simulados geram eventos em formatos diferentes e com relogios
diferentes. Este modulo converte os dois para a mesma forma, no mesmo tempo -
e sem isso a correlacao compara coisa incomparavel.

## Relogio diferente e o problema real

O VMS carimba em segundos desde a epoca; o controle de acesso carimba em
`AAAA-MM-DDTHH:MM:SS`. Pior: os dois relogios nao andam juntos. O acesso esta
47 segundos adiantado em relacao ao VMS, e 47 segundos e a diferenca entre
"o cartao passou na porta e a camera viu" e "a camera viu antes do cartao
passar", que e conclusao oposta sobre o mesmo fato.

A funcao `alinhar` aplica o deslocamento conhecido. Deslocamento conhecido,
nao estimado: estimar drift de relogio a partir dos proprios eventos que se
quer correlacionar e raciocinio circular. O valor vem da topologia, e o teste
trava o valor.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Deslocamento do controle de acesso em relacao ao VMS, em segundos. Positivo
# significa que o acesso esta adiantado: subtrair alinha.
DESLOCAMENTO_ACESSO_S = 47


class ErroDeEvento(Exception):
    """O evento nao pode ser normalizado.

    The event cannot be normalized.
    """


@dataclass(frozen=True)
class Evento:
    """Um evento canonico, com tempo alinhado.

    A canonical event, with aligned time.

    Attributes:
        id: Identificador unico no lote.
        sistema: `vms` ou `acesso`.
        tipo: O tipo no sistema de origem.
        tempo: Segundos desde a epoca, ja alinhados.
        ator: Quem: cartao, usuario ou camera.
        local: Onde: porta, camera ou zona.
        campos: O resto, preservado.
        linha: A linha no arquivo.
    """

    id: str
    sistema: str
    tipo: str
    tempo: int
    ator: str
    local: str
    campos: dict[str, Any] = field(default_factory=dict)
    linha: int = 0


def _tempo_vms(bruto: Any, linha: int) -> int:
    """O tempo de um evento VMS.

    Args:
        bruto: O valor cru.
        linha: A linha, para o erro.

    Returns:
        Os segundos desde a epoca.

    Raises:
        ErroDeEvento: Se o valor nao for inteiro.
    """
    try:
        return int(bruto)
    except (TypeError, ValueError):
        raise ErroDeEvento(f"linha {linha}: tempo VMS invalido {bruto!r}") from None


def _tempo_acesso(bruto: Any, linha: int) -> int:
    """O tempo de um evento de acesso, ja alinhado.

    Args:
        bruto: O texto `AAAA-MM-DDTHH:MM:SS`.
        linha: A linha, para o erro.

    Returns:
        Os segundos desde a epoca, menos o deslocamento.

    Raises:
        ErroDeEvento: Se o texto nao for data valida.
    """
    try:
        momento = datetime.strptime(str(bruto), "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        raise ErroDeEvento(f"linha {linha}: tempo de acesso invalido {bruto!r}") from None
    return int(momento.timestamp()) - DESLOCAMENTO_ACESSO_S


def normalizar(bruto: dict[str, Any], sistema: str, linha: int = 0) -> Evento:
    """Converte um mapa em evento canonico.

    Convert a map into a canonical event.

    Args:
        bruto: O mapa do JSON.
        sistema: `vms` ou `acesso`.
        linha: A linha no arquivo.

    Returns:
        O evento normalizado, com tempo alinhado.

    Raises:
        ErroDeEvento: Se o sistema for desconhecido ou faltar campo.
    """
    if sistema not in ("vms", "acesso"):
        raise ErroDeEvento(f"linha {linha}: sistema {sistema!r} desconhecido")
    if not isinstance(bruto, dict):
        raise ErroDeEvento(f"linha {linha}: evento nao e um mapa")

    if sistema == "vms":
        tempo = _tempo_vms(bruto.get("timestamp"), linha)
        ator = str(bruto.get("camera", ""))
        local = str(bruto.get("camera", ""))
    else:
        tempo = _tempo_acesso(bruto.get("datahora"), linha)
        ator = str(bruto.get("cartao", ""))
        local = str(bruto.get("porta", ""))

    for campo, valor in (("tipo", bruto.get("tipo")),):
        if not str(valor).strip():
            raise ErroDeEvento(f"linha {linha}: campo {campo!r} obrigatorio")
    # Porta forcada nao tem cartao: e justamente a ausencia de ator que a
    # define. Exigir ator aqui transformaria o incidente mais importante do
    # laboratorio em erro de validacao.
    if sistema == "acesso" and str(bruto.get("tipo")) != "porta-forcada":
        if not ator.strip():
            raise ErroDeEvento(f"linha {linha}: campo 'ator' obrigatorio")

    extras = {
        chave: valor
        for chave, valor in bruto.items()
        if chave not in ("timestamp", "datahora", "camera", "cartao", "porta", "tipo")
    }
    return Evento(
        id=str(bruto.get("id", f"{sistema}-{linha}")),
        sistema=sistema,
        tipo=str(bruto.get("tipo")),
        tempo=tempo,
        ator=ator,
        local=local,
        campos=extras,
        linha=linha,
    )


def carregar(caminho: str | Path, sistema: str) -> list[Evento]:
    """Le um JSONL de eventos de um sistema.

    Read a system's JSONL event file.

    Args:
        caminho: O arquivo.
        sistema: `vms` ou `acesso`.

    Returns:
        Os eventos normalizados, na ordem do arquivo.

    Raises:
        ErroDeEvento: Se o arquivo nao existir ou alguma linha for invalida.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise ErroDeEvento(f"arquivo nao encontrado: {caminho}")
    try:
        texto = caminho.read_text(encoding="utf-8")
    except UnicodeDecodeError as erro:
        raise ErroDeEvento(f"{caminho}: nao decodifica como UTF-8 ({erro})") from None

    eventos: list[Evento] = []
    for numero, linha in enumerate(texto.splitlines(), start=1):
        if not linha.strip():
            continue
        try:
            bruto = json.loads(linha)
        except json.JSONDecodeError as erro:
            raise ErroDeEvento(f"linha {numero}: JSON invalido ({erro})") from None
        eventos.append(normalizar(bruto, sistema, linha=numero))
    if not eventos:
        raise ErroDeEvento(f"{caminho}: nenhum evento valido")
    return eventos