# Trilha de auditoria: por que o log precisa ser append-only

Um log de segurança é um registro de fatos: quando uma porta é forçada ou um
cartão é lido, o evento já aconteceu. A função do log é preservar o ocorrido,
não o que os participantes gostariam que tivesse ocorrido.

## 1. Por que append-only: editar passado é reescrever história

Se o arquivo permite apagar linhas ou sobrescrever carimbos, quem tem escrita
pode alterar a narrativa. O log editável deixa de ser evidência e vira
rascunho compartilhado, cujo conteúdo final depende de quem escreveu por
último.

O laboratório ilustra o risco sem precisar de adulteração: dois sistemas
registram os mesmos fenômenos com relógios diferentes — o acesso anda 47
segundos adiantado. Sem essa constatação, a conclusão seria "a câmera viu
antes do cartão passar"; com ela, é o oposto. Quarenta e sete segundos separam
conclusões opostas sobre o mesmo fato. Se o log fosse editável, o risco
adicional seria ajustar carimbos para "esquecer" o deslocamento. O append-only
elimina essa via: mudança só aparece como registro novo, com carimbo próprio
também imutável.

    Editar um registro antigo não é um detalhe operacional: é reescrever o
    passado. Em um incidente de porta forçada, mudar o carimbo de um evento
    atrasa ou acelera toda a sequência; o que era um acesso legítimo pode virar
    invasão, ou vice-versa. O append-only torna impossível esse truque. Se é
    preciso admitir algo novo, escreve-se outro registro, e o próprio ato de
    escrever recebe um carimbo que, por sua vez, também não pode ser apagado. A
    história só se modifica pelo acúmulo de registros, nunca pela correção de
    linhas.

## 2. Hash encadeado: cada registro amarra o anterior

Append-only impede reescrita, mas não prova que o gravado é o original. Para
isso, cada registro guarda o hash do anterior, a partir de um estado inicial
conhecido.

A função hash é de mão única: o conteúdo gera o resumo, mas o resumo não
devolve o conteúdo, e é praticamente impossível produzir dois conteúdos
distintos com o mesmo resumo. Alterar um único byte no registro — um carimbo,
um identificador, uma palavra — não ajusta o hash em um ponto qualquer:
produz um resumo totalmente novo, sem relação visível com o anterior. Como
cada sucessor guarda o hash do antecessor, esse novo resumo já não bate com
o esperado pelo próximo registro, e a discordância se arrasta até o último.
A proteção não depende de guardar um log à parte; depende de cada linha
validar a anterior.

Alterar um bit em qualquer registro muda seu hash, e como o seguinte guarda o
antigo como referência, a quebra se propaga até o fim. Não existe "alteração
silenciosa": o auditor descobre onde a corrente se rompe e sabe em que ponto a
confiança falhou. O relatório não diz "o log está corrompido"; diz "entre o
registro N e o N+1 a corrente se rompe", que é informação acionável.

Isso permite distinguir "o log foi alterado" de "o log foi corrompido
acidentalmente": ambos quebram o encadeamento, e só um envolve intenção. A
distinção importa porque a resposta é diferente — investigação num caso,
recuperação de backup no outro — e sem a localização exata da quebra as duas
respostas começam no escuro.

O efeito protetor vale também para o alinhamento: como os 47 segundos vêm da
topologia e não dos eventos, quem reescrevesse o log poderia apagar essa
constatação e induzir correlações falsas. Com o encadeamento, o registro do
ajuste também fica protegido.

## 3. Verificar sem ferramenta paga: recalcular e comparar

Três passos, sem licença nem produto comercial. Primeiro, um estado inicial
acordado — por exemplo, o hash de string vazia com assinatura manual. Sem
ponto de partida, toda cadeia seria válida e não valeria nada. Segundo,
percorrer linha a linha aplicando a mesma função hash pública e comparando
com o hash que o bloco seguinte declara: mesmo algoritmo e mesmo
empacotamento produzem o mesmo resumo em qualquer máquina. Terceiro, declarar
onde quebrou, se quebrou.

O custo é um laço sobre arquivo de texto, com funções do próprio sistema. Não
há caixa-preta: algoritmo, estado inicial e empacotamento são visíveis. O
resultado não é "confiança total": o auditor sabe quantos registros estão
abaixo da quebra e quantos permanecem na corrente — suficiente para decidir
num incidente.

## 4. O que append-only não resolve: omissão nem atraso

Append-only impede reescrever, não impede omitir. Um evento nunca registrado
não quebra cadeia nenhuma — e é por isso que a trilha precisa de
completude verificável por fora, como contadores de sequência sem buraco.

Também não impede atraso: registro gravado horas depois carimba a hora da
gravação, não a do fato. Em incidente com dois relógios, atraso e deslocamento
se confundem, e só a disciplina de gravar na hora separa um do outro.

O append-only é condição necessária, não suficiente. Ele garante que o que
está no log não foi alterado; não garante que tudo que aconteceu está no log.
