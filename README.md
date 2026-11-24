# Rota Vital | Guia de transporte

Atividade individual de Infraestrutura de Software da CESAR School.
O Caminho A roda localmente com AWS SAM, Docker e Python 3.12.
A função `POST /guias` monta uma guia JSON de expedição.
Os identificadores de requisições, hospitais e bolsas são fictícios.

## Como rodar

Inicie o Docker Desktop com contêineres Linux.
Instale o AWS SAM CLI e o Python 3.12.
No Windows, use Git Bash na raiz do repositório.
[Docker Desktop](https://docs.docker.com/get-docker/) · [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)

```bash
export SAM_CLI_TELEMETRY=0
export DOCKER_HOST="$(docker context inspect "$(docker context show)" --format '{{.Endpoints.docker.Host}}')"
sam --version
python --version
docker version
sam validate --lint
sam build
python -B -m unittest discover -s tests -v
```

O template adapta o Hello World do SAM.
O pacote Zip usa apenas a biblioteca padrão do Python.

### Invocação por evento

Use o [evento do API Gateway](events/pedido.json) incluído no repositório.
Execute duas invocações independentes com a imagem já disponível.
O Docker baixa a imagem na primeira execução, quando necessário.

```bash
time sam local invoke -e events/pedido.json
time sam local invoke -e events/pedido.json
```

Este comando gera um evento equivalente no terminal.
O SAM pode codificar o corpo do evento em Base64.

```bash
sam local generate-event apigateway aws-proxy --method POST --path guias \
  --body '{"requisicaoId":"R-001","hospital":"H-Recife","bolsas":["O-NEG-0142"]}'
```

### Chamadas HTTP

No primeiro terminal, mantenha a API local aberta.

```bash
sam local start-api --host 127.0.0.1
```

No segundo terminal, execute a chamada três vezes.

```bash
curl -sS -i -w '\nTempo HTTP: %{time_total}s\n' -X POST http://127.0.0.1:3000/guias \
  -H 'Content-Type: application/json' \
  --data-binary '{"requisicaoId":"R-002","hospital":"H-Caruaru"}'
```

`requisicaoId` exige texto não vazio.
`hospital` e `bolsas` são opcionais.
`bolsas` aceita uma lista de identificadores.
`demorar` aceita um booleano e serve ao experimento.
Entradas inválidas retornam HTTP `400`.

Pare o primeiro servidor com `Ctrl+C`.
Suba a API com reaproveitamento e repita as três chamadas.

```bash
sam local start-api --host 127.0.0.1 --warm-containers LAZY
```

### Teste do tempo limite

Reinicie a API com `sam local start-api --host 127.0.0.1`.
Envie o pedido lento no segundo terminal.

```bash
curl -sS -i -w '\nTempo HTTP: %{time_total}s\n' -X POST http://127.0.0.1:3000/guias \
  -H 'Content-Type: application/json' \
  --data-binary '{"requisicaoId":"R-003","demorar":true}'
```

Pare o servidor e altere o parâmetro para dez segundos.
Repita o mesmo `curl` após iniciar a API.

```bash
sam build --parameter-overrides ParameterKey=TempoLimite,ParameterValue=10
sam local start-api --host 127.0.0.1 \
  --parameter-overrides ParameterKey=TempoLimite,ParameterValue=10
```

## Respostas

### 1. Inicialização

Medição local de 23/11/2026 com a imagem Docker em cache.

| Invocação por evento | Tempo total | Init Duration | Duration | Contador |
| --- | ---: | ---: | ---: | ---: |
| Primeira | 5,008 s | 0,03 ms | 37,19 ms | 1 |
| Segunda | 4,736 s | 0,03 ms | 33,14 ms | 1 |

Os dois comandos criaram ambientes de execução diferentes.
O total inclui SAM, Docker e função.
A primeira levou 0,272 s a mais no total.
A maior parte da diferença ocorreu fora da função.
Em `Init`, o Lambda inicia extensões e prepara o runtime.
Também roda os imports e inicializa o contador global.
[Ciclo de vida do Lambda](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html)

### 2. Reaproveitamento do ambiente

| Modo | Contador nas três chamadas HTTP `201` | Tempos HTTP |
| --- | --- | --- |
| Padrão | `1, 1, 1` | 3,454 s / 1,586 s / 1,633 s |
| `LAZY` | `1, 2, 3` | 3,143 s / 1,065 s / 1,063 s |

No modo padrão, cada chamada abriu um novo contêiner.
O pedido sem identificador retornou HTTP `400` em 1,556 s.
Com `LAZY`, a primeira chamada abriu o contêiner.
As seguintes reutilizaram o processo e suas variáveis.
Cada ambiente mantém seu próprio contador.
Estado durável precisa de armazenamento externo.
[Reaproveitamento no SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/using-sam-cli-local-start-api.html)

### 3. Tempo limite

`demorar: true` faz a função dormir por cinco segundos.

| Limite configurado | Resultado | Tempo HTTP |
| --- | --- | ---: |
| 3 s | SAM interrompeu a execução e retornou HTTP `502`. | 9,857 s |
| 10 s | HTTP `201` com a guia `G-R-003`. | 8,425 s |

O relógio HTTP inclui o trabalho do emulador e do Docker.
O log do SAM registrou a interrupção após três segundos.
No segundo teste, o runtime registrou 5.039,90 ms de execução.

O limite anterior do Lambda sob demanda era 15 minutos.
A AWS ampliou o limite em 19/11/2026.
Hoje, funções de evento sob demanda aceitam até 30 minutos.
Trabalhos maiores podem ser divididos em etapas com checkpoints.
O Step Functions pode coordenar essas etapas.
[Anúncio da AWS](https://aws.amazon.com/about-aws/whats-new/2026/11/aws-lambda-30-minute-ondemand-event-functions/)

### 4. Custo de um milhão de execuções

A conta usa os preços do enunciado em `us-east-1`.

```text
128 MB ÷ 1.024 = 0,125 GB
100 ms ÷ 1.000 = 0,1 s
1.000.000 × 0,125 GB × 0,1 s = 12.500 GB-s
12.500 GB-s × US$ 0,0000166667 = US$ 0,20833375
1.000.000 de requisições = US$ 0,20
Total bruto = US$ 0,40833375 ≈ US$ 0,41
```

### 5. Aplicação no Rota Vital

A função faz sentido depois da confirmação do atendimento.
O Rota Vital já emite uma guia na expedição.
Um adaptador poderia enviar os identificadores para `POST /guias`.
Eu manteria a baixa e a fila na transação principal.
Essas operações precisam de consistência entre estoque e requisição.
[Fluxo de atendimento do Rota Vital](https://github.com/Luizrocha0/Proj-EAD/blob/da36222dd086696bd7bb7a6b5dda8d3a6be8ee21/src/main/java/com/rotavital/expedicao/negocio/aplicacao/AtenderRequisicao.java)

## Evidências

Execução registrada com SAM CLI 1.174.0 e Docker 29.8.2.
As seis capturas registram a execução usada nas tabelas.

- [Ambiente, validação e build](evidencias/01-ambiente.png)
- [Duas invocações por evento](evidencias/02-eventos.png)
- [HTTP sem reaproveitamento e entrada inválida](evidencias/03-http-sem-reuso.png)
- [HTTP com reaproveitamento](evidencias/04-http-com-reuso.png)
- [Erro com limite de 3 segundos](evidencias/05-timeout-3s.png)
- [Guia com limite de 10 segundos](evidencias/06-timeout-10s.png)

## Uso de IA

Escolhi o Caminho A e o fluxo de expedição.
Solicitei a revisão manual da função e do template.

Usei o Codex da OpenAI para apoiar o desenvolvimento.
Ele gerou a implementação inicial, os testes e a documentação.
Também auxiliou na instalação e configuração do AWS SAM CLI.
O Codex formatou as evidências da execução inicial.
Refiz os experimentos e capturei as saídas no PowerShell.

Os testes foram escritos antes da função.
A validação incluiu `sam validate`, oito testes unitários e `curl`.
O Codex conferiu manualmente as entradas e a configuração.
