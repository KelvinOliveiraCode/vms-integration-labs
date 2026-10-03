"""Regras de incidente sobre eventos correlacionados.

Incident rules over correlated events.

Quatro regras, cada uma com janela e severidade vindas do YAML - nunca do
codigo. Severidade no codigo e politica congelada: quem muda janela e motivo
edita dado, nao programa, e dado errado se corrige sem deploy.

## Cada regra prova uma coisa diferente

- **badge-clonado**: o mesmo cartao em dois lugares rapido demais. Fisica,
  nao logica: ninguem atravessa o predio em 90 segundos.
- **porta-forcada**: abertura sem cartao antes. A ausencia de ator e o sinal,
  e e por isso que o normalizador permite ator vazio so neste tipo.
- **fora-de-horario**: hora fora da janela 06:00-22:00. Madrugada nao e
  horario de visita.
- **camera-offline**: acesso numa zona cuja camera esta offline. Sozinho nao
  prova nada - e o quarto da lista por isso. Junto com os outros, conta
  historia.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .correlacao import cartoes_duplicados
from .eventos import Evento


@dataclass(frozen=True)
class Incidente:
    """Um incidente detectado.

    A detected incident.

    Attributes:
        regra: O id da regra que disparou.
        descricao: O que aconteceu, em uma frase.
        eventos: Os ids dos eventos que provam.
        severidade: `alta` ou `media`, vinda do YAML.
    """

    regra: str
    descricao: str
    eventos: tuple[str, ...] = ()
    severidade: str = "media"


@dataclass
class RegraIncidente:
    """Uma regra carregada do YAML.

    A rule loaded from YAML.

    Attributes:
        id: O identificador.
        descricao: O que a regra detecta.
        janela_s: A janela em segundos, quando aplicavel.
        severidade: `alta` ou `media`.
    """

    id: str
    descricao: str = ""
    janela_s: int = 300
    severidade: str = "media"


def carregar_regras(caminho: str | Path) -> tuple[list[RegraIncidente], tuple[int, int]]:
    """Le as regras e a janela de horario.

    Read the rules and the time window.

    Args:
        caminho: O YAML.

    Returns:
        O par `(regras, (hora_inicio, hora_fim))`.
    """
    documento = yaml.safe_load(Path(caminho).read_text(encoding="utf-8")) or {}
    janela = tuple(documento.get("janela_horario", [6, 22]))
    regras = [
        RegraIncidente(
            id=str(item.get("id", "")),
            descricao=str(item.get("descricao", "")),
            janela_s=int(item.get("janela_s", 300)),
            severidade=str(item.get("severidade", "media")),
        )
        for item in documento.get("regras") or []
    ]
    return regras, (int(janela[0]), int(janela[1]))


def _hora_de(tempo: int) -> int:
    """A hora do dia de um timestamp.

    Args:
        tempo: Segundos desde a epoca.

    Returns:
        A hora, 0 a 23, em UTC.
    """
    return datetime.fromtimestamp(tempo, tz=timezone.utc).hour


def detectar(
    vms: list[Evento], acesso: list[Evento], regras: list[RegraIncidente],
    janela_horario: tuple[int, int] = (6, 22),
) -> list[Incidente]:
    """Aplica as regras e devolve os incidentes.

    Apply the rules and return the incidents.

    Args:
        vms: Os eventos do VMS.
        acesso: Os eventos de acesso.
        regras: As regras carregadas.
        janela_horario: O par `(inicio, fim)` permitido.

    Returns:
        Os incidentes, na ordem das regras.
    """
    por_id = {regra.id: regra for regra in regras}
    achados: list[Incidente] = []

    regra = por_id.get("badge-clonado")
    if regra is not None:
        for anterior, atual in cartoes_duplicados(acesso, regra.janela_s):
            achados.append(
                Incidente(
                    regra="badge-clonado",
                    descricao=(
                        f"cartao {atual.ator} em {anterior.local} e "
                        f"{atual.local} com "
                        f"{atual.tempo - anterior.tempo}s de diferenca"
                    ),
                    eventos=(anterior.id, atual.id),
                    severidade=regra.severidade,
                )
            )

    regra = por_id.get("porta-forcada")
    if regra is not None:
        for entrada in acesso:
            if entrada.tipo != "porta-forcada":
                continue
            anterior = [
                a for a in acesso
                if a.tipo == "acesso"
                and a.local == entrada.local
                and 0 < entrada.tempo - a.tempo <= regra.janela_s
            ]
            if not anterior:
                achados.append(
                    Incidente(
                        regra="porta-forcada",
                        descricao=f"{entrada.local} abriu sem cartao antes",
                        eventos=(entrada.id,),
                        severidade=regra.severidade,
                    )
                )

    regra = por_id.get("fora-de-horario")
    if regra is not None:
        inicio, fim = janela_horario
        for entrada in acesso:
            if entrada.tipo != "acesso":
                continue
            hora = _hora_de(entrada.tempo)
            if hora < inicio or hora >= fim:
                achados.append(
                    Incidente(
                        regra="fora-de-horario",
                        descricao=(
                            f"{entrada.ator} em {entrada.local} as "
                            f"{hora:02d}:00, fora de {inicio:02d}:00-{fim:02d}:00"
                        ),
                        eventos=(entrada.id,),
                        severidade=regra.severidade,
                    )
                )

    regra = por_id.get("camera-offline")
    if regra is not None:
        inicios: list[tuple[str, int]] = []
        for evento in vms:
            if evento.tipo != "status":
                continue
            if str(evento.campos.get("estado", "")) == "offline":
                inicios.append((evento.local, evento.tempo))
        for entrada in acesso:
            if entrada.tipo != "acesso":
                continue
            for camera, inicio_off in inicios:
                # So depois do inicio da queda, nunca antes. Acesso anterior
                # a queda e rotina que por acaso precedeu: acusar faria todo
                # acesso da manha virar incidente quando uma camera cai a
                # tarde. O sinal e alguem aproveitar a queda, nao precede-la.
                delta = entrada.tempo - inicio_off
                if 0 <= delta <= regra.janela_s:
                    achados.append(
                        Incidente(
                            regra="camera-offline",
                            descricao=(
                                f"{entrada.ator} em {entrada.local} com "
                                f"{camera} offline ha {delta}s"
                            ),
                            eventos=(entrada.id,),
                            severidade=regra.severidade,
                        )
                    )
                    break

    return achados