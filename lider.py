import os
import time
from database import Database
from bs4 import BeautifulSoup
from helium import *
import datetime
import db_test
import logging
import pandas as pd
#from playsound import playsound

logging.basicConfig(filename='lider.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')
producto_object = Database()


def urls(empresa, url):
    cuenta_url = 1
    respuesta = ''
    productos = True
    # while True:
    while True:

        zurl = url.format(cuenta_url)
        print(zurl)
        ids = None
        sku = ''
        marca = ''
        descripcion = ''
        # precio = ''
        lo_sentimos = None
        browser = start_firefox(zurl, headless=True)
        # browser = start_firefox(zurl)
        time.sleep(10)

        try:
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            if soup:  # si devuelve codigo html

                lo_sentimos = soup.find_all('h2',
                                            class_='void-plp__page__title')  # si tiene esta clase no hay mas productos

                if lo_sentimos:
                    print(str(lo_sentimos[0].text))
                    # productos = False
                    # zurl = ''
                    kill_browser()
                    break
                producto = list()
                tarjetas = soup.find_all('li', class_='ais-Hits-item')
                if tarjetas:
                    
                    for t in tarjetas:
                        # print(t)
                        m = (t.find_next('div', class_='product-card_description-wrapper'))
                        ###################marca###################
                        marca = m.find_next('span', class_='').text

                        #####descripcion producto #################
                        descripcion = m.find_next().text
                        palabras = (descripcion.split(' ')[1:])
                        descripcion = ''
                        for p in palabras:
                            descripcion = descripcion + ' ' + p

                        #########precio###################
                        precio = t.find_next('div', class_='product-card__sale-price').text
                        precio = precio.split('$')[1]
                        precio = precio.replace('.', '')

                        #####ID#######
                        id = t.find_next('div', class_='rct-block')
                        # print(id)
                        sku = str(id).split("sku/")[1]
                        sku = sku.split("/")[0]
                        # print(sku, marca, descripcion, precio)

                        datos = {"sku": sku,
                                 "marca": marca,
                                 "descripcion": descripcion.strip(),
                                 "precio": precio,
                                 "precio_tc": '0',
                                 'fecha': datetime.datetime.now().timestamp(),
                                 'tienda': empresa,
                                 'precio_historico': ''}
                        if sku.isnumeric():
                            datos = es_historico(empresa, datos)
                            #print(datos)
                            insertar_producto(empresa, datos)
                    #kill_browser()

                else:
                    kill_browser()
                    break
                    

        except Exception as e:
            print(e)
            logging.error(e)
            pass
        kill_browser()

        cuenta_url += 1


def es_historico(empresa, datos):
    producto_his = producto_object.find(empresa, datos['sku'])
    if producto_his:  # si existe producto en db
        if producto_his.get('precio_historico', ''):
            if producto_his['precio_historico'] != '':  # si el producto tiene el campo precio_historico
                if int(producto_his['precio_historico']) > int(datos['precio']):  # si precio historico es mayor que precio actual
                    datos['precio_historico'] = datos['precio']  # asginar precio actual a precio historico.
                    print("historico_mayor")
                    return datos
                elif int(producto_his['precio_historico']) < int(datos['precio']): # si el precio historico es menor que el precio actual
                    datos['precio_historico'] = producto_his['precio_historico']  # asigna el precio historico a precio historico actual
                    print("historico_menor")
                    return datos
                elif int(producto_his['precio_historico']) == int(datos['precio']):
                    datos['precio_historico'] = producto_his['precio_historico']
                    print("precio_igual")
                    return datos
            else:
                datos['precio_historico'] = datos['precio']
                return datos
        datos['precio_historico'] = datos['precio']
        return datos
    else:
        datos['precio_historico'] = datos['precio']
    
    return datos 

                    
