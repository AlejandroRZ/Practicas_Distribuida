"""
Práctica 3 - 

Gráficas generales
             

Computación Distribuida 2025-2

Profesores:

- Mauricio Riva Palacio Orozco

- Adrián Felipe Fernández Romero

- Daniel Michel Tavera

Alumno:

- Javier Alejandro Rivera Zavala
"""

import simpy
import random
from collections import defaultdict

"""
Función que construye una gráfica ad hoc para esta práctica.
Recibe el número de nodos en la gráfica, los conecta formando
un camino simple que pasa por todos y luego de ello, recorre cada
nodo y lo conecta con los restantes a razón del 50 % de probabilidad.
"""
def construir_grafica(n):   
    grafica = {i: [] for i in range(n)}
    
    # Conectar en trayectoria lineal (0-1-2-...-n-1)
    for i in range(n - 1):
        grafica[i].append(i + 1)
        grafica[i + 1].append(i)
    
    # Conectar cada vértice con los demás con probabilidad del 50%
    for i in range(n):
        for j in range(n):
            # No conectar consigo mismo, ni repetir conexiones existentes
            if i != j and j not in grafica[i]:
                if random.random() < 0.5:  
                    grafica[i].append(j)
                    grafica[j].append(i)
    
    return grafica

"""
Función que representa la gráfica construida a través de
su matriz de adyacencias.
"""
def mostrar_grafica(grafica):
    n = len(grafica)
    print("\nMatriz de adyacencias:")
    print("   " + " ".join(f"{i:2}" for i in range(n)))
    for i in range(n):
        fila = [1 if j in grafica[i] else 0 for j in range(n)]
        print(f"{i:2} " + " ".join(f"{x:2}" for x in fila))

# Variables de estado globales
padre = {}
hijos = {}
nivel = {}
msg_esperados = {}
excentricidades = {}
diametro = 0
terminar_early = False

# Elementos para la simulación
env = simpy.Environment()
msg_rondas = defaultdict(list)

"""
Función que se encarga de enviar mensajes de Go.
Recibe los procesos que son parte de la comunicación y la distancia
actual desde el nodo de partida.
Está pendiende de si ocurre un evento que termine antes la ejecución.
"""
def enviar_go(emisor, remitente, d):
    global terminar_early
    
    if terminar_early:
        return
    
    retraso = 1  # Asumimos peso 1 para todas las aristas
    msg_rondas[env.now].append(f"El proceso {emisor} envió GO({d}) al {remitente}")
    yield env.timeout(retraso)
    yield from recibir_go(remitente, emisor, d)

"""
Función que se encarga de manejar la recepción de los mensajes de Go.
Recibe los procesos que son parte de la comunicación y la distancia
actual desde el nodo de partida.
Está pendiende de si ocurre un evento que termine antes la ejecución.
"""
def recibir_go(remitente, emisor, d):
    global padre, hijos, nivel, msg_esperados, excentricidades, terminar_early
    
    if terminar_early:
        return
    
    if padre[remitente] is None:
        padre[remitente] = emisor
        msg_rondas[env.now].append(f"El proceso {remitente} recibió GO({d}) de {emisor}")
        
        hijos[remitente] = set()
        nivel[remitente] = d + 1
        msg_esperados[remitente] = len(grafica[remitente]) - 1
        
        # Actualizar excentricidad del nodo origen
        origen = emisor
        while padre[origen] != origen:
            origen = padre[origen]
        excentricidades[origen] = max(excentricidades.get(origen, 0), d + 1)
        
        # Terminar temprano si encontramos diámetro máximo posible
        if excentricidades[origen] == len(grafica) - 1:
            terminar_early = True
            diametro = excentricidades[origen]
            msg_rondas[env.now].append(f"¡Diámetro máximo encontrado! {diametro}")
            return
        
        if msg_esperados[remitente] == 0:
            yield env.process(enviar_back(remitente, padre[remitente], nivel[remitente], "yes"))
        else:
            for vecino in grafica[remitente]:
                if vecino != emisor:
                    env.process(enviar_go(remitente, vecino, d + 1))
    elif nivel[remitente] > d + 1:
        padre[remitente] = emisor
        nivel[remitente] = d + 1
        msg_esperados[remitente] = len(grafica[remitente]) - 1
        
        if msg_esperados[remitente] == 0:
            yield env.process(enviar_back(remitente, padre[remitente], nivel[remitente], "yes"))
        else:
            for vecino in grafica[remitente]:
                if vecino != emisor:
                    env.process(enviar_go(remitente, vecino, d + 1))
    else:
        yield env.process(enviar_back(remitente, emisor, d + 1, "no"))

"""
Función que se encarga de enviar mensajes de Back.
Recibe los procesos que son parte de la comunicación, la distancia 
actual desde el nodo de partida y la respuesta de confirmación.
"""
def enviar_back(emisor, remitente, d, resp):
    retraso = 1
    yield env.timeout(retraso)
    msg_rondas[env.now].append(f"El proceso {emisor} envió BACK({resp}, {d}) a {remitente}")
    yield from recibir_back(remitente, emisor, d, resp)

