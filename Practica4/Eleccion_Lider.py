"""
Práctica 4 - 

Elección de líder
             

Computación Distribuida 2025-2

Profesores:

- Mauricio Riva Palacio Orozco

- Adrián Felipe Fernández Romero

- Daniel Michel Tavera

Alumno:

- Javier Alejandro Rivera Zavala
"""
import simpy
import math

"""
Función que construye una gráfica ad hoc para esta práctica.
Recibe el número n de nodos en la gráfica, los conecta formando
un ciclo o anillo y les asigna id's únicos desde 0 hasta n-1.
"""
def construir_grafica(n):
    ids = list(range(0, n)) 
    grafica = {ids[i]: [] for i in range(n)} 

    for i in range(n):  
        grafica[ids[i]] = [(i-1) % n, (i+1) % n]  
    
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

"""
Función que asigna valores iniciales a diversos campos para los nodos 
del sistema, estos incluyen los vecinos inmediatos del nodo, un id propio 
y un mínimo id conocido, un estado para el algoritmo y estructuras para 
el envío y recepción de mensajes.
"""
def inicializar_nodos(grafica):
    nodos = {}
    for id_nodo in grafica:
        nodos[id_nodo] = {
            'id': id_nodo,
            'vecinos': grafica[id_nodo],
            'vecino_izq': grafica[id_nodo][0], 
            'min_id': math.inf,                 
            'estado': 'asleep',                 
            'R': [],                            
            'S': [],                           
            'waiting': []                       
        }
    return nodos

"""
Función para manejar la recepción de mensajes a través de una
estructura que almacena los recibidos, aquellos en espera y
aquellos por enviar.
"""
def procesar_mensajes_nodo(nodo, ronda):    
    estado_previo = nodo['estado']    

    # Si el nodo está dormido y no ha recibido mensajes, se activa y se postula a líder
    if not nodo['R'] and nodo['estado'] == 'asleep':
        nodo['estado'] = 'participating'
        nodo['min_id'] = nodo['id']
        nodo['S'].append((nodo['id'], 1)) 

    # Si el nodo recibe mensajes mientras está dormido, cambia a estado "relay"
    elif nodo['R'] and nodo['estado'] == 'asleep':
        nodo['estado'] = 'relay'
        nodo['min_id'] = math.inf 

    # Procesamiento de cada mensaje recibido
    for mensaje in nodo['R'][:]:
        m, h = mensaje
        if m < nodo['min_id']:
            nodo['estado'] = 'not_elected'
            nodo['min_id'] = m

            if nodo['estado'] == 'relay' and h == 1:
                nodo['S'].append((m, h))  
            else:
                # Espera para reenviar con delay controlado por h (tiempo ∝ 2^m)
                nodo['waiting'].append(((m, 2), ronda))
        elif m == nodo['id']:
            nodo['estado'] = 'elected'  # Si recibe su propio ID, pasará a ser el minímo y
                                        # entonces será el líder 
        nodo['R'].remove(mensaje)  

    # Verifica si algún mensaje en espera ya puede ser reenviado
    for item in nodo['waiting'][:]:
        (m, h), ronda_aparicion = item
        if ronda - 2**m - 1 == ronda_aparicion:
            nodo['S'].append((m, h))
            nodo['waiting'].remove(item)

    return estado_previo != nodo['estado']

"""
Función que gestiona el envío de mensajes de un nodo a su vecino
a través de una estructura que almacena los mensajes adecuados.
"""
def enviar_mensajes_nodo(nodos, nodo_id):    
    nodo = nodos[nodo_id]
    vecino_izq = nodo['vecino_izq']  # Solo envía hacia un lado
    for msg in nodo['S']:
        nodos[vecino_izq]['R'].append(msg)  # Agrega el mensaje al buzón del vecino
        print(f"Nodo {nodo_id} envía {msg} a {vecino_izq}")    
    nodo['S'] = []  

"""
Función que corre la simulación del algoritmo.
Se recibe el número de procesos que serán parte de la simulación
y cuyo número debe de ser al menos 3 para poder formar un anillo.
En primer instancia se despiertan los nodos y se alistan para
enviar y recibir mensajes, se procede a mantener la comunicación
según lo dicta el algoritmo y cuando finalmente todos los nodos tienen
estado not_elected, salvo uno solo con estado elected, entonces termina
la simulación.
"""
def simular_eleccion(env, grafica):
    nodos = inicializar_nodos(grafica)
    todos_cambiaron = False  

    while not todos_cambiaron:
        ronda = env.now
        cambios_en_ronda = False
        print(f"\n------------------Ronda {ronda}------------------\n")

        # Procesamiento de los mensajes recibidos por cada nodo
        for id_nodo in nodos:
            cambios = procesar_mensajes_nodo(nodos[id_nodo], ronda)
            if cambios:
                cambios_en_ronda = True
                print(f"Nodo {id_nodo} cambió a estado '{nodos[id_nodo]['estado']}'")  

        if not cambios_en_ronda and ronda == 1:
            print(f"Inicialización del anillo")
        elif not cambios_en_ronda:
            print(f"Nadie cambió de estado en esta ronda")

        # Envío de mensajes después del procesamiento
        for id_nodo in nodos:
            enviar_mensajes_nodo(nodos, id_nodo)   

        # Verifica si todos están en estado final
        if all(nodo['estado'] in ['elected', 'not_elected'] for nodo in nodos.values()):
            todos_cambiaron = True 
            print(f"\n¡Se ha elegido un líder!")                   
            print("\nEstados finales:")
            for id_nodo, nodo in nodos.items():
                print(f"Nodo {id_nodo}: {nodo['estado']}")  
                             
        yield env.timeout(1) 

"""
Menú en la terminal para correr la simulación.
"""
if __name__ == "__main__":
    continuar = True
    while continuar:
        try:
            n = int(input("Ingrese el número de vértices (mayor o igual que 3): "))            
            if n < 3:
                print("El número de vértices en un anillo debe de ser mayor que dos")
            else:
                grafica = construir_grafica(n)
                print("Esta es la gráfica construida: ")
                mostrar_grafica(grafica)
                continuar = False

                env = simpy.Environment()
                env.process(simular_eleccion(env, grafica))
                env.run(until=200)  
        except ValueError:
            print("Entrada no válida, el número debe de ser un entero mayor que dos.")
