"""Confere que nenhum arquivo do projeto saiu corrompido.

Check that no file in the project came out corrupted.

Tres criterios: sem U+FFFD, sem CJK, e codigo e dados em ASCII puro. Markdown
pode ter acento. O portao precisa sobreviver ao que ele detecta: o console do
Windows e cp1252, e um ideograma nao existe la, entao a mensagem passa por
`_seguro` antes de ser impressa.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

IGNORAR_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules",
}
IGNORAR_ARQUIVOS = {".coverage", "coverage.xml", "Thumbs.db", "Desktop.ini"}
PREFIXOS_TEMPORARIOS = ("out-", "tmp_", "out.")
EXTENSOES = {".py", ".yaml", ".yml", ".md", ".txt", ".toml", ".json", ".csv", ".html"}
ASCII_PURO = {".py", ".yaml", ".yml", ".toml", ".csv"}

FAIXAS_CJK = (
    (0x2E80, 0x2EFF), (0x3000, 0x303F), (0x3040, 0x30FF),
    (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xA000, 0xA4CF),
    (0xAC00, 0xD7AF), (0xF900, 0xFAFF), (0xFF00, 0xFFEF),
)


def _tem_cjk(caractere: str) -> bool:
    """Se o caractere esta em alguma faixa CJK.

    Args:
        caractere: Um caractere.

    Returns:
        Verdadeiro se for ideograma, kana ou hangul.
    """
    ponto = ord(caractere)
    return any(inicio <= ponto <= fim for inicio, fim in FAIXAS_CJK)


def _seguro(texto: str) -> str:
    """O texto com o que o console nao sabe imprimir escapado.

    Args:
        texto: A mensagem original.

    Returns:
        A mensagem com caracteres nao imprimiveis em `\\uXXXX`.
    """
    try:
        texto.encode(sys.stdout.encoding or "utf-8")
        return texto
    except (UnicodeEncodeError, LookupError):
        return texto.encode("ascii", "backslashreplace").decode("ascii")


def _rotulo(caminho: Path) -> Path:
    """O caminho relativo ao repositorio, ou o absoluto.

    Args:
        caminho: O arquivo.

    Returns:
        O rotulo para o relatorio.
    """
    try:
        return caminho.relative_to(RAIZ)
    except ValueError:
        return caminho


def arquivos() -> list[Path]:
    """Os arquivos de texto do projeto.

    Returns:
        Todos os arquivos com extensao conhecida, exceto os ignorados.
    """
    encontrados: list[Path] = []
    for caminho in RAIZ.rglob("*"):
        if not caminho.is_file():
            continue
        if any(parte in IGNORAR_DIRS for parte in caminho.parts):
            continue
        if caminho.name in IGNORAR_ARQUIVOS:
            continue
        if caminho.name.startswith(PREFIXOS_TEMPORARIOS):
            continue
        if caminho.suffix.lower() in EXTENSOES or caminho.name.startswith("."):
            encontrados.append(caminho)
    return sorted(encontrados)


def confere(caminho: Path) -> list[str]:
    """Confere um arquivo.

    Args:
        caminho: O arquivo.

    Returns:
        Uma mensagem por problema. Vazio significa ok.
    """
    try:
        texto = caminho.read_text(encoding="utf-8")
    except UnicodeDecodeError as erro:
        return [f"{_rotulo(caminho)}: nao decodifica como UTF-8 ({erro})"]

    problemas: list[str] = []
    rotulo = _rotulo(caminho)
    ascii_puro = caminho.suffix.lower() in ASCII_PURO

    for numero, linha in enumerate(texto.splitlines(), start=1):
        if "\ufffd" in linha:
            problemas.append(f"{rotulo}:{numero}: U+FFFD (substituicao)")
        for caractere in linha:
            ponto = ord(caractere)
            if _tem_cjk(caractere):
                problemas.append(
                    f"{rotulo}:{numero}: CJK {caractere!r} U+{ponto:04X}"
                )
                break
            if ascii_puro and ponto > 127:
                problemas.append(
                    f"{rotulo}:{numero}: nao-ASCII {caractere!r} "
                    f"U+{ponto:04X} em codigo/dado"
                )
                break
    return problemas


def principal() -> int:
    """Roda a conferencia em todos os arquivos.

    Returns:
        0 se nenhum problema, 1 se algum.
    """
    problemas: list[str] = []
    lista = arquivos()
    for caminho in lista:
        problemas.extend(confere(caminho))
    if problemas:
        print("encoding FALHOU:")
        for problema in problemas:
            print("  ", _seguro(problema))
        return 1
    print(
        f"encoding ok: {len(lista)} arquivo(s), nenhum U+FFFD, nenhum CJK, "
        "nenhum nao-ASCII em codigo/dado"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())