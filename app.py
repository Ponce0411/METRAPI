from flask import Flask, render_template, jsonify, request
from websocket import create_connection
import requests
import json
import threading
import time

app = Flask(__name__)

# Define la URL del servidor WebSocket
websocket_url = "wss://tarea-2.2024-1.tallerdeintegracion.cl/connect"

# Variable para almacenar la conexión WebSocket
ws = None

# Variable para controlar si la sesión está desconectada
Desconectado = True

# Diccionario para almacenar la última posición conocida de cada tren
train_positions = {}
trains_status = {}
trains_arrival = {}
messages = {}
messages_users = {}

# Función para correr el listener del WebSocket
def run_websocket_listener():
    global ws
    global Desconectado
    while True:
        try:
            if Desconectado:
                ws = create_connection(websocket_url)
                join_event = {
                    "type": "JOIN",
                    "payload": {
                        "id": "19641990",
                        "username": "Martín Ponce"
                    }
                }
                ws.send(json.dumps(join_event))
                Desconectado = False

            # Manejar eventos recibidos
            connect_and_handle_events()
            
        except Exception as e:
            print("Error al conectarse:", e)
            Desconectado = True
            if ws:
                ws.close()
            # Esperar un tiempo antes de intentar reconectar
            time.sleep(5)

# Función para conectar al WebSocket y recibir eventos
def connect_and_handle_events():
    global ws
    try:
        while True:
            event = ws.recv()
            if event:  
                handle_event(json.loads(event))

    except Exception as e:
            print("Error al recibir el evento:", e)
            time.sleep(5)
            run_websocket_listener()

# Manejar eventos WebSocket
def handle_event(event):
    global train_positions
    if event['type'] == 'position':
        position_data = event['data']
        train_id = position_data['train_id']
        line_id = position_data['line_id']
        lat = position_data['position']['lat']
        long = position_data['position']['long']
        train_positions[train_id] = {'train_id': train_id, 'line_id': line_id, 'lat': lat, 'long': long}

    elif event['type'] == 'status':
        global trains_status
        status_data = event['data']
        train_id = status_data['train_id']
        status = status_data['status']
        trains_status[train_id] = {'train_id': train_id,'status': status}

    elif event['type'] == 'arrival':
        global trains_arrival
        status_data = event['data']
        train_id = status_data['train_id']
        line_id = status_data['line_id']
        station_id = status_data['station_id']
        trains_arrival[train_id] = {'train_id': train_id,'line_id': line_id, 'station_id': station_id}

    elif event['type'] == 'message':
        global messages
        status_data = event['data']
        train_id = status_data['train_id']
        name = status_data['name']
        time = event['timestamp']
        content = status_data['content']
        messages[train_id] = {'train_id': train_id,'name': name, 'time': time, 'content': content}            

    else:
        print("Evento no manejado:", event)

# Obtener información sobre estaciones, líneas y trenes
def obtener_estaciones():
    url = "https://tarea-2.2024-1.tallerdeintegracion.cl/api/metro/stations"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print("Error al obtener información sobre las estaciones del metro. Código de estado:", response.status_code)
            return []
    except Exception as e:
        print("Error al realizar la solicitud:", e)
        return []

def obtener_lineas():
    url = "https://tarea-2.2024-1.tallerdeintegracion.cl/api/metro/lines"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print("Error al obtener información sobre las líneas del metro. Código de estado:", response.status_code)
            return []
    except Exception as e:
        print("Error al realizar la solicitud:", e)
        return []

def obtener_trenes():
    url = "https://tarea-2.2024-1.tallerdeintegracion.cl/api/metro/trains"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print("Error al obtener información sobre los trenes del metro. Código de estado:", response.status_code)
            return []
    except Exception as e:
        print("Error al realizar la solicitud:", e)
        return []

@app.route('/train_positions')
def get_train_positions():
    global train_positions
    return jsonify(list(train_positions.values()))

@app.route('/train_status')
def get_train_status():
    global trains_status
    return jsonify(list(trains_status.values()))

@app.route('/train_arrival')
def get_train_arrival():
    global trains_arrival
    return jsonify(list(trains_arrival.values()))

@app.route('/messages')
def get_messages():
    global messages
    return jsonify(list(messages.values()))

@app.route('/send_message', methods=['POST'])
def send_message():
    global messages
    # Obtener el contenido del mensaje del cuerpo de la solicitud POST
    train_id = "User"
    name = request.json.get('name')
    time = request.json.get('time')
    content = request.json.get('content')

    messages[name] = {'train_id': train_id,'name': name, 'time': time, 'content': content} 

    if content:
        # Crear el evento MESSAGE con el contenido del mensaje
        message_event = {
            "type": "MESSAGE",
            "payload": {
                "content": content
            }
        }
        # Enviar el evento al WebSocket para propagar el mensaje a todos los usuarios conectados
        ws.send(json.dumps(message_event))
        return jsonify({'message': 'Mensaje enviado correctamente'}), 200
    else:
        return jsonify({'error': 'Contenido del mensaje no válido'}), 400

@app.route('/')
def index():
    # Conectar al WebSocket y manejar eventos en un hilo separado
    websocket_thread = threading.Thread(target=run_websocket_listener)
    websocket_thread.daemon = True
    websocket_thread.start()

    # Obtener información sobre estaciones, líneas y trenes
    estaciones = obtener_estaciones()
    lineas = obtener_lineas()
    trenes = obtener_trenes()

    stations = []
    trains = []

    for estacion in estaciones:
        station = []
        station.append(estacion['name'])
        station.append(estacion['station_id'])
        station.append(estacion['line_id'])
        stations.append(station)

    for tren in trenes:
        train = []
        train.append(tren['train_id'])
        train.append(tren['driver_name'])
        train.append(tren['origin_station_id'])
        train.append(tren['destination_station_id'])
        trains.append(train)    

    # Almacenar las estaciones por línea
    estaciones_por_linea = {}
    for linea in lineas:
        estaciones_linea = []
        for estacion in estaciones:
            if estacion['station_id'] in linea['station_ids'] and estacion['line_id'] == linea['line_id']:
                estaciones_linea.append(estacion)
        estaciones_por_linea[linea['line_id']] = {'color': linea['color'], 'stations': estaciones_linea}

    # Convertir a JSON
    estaciones_por_linea_json = json.dumps(estaciones_por_linea)

    # Crear lista de estaciones con información para marcadores
    estaciones_marcadores = []
    for estacion in estaciones:
        lineas_estacion = [linea['line_id'] for linea in lineas if estacion['station_id'] in linea['station_ids']]
        estacion_info = {
            'name': estacion['name'],
            'station_id': estacion['station_id'],
            'position': estacion['position'],
            'lines': lineas_estacion
        }
        estaciones_marcadores.append(estacion_info)
    
    # Convertir a JSON
    estaciones_marcadores_json = json.dumps(estaciones_marcadores)

    # Convertir información de trenes a JSON
    trenes_json = json.dumps(trenes)

    return render_template('index.html', estaciones_marcadores=estaciones_marcadores_json, estaciones_por_linea=estaciones_por_linea_json, trenes=trenes_json, estaciones=stations, trains=trains)

if __name__ == '__main__':
    app.run(debug=True)