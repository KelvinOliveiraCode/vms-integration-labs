"""Prova de aceite do vmslabs.

vmslabs acceptance proof.

O criterio de aceite tem duas metades:

1. **Os 4 incidentes sao detectados**, cada um pela sua regra. Tres nao
   basta: o quarto e o que prova que a correlacao distingue casos parecidos.
2. **Alterar um registro invalida a cadeia.** E o teste negativo
   obrigatorio: trilha que nao acusa adulteracao e decoracao.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from vmslabs import auditoria as modulo_auditoria  # noqa: E402
from vmslabs import eventos as modulo_eventos  # noqa: E402
from vmslabs import incidentes as modulo_incidentes  # noqa: E402

VMS = RAIZ / "dados" / "eventos-vms.jsonl"
ACESSO = RAIZ / "dados" / "eventos-acesso.jsonl"
REGRAS = RAIZ / "dados" / "regras-incidente.yaml"

ESPERADOS = {"badge-clonado", "porta-forcada", "fora-de-horario", "camera-offline"}


class Falha(Exception):
    """Uma condicao de aceite nao foi satisfeita."""


def checar(condicao: bool, mensagem: str) -> None:
    """Falha se a condicao e falsa.

    Args:
        condicao: A condicao.
        mensagem: O que deu errado.

    Raises:
        Falha: Se a condicao for falsa.
    """
    if not condicao:
        raise Falha(mensagem)


def principal() -> int:
    """Roda a prova de aceite.

    Returns:
        0 se tudo passar, 1 se alguma condicao falhar.
    """
    try:
        vms = modulo_eventos.carregar(VMS, "vms")
        acesso = modulo_eventos.carregar(ACESSO, "acesso")
        regras, janela = modulo_incidentes.carregar_regras(REGRAS)
        incidentes = modulo_incidentes.detectar(vms, acesso, regras, janela)

        achadas = {i.regra for i in incidentes}
        checar(
            achadas == ESPERADOS,
            f"esperava {sorted(ESPERADOS)}, vieram {sorted(achadas)}",
        )
        print(f"1) os 4 incidentes detectados: {sorted(achadas)}")

        trilha = modulo_auditoria.montar(vms + acesso)
        ok, _ = modulo_auditoria.verificar(trilha)
        checar(ok, "a trilha intacta nao verificou")
        adulterada = [
            dataclasses.replace(r, resumo=r.resumo + "X") if i == 5 else r
            for i, r in enumerate(trilha)
        ]
        ok2, indice = modulo_auditoria.verificar(adulterada)
        checar(not ok2 and indice == 5, "a adulteracao nao quebrou onde devia")
        print("2) adulterar 1 registro invalida a cadeia no ponto exato")
    except Falha as erro:
        print("\nACEITE FALHOU:")
        print(f"  - {erro}")
        return 1

    print("\nok: 4 incidentes, cadeia valida e adulteracao detectada")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())