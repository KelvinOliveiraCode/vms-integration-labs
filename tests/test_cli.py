"""Testes da CLI.

CLI tests.

A CLI tem dois trabalhos: listar os 4 incidentes com saida 1, e verificar a
cadeia com saida 0. O teste que importa e o de saida: integracao que acha
problema e passa e pior do que integracao que nao procura.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

import pytest

from vmslabs.cli import main as cli_main

RAIZ = Path(__file__).resolve().parent.parent
VMS = RAIZ / "dados" / "eventos-vms.jsonl"
ACESSO = RAIZ / "dados" / "eventos-acesso.jsonl"
REGRAS = RAIZ / "dados" / "regras-incidente.yaml"


def _roda(argv):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        codigo = cli_main(argv)
    return codigo, buffer.getvalue()


class TestCorrelacionar:
    """O cruzamento pela CLI."""

    def test_quatro_incidentes_saida_um(self) -> None:
        codigo, saida = _roda([
            "correlacionar", str(VMS), str(ACESSO), "--regras", str(REGRAS),
        ])
        assert codigo == 1
        for regra in ("badge-clonado", "porta-forcada",
                      "fora-de-horario", "camera-offline"):
            assert regra in saida

    def test_grava_saida(self, tmp_path: Path) -> None:
        destino = tmp_path / "inc.md"
        _roda([
            "correlacionar", str(VMS), str(ACESSO),
            "--regras", str(REGRAS), "--saida", str(destino),
        ])
        assert "badge-clonado" in destino.read_text(encoding="utf-8")

    def test_arquivo_inexistente(self, tmp_path: Path) -> None:
        codigo = cli_main([
            "correlacionar", str(tmp_path / "nao-existe.jsonl"),
            str(ACESSO), "--regras", str(REGRAS),
        ])
        assert codigo == 2


class TestAuditar:
    """A trilha pela CLI."""

    def test_cadeia_integra_saida_zero(self) -> None:
        codigo, saida = _roda(["auditar", str(VMS), str(ACESSO)])
        assert codigo == 0
        assert "integra" in saida

    def test_help_sai_com_zero(self) -> None:
        with pytest.raises(SystemExit) as erro:
            cli_main(["--help"])
        assert erro.value.code == 0

    def test_sem_comando_falha(self) -> None:
        with pytest.raises(SystemExit):
            cli_main([])