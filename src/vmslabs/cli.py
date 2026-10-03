"""A linha de comando do vmslabs.

The vmslabs command line.

Dois comandos: `correlacionar` cruza os dois sistemas e lista os incidentes, e
`auditar` monta a trilha e verifica a cadeia. O codigo de saida e 1 quando ha
incidente ou a cadeia quebrou, porque integracao que acha problema e passa e
pior do que integracao que nao procura.
"""

from __future__ import annotations

import argparse
import sys

from . import auditoria as modulo_auditoria
from . import eventos as modulo_eventos
from . import incidentes as modulo_incidentes

SAIDA_OK = 0
SAIDA_INCIDENTE = 1
SAIDA_ERRO = 2


def _constroi_parser() -> argparse.ArgumentParser:
    """Monta o parser de argumentos.

    Build the argument parser.

    Returns:
        O parser pronto.
    """
    parser = argparse.ArgumentParser(
        prog="vmslabs",
        description=(
            "Integracao simulada entre CFTV e controle de acesso. / "
            "Simulated CFTV and access control integration."
        ),
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p_cor = sub.add_parser("correlacionar", help="cruza os sistemas e lista incidentes")
    p_cor.add_argument("vms", help="o JSONL do VMS")
    p_cor.add_argument("acesso", help="o JSONL do acesso")
    p_cor.add_argument("--regras", required=True)
    p_cor.add_argument("--saida", help="grava os incidentes neste arquivo")

    p_aud = sub.add_parser("auditar", help="monta a trilha e verifica a cadeia")
    p_aud.add_argument("vms", help="o JSONL do VMS")
    p_aud.add_argument("acesso", help="o JSONL do acesso")

    return parser


def _cmd_correlacionar(args: argparse.Namespace, destino) -> int:
    """Executa `correlacionar`.

    Run `correlacionar`.

    Args:
        args: Os argumentos.
        destino: Onde imprimir.

    Returns:
        O codigo de saida.
    """
    try:
        vms = modulo_eventos.carregar(args.vms, "vms")
        acesso = modulo_eventos.carregar(args.acesso, "acesso")
        regras, janela = modulo_incidentes.carregar_regras(args.regras)
    except Exception as erro:
        print(f"erro de entrada: {erro}", file=sys.stderr)
        return SAIDA_ERRO

    incidentes = modulo_incidentes.detectar(vms, acesso, regras, janela)
    linhas = [
        f"eventos: {len(vms)} VMS, {len(acesso)} acesso",
        f"incidentes: {len(incidentes)}",
        "",
    ]
    for incidente in incidentes:
        linhas.append(f"[{incidente.severidade}] {incidente.regra}")
        linhas.append(f"  {incidente.descricao}")
        linhas.append(f"  eventos: {', '.join(incidente.eventos)}")
    texto = "\n".join(linhas)
    print(texto, file=destino)

    if args.saida:
        from pathlib import Path

        caminho = Path(args.saida)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(texto + "\n", encoding="utf-8", newline="\n")
        print(f"incidentes gravados em {caminho}", file=destino)

    return SAIDA_INCIDENTE if incidentes else SAIDA_OK


def _cmd_auditar(args: argparse.Namespace, destino) -> int:
    """Executa `auditar`.

    Run `auditar`.

    Args:
        args: Os argumentos.
        destino: Onde imprimir.

    Returns:
        O codigo de saida.
    """
    try:
        vms = modulo_eventos.carregar(args.vms, "vms")
        acesso = modulo_eventos.carregar(args.acesso, "acesso")
    except Exception as erro:
        print(f"erro de entrada: {erro}", file=sys.stderr)
        return SAIDA_ERRO

    trilha = modulo_auditoria.montar(vms + acesso)
    ok, indice = modulo_auditoria.verificar(trilha)
    print(f"registros: {len(trilha)}", file=destino)
    if ok:
        print("cadeia integra: nenhum registro adulterado", file=destino)
        return SAIDA_OK
    print(f"cadeia QUEBRADA no registro {indice}", file=destino)
    return SAIDA_INCIDENTE


def main(argv: list[str] | None = None) -> int:
    """O ponto de entrada.

    The entry point.

    Args:
        argv: Os argumentos, sem `argv[0]`.

    Returns:
        O codigo de saida.
    """
    parser = _constroi_parser()
    args = parser.parse_args(argv)

    acoes = {"correlacionar": _cmd_correlacionar, "auditar": _cmd_auditar}
    acao = acoes.get(args.comando)
    if acao is None:
        parser.error(f"comando desconhecido: {args.comando}")
        return SAIDA_ERRO
    return acao(args, sys.stdout)


if __name__ == "__main__":
    main()