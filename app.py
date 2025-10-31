from flask import Flask, request, jsonify
# Importa las funciones de nuestro Microservicio
from client_manager import create_new_client, get_client_info, update_client_data

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Microservicio MS-Gestión-Clientes de Sky V2.0. Utiliza /api/clientes para interactuar."

@app.route('/api/clientes', methods=['POST'])
def crear_cliente():
    """Crea un nuevo cliente y su archivo."""
    try:
        data = request.json
        client_id, error_message = create_new_client(data['cliente'], data['servicio'])

        if client_id:
            return jsonify({"message": "Cliente creado exitosamente.", "id": client_id}), 201
        else:
            return jsonify({"message": "Error al crear cliente.", "details": error_message}), 500
    except Exception as e:
         return jsonify({"message": "Solicitud POST inválida.", "error": str(e)}), 400

@app.route('/api/clientes/<search_value>', methods=['GET'])
def consultar_cliente(search_value):
    """Consulta de información de un cliente por ID o nombre."""
    info = get_client_info(search_value)

    if 'error' in info:
        return jsonify(info), 404
    return jsonify(info), 200

@app.route('/api/clientes/<client_id>', methods=['PUT'])
def modificar_cliente(client_id):
    """Modificar datos o agregar servicio a cliente existente."""
    try:
        data = request.json
        result = update_client_data(client_id, data)

        if result.get("status") == "success":
            return jsonify(result), 200
        else:
            return jsonify({"message": "Error al modificar cliente.", "details": result.get('message')}), 404
    except Exception as e:
        return jsonify({"message": "Solicitud PUT inválida.", "error": str(e)}), 400

if __name__ == '__main__':
    # Se usa el puerto 80 ya que es el puerto por defecto en muchas configuraciones de AWS
    app.run(host='0.0.0.0', port=80, debug=True)