"""Testes da normalizacao entre sistemas.

Cross-system normalization tests.

Dois sistemas, dois formatos, dois relogios. Se a normalizacao errar o
alinhamento por 1 segundo que seja, a correlacao conclui o oposto sobre o
mesmo fato - e o teste que pega isso e o dos 90 segundos do badge clonado,
que e exato por construcao e nao por sorte.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vmslabs.eventos import (
    DESLOCAMENTO_ACESSO_S,
    ErroDeEvento,
    carregar,
    normalizar,
)

RAIZ = Path(__file__).resolve().parent.parent
VMS = RAIZ / "dados" / "eventos-vms.jsonl"
ACESSO = RAIZ / "dados" / "eventos-acesso.jsonl"


class TestArquivosReais:
    """Os dois arquivos carregam."""

    def test_vms_12(self) -> None:
        assert len(carregar(VMS, "vms")) == 12

    def test_acesso_9(self) -> None:
        assert len(carregar(ACESSO, "acesso")) == 9

    def test_deslocamento_travado(self) -> None:
        assert DESLOCAMENTO_ACESSO_S == 47

    def test_badge_clonado_alinhado(self) -> None:
        eventos = {e.id: e for e in carregar(ACESSO, "acesso")}
        assert eventos["a-011"].tempo - eventos["a-010"].tempo == 90


class TestVms:
    """O formato do VMS."""

    def test_basico(self) -> None:
        evento = normalizar(
            {"id": "x", "tipo": "movimento", "camera": "CAM-01", "timestamp": 1000},
            "vms",
        )
        assert evento.tempo == 1000
        assert evento.ator == "CAM-01"

    def test_tempo_invalido(self) -> None:
        with pytest.raises(ErroDeEvento):
            normalizar({"id": "x", "tipo": "t", "camera": "c", "timestamp": "ontem"}, "vms")


class TestAcesso:
    """O formato do acesso, com alinhamento."""

    def test_subtrai_o_deslocamento(self) -> None:
        evento = normalizar(
            {"id": "x", "tipo": "acesso", "cartao": "C-1", "porta": "P",
             "datahora": "2026-10-01T08:10:00"},
            "acesso",
        )
        import datetime

        esperado = int(datetime.datetime(
            2026, 10, 1, 8, 10, 0, tzinfo=datetime.timezone.utc
        ).timestamp()) - 47
        assert evento.tempo == esperado

    def test_data_invalida(self) -> None:
        with pytest.raises(ErroDeEvento):
            normalizar(
                {"id": "x", "tipo": "acesso", "cartao": "C", "porta": "P",
                 "datahora": "ontem"},
                "acesso",
            )

    def test_porta_forcada_sem_cartao(self) -> None:
        # Porta forcada nao tem cartao: e a ausencia de ator que a define.
        # Exigir ator transformaria o incidente mais importante em erro.
        evento = normalizar(
            {"id": "x", "tipo": "porta-forcada", "cartao": "", "porta": "P",
             "datahora": "2026-10-01T08:10:00"},
            "acesso",
        )
        assert evento.tipo == "porta-forcada"

    def test_acesso_normal_sem_cartao_falha(self) -> None:
        with pytest.raises(ErroDeEvento):
            normalizar(
                {"id": "x", "tipo": "acesso", "cartao": "", "porta": "P",
                 "datahora": "2026-10-01T08:10:00"},
                "acesso",
            )

    def test_sistema_desconhecido(self) -> None:
        with pytest.raises(ErroDeEvento):
            normalizar({"id": "x"}, "fax")

    def test_nao_mapa(self) -> None:
        with pytest.raises(ErroDeEvento):
            normalizar(["x"], "vms")  # type: ignore[arg-type]


class TestArquivo:
    """A leitura."""

    def test_inexistente(self, tmp_path: Path) -> None:
        with pytest.raises(ErroDeEvento):
            carregar(tmp_path / "nao-existe.jsonl", "vms")

    def test_json_quebrado(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "x.jsonl"
        arquivo.write_text('{"id":\n', encoding="utf-8")
        with pytest.raises(ErroDeEvento):
            carregar(arquivo, "vms")

    def test_vazio(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "x.jsonl"
        arquivo.write_text("\n", encoding="utf-8")
        with pytest.raises(ErroDeEvento):
            carregar(arquivo, "vms")