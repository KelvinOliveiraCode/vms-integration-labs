"""Trilha de auditoria com hash encadeado.

Chained-hash audit trail (sha256).

Cada registro faz o sha256 do hash anterior mais o proprio conteudo.
Qualquer mudanca em qualquer registro invalida a cadeia a partir dali.
A ordem e por tempo, nunca por ordem de chegada.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .eventos import Evento

# Hash de origem: ponto de partida da cadeia.
# Genesis hash: the start of the chain.
GENESIS = "0" * 64


@dataclass(frozen=True)
class Registro:
    """Registro da trilha de auditoria.

    A record in the audit trail.

    Attributes:
        sequencia: Posicao zero-based na trilha.
        evento_id: O id do evento de origem.
        resumo: Resumo canonico do evento.
        hash_anterior: O hash do registro anterior.
        hash_atual: O hash deste registro.
    """

    sequencia: int
    evento_id: str
    resumo: str
    hash_anterior: str
    hash_atual: str


def _resumo(evento: Evento) -> str:
    """Resumo canonico do evento.

    Canonical summary of the event.

    Args:
        evento: O evento a resumir.

    Returns:
        A serializacao deterministica dos campos.
    """
    dados = {
        "id": evento.id,
        "sistema": evento.sistema,
        "tipo": evento.tipo,
        "tempo": evento.tempo,
        "ator": evento.ator,
        "local": evento.local,
        "campos": evento.campos,
        "linha": evento.linha,
    }
    return json.dumps(dados, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _digest(hash_anterior: str, sequencia: int, evento_id: str, resumo: str) -> str:
    """O sha256 do hash anterior mais o conteudo do registro.

    The sha256 of the previous hash plus the record content.
    """
    conteudo = f"{hash_anterior}|{sequencia}|{evento_id}|{resumo}"
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def acrescentar(trilha: list[Registro], evento: Evento) -> Registro:
    """Cria o proximo registro da trilha.

    Create the next record in the trail.

    Args:
        trilha: A trilha ate aqui, em ordem.
        evento: O evento a registrar.

    Returns:
        O novo registro; o chamador o acrescenta a trilha.
    """
    if trilha:
        sequencia = trilha[-1].sequencia + 1
        hash_anterior = trilha[-1].hash_atual
    else:
        sequencia = 0
        hash_anterior = GENESIS
    resumo = _resumo(evento)
    return Registro(
        sequencia=sequencia,
        evento_id=evento.id,
        resumo=resumo,
        hash_anterior=hash_anterior,
        hash_atual=_digest(hash_anterior, sequencia, evento.id, resumo),
    )


def verificar(trilha: list[Registro]) -> tuple[bool, int]:
    """Recalcula a cadeia inteira.

    Recompute the whole chain.

    Args:
        trilha: Os registros, em ordem.

    Returns:
        A tupla (ok, indice da primeira quebra); -1 se intacta ou vazia.
    """
    esperado = GENESIS
    for indice, registro in enumerate(trilha):
        if registro.hash_anterior != esperado:
            return (False, indice)
        if registro.sequencia != indice:
            return (False, indice)
        atual = _digest(
            registro.hash_anterior, registro.sequencia, registro.evento_id, registro.resumo
        )
        if registro.hash_atual != atual:
            return (False, indice)
        esperado = registro.hash_atual
    return (True, -1)


def montar(eventos: list[Evento]) -> list[Registro]:
    """Monta a trilha em ordem de tempo.

    Build the trail in time order.

    A ordem e pelo campo tempo (estavel: empates mantem a ordem de
    chegada), nunca pela ordem de chegada sozinha.

    Args:
        eventos: Os eventos, em qualquer ordem.

    Returns:
        A trilha completa, do registro mais antigo ao mais novo.
    """
    ordenados = sorted(eventos, key=lambda evento: evento.tempo)
    trilha: list[Registro] = []
    for evento in ordenados:
        trilha.append(acrescentar(trilha, evento))
    return trilha
