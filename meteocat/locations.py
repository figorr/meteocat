import requests
import os
import json
from dotenv import load_dotenv
from meteocat import _LOGGER

# Cargar variables desde el archivo .env si existe
load_dotenv()

# Leer la clave API desde la variable de entorno
API_KEY = os.getenv("METEOCAT_API_KEY")

if not API_KEY:
    _LOGGER.error("La clave API no está configurada. Asegúrate de definir METEOCAT_API_KEY.")
    raise ValueError("La clave API no está configurada.")

# URL base para el API
BASE_URL = 'https://api.meteo.cat'

def get_meteocat_data(path):
    """
    Función genérica para consultar datos del API de Meteocat.
    
    Args:
        path (str): El endpoint específico a consultar, por ejemplo '/referencia/v1/municipis'.
    
    Returns:
        tuple: Código de estado y contenido de la respuesta o mensaje de error detallado.
    """
    url = f"{BASE_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": API_KEY
    }

    _LOGGER.debug(f"Realizando solicitud a {url}")
    
    try:
        response = requests.get(url, headers=headers)
        _LOGGER.info(f"Solicitud al endpoint {path} completada con código {response.status_code}")
        
        if response.status_code == 200:
            return response.status_code, response.json()  # Devuelve el contenido como un diccionario
        
        elif response.status_code == 400:
            _LOGGER.warning("Solicitud con errores (400)")
            return response.status_code, f"Bad Request: {response.json().get('message', 'Causa desconocida')}"

        elif response.status_code == 403:
            message = response.json().get("message", "Causa desconocida")
            if message == "Forbidden":
                _LOGGER.error("Error 403: No tienes permiso para realizar esta petición.")
                return response.status_code, "Error 403: No tienes permiso para realizar esta petición."
            elif message == "Missing Authentication Token":
                _LOGGER.error("Error 403: El recurso no existe.")
                return response.status_code, "Error 403: El recurso no existe."
            else:
                _LOGGER.error(f"Error 403: {message}")
                return response.status_code, f"Error 403: {message}"
        
        elif response.status_code == 429:
            _LOGGER.warning("Límite de solicitudes alcanzado (429)")
            return response.status_code, "Error 429: Límite de solicitudes superado. Intenta nuevamente más tarde."
        
        elif response.status_code == 500:
            _LOGGER.error("Error interno del servidor (500)")
            return response.status_code, f"Error 500: Error interno del servidor. Causa: {response.json().get('message', 'Causa desconocida')}"

        else:
            _LOGGER.error(f"Error inesperado: {response.status_code}")
            return response.status_code, f"Error inesperado: {response.status_code}. Respuesta: {response.text}"
    
    except requests.exceptions.RequestException as e:
        _LOGGER.critical(f"Error en la conexión: {e}")
        return None, f"Error en la conexión: {e}"

if __name__ == "__main__":
    # Ejemplo 1: Lista de municipios
    path_municipis = '/referencia/v1/municipis'
    status_code, message = get_meteocat_data(path_municipis)
    print("=== Consulta de Municipios ===")
    print(f"Status Code: {status_code}")
    print(f"Message: {message}")
    
    # Guardar la respuesta en un archivo .json si la respuesta fue exitosa
    if status_code == 200:
        with open('municipis_result.json', 'w', encoding='utf-8') as f:
            json.dump(message, f, ensure_ascii=False, indent=4)
        print(f"Archivo guardado: municipis_result.json")