"""
Función que se encarga de manejar la recepción de los mensajes de Back.
Recibe los procesos que son parte de la comunicación, la distancia 
actual desde el nodo de partida y la respuesta de confirmación.
"""
def recibir_back(remitente, emisor, d, resp):
    global padre, hijos, nivel, msg_esperados, excentricidades
    
    if d == nivel[remitente] + 1:
        if resp == "yes":
            hijos[remitente].add(emisor)
        
        msg_esperados[remitente] -= 1
        
        if msg_esperados[remitente] == 0:
            if padre[remitente] != remitente:
                yield env.process(enviar_back(remitente, padre[remitente], nivel[remitente], "yes"))
            else:
                msg_rondas[env.now].append(f"La raíz {remitente} completó su BFS. Excentricidad: {excentricidades.get(remitente, 0)}")

"""
Función de arranque para el recorrido.
Recibe el que será el nodo distinguido.
"""
def start(nodo_distinguido):
    global padre, hijos, nivel, msg_esperados, excentricidades
    
    padre = {n: None for n in grafica}
    hijos = {n: set() for n in grafica}
    nivel = {n: -1 for n in grafica}
    msg_esperados = {n: 0 for n in grafica}
    excentricidades = {}
    
    padre[nodo_distinguido] = nodo_distinguido
    nivel[nodo_distinguido] = 0
    msg_esperados[nodo_distinguido] = len(grafica[nodo_distinguido])
    excentricidades[nodo_distinguido] = 0

    for vecino in grafica[nodo_distinguido]:
        env.process(enviar_go(nodo_distinguido, vecino, 0))
    
    yield env.timeout(1)

"""
Función auxiliar para imprimir los mensajes de cada ronda.
"""
def print_msg_rondas():
    for num_ronda in sorted(msg_rondas.keys()):
        print(f"--- Ronda {num_ronda} ---")
        for mensaje in msg_rondas[num_ronda]:
            print(mensaje)


if __name__ == "__main__":  
    
    continuar = True
    while continuar:
        try:
            # Construir la gráfica
            n = int(input("Ingrese el número de vértices (mayor que 1): "))            
            if n < 1:
                print("El número de vértices debe de ser mayor que cero")
            else:
                grafica = construir_grafica(n)
                mostrar_grafica(grafica)
            
                # Inicializar variables necesarias
                procesos = list(range(n))
                
                # Ejecutar BFS desde cada nodo para encontrar el diámetro
                diametro = 0
                
                for nodo_inicial in procesos:
                    print(f"\nIniciando BFS desde el nodo {nodo_inicial}...")
                    
                    # Reiniciar entorno de simulación
                    env = simpy.Environment()
                    msg_rondas = defaultdict(list)
                    terminar_early = False
                    
                    env.process(start(nodo_inicial))
                    env.run(until=100) #Variar si es necesario
                    
                    #print_msg_rondas()  # Descomentar para ver mensajes de envío y recepción
                    
                    excentricidad = excentricidades.get(nodo_inicial, 0)
                    print(f"Excentricidad del nodo {nodo_inicial}: {excentricidad}")
                    
                    diametro = max(diametro, excentricidad)
                    
                    # Terminar temprano si encontramos el diámetro máximo posible (longitud)
                    # del camino simple inicial
                    if diametro == n - 1:
                        break
                
                print(f"\nEl diámetro de la gráfica es: {diametro}")
                continuar = False
        
        except ValueError:
            print("Entrada no válida, el número debe de ser un entero mayor que cero.")
        
    """
    n = 6
    grafica = {
        0: [1, 4],
        1: [0, 2],
        2: [1, 3],
        3: [2, 4],
        4: [3, 5],
        5: [4, 0]
    }    
    mostrar_grafica(grafica)

    # Inicializar variables necesarias
    procesos = list(range(n))
    
    # Ejecutar BFS desde cada nodo para encontrar el diámetro
    diametro = 0
    
    for nodo_inicial in procesos:
        print(f"\nIniciando BFS desde el nodo {nodo_inicial}...")
        
        # Reiniciar entorno de simulación
        env = simpy.Environment()
        msg_rondas = defaultdict(list)
        terminar_early = False
        
        env.process(start(nodo_inicial))
        env.run(until=100) #Variar si es necesario
        
        #print_msg_rondas()  # Descomentar para ver mensajes de envío y recepción
        
        excentricidad = excentricidades.get(nodo_inicial, 0)
        print(f"Excentricidad del nodo {nodo_inicial}: {excentricidad}")
        
        diametro = max(diametro, excentricidad)
        
        # Terminar temprano si encontramos el diámetro máximo posible (longitud)
        # del camino simple inicial
        if diametro == n - 1:
            break
    
    print(f"\nEl diámetro de la gráfica es: {diametro}")
    """
    

