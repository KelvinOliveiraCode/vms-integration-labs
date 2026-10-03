# A Trilha de Auditoria: por que o log precisa ser append-only

## 1. Por que o log precisa ser append-only: editar passado é reescrever história

Um log de segurança é, antes de qualquer outra coisa, um registro de fatos: quando uma porta é forçada, um cartão é lido ou uma câmera registra movimento, o evento já aconteceu. A função do log é preservar o que ocorreu, não o que os participantes gostariam que tivesse ocorrido.

Se o arquivo permite edição em posições arbitrárias — apagar linhas, sobrescrever carimbos, inserir ocorrências em tempo real para preencher buracos —, cada um com privilégio de escrita pode alterar a narrativa. O log editável deixa de ser evidência e vira um rascunho compartilhado, cujo conteúdo final depende de quem escreveu por último e não do que aconteceu de fato.

Essa diferença separa uma conclusão correta de uma equivocada. O próprio ambiente de laboratório ilustra o risco: dois sistemas registram os mesmos fenômenos físicos, mas com relógios diferentes. O VMS carimba em segundos desde a época; o controle de acesso carimba em formato ISO, e os dois relógios não andam juntos — o acesso está 47 segundos adiantado em relação ao VMS. Sem essa constatação, a conclusão sobre a mesma sequência seria "a câmera viu antes do cartão passar"; com ela, passa a ser "o cartão passou na porta e a câmera viu". Quarenta e sete segundos são a diferença entre conclusões opostas sobre o mesmo fato, uma ambiguidade que nasce da medição, sem que ninguém precise adulterar nada. Se o log fosse editável, o risco adicional seria ajustar carimbos para "esquecer" o deslocamento ou aproximar ou distanciar ocorrências do que estavam. O append-only elimina essa via: uma vez gravado, um registro não pode ser reescrito, substituído ou movido. Qualquer mudança só pode aparecer como um novo registro, que carimba o momento em que foi feito — e esse carimbo também fica imutável. O append-only, portanto, não protege contra erro humano isolado, mas impede que uma edição localizada reescreva a história em escala.

## 2. Hash encadeado: como cada registro amarra o anterior e alterar um byte invalida a cadeia

Append-only é a condição necessária para uma trilha confiável, mas por si só não prova que os dados gravados são os originais. Para isso, usa-se um hash encadeado: cada registro guarda, além do seu conteúdo, o resumo criptográfico — o hash — do registro imediatamente anterior, repetindo-se a partir de um estado inicial conhecido e assinado.

Isso cria uma corrente em que a integridade de qualquer linha depende da de todas as anteriores. O hash é uma função de mão única: a partir do conteúdo anterior obtém-se um resumo determinístico, mas não é possível reverter o resumo nem produzir outro conteúdo que gere o mesmo resumo. Se alguém alterar um único bit em um registro histórico — um carimbo, um identificador, uma palavra — o hash daquele registro muda completamente. Como o registro seguinte guarda esse hash antigo como referência, a mudança se propaga até o fim da sequência.

A consequência é que a cadeia não admite "uma alteração silenciosa": qualquer modificação localizada quebra o encadeamento a partir do ponto da alteração, e a discordância corre até o final. O auditor descobre onde a corrente se rompe e sabe exatamente em que ponto a confiança começou a falhar. Esse comportamento permite ainda distinguir "o log foi alterado" de "o log foi corrompido acidentalmente": ambos geram quebra no encadeamento, e apenas um envolve intenção. Em um ambiente com dois relógios, o efeito protetor é particularmente valioso: como o alinhamento dos tempos depende de um deslocamento conhecido vindo da topologia e não dos próprios eventos, o log precisa guardar também a versão desse ajuste. Quem reescrevesse o log sem o encadeamento poderia apagar a constatação dos 47 segundos e induzir correlações falsas; com o encadeamento, o registro dessa constatação também fica sob proteção.

## 3. Como verificar integridade sem ferramenta paga: recalcular do zero e comparar

