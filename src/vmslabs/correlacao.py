"""Correlacao entre camera, acesso e horario.

Camera, access and time correlation.

Dois sistemas contam a mesma manha, cada um na sua lingua. Correlacionar e
juntar o que aconteceu junto: um movimento na camera e um acesso na porta com
menos de N segundos de diferenca e o mesmo fato visto de dois lugares.

## Tempos alinhados, nao realinhados

Os tempos chegam alinhados do `eventos.py` - o deslocamento de 47 segundos ja
foi aplicado na carga. Realinhar aqui seria aplicar duas vezes, e aplicar
duas vezes desloca tudo para o outro lado. A regra e simples: quem normaliza
alinha, quem correlaciona confia.
"""

from __future__ import annotations

from .eventos import Evento


def pares_por_cartao(acesso: list[Evento]) -> dict[str, list[Evento]]:
    """Agrupa acessos por cartao, em ordem de tempo.

    Group accesses by card, in time order.

    Args:
        acesso: Os eventos de acesso.

    Returns:
        Mapa cartao para eventos ordenados por tempo.
    """
    grupos: dict[str, list[Evento]] = {}
    for evento in sorted(acesso, key=lambda e: e.tempo):
        grupos.setdefault(evento.ator, []).append(evento)
    return grupos


def correlacionar(
    vms: list[Evento], acesso: list[Evento], janela_s: int = 120
) -> list[tuple[Evento, Evento]]:
    """Junta movimento e acesso que aconteceram juntos.

    Join movement and access that happened together.

    O criterio e so tempo. VMS fala em cameras e acesso fala em cartoes e
    portas: nao ha chave compartilhada entre os sistemas, e exigir uma seria
    exigir um mapeamento porta-camera que nao existe nos dados. Quem da
    significado ao par e a regra de incidente, nao o correlacionador - ele
    entrega materia-prima, nao veredito.

    Args:
        vms: Os eventos do VMS.
        acesso: Os eventos de acesso.
        janela_s: Diferenca maxima em segundos.

    Returns:
        Pares `(movimento, acesso)` com tempo proximo. Ordenados pelo tempo
        do movimento.
    """
    pares: list[tuple[Evento, Evento]] = []
    movimentos = sorted(
        (e for e in vms if e.tipo == "movimento"), key=lambda e: e.tempo
    )
    for movimento in movimentos:
        for entrada in acesso:
            if abs(movimento.tempo - entrada.tempo) <= janela_s:
                pares.append((movimento, entrada))
    return pares


def acessos_sem_camera(
    acesso: list[Evento], vms: list[Evento], janela_s: int = 300
) -> list[Evento]:
    """Acessos sem movimento proximo de camera.

    Accesses with no nearby camera movement.

    Um acesso sem camera por perto pode ser normal (ponto cego) ou incidente
    (camera desligada). A funcao nao decide qual: ela lista, e a regra de
    incidente decide.

    Args:
        acesso: Os eventos de acesso.
        vms: Os eventos do VMS.
        janela_s: Janela de proximidade em segundos.

    Returns:
        Os acessos sem movimento na janela.
    """
    movimentos = [e.tempo for e in vms if e.tipo == "movimento"]
    sem_camera: list[Evento] = []
    for entrada in acesso:
        if not any(abs(entrada.tempo - tempo) <= janela_s for tempo in movimentos):
            sem_camera.append(entrada)
    return sem_camera


def cartoes_duplicados(
    acesso: list[Evento], janela_s: int = 120
) -> list[tuple[Evento, Evento]]:
    """O mesmo cartao em lugares diferentes, rapido demais.

    The same card in different places, too fast.

    Args:
        acesso: Os eventos de acesso.
        janela_s: Diferenca maxima em segundos.

    Returns:
        Pares de acessos do mesmo cartao em locais diferentes dentro da
        janela. Ordenados pelo tempo do segundo acesso.
    """
    pares: list[tuple[Evento, Evento]] = []
    for cartao, eventos in pares_por_cartao(acesso).items():
        if not cartao:
            continue
        for anterior, atual in zip(eventos, eventos[1:]):
            if atual.local != anterior.local and atual.tempo - anterior.tempo <= janela_s:
                pares.append((anterior, atual))
    return sorted(pares, key=lambda par: par[1].tempo)