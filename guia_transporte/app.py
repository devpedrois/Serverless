import base64
import json
import time

contador = 0


def _resposta(status, corpo):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(corpo),
    }


def _texto_valido(valor):
    return isinstance(valor, str) and bool(valor.strip())


def lambda_handler(event, context):
    global contador
    contador += 1

    corpo = event.get("body")
    if not isinstance(corpo, str):
        return _resposta(400, {"erro": "O corpo deve ser um objeto JSON."})

    try:
        if event.get("isBase64Encoded"):
            corpo = base64.b64decode(corpo, validate=True).decode("utf-8")
        pedido = json.loads(corpo)
    except (ValueError, RecursionError):
        return _resposta(400, {"erro": "O corpo deve ser um objeto JSON."})

    if not isinstance(pedido, dict):
        return _resposta(400, {"erro": "O corpo deve ser um objeto JSON."})

    requisicao_id = pedido.get("requisicaoId")
    hospital = pedido.get("hospital")
    bolsas = pedido.get("bolsas", [])
    demorar = pedido.get("demorar", False)

    if not _texto_valido(requisicao_id):
        return _resposta(400, {"erro": "requisicaoId exige texto não vazio."})
    if hospital is not None and not _texto_valido(hospital):
        return _resposta(400, {"erro": "hospital exige texto não vazio."})
    if not isinstance(bolsas, list) or not all(map(_texto_valido, bolsas)):
        return _resposta(400, {"erro": "bolsas exige uma lista de identificadores."})
    if not isinstance(demorar, bool):
        return _resposta(400, {"erro": "demorar exige um valor booleano."})

    if demorar:
        time.sleep(5)

    return _resposta(201, {
        "guia": f"G-{requisicao_id}",
        "hospital": hospital,
        "bolsas": bolsas,
        "invocacaoNesteAmbiente": contador,
    })
