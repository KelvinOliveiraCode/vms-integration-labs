# Fluxo de evento entre sistemas

Dois sistemas contam a mesma manhã, cada um na sua língua e no seu relógio.
Este documento é o mapa de como um fato atravessa os dois e chega ao
incidente — e onde ele pode se perder no caminho.

## As duas línguas

O VMS fala em câmeras e segundos desde a época: `{"tipo": "movimento",
"camera": "CAM-01", "timestamp": 1790824800}`. O acesso fala em cartões,
portas e texto: `{"tipo": "acesso", "cartao": "C-100", "porta": "PORTA-A",
"datahora": "2026-10-01T08:10:00"}`.

Nenhum dos dois está errado; nenhum dos dois é completo. O movimento sem o
cartão é gente sem nome; o cartão sem o movimento é nome sem prova. A
integração existe porque cada lado sabe metade.

## Os relógios não andam juntos

O acesso anda 47 segundos adiantado. Sem alinhar, a correlação conclui o
oposto: a câmera "viu" antes do cartão passar, quando foi o contrário. E 47
segundos decidem conclusão — não são arredondamento.

O deslocamento é conhecido e vem da topologia, não estimado dos dados.
Estimar drift a partir dos próprios eventos que se quer correlacionar é
raciocínio circular: os mesmos pares que provam o incidente provariam
qualquer deslocamento.

## Onde o fato pode se perder

Três lugares, em ordem de frequência:

1. **Na normalização.** Campo obrigatório vazio, data fora do formato, sistema
   desconhecido. Cada um vira erro com linha, não exceção silenciosa — porque
   evento descartado sem aviso é fato perdido sem rastro.
2. **No alinhamento.** Deslocamento aplicado duas vezes, ou não aplicado.
   Erro aqui não falha: desloca tudo e a correlação conclui errado em
   silêncio.
3. **Na janela.** Curta demais perde o incidente; longa demais junta o que
   não tem a ver. Os valores do YAML são os que separam os 4 plantados da
   rotina — outra rotina precisaria outros valores.

## O que a correlação não faz

Ela junta o que aconteceu junto; não decide o que é incidente. Essa decisão é
das regras, com janela e severidade no YAML. Separar as duas coisas é o que
permite testar cada lado sozinho: a correlação com pares conhecidos, as regras
com casos plantados.
