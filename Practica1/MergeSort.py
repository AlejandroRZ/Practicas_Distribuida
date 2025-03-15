"""
Práctica 1 - Árboles

Computación Distribuida 2025-2

Profesores:

- Mauricio Riva Palacio Orozco

- Adrián Felipe Fernández Romero

- Daniel Michel Tavera

Alumno:

- Javier Alejandro Rivera Zavala
"""

import multiprocessing
import random
import sys


"""
Función que mezcla 2 listas siguiendo el algoritmo Merge sort.
Recibe las 2 listas a mezclar.
"""
def merge(izq, der):    
    resultado = []
    i, j = 0, 0    
    # Recorremos ambas listas de inicio a fin, 
    # tomando a cada vez el elemento menor.
    for _ in range(len(izq) + len(der)):
        if i < len(izq) and (j >= len(der) or izq[i] < der[j]):
            resultado.append(izq[i])
            i += 1
        elif j < len(der):
            resultado.append(der[j])
            j += 1
    
    return resultado

"""
Función que nos ayuda a hacer un recorrido de tipo 
Convergecast para realizar el ordenamiendo por mezcla.

Recibe el identificador del proceso en turno, el sub árbol sobre cuya
raíz se trabaja, un diccionario para ir almacenando resultados parciales
y poder enviarlos de vuelta. Recibe también el valor de la última ronda de 
mensajes con Go.

Esta función servirá para ir ordenando el arreglo mediante un recorrido Convergecast.
"""
def merge_sort(id_proceso, arbol_datos, dic_result, max_ronda_go):
   
    hijo_izq, hijo_der, arr, ronda_go = arbol_datos[id_proceso]
    ronda_back = max_ronda_go.value + (max_ronda_go.value - ronda_go) + 1
    
    # Si el nodo es padre de 2 hijos, combinamos data y enviamos de vuelta
    if hijo_izq and hijo_der:
        resultado_izq = dic_result[hijo_izq]
        resultado_der = dic_result[hijo_der]
        arr_ordenado = merge(resultado_izq, resultado_der)
    else:
        arr_ordenado = arr # Si el nodo es hoja, sólo lo mandamos de vuelta

    if ronda_back != max_ronda_go.value + 1:
        print(f"Proceso {id_proceso}, ronda {ronda_back}: recibí mensaje") 
    
    if id_proceso != 1:
        print(f"Proceso {id_proceso}, ronda {ronda_back}: Enviando BACK con {arr_ordenado}")

    dic_result[id_proceso] = arr_ordenado


"""
Función recursiva que construye un árbo lde procesos en el que
se va descomponiendo el arreglo original y sus datos.

Recibe el arreglo de datos, un identificador del proceso que genera el nodo,
el número de ronda en el que se mandó el mensaje Go, el sub árbol de referencia
así como el valor de la última ronda alcanzada para llevar un conteo adecuado.

Esta función se encarga de la parte del recorrido donde se enviarán mensajes Go(data).
"""
def construye_arbol(arr, id_proceso, no_ronda, arbol_datos, max_ronda_go):
    
    with max_ronda_go.get_lock():
        if no_ronda > max_ronda_go.value:
            max_ronda_go.value = no_ronda

    if no_ronda > 1 and id_proceso != 1:
        print(f"Proceso {id_proceso}, ronda {no_ronda}: recibí mensaje")   

    if id_proceso != 1: 
        print(f"Proceso {id_proceso}, ronda {no_ronda}: Enviando GO con {arr}")
         
    
    if len(arr) > 1:
        mitad = len(arr) // 2
        arr_izq, arr_der = arr[:mitad], arr[mitad:]
        
        hijo_izq = id_proceso * 2
        hijo_der = id_proceso * 2 + 1
        
        # Generamos el sub árbol de referencia con raíz en el nodo actual
        arbol_datos[id_proceso] = (hijo_izq, hijo_der, arr, no_ronda)
        
        # Crear procesos para enviar mensajes a los hijos
        proceso_izq = multiprocessing.Process(target=construye_arbol, args=(arr_izq, hijo_izq, no_ronda + 1, arbol_datos, max_ronda_go))
        proceso_der = multiprocessing.Process(target=construye_arbol, args=(arr_der, hijo_der, no_ronda + 1, arbol_datos, max_ronda_go))
        
        # Ejecució de los procesos hijos, el proceso padre espera por ellos antes de continuar.
        proceso_izq.start()
        proceso_der.start()        
        
        proceso_izq.join()
        proceso_der.join()        
    
    else:
        arbol_datos[id_proceso] = (None, None, arr, no_ronda)
    
    # Todos los procesos hijos terminan una vez que se enviaron los Go,
    # funciona así para esta simulación. Solo los procesos hijos terminan, el proceso raíz continúa
    if id_proceso != 1:  
        sys.exit()
   

if __name__ == "__main__":
    arr = [random.randint(1, 100) for _ in range(16)]
    print(f"Arreglo original: {arr}")
    
    arbol_datos = multiprocessing.Manager().dict()
    max_ronda_go = multiprocessing.Value('i', 1)
    
    # Construcción del árbol
    construye_arbol(arr, 1, 0, arbol_datos, max_ronda_go)
    print("\nPrimera fase completada.\n")
    
    # Fase de ordenamiento (Convergecast)
    dic_result = multiprocessing.Manager().dict()
    procesos = []
    
    for id_proceso in sorted(arbol_datos.keys(), reverse=True):
        p = multiprocessing.Process(target=merge_sort, args=(id_proceso, arbol_datos, dic_result, max_ronda_go))
        procesos.append(p)
        p.start()
    
    for p in procesos:
        p.join()
    
    print(f"Arreglo ordenado recibido: {dic_result[1]}")