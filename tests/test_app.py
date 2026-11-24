import base64
import json
import unittest

from guia_transporte.app import lambda_handler


def invocar(pedido):
    return lambda_handler({"body": json.dumps(pedido)}, None)


class GuiaDeTransporteTest(unittest.TestCase):
    def test_gera_guia_com_os_dados_do_pedido(self):
        resposta = invocar({
            "requisicaoId": "R-001",
            "hospital": "H-Recife",
            "bolsas": ["O-NEG-0142"],
        })

        self.assertEqual(resposta["statusCode"], 201)
        self.assertEqual(resposta["headers"]["Content-Type"], "application/json")
        guia = json.loads(resposta["body"])
        self.assertGreaterEqual(guia.pop("invocacaoNesteAmbiente"), 1)
        self.assertEqual(guia, {
            "guia": "G-R-001",
            "hospital": "H-Recife",
            "bolsas": ["O-NEG-0142"],
        })

    def test_campos_opcionais_podem_ser_omitidos(self):
        resposta = invocar({"requisicaoId": "R-002"})

        self.assertEqual(resposta["statusCode"], 201)
        guia = json.loads(resposta["body"])
        self.assertIsNone(guia["hospital"])
        self.assertEqual(guia["bolsas"], [])

    def test_contador_avanca_no_mesmo_ambiente(self):
        primeira = json.loads(invocar({"requisicaoId": "R-001"})["body"])
        segunda = json.loads(invocar({"requisicaoId": "R-001"})["body"])

        self.assertEqual(
            segunda["invocacaoNesteAmbiente"],
            primeira["invocacaoNesteAmbiente"] + 1,
        )
        self.assertEqual(segunda["guia"], primeira["guia"])

    def test_rejeita_requisicao_sem_identificador_valido(self):
        for pedido in ({}, {"requisicaoId": " "}, {"requisicaoId": 123}):
            with self.subTest(pedido=pedido):
                resposta = invocar(pedido)
                self.assertEqual(resposta["statusCode"], 400)
                self.assertIn("requisicaoId", json.loads(resposta["body"])["erro"])

    def test_rejeita_corpo_invalido(self):
        for corpo in (None, "{", "[]", "null", 42):
            with self.subTest(corpo=corpo):
                resposta = lambda_handler({"body": corpo}, None)
                self.assertEqual(resposta["statusCode"], 400)
                self.assertIn("erro", json.loads(resposta["body"]))

    def test_rejeita_campos_opcionais_invalidos(self):
        casos = [
            ("hospital", 123),
            ("hospital", ""),
            ("bolsas", "O-NEG-0142"),
            ("bolsas", [123]),
            ("bolsas", [" "]),
            ("demorar", "true"),
        ]
        for campo, valor in casos:
            with self.subTest(campo=campo, valor=valor):
                resposta = invocar({"requisicaoId": "R-001", campo: valor})
                self.assertEqual(resposta["statusCode"], 400)
                self.assertIn(campo, json.loads(resposta["body"])["erro"])

    def test_decodifica_o_corpo_base64_do_api_gateway(self):
        corpo = base64.b64encode(b'{"requisicaoId":"R-004"}').decode("ascii")
        resposta = lambda_handler({"body": corpo, "isBase64Encoded": True}, None)

        self.assertEqual(resposta["statusCode"], 201)
        self.assertEqual(json.loads(resposta["body"])["guia"], "G-R-004")

    def test_rejeita_base64_invalido(self):
        resposta = lambda_handler({"body": "???", "isBase64Encoded": True}, None)

        self.assertEqual(resposta["statusCode"], 400)
        self.assertIn("erro", json.loads(resposta["body"]))
