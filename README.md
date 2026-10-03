# vmslabs

Integração simulada entre CFTV e controle de acesso: fluxo de evento, trilha
de auditoria com hash encadeado e correlação de incidente.

Simulated integration between CFTV and access control: event flow,
hash-chained audit trail and incident correlation.

> **Nada aqui é real.** Dois sistemas simulados geram eventos com relógios
> diferentes. Nenhuma câmera, porta ou nuvem é tocada.

## O que é

Doze eventos VMS e nove de acesso contam a mesma manhã, cada um na sua língua
e no seu relógio. O acesso anda 47 segundos adiantado. O pipeline normaliza os
dois para o mesmo tempo, correlaciona, aplica 4 regras de incidente e monta
uma trilha de auditoria que invalida se 1 byte mudar.

## Por que foi feito

Integração entre sistemas de segurança é o que diferencia instalador de
integrador. E o problema real não é ler dois formatos: é que os relógios não
andam juntos, e 47 segundos são a diferença entre "a câmera viu antes do
cartão passar" e o oposto — conclusão oposta sobre o mesmo fato.

## Como rodar

```powershell
python -m vmslabs correlacionar dados/eventos-vms.jsonl dados/eventos-acesso.jsonl --regras dados/regras-incidente.yaml
```

```
eventos: 12 VMS, 9 acesso
incidentes: 4

[alta] badge-clonado
  cartao C-100 em PORTA-A e PORTA-B com 90s de diferenca
  eventos: a-010, a-011
[alta] porta-forcada
  PORTA-C abriu sem cartao antes
  eventos: a-020
[media] fora-de-horario
  C-103 em PORTA-A as 03:00, fora de 06:00-22:00
  eventos: a-030
[media] camera-offline
  C-104 em PORTA-B com CAM-07 offline ha 40s
  eventos: a-040
```

```powershell
python -m vmslabs auditar dados/eventos-vms.jsonl dados/eventos-acesso.jsonl
```

```
registros: 21
cadeia integra: nenhum registro adulterado
```

Instalação:

```powershell
pip install -e ".[dev]"
```

## Os 4 incidentes

| Regra | O que prova |
|---|---|
| badge-clonado | mesmo cartão em dois lugares com 90s — física, não lógica |
| porta-forcada | abertura sem cartão antes — a ausência de ator é o sinal |
| fora-de-horario | 03:14 fora da janela 06:00-22:00 |
| camera-offline | acesso depois da queda — antes da queda é rotina, não incidente |

A regra de câmera só dispara para acesso **depois** do início da queda. Acesso
anterior é rotina que por acaso precedeu; acusar faria toda a manhã virar
incidente quando uma câmera cai à tarde.

## Trilha append-only

Cada registro amarra o hash do anterior. Alterar 1 byte invalida a cadeia a
partir dali — verificado pelo teste negativo obrigatório. Log que não acusa
adulteração é decoração.

## O que aprendi

- **Quem normaliza alinha; quem correlaciona confia.** Realinhar na correlação
  aplicaria o deslocamento duas vezes.
- **Sem chave compartilhada, só tempo.** VMS fala em câmeras, acesso em
  cartões e portas. Exigir coincidência de local paralisava o correlacionador;
  o significado vem das regras, não dele.
- **Porta forçada não tem cartão.** Exigir ator transformava o incidente mais
  importante em erro de validação.
- **47 segundos decidem conclusão.** Alinhamento conhecido, não estimado —
  estimar drift dos próprios eventos seria raciocínio circular.

## Testes

```powershell
python -m pytest -v
```

41 testes, 94% de cobertura. Cobrem normalização e alinhamento, correlação,
os 4 incidentes cada um pela sua regra, a trilha íntegra e adulterada, e a CLI.

```powershell
python tools/verificar_aceite.py     # 4 incidentes + cadeia valida e quebrada
python tools/verificar_encoding.py   # nenhum caractere corrompido
```

## Limitações

- **Sem zona.** Porta e câmera não têm mapeamento; a correlação é temporal.
- **Deslocamento fixo.** Relógio real deriva; aqui são 47 segundos constantes.
- **Janelas no YAML, não aprendidas.** Valores que separam os plantados da
  rotina; outra rotina precisaria outros valores.
- **Trilha em memória.** Sem persistência, sem rotação, sem backup da trilha.

## Licença

MIT.

---

## English

Simulated CFTV and access-control integration: 12 VMS events and 9 access
events tell the same morning in different formats and clocks (47s apart).
Normalize, correlate, apply 4 incident rules, build a hash-chained audit trail.

### The 4 incidents

Cloned badge (same card, two doors, 90s), forced door (no card before),
off-hours (03:14), camera offline (access after the drop — before is routine).

### Tests

41 tests, 94% coverage.

```powershell
python -m pytest -v
python tools/verificar_aceite.py
python tools/verificar_encoding.py
```

### Limitations

No zone mapping; fixed clock skew; YAML windows, not learned; in-memory trail.

### License

MIT.