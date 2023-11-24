import datetime
import time
import logging
import requests
import json
import pandas as pd
from pandas import ExcelWriter
from bs4 import BeautifulSoup
# import pandas as pd
from database import Database
import db_test
from multiprocessing import Process, Pool

logging.basicConfig(filename='paris.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

producto_object = Database()



def urls(url):
    cuenta_url = 0
    respuesta = ''
    empresa = 'paris'
    while True:

        #zurl = (url + '?start={}&sz=24').format(cuenta_url)
        zurl = "https://cl-ccom-parisapp-plp.ecomm.cencosud.com/v2/getServicePLP/0/0/24?refine_1=cgid=elcTvSmartTV&refine_2=isMarketplace=Paris"
        apikey = "cl-ccom-parisapp-plp"
        cors:"cors"
        params = {"apikey": apikey, "Sec-Fetch-Mode": cors}
        print(zurl)
        time.sleep(1)
        try:
            pagina = requests.get(zurl,params)

        except Exception as e:
            print(e)
            logging.error(e)
            logging.info(zurl)
            print(zurl)
            pagina = None
            continue
        if pagina:
            print(pagina.status_code)
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
        print("no_data")
        return 'nok'
    temp = dict()
    for d in data:
        productos.append(d.get('data-product', 'sin informacion'))

    print("len_productos: {}".format(len(productos)))

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
                        data = es_historico(empresa, data)
                        insertar_producto(empresa, data)

            except Exception as e:
                logging.error(e)
                print('error_sin data json')
                continue


# logging.error(e)
# print('error_sin data sopa')
def es_historico(empresa, datos):
    producto_his = producto_object.find(empresa, datos['sku'])
    if producto_his:  # si existe producto en db
        if not producto_his.get('precio_historico', ''):
            if int(datos['precio']) > int(producto_his['precio']):
                datos['precio_historico'] = producto_his['precio']
                #print("datos1: {}".format(datos))
            elif int(datos['precio']) < int(producto_his['precio']):
                datos['precio_historico'] = datos['precio']

        else:  # si el producto tiene el campo precio_historico
            if int(producto_his['precio_historico']) > int(
                    datos['precio']):  # si precio historico es mayor que precio actual
                datos['precio_historico'] = datos['precio']
                #print("datos2: {}".format(datos))  #  asginar precio actual a precio historico.
            elif int(producto_his['precio_historico']) < int(datos['precio']):
                pass
    else:
        datos['precio_historico'] = datos['precio']
    #print("datos3: {}".format(datos))
    return datos


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
                              p.get('precio_antiguo', ''),p.get('precio_historico', ''), p.get('variacion', ''), p.get('tienda', '')])

    if len(productos) > 0:
        df = pd.DataFrame(productos,
                          columns=['SKU', 'MARCA', 'DESCRIPCION', 'PRECIO', 'PRECIO_ANTIGUO','PRECIO_HISTORICO', 'VARIACION', 'TIENDA'])
        # print(df)
        inicio = datetime.datetime.fromtimestamp(inicio)
        inicio = str(inicio)
        fecha = inicio.split(" ")[0]
        hora = inicio.split(" ")[1]
        hora = hora.replace(":", "_")
        hora = hora.split('.')[0]
        print(hora)
        df.to_excel(
            'C:\\Users\\lander\\Desktop\\Desarrollo Personal\\Spyder\\Paris\\ofertas\\{}_{}_{}.xlsx'.format(empresa,
                                                                                                            fecha,
                                                                                                            hora))
        # writer = ExcelWriter('{}_{}.xlsx'.format(empresa, inicio))
    else:
        print("No hay cambio de precios en paris")


if __name__ == '__main__':
    links = [
        'https://www.paris.cl/deportes/hombre/',
        
        'https://www.paris.cl/hombre/ropa-interior/',
        'https://www.paris.cl/zapatos/hombre/',
        'https://www.paris.cl/zapatos/zapatillas/',]

    links0 =[
            'https://www.paris.cl/electro/television/',
            'https://www.paris.cl/electro/audio/',
            'https://www.paris.cl/electro/audio-hifi/',
            'https://www.paris.cl/tecnologia/computadores/',
            'https://www.paris.cl/tecnologia/celulares/',
            'https://www.paris.cl/tecnologia/smart-home/',
            'https://www.paris.cl/tecnologia/gamers/',
            'https://www.paris.cl/tecnologia/fotografia/',
            'https://www.paris.cl/linea-blanca/refrigeracion/',
            'https://www.paris.cl/linea-blanca/lavado-secado/',
            'https://www.paris.cl/linea-blanca/electrodomesticos/',
            'https://www.paris.cl/deportes/bicicletas/',
            'https://www.paris.cl/electro/instrumentos-musicales/',
            'https://www.paris.cl/linea-blanca/estufas/',

        
        ]
    
    links0 = ['https://www.paris.cl/hombre/moda/']


    
    # while True:
    start = time.time()
    # start = datetime.datetime.fromisoformat(start)
    # start = 1673615740
    print(datetime.datetime.fromtimestamp(start))
    with Pool(processes=1) as pool:
        pool.map(urls, links)
    # empresa = "paris"
    print('Terminé con los datos de Paris')
    informe = {"informe": "informe"}
    genera_informe('paris', start, **informe)
    print("Finalizado")
    fin = time.time()
    
    print(datetime.datetime.fromtimestamp(start))
    print(datetime.datetime.fromtimestamp(fin))
