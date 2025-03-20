"""
Práctica 2 - Algoritmo BFS

Computación Distribuida 2025-2

Profesores:

- Mauricio Riva Palacio Orozco

- Adrián Felipe Fernández Romero

- Daniel Michel Tavera

Alumno:

- Javier Alejandro Rivera Zavala
"""
import simpy
from collections import defaultdict

# Construimos la gráfica 
procesos = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6']
adjacencias = {    
    'p1': ['p3', 'p2'],
    'p2': ['p1', 'p3'],
    'p3': ['p1', 'p2', 'p4', 'p5'],
    'p4': ['p3', 'p5', 'p6'],
    'p5': ['p3', 'p4'],
    'p6': ['p4']
}

# Asignamos los pesos de las aristas (cuántas rondas debe esperar cada mensaje)
pesos = {
    ('p1', 'p3'): 1, ('p3', 'p1'): 1,
    ('p1', 'p2'): 2, ('p2', 'p1'): 2,
    ('p2', 'p3'): 3, ('p3', 'p2'): 3,
    ('p3', 'p4'): 3, ('p4', 'p3'): 3,
    ('p3', 'p5'): 1, ('p5', 'p3'): 1,
    ('p4', 'p5'): 1, ('p5', 'p4'): 1,
    ('p4', 'p6'): 1, ('p6', 'p4'): 1
}

# Variables de estado
padre = {p: None for p in procesos}
hijos = {p: set() for p in procesos}
nivel = {p: -1 for p in procesos}
msg_esperados = {p: 0 for p in procesos}

# Elementos necesarios para la simulación
env = simpy.Environment()
msg_rondas = defaultdict(list)

"""
Función que se encarga de enviar mensajes de Go.
Recibe los procesos que son parte de la comunicación y la distancia
actual desde la raíz
"""
def enviar_go(emisor, remitente, d):
    retraso = pesos.get((emisor, remitente), 1)  # Obtener el peso de la arista o usar 1 por defecto
    msg_rondas[env.now].append(f"El proceso {emisor} envió GO({d}) al {remitente} con espera de {retraso} rondas")
    yield env.timeout(retraso)  # Esperar según el peso de la arista
    yield from recibir_go(remitente, emisor, d)

"""
Función que se encarga de manejar la recepción de los mensajes de Go.
Recibe los procesos que son parte de la comunicación y la distancia
actual desde la raíz.
"""
def recibir_go(remitente, emisor, d):
    global padre, hijos, nivel, msg_esperados
    
    if padre[remitente] is None:
        padre[remitente] = emisor
        msg_rondas[env.now].append(f"El proceso {remitente} recibió GO({d}) de {emisor}\nEl proceso {remitente} tiene por padre: {emisor}, ronda: {env.now}")
        
        hijos[remitente] = set()
        nivel[remitente] = d + 1
        msg_esperados[remitente] = len(adjacencias[remitente]) - 1
        
        if msg_esperados[remitente] == 0:
            yield env.process(enviar_back(remitente, padre[remitente], nivel[remitente], "yes")) #Enviar Back a los vecinos
        else:
            for vecino in adjacencias[remitente]:
                if vecino != emisor:
                    env.process(enviar_go(remitente, vecino, d + 1)) #Enviar Go a los vecinos
    elif nivel[remitente] > d + 1:
        padre[remitente] = emisor
        msg_rondas[env.now].append(f"El proceso {remitente} cambió su padre a: {emisor}")

        hijos[remitente] = set()
        nivel[remitente] = d + 1
        msg_esperados[remitente] = len(adjacencias[remitente]) - 1
        
        if msg_esperados[remitente] == 0:
            yield env.process(enviar_back(remitente, padre[remitente], nivel[remitente], "yes"))
        else:
            for vecino in adjacencias[remitente]:
                if vecino != emisor:
                    env.process(enviar_go(remitente, vecino, d + 1))
    else:
        yield env.process(enviar_back(remitente, emisor, d + 1, "no"))

"""
Función que se encarga de enviar mensajes de Back.
Recibe los procesos que son parte de la comunicación, la distancia 
actual desde la raíz y la respuesta de confirmación.
"""
def enviar_back(emisor, remitente, d, resp):
    retraso = pesos.get((emisor, remitente), 1)  # Obtener el peso de la arista o usar 1 por defecto
    yield env.timeout(retraso)  # Esperar según el peso de la arista
    msg_rondas[env.now].append(f"El proceso {emisor} envió BACK({resp}, {d}) a {remitente} con espera de {retraso} rondas")
    yield from recibir_back(remitente, emisor, d, resp)

"""
Función que se encarga de manejar la recepción de los mensajes de Back.
Recibe los procesos que son parte de la comunicación, la distancia 
actual desde la raíz y la respuesta de confirmación.
"""
def recibir_back(remitente, emisor, d, resp):
    global padre, hijos, nivel, msg_esperados
    
    if d == nivel[remitente] + 1:
        if resp == "yes":
            hijos[remitente].add(emisor)
        
        msg_esperados[remitente] -= 1
        
        if msg_esperados[remitente] == 0:
            if padre[remitente] != remitente:
                yield env.process(enviar_back(remitente, padre[remitente], nivel[remitente], "yes"))
            else:
                msg_rondas[env.now].append(f"La raíz {remitente} ya sabe que se recorrió la gráfica")
"""
Función de arranque para el recorrido.
Recibe el que será el nodo distinguido.
"""
def start(nodo_distinguido):
    global padre, hijos, nivel, msg_esperados
    padre[nodo_distinguido] = nodo_distinguido
    nivel[nodo_distinguido] = 0
    msg_esperados[nodo_distinguido] = len(adjacencias[nodo_distinguido])

    for vecino in adjacencias[nodo_distinguido]:
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
    print("Procesos disponibles:", procesos)   
        
    while True:
        try:
            nodo_distinguido_index = int(input("Ingrese el índice del nodo inicial (1 a {}): ".format(len(procesos))))
            if 1 <= nodo_distinguido_index <= len(procesos):
                break
            else:
                print("Índice de nodo no válido. Intente nuevamente.")
        except ValueError:
            print("Entrada no válida. Ingrese un número entero.")

    nodo_distinguido = procesos[nodo_distinguido_index - 1]
    print(f"Iniciando algoritmo desde el nodo {nodo_distinguido}")
    
    env.process(start(nodo_distinguido))    
    env.run(until=50)  
    
    print_msg_rondas()