def insertar_producto(empresa, datos):
    porcentage = ''
    # print(datos)

    producto = producto_object.find(empresa, datos['sku'])
    if producto:
        if int(producto.get('precio', '')) != int(datos['precio']):
            if int(producto.get('precio', '')) > int(datos['precio']):
                porcentage = "bajo"
                print("producto {} de {} bajó de precio. Precio anterior {}, precio actual {}".format(datos['sku'],
                                                                                                      empresa, producto[
                                                                                                          'precio'],
                                                                                                      datos['precio']))

            elif int(producto.get('precio', '')) < int(datos['precio']):
                porcentage = 'subio'
                print("producto {} de {} subio de precio. Precio anterior {}, precio actual {}, precio historico {}".format(datos['sku'],
                                                                                                       empresa,
                                                                                                       producto[
                                                                                                           'precio'],
                                                                                                       datos['precio'],datos['precio_historico']))

            if porcentage == 'bajo':
                porcentage = int(int(datos['precio']) * 100) / int(producto.get('precio', ''))
                porcentage = int(-(100 - porcentage))

            if porcentage == 'subio':
                porcentage = int(int(datos['precio']) * 100) / int(producto.get('precio', ''))
                porcentage = int(porcentage - 100)

            print(datos['precio_historico'])
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
                print(e)
                logging.error(e)
            producto_object.update(empresa, datos['sku'], datos['precio'], datos['precio_tc'],
                                   producto.get('precio', ''), producto.get('precio_tc', ''), porcentage, 
                                  datos['precio_historico'])

    else:
        # print(datos)
        print("producto_nuevo: {}".format(datos))
        try:
            db_test.inserta(empresa, datos)
        except Exception as e:
            logging.error(e)
            print(e)
        producto_object.inserta(empresa, datos)


def genera_informe(empresa, inicio, **informe):
    productos = []
    
    precios_bajos = producto_object.find(empresa, inicio, **informe)
    if precios_bajos:
        for p in precios_bajos:
            #print(p.get('sku', ''))
            productos.append([p.get('sku', ''), p.get('marca', ''), p.get('descripcion', ''), p.get('precio', ''),
                             p.get('precio_antiguo', ''),p.get('precio_historico', '') ,p.get('variacion', ''), p.get('tienda', '')])

    if len(productos)>0:

        df = pd.DataFrame(productos, columns=['SKU', 'MARCA', 'DESCRIPCION', 'PRECIO', 'PRECIO_ANTIGUO', 'PRECIO_HISTORICO', 'VARIACION', 'TIENDA'])

        inicio = datetime.datetime.fromtimestamp(inicio)
        inicio = str(inicio)
        fecha = inicio.split(" ")[0]
        hora = inicio.split(" ")[1]
        hora = hora.replace(":", "_")
        hora = hora.split('.')[0]
        print(hora)
        df.to_excel('C:\\Users\\lander\\Desktop\\Desarrollo Personal\\Spyder\\Paris\\ofertas\\{}_{}_{}.xlsx'.format(empresa, fecha, hora))
      
    else:
        print("No hay nuevos cambios de precio en lider")


if __name__ == '__main__':

    links = [
        'https://www.lider.cl/catalogo/category/Celulares/Celulares_y_Telefonos?page={}&hitsPerPage=100',
        'https://www.lider.cl/catalogo/category/Computacion?page={}&hitsPerPage=100',
        'https://www.lider.cl/catalogo/category/Tecno/TV?page={}&hitsPerPage=100',
        'https://www.lider.cl/catalogo/category/Tecno/Audio?page={}&hitsPerPage=100',
        'https://www.lider.cl/catalogo/category/Deportes?page={}&hitsPerPage=100',
        'https://www.lider.cl/catalogo/category/Automovil?page={}&hitsPerPage=100',
        'https://www.lider.cl/catalogo/category/Tecno/Videojuegos?page={}&hitsPerPage=100',
        'https://www.lider.cl/catalogo/category/Tecno/Fotografia?page={}&hitsPerPage=100',
        'https://www.lider.cl/catalogo/category/Electrohogar/Refrigeracion?page={}&hitsPerPage=100',
        'https://www.lider.cl/catalogo/category/Electrohogar/Electrodomesticos?page={}&hitsPerPage=100',
        'https://www.lider.cl/catalogo/category/Dormitorio/?page={}&hitsPerPage=100',
        'https://www.lider.cl/catalogo/category/Climatizacion?page={}&hitsPerPage=100',
        'https://www.lider.cl/catalogo/category/Decohogar?page={}&hitsPerPage=100',
        'https://www.lider.cl/catalogo/category/Deportes_y_Aire_Libre?page={}&hitsPerPage=100'

    ]

    # while True:
    start = time.time()
    print(start)
    #start = 1673637646
    for le in links:
        urls('lider', le)
    print("Terminé con Lider")
    print('Generando Informe')
    informe = {"informe": "informe"}
    genera_informe('lider', start, **informe)
    print("Finalizado")

