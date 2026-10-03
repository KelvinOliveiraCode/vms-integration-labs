"""Testes da correlacao e dos incidentes.

Correlation and incident tests.

A correlacao junta o que aconteceu junto; as regras decidem o que e
incidente. Os testes provam os dois lados: os 4 plantados aparecem cada um
pela sua regra, e a rotina normal nao gera nada.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vmslabs import correlacao
from vmslabs.eventos import carregar
from vmslabs.incidentes import carregar_regras, detectar

RAIZ = Path(__file__).resolve().parent.parent
VMS = RAIZ / "dados" / "eventos-vms.jsonl"
ACESSO = RAIZ / "dados" / "eventos-acesso.jsonl"
REGRAS = RAIZ / "dados" / "regras-incidente.yaml"


@pytest.fixture(scope="module")
def vms():
    return carregar(VMS, "vms")


@pytest.fixture(scope="module")
def acesso():
    return carregar(ACESSO, "acesso")


@pytest.fixture(scope="module")
def regras():
    regras, janela = carregar_regras(REGRAS)
    return regras, janela


class TestCorrelacao:
    """O cruzamento."""

    def test_pares_por_cartao(self, acesso) -> None:
        grupos = correlacao.pares_por_cartao(acesso)
        assert len(grupos["C-100"]) == 2

    def test_cartoes_duplicados(self, acesso) -> None:
        pares = correlacao.cartoes_duplicados(acesso, 120)
        assert len(pares) == 1
        assert pares[0][1].id == "a-011"

    def test_tempos_alinhados_nao_realinhados(self, acesso) -> None:
        # Os tempos chegam alinhados do normalizador. Se a correlacao
        # realinhasse, os 90 segundos virariam 137 ou 43.
        eventos = {e.id: e for e in acesso}
        assert eventos["a-011"].tempo - eventos["a-010"].tempo == 90

    def test_correlacionar_junta_proximos(self, vms, acesso) -> None:
        pares = correlacao.correlacionar(vms, acesso, 120)
        assert len(pares) > 0
        for movimento, entrada in pares:
            assert abs(movimento.tempo - entrada.tempo) <= 120

    def test_correlacionar_janela_zero(self, vms, acesso) -> None:
        # Janela zero so junta o simultaneo exato. v-030 e a-030 dividem o
        # segundo porque foram plantados juntos: simultaneidade exata ainda
        # e correlacao, e o teste prova que a janela e inclusiva.
        pares = correlacao.correlacionar(vms, acesso, 0)
        assert [(m.id, e.id) for m, e in pares] == [("v-030", "a-030")]

    def test_acessos_sem_camera(self, vms, acesso) -> None:
        # Um acesso sintetico longe de qualquer movimento: sem ele, o teste
        # dependeria de um buraco acidental nos dados, e buraco acidental
        # vira cobertura acidental quando alguem acrescenta evento.
        from vmslabs.eventos import Evento

        sozinho = Evento(
            id="x-1", sistema="acesso", tipo="acesso", tempo=10_000,
            ator="C-999", local="PORTA-Z",
        )
        sem = correlacao.acessos_sem_camera([sozinho], vms, 300)
        assert [e.id for e in sem] == ["x-1"]

    def test_acesso_com_camera_nao_lista(self, vms, acesso) -> None:
        # a-001 tem movimento a 20 segundos: coberto, nao listado.
        sem = correlacao.acessos_sem_camera(acesso, vms, 300)
        assert "a-001" not in {e.id for e in sem}


class TestIncidentes:
    """Os 4 plantados, cada um pela sua regra."""

    def test_quatro_incidentes(self, vms, acesso, regras) -> None:
        regras_lista, janela = regras
        incidentes = detectar(vms, acesso, regras_lista, janela)
        assert len(incidentes) == 4

    def test_cada_um_pela_sua_regra(self, vms, acesso, regras) -> None:
        regras_lista, janela = regras
        por_regra = {
            i.regra: i for i in detectar(vms, acesso, regras_lista, janela)
        }
        assert set(por_regra) == {
            "badge-clonado", "porta-forcada",
            "fora-de-horario", "camera-offline",
        }
        assert por_regra["badge-clonado"].eventos == ("a-010", "a-011")
        assert por_regra["porta-forcada"].eventos == ("a-020",)
        assert por_regra["fora-de-horario"].eventos == ("a-030",)
        assert por_regra["camera-offline"].eventos == ("a-040",)

    def test_severidade_vem_do_yaml(self, vms, acesso, regras) -> None:
        regras_lista, janela = regras
        por_regra = {
            i.regra: i for i in detectar(vms, acesso, regras_lista, janela)
        }
        assert por_regra["badge-clonado"].severidade == "alta"
        assert por_regra["fora-de-horario"].severidade == "media"

    def test_rotina_nao_gera(self, vms, acesso, regras) -> None:
        # So rotina: dois acessos normais e um movimento. Nada para acusar.
        regras_lista, janela = regras
        rotina_v = [e for e in vms if e.id in ("v-001", "v-002")]
        rotina_a = [e for e in acesso if e.id in ("a-001", "a-002")]
        assert detectar(rotina_v, rotina_a, regras_lista, janela) == []