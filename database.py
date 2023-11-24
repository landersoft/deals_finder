import pymongo
import urllib.parse
import datetime


class Database(object):

    def __init__(self):
        self.mycol = None
        self.client = pymongo.MongoClient('mongodb://localhost:27017')
        self.mydb = self.client['SpyderDB']

    def inserta(self, col, data):
        self.mycol = self.mydb[col]
        self.mycol.insert_one(data)

    def find(self, col, where, **informe):
        # print("where: {}".format(where))
        self.mycol = self.mydb[col]
        if informe:

            query = {'fecha': {'$gt': where}, 'variacion': {'$lt': 0}}
            print(query)
            #print(self.mycol.find())
            respuesta = self.mycol.find(query)

        else:
            respuesta = self.mycol.find_one({"sku": where})

        return respuesta

    def update(self, col, sku, precio, precio_tc, precio_antigua, precio_antiguo_tc, porcentage, historico):
        self.mycol = self.mydb[col]
        self.mycol.update_one({"sku": sku},
                              {"$set": {"precio": precio,
                                        "precio_tc": precio_tc,
                                        "fecha": datetime.datetime.now().timestamp(),
                                        "precio_antiguo": precio_antigua,
                                        "precio_antiguo_tc": precio_antiguo_tc,
                                        "variacion": porcentage,
                                        "precio_historico": historico}
                               })
        # pass


if __name__ == '__main__':
    conexion = Database()
    # conexion.inserta('paris', {"nombre": "yoyo2"})