A grande vantagem do hash encadeado é que ele não exige licença de software, assinatura de serviço ou produto comercial para ser auditado. A verificação consiste em três passos simples e reproduzíveis.

Primeiro, escolher um estado inicial. Um valor genérico e explícito — por exemplo, o hash de uma string vazia, seguido de uma assinatura manual desse estado — define o ponto de partida. Sem esse ponto de partida acordado, toda a cadeia seria válida e, portanto, não valeria nada.

Segundo, percorrer o arquivo linha a linha, do começo ao fim, aplicando a mesma função hash a cada bloco e comparando o resultado com o hash que o bloco seguinte declara conter. A função deve ser pública e verificável: o mesmo algoritmo e as mesmas regras de empacotamento produzem o mesmo resumo em qualquer máquina.

Terceiro, declarar o resultado. Se o último bloco do arquivo leva, passo a passo, ao estado final esperado, o log é íntegro. Se em algum ponto o recálculo diverge do hash declarado, o auditor para ali e relata exatamente onde a quebra ocorreu: o relatório não diz "o log está corrompido"; diz "entre o registro N e o registro N+1 a corrente se rompe", o que é informação acionável.

Essa abordagem é transparente o suficiente para o auditor rodar a própria verificação em vez de confiar em terceiros. Não há caixa-preta, não há binary proprietário e não há promessa de fornecedor. Cada linha de raciocínio é visível: qual é o algoritmo, qual é o estado inicial, quais bytes entram em cada cálculo. O custo de verificar um log inteiro é praticamente nulo — um laço simples sobre um arquivo de texto. Qualquer script básico, feito a partir de funções já disponíveis no sistema operacional, realiza essa verificação sem aquisição adicional. O resultado não é "confiança zero" nem "confiança total": o auditor sabe exatamente quantos registros estão abaixo da quebra conhecida e quantos permanecem dentro da corrente preservada. Isso é suficiente para tomar decisões em um incidente e é melhor do que o log editável, onde a integridade é uma aposta sobre a boa-fé de quem tem acesso de escrita.

## 4. O que append-only não resolve: não impede omissão nem atraso

Append-only resolve um problema preciso: impede que um registro gravado seja reescrito ou apagado após a gravação. Ele não resolve os problemas de omissão e de atraso, que são de natureza diferente e exigem outras defesas.

A omissão ocorre quando um evento nunca é registrado. Se um atacante tem acesso ao agente que produz eventos, ele pode interromper a produção ou descartar os eventos mais incômodos antes que cheguem ao log. Nenhum mecanismo de hash encadeado detecta isso, porque a cadeia está perfeitamente íntegra do começo ao fim — ela apenas nunca foi alimentada com aquele evento. O append-only protege o que existe; não protege o que não existe.

O atraso ocorre quando um evento é registrado, mas só aparece muito depois. Um registrador que armazena localmente e sincroniza quando a rede volta pode entregar uma rajada de eventos com carimbos antigos. Para um auditor que busca linhas de tempo, essa rajada pode parecer uma reescrita do passado. A cadeia continua válida, porque cada registro contém o hash correto do anterior. O que não é visível pelo encadeamento é o intervalo de silêncio entre a gravação no sistema de origem e a chegada ao log.

A omissão e o atraso são atenuados por outras medidas: replicação imediata para um repositório de log sob controle de outra conta, verificação de continuidade numérica de sequências, carimbos de recebimento separados dos carimbos de ocorrência e monitoramento do estado dos próprios registradores de evento. Em um ambiente com dois relógios como o descrito, uma medida adicional é comparar o ritmo esperado de eventos em cada origem com o ritmo efetivo no log consolidado; um ritmo que para subitamente indica omissão, e um ritmo que volta todos de uma vez indica atraso.

Em suma, append-only é a base — a condição sobre a qual hash encadeado, verificação recorrente e carimbos de recebimento fazem o resto do trabalho. Não é a defesa completa, mas é a que sustenta todas as outras: sem ela, nada do que vem depois tem para quem dizer.
