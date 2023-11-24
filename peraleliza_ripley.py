import datetime
import time
import logging

import requests
#import json
from bs4 import BeautifulSoup
# import pandas as pd
from database import Database
import db_test
import pandas as pd
from multiprocessing import Pool

logging.basicConfig(filename='ripley.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')
producto_object = Database()


def urls(url):
    empresa = 'ripley'
    cuenta_url = 1
    respuesta = ''

    while True:

        zurl = (url + '?source=menu&page={}&s=mdco').format(cuenta_url)
        print(zurl)
        time.sleep(1)
        try:
            pagina = requests.get(zurl, timeout=30)
        except Exception as e:
            logging.error(e)
            print(e)
            print(zurl)
            pagina = None
            continue
        if pagina:
            if pagina.status_code == 200:
                respuesta = sopa(empresa, pagina)
                if respuesta == 'nok':
                    break
                cuenta_url += 1
                # print('OK')

        else:
            print(pagina.status_code)
            print("no hay respuesta")
            continue


def sopa(empresa, pagina):
    soup = BeautifulSoup(pagina.content, 'html.parser')
    tarjetas = soup.find_all('div', class_='catalog-product-item catalog-product-item__container col-xs-6 col-sm-6 '
                                           'col-md-4 col-lg-4')
    # if data:
    #    for d in data:
    # tarjetas = d.find_all_next('div', class_='catalog-product-item')
    print(len(tarjetas))
    if tarjetas:
        for t in tarjetas:
            # logging.info(t)

            # marca = ''
            # producto = ''
            # sku = ''
            precio1 = None
            precio2 = None
            precio = None
            sku = (t.find_next('a',
                               class_='catalog-product-item catalog-product-item__container undefined')).get(
                'id', '')
            # if not sku.startswith("MP"):

            # print(sku)
            # print(t)
            # print(precio)
            sopa_precio = list
            marca = (t.find_next('div', class_='brand-logo')).text
            # print(marca)
            producto = t.find_next('div', class_='catalog-product-details__name').text
            # print(producto)
            sopa_precio = t.find_next('div', class_='catalog-product-details__prices').text
            sopa_precio = sopa_precio.strip()
            sopa_precio = sopa_precio.split('$')
            # print(len(sopa_precio))
            precio = sopa_precio[len(sopa_precio) - 1].replace('.', '')
            # print(precio)

            # precio = t.find_next()
            # precio1 = busca_precio_tarjeta(sopa_precio)

            # if not precio1:
            #    precio2 = busca_precio_normal(sopa_precio)
            # precio = precio.replace('$', '')
            # precio = precio.replace('.', '')
            # print("precio_ripley: {}".format(precio1))
            # print("precio_internet:{}".format(precio2))

            datos = {"sku": sku,
                     "marca": marca.strip(),
                     "producto": producto.strip(),
                     "precio": precio,
                     "precio_tc": '0',
                     "fecha": datetime.datetime.now().timestamp(),
                     "tienda": empresa,
                     "precio_historico": ''
                     }
            if sku.startswith("MP"):
                # print(data)
                pass
            else:
                # print(data)
                #juego = es_historico(empresa, datos)
                #print("juego:{}".format(juego))
                insertar_producto(empresa, datos)
    else:
        return 'nok'


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


def busca_precio_tarjeta(t):
    precio = t.find_next('li', title='Precio Ripley')
    if precio:
        # print(precio)
        return precio.text
    return precio


def busca_precio_normal(t):
    precio = t.find_next('li', title='Precio Internet')
    if precio:
        # print(precio)
        return precio.text
    return precio


def insertar_producto(empresa, datos):
    producto = producto_object.find(empresa, datos['sku'])
    if producto:
        porcentage = ''

        if int(producto.get('precio', '')) != int(datos.get('precio', '')):
            if int(producto.get('precio', '')) > int(datos.get('precio', '')):
                print("ALERTA BAJÓ PRECIO DE: sku {} en tienda {} precio antiguo {} precio actual {}".format(
                    datos.get('sku', ''), producto.get('tienda', ''), producto.get('precio', ''),
                    datos.get('precio')))
                porcentage = 'bajo'

            elif int(producto.get('precio', '')) < int(datos.get('precio', '')):
                # print("ALERTA  PRECIO CON TC: sku {} en tienda {} precio antiguo {} precio actual {}".format(
                # datos.get('sku', ''), producto.get('tienda', ''), producto.get('precio', ''),
                # datos.get('precio', ''))
                porcentage = 'subio'

            if porcentage == 'bajo':
                porcentage = (int(datos['precio']) * 100) / int(producto.get('precio', ''))
                porcentage = int(-(100 - porcentage))

            if porcentage == 'subio':
                porcentage = (int(datos['precio']) * 100) / int(producto.get('precio', ''))
                porcentage = int(porcentage - 100)
            print("datos")
            print(datos)
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
                             p.get('precio_antiguo', ''),p.get('precio_historico', ''), p.get('variacion', '')
                             , p.get('tienda', '')])
    if len(productos)> 0:
        df = pd.DataFrame(productos, columns=['SKU', 'MARCA', 'DESCRIPCION', 'PRECIO', 'PRECIO_ANTIGUO','PRECIO_HISTORICO' ,'VARIACION', 'TIENDA'])
    #print(df)
        inicio = datetime.datetime.fromtimestamp(inicio)
        inicio = str(inicio)
        fecha = inicio.split(" ")[0]
        hora = inicio.split(" ")[1]
        hora = hora.replace(":", "_")
        hora = hora.split('.')[0]
        print(hora)
        df.to_excel("C:\\Users\\lander\\Desktop\\Desarrollo Personal\\Spyder\\Paris\\ofertas\\{}_{}_{}.xlsx".format(empresa, fecha,hora))
    else:
        print("No hay cambios de bajas de precio")


if __name__ == '__main__':

    links = [
        'https://simple.ripley.cl/tecno/computacion',
        'https://simple.ripley.cl/tecno/celulares',
        'https://simple.ripley.cl/tecno/fotografia-y-video',
        'https://simple.ripley.cl/tecno/smartwatches-y-smartbands',
        'https://simple.ripley.cl/tecno/television',
        'https://simple.ripley.cl/tecno/audio-y-musica',
        'https://simple.ripley.cl/tecno/computacion-gamer',
        'https://simple.ripley.cl/electro/refrigeracion',
        'https://simple.ripley.cl/deporte-y-aventura/bicicletas',
        'https://simple.ripley.cl/deporte-y-aventura/zapatillas',
        'https://simple.ripley.cl/moda-hombre',
        #'https://simple.ripley.cl/automotriz',
        'https://simple.ripley.cl/otras-categorias/instrumentos-musicales',
        'https://simple.ripley.cl/deporte-y-aventura/ropa-deportiva',
        #'https://simple.ripley.cl/electro/especial-calefaccion'


    ]
    #start = 1673637643
    # while True:
    start = time.time()
    
    print(datetime.datetime.fromtimestamp(start))
    
    with Pool(processes=1) as pool:
        pool.map(urls, links)

    #for le in links:
    #    urls('ripley', le)
    print("Terminé con Ripley")
    print("Generando Informe")
    informe = {"informe": "informe"}
    genera_informe('ripley', start, **informe)
    print("Finalizado")
    fin = time.time()
    print(datetime.datetime.fromtimestamp(start))
    print(datetime.datetime.fromtimestamp(fin))
