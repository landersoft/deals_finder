import requests
import json

base = "https://data.mongodb-api.com/app//endpoint/data/v1/action/"


def actualiza(empresa, where, update):
    url = base + 'updateOne'
    payload = json.dumps({
        "collection": empresa,
        "database": "SpyderDB",
        "dataSource": "Cluster0",

        'filter': where,
        'update': {
            '$set': update
        }
    })
    res = response(url, payload)


def inserta(empresa, where):
    url = base + 'insertOne'
    payload = json.dumps({
        "collection": empresa,
        "database": "SpyderDB",
        "dataSource": "Cluster0",
        "document": where
    })
    res = response(url, payload)


def response(url, payload):

    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Request-Headers': '*',
        'api-key': '',
        'Accept': 'application/ejson'
    }

    respuesta = requests.request("POST", url, headers=headers, data=payload)
    print(respuesta)
    if respuesta:
        return response


