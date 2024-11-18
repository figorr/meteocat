import json
import os

def buscar_y_guardar_municipio(nombre_municipio, archivo_json, archivo_resultado):
    """
    Busca el código asociado a un municipio y guarda el resultado en un archivo JSON.

    Args:
        nombre_municipio (str): Nombre del municipio a buscar (insensible a mayúsculas).
        archivo_json (str): Ruta del archivo JSON donde buscar.
        archivo_resultado (str): Ruta del archivo JSON donde guardar el resultado.

    Returns:
        str: Mensaje con el resultado de la operación.
    """
    # Comprobar si el archivo existe
    if not os.path.exists(archivo_json):
        return f"Error: El archivo {archivo_json} no existe."
    
    try:
        # Cargar el archivo JSON
        with open(archivo_json, 'r', encoding='utf-8') as f:
            datos = json.load(f)

        # Inicializar variables para el resultado
        codi = None
        nom = None
        
        # Buscar el municipio ignorando mayúsculas/minúsculas
        for municipio in datos:
            if municipio['nom'].lower() == nombre_municipio.lower():
                codi = municipio['codi']
                nom = municipio['nom']
                break

        # Si no se encuentra, establecer nom y codi a null
        if codi is None:
            nom = "null"
            codi = "null"

        # Crear el diccionario del resultado
        resultado = {
            "nom": nom,
            "codi": codi
        }

        # Guardar el resultado en el archivo JSON
        with open(archivo_resultado, 'w', encoding='utf-8') as f:
            json.dump(resultado, f, ensure_ascii=False, indent=4)

        # Mensaje de éxito o no encontrado
        if codi != "null":
            return f"El municipio '{nombre_municipio}' fue encontrado y guardado con código: {codi}"
        else:
            return f"Municipio '{nombre_municipio}' no encontrado. Guardado con nom: null y codi: null"

    except json.JSONDecodeError:
        return f"Error: El archivo {archivo_json} no es un archivo JSON válido."


def obtener_ruta_repositorio():
    """
    Obtiene la ruta base del repositorio asumiendo que este script se ejecuta desde el repositorio.
    
    Returns:
        str: Ruta base del repositorio.
    """
    # Obtener la ruta absoluta del directorio donde está este script
    ruta_script = os.path.abspath(__file__)
    # Asumimos que el repositorio es el directorio raíz del script
    ruta_repositorio = os.path.dirname(ruta_script)
    return ruta_repositorio


if __name__ == "__main__":
    # Obtener la ruta del repositorio
    ruta_repositorio = obtener_ruta_repositorio()

    # Ruta de la carpeta /meteocat/files/
    carpeta_files = os.path.join(ruta_repositorio, "meteocat", "files")

    # Crear la carpeta si no existe
    if not os.path.exists(carpeta_files):
        os.makedirs(carpeta_files)

    # Nombre del municipio a buscar
    nombre = input("Introduce el nombre del municipio: ")

    # Ruta del archivo JSON generado previamente
    archivo_origen = os.path.join(carpeta_files, "municipis_list.json")

    # Ruta del archivo JSON para guardar el resultado
    archivo_destino = os.path.join(carpeta_files, "municipi.json")

    # Buscar y guardar el municipio
    resultado = buscar_y_guardar_municipio(nombre, archivo_origen, archivo_destino)
    print(resultado)
