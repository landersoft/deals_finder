import datetime
import time
import logging
import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
# import pandas as pd
from database import Database
import db_test

logging.basicConfig(filename='paris.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

producto_object = Database()


def urls(empresa, url):
    cuenta_url = 0
    respuesta = ''

    while True:

        zurl = (url + '?start={}&sz=24').format(cuenta_url)
        print(zurl)
        time.sleep(10)
        try:
            pagina = requests.get(zurl, timeout=30)
        except Exception as e:
            print(e)
            logging.error(e)
            logging.info(zurl)
            print(zurl)
            pagina = None
            continue
        if pagina:
            if pagina.status_code == 200:
                time.sleep(10)
                respuesta = sopa(empresa, pagina)
                if respuesta == 'nok':
                    break
                cuenta_url += 24
        else:
            print(pagina.status_code)
            print("no hay respuesta")
            break


def sopa(empresa, pagina):
    soup = BeautifulSoup(pagina.content, 'html.parser')
    data = soup.find_all('div', class_='product-tile')
    # print(data)
    productos = list()
    if not data:
        return 'nok'
    temp = dict()
    for d in data:
        productos.append(d.get('data-product', 'sin informacion'))

    if len(productos) > 0:
        for p in range(len(productos)):
            try:
                temp[p] = json.loads(productos[p])

                if temp[p]:
                    data = {"sku": str(temp[p]['id']),
                            "marca": str(temp[p]['brand']),
                            "producto": str(temp[p]['name']).strip(),
                            "precio": str(temp[p]['price']),
                            "precio_tc": str(temp[p].get('dimension20', str(temp[p]['price']))),
                            "fecha": datetime.datetime.now().timestamp(),
                            "tienda": empresa,
                            "marketplace": str(temp[p]['id']).startswith('MK'),
                            "precio_historico": ""
                            }
                    if not str(temp[p]['id']).startswith('MK'):
                        # es_historico(empresa, data)
                        insertar_producto(empresa, data)

            except Exception as e:
                logging.error(e)
                print('error_sin data json')
                continue


def es_historico(empresa, datos):
    producto_his = producto_object.find(empresa, datos['sku'])
    if producto_his:  # si existe producto en db
        if producto_his.get('precio_historico', ''):  # si el producto tiene el campo precio_historico
            if producto_his['precio_historico'] > datos['precio']:  # si precio historico es mayor que precio actual
                datos['precio_historico'] = datos['precio']  # asginar precio actual a precio historico.

        else:
            if datos['precio'] > producto_his.get('precio', ''):
                datos['precio_historico'] = producto_his.get('precio', '')


def insertar_producto(empresa, datos):
    producto = producto_object.find(empresa, datos['sku'])
    if producto:
        porcentage = ''

        if int(producto.get('precio', '')) != int(datos.get('precio', '')):
            if int(producto.get('precio', '')) > int(datos.get('precio', '')):
                print("ALERTA BAJÓ PRECIO DE: sku {} en tienda {} precio antiguo {} precio actual {}".format(
                    datos.get('sku', ''), producto.get('tienda', ''), producto.get('precio', ''), datos.get('precio')))
                porcentage = 'bajo'

            elif int(producto.get('precio', '')) < int(datos.get('precio', '')):
                # print("ALERTA DE PRECIO CON TC: sku {} en tienda {} precio antiguo {} precio actual {}".format(
                # datos.get('sku', ''), producto.get('tienda', ''), producto.get('precio', ''),
                # datos.get('precio', '')))
                porcentage = 'subio'

            if porcentage == 'bajo':
                porcentage = int(int(datos['precio']) * 100) / int(producto.get('precio', ''))
                porcentage = int(-(100 - porcentage))

            if porcentage == 'subio':
                porcentage = int(int(datos['precio']) * 100) / int(producto.get('precio', ''))
                porcentage = int((porcentage - 100))

            where = {"sku": datos['sku'],
                     "tienda": empresa}
            update = {"precio": datos['precio'],
                      "precio_tc": datos['precio_tc'],
                      "precio_antiguo": producto.get('precio', ''),
                      "precio_antiguo_tc": producto.get('precio_tc', ''),
                      "variacion": porcentage,
                      "fecha": datetime.datetime.now().timestamp(),
                      "precio_historico": datos['precio_historico']
                      }
            try:
                db_test.actualiza(empresa, where, update)
            except Exception as e:
                logging.error(e)
                print(e)

            producto_object.update(empresa, datos['sku'], datos['precio'], datos['precio_tc'],
                                   producto.get('precio', ''), producto.get('precio_tc', ''), porcentage,
                                   datos['precio_historico'])

    else:
        print("producto_nuevo: {}".format(datos))
        try:
            db_test.inserta(empresa, datos)
        except Exception as e:
            logging.error(e)
            print(e)
        producto_object.inserta(empresa, datos)


def genera_informe(empresa, inicio, **informe):
    productos = []
    # where = {"fecha":{"$gte":inicio}}
    precios_bajos = producto_object.find(empresa, inicio, **informe)
    if precios_bajos:
        for p in precios_bajos:
            productos.append([p.get('sku', ''), p.get('marca', ''), p.get('producto', ''), p.get('precio', ''),
                              p.get('precio_antiguo', ''), p.get('variacion', ''), p.get('tienda', '')])

    if len(productos)> 0:
        df = pd.DataFrame(productos, columns=['SKU', 'MARCA', 'DESCRIPCION', 'PRECIO', 'PRECIO_ANTIGUO', 'VARIACION', 'TIENDA'])
        #print(df)
        inicio = datetime.datetime.fromtimestamp(inicio)
        inicio = str(inicio)
        fecha = inicio.split(" ")[0]
        hora = inicio.split(" ")[1]
        hora = hora.replace(":", "_")
        hora = hora.split('.')[0]
        print(hora)
        df.to_excel('C:\\Users\\lander\\Desktop\\Desarrollo Personal\\Spyder\\Paris\\ofertas\\{}_{}_{}.xlsx'.format(empresa, fecha, hora))
        #writer = ExcelWriter('{}_{}.xlsx'.format(empresa, inicio))
    else:
        print("No hay cambio de precios en lider")

if __name__ == '__main__':
    links = [
        'https://www.paris.cl/electro/television/',
        'https://www.paris.cl/electro/audio/',
        'https://www.paris.cl/electro/audio-hifi/',
        'https://www.paris.cl/tecnologia/computadores/',
        'https://www.paris.cl/tecnologia/celulares/',
        # 'https://www.paris.cl/tecnologia/smart-home/',
        'https://www.paris.cl/tecnologia/gamers/',
        'https://www.paris.cl/tecnologia/fotografia/',
        'https://www.paris.cl/linea-blanca/refrigeracion/',
        'https://www.paris.cl/linea-blanca/lavado-secado/',
        'https://www.paris.cl/linea-blanca/electrodomesticos/',
        'https://www.paris.cl/deportes/bicicletas/',
        'https://www.paris.cl/electro/instrumentos-musicales/',
        'https://www.paris.cl/zapatos/hombre/',
        'https://www.paris.cl/zapatos/zapatillas/'


        # 'https://www.paris.cl/decohogar/navidad/pinos/',
        # 'https://www.paris.cl/decohogar/navidad/esferas/',

    ]
    # while True:
    start = time.time()
    #start = datetime.datetime.fromisoformat(start)
    #start = 1673615740
    print(start)
    for le in links:
        empresa = le.split(".")[1]
        urls(empresa, le)
    #empresa = "paris"
    print('Terminé con los datos de Paris')
    informe = {"informe": "informe"}
    genera_informe('paris', start, **informe)
    print("Finalizado")
