import database
import db_test
import lider
import paris
import ripley
import time 
import datetime



def despliega_menu():
    try:
        empresa = int(input("¿de cual empresa?\n\n1)lider \n2)ripley \n3)paris : \n"))
    except ValueError:
        print("No es una opcion valida")
    if empresa == 1:
        solicita_informe('lider')
    elif empresa == 2:
        solicita_informe('ripley')
    else:
        solicita_informe('paris')


def solicita_informe(empresa):
    
        
        fecha = datetime.datetime.today()
        fecha = str(fecha).split(' ')[0]
        calendario = fecha.split('-')
        inicio = datetime.datetime(int(calendario[0]),int(calendario[1]),int(calendario[2]),0,0).timestamp()
        informe = {"informe": "informe"}

        if empresa == 'lider':
            lider.genera_informe(empresa,inicio, **informe)
        elif empresa == 'ripley':
            ripley.genera_informe(empresa,inicio, **informe)
        elif empresa == 'paris':
            paris.genera_informe(empresa,inicio, **informe)


if __name__== '__main__':
    despliega_menu()