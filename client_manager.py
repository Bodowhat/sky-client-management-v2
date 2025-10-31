import json
import boto3
from datetime import datetime
import os
import uuid
from dotenv import load_dotenv

load_dotenv() # Carga las variables del archivo .env

# --- Configuración AWS ---
# Estas variables vienen de .env
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
DYNAMODB_INDEX_TABLE = os.environ.get("DYNAMODB_INDEX_TABLE_NAME")
AWS_REGION = os.environ.get("AWS_REGION")

# Configura las credenciales de AWS desde las variables de entorno
s3_client = boto3.client(
    's3', 
    region_name=AWS_REGION,
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
)
dynamodb = boto3.resource(
    'dynamodb', 
    region_name=AWS_REGION,
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
)
index_table = dynamodb.Table(DYNAMODB_INDEX_TABLE)

# ----------------- Funcionalidad DDD (Entidades y Objetos de Valor) -----------------

class Cliente:
    def __init__(self, name, client_type, contact=None):
        self.ID_Cliente = str(uuid.uuid4()) # ID único
        self.NombreCompleto = name
        self.TipoCliente = client_type
        self.FechaRegistro = datetime.now().isoformat()
        self.ServiciosContratados = [] 
        self.InformacionContacto = contact or {}

    def agregar_servicio(self, service_type, plan):
        # Objeto de Valor DetalleServicioContratado
        nuevo_servicio = {
            "TipoServicioSolicitado": service_type,
            "PlanEspecifico": plan,
            "FechaContratacion": datetime.now().isoformat(),
            "EstadoServicio": "Activo"
        }
        self.ServiciosContratados.append(nuevo_servicio)

    def to_dict(self):
        return self.__dict__

# ----------------- Operaciones del Microservicio (Persistencia) -----------------

def create_new_client(client_data, service_data):
    """Crea nuevo cliente, guarda en S3 y lo indexa en DynamoDB."""

    try:
        # 1. Lógica DDD: Crear objeto Cliente
        cliente = Cliente(client_data['nombre'], client_data['tipo'], client_data.get('contacto'))
        cliente.agregar_servicio(service_data['tipo'], service_data['plan'])

        client_id = cliente.ID_Cliente
        client_key = f"clientes/{client_id}.json"
        client_data_json = json.dumps(cliente.to_dict(), indent=4)

        # 2. Guardar en S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=client_key,
            Body=client_data_json
        )

        # 3. Indexar en DynamoDB
        index_table.put_item(
           Item={
               'NombreCompleto': client_data['nombre'].lower(),
               'ID_Cliente': client_id,
               'S3_Key': client_key
           }
        )
        return client_id, client_key
    except Exception as e:
        print(f"Error al crear cliente: {e}")
        return None, str(e)

def get_client_info(search_value):
    """Busca cliente por nombre o ID."""

    try:
        # 1. Buscar en DynamoDB por Nombre Completo (índice primario)
        response = index_table.get_item(Key={'NombreCompleto': search_value.lower()})

        if 'Item' in response:
            s3_key = response['Item']['S3_Key']
        else:
            return {"error": "Cliente no encontrado en el índice. Intente con el nombre completo."}

        # 2. Leer archivo completo desde S3
        s3_object = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        client_data = json.loads(s3_object['Body'].read())
        return client_data

    except Exception as e:
        return {"error": str(e)}

def update_client_data(client_id, update_payload):
    """Modifica datos de contacto o agrega un servicio."""

    try:
        s3_key = f"clientes/{client_id}.json"

        # 1. Descargar datos de S3
        s3_object = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        client_data = json.loads(s3_object['Body'].read())

        # 2. Aplicar lógica de modificación (DDD)
        if 'nuevo_servicio' in update_payload:
            # Crea un objeto temporal para usar la lógica de agregar_servicio
            cliente_temp = Cliente(None, None) 
            cliente_temp.ServiciosContratados = client_data['ServiciosContratados']
            cliente_temp.agregar_servicio(
                update_payload['nuevo_servicio']['tipo'],
                update_payload['nuevo_servicio']['plan']
            )
            client_data['ServiciosContratados'] = cliente_temp.ServiciosContratados

        if 'contacto' in update_payload:
            # Actualiza o reemplaza el Objeto de Valor contacto
            client_data['InformacionContacto'].update(update_payload['contacto'])

        # 3. Sobrescribir en S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(client_data, indent=4)
        )
        return {"status": "success", "message": f"Cliente {client_id} actualizado."}
    except s3_client.exceptions.NoSuchKey:
        return {"status": "error", "message": f"Archivo de cliente {client_id} no encontrado en S3."}
    except Exception as e:
        return {"status": "error", "message": str(e)}