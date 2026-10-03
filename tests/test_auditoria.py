"""Testes da trilha de auditoria.

Audit trail tests.

A trilha tem uma propriedade que precisa ser verdade sempre: alterar 1 byte
em qualquer registro invalida a cadeia a partir dali. E o teste negativo
obrigatorio da especificacao, e e o mais importante do arquivo - trilha que
nao acusa adulteracao e decoracao.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from vmslabs import auditoria
from vmslabs.eventos import carregar

RAIZ = Path(__file__).resolve().parent.parent
VMS = RAIZ / "dados" / "eventos-vms.jsonl"
ACESSO = RAIZ / "dados" / "eventos-acesso.jsonl"


@pytest.fixture(scope="module")
def trilha():
    eventos = carregar(VMS, "vms") + carregar(ACESSO, "acesso")
    return auditoria.montar(eventos)


class TestIntegra:
    """A trilha intacta verifica."""

    def test_monta_21(self, trilha) -> None:
        assert len(trilha) == 21

    def test_verifica_ok(self, trilha) -> None:
        ok, indice = auditoria.verificar(trilha)
        assert ok is True

    def test_ordem_por_tempo(self, trilha) -> None:
        tempos = [r.tempo for r in trilha] if hasattr(trilha[0], "tempo") else None
        if tempos is not None:
            assert tempos == sorted(tempos)

    def test_vazia_ok(self) -> None:
        assert auditoria.verificar(auditoria.montar([]))[0] is True


class TestAdulteracao:
    """O teste negativo obrigatorio."""

    def test_um_byte_quebra(self, trilha) -> None:
        adulterada = [
            dataclasses.replace(r, resumo=r.resumo + "X") if i == 5 else r
            for i, r in enumerate(trilha)
        ]
        ok, indice = auditoria.verificar(adulterada)
        assert ok is False
        assert indice == 5

    def test_primeiro_quebra_no_zero(self, trilha) -> None:
        adulterada = [
            dataclasses.replace(r, resumo="outro") if i == 0 else r
            for i, r in enumerate(trilha)
        ]
        ok, indice = auditoria.verificar(adulterada)
        assert ok is False
        assert indice == 0

    def test_ultimo_quebra_no_fim(self, trilha) -> None:
        ultimo = len(trilha) - 1
        adulterada = [
            dataclasses.replace(r, resumo="outro") if i == ultimo else r
            for i, r in enumerate(trilha)
        ]
        ok, indice = auditoria.verificar(adulterada)
        assert ok is False
        assert indice == ultimo


class TestAcrescentar:
    """O encadeamento."""

    def test_hash_amarra_anterior(self, trilha) -> None:
        for anterior, atual in zip(trilha, trilha[1:]):
            assert atual.hash_anterior == anterior.hash_atual

    def test_genese_tem_anterior_zero(self, trilha) -> None:
        assert trilha[0].hash_anterior in ("0" * 64, "0", "")