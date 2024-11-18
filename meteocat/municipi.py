import json
import os


def buscar_y_guardar_municipio(nombre_municipio, archivo_json, archivo_resultado):
    """
    Busca el código asociado a un municipio y guarda el resultado en un archivo JSON con un mensaje adicional.

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

    # Comprobar si el archivo está vacío
    if os.stat(archivo_json).st_size == 0:
        return f"Error: El archivo {archivo_json} está vacío."

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

        # Si no se encuentra, establecer nom y codi a "null"
        if codi is None:
            nom = "null"
            codi = "null"
            missatge = "El municipio no se encontró en la base de datos."
        else:
            missatge = f"El municipio {nom} se encontró en la base de datos con código {codi}."

        # Crear el diccionario del resultado
        resultado = {
            "nom": nom,
            "codi": codi,
            "missatge": missatge
        }

        # Guardar el resultado en el archivo JSON
        with open(archivo_resultado, 'w', encoding='utf-8') as f:
            json.dump(resultado, f, ensure_ascii=False, indent=4)

        return missatge

    except json.JSONDecodeError as e:
        return f"Error: El archivo {archivo_json} no es un archivo JSON válido. Detalles: {e}"


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
    os.makedirs(carpeta_files, exist_ok=True)

    # Nombre del municipio a buscar
    nombre = input("Introduce el nombre del municipio: ").strip()

    # Validar entrada del usuario
    if not nombre:
        print("Error: El nombre del municipio no puede estar vacío.")
        exit(1)

    # Ruta del archivo JSON generado previamente
    archivo_origen = os.path.join(carpeta_files, "municipis_list.json")

    # Ruta del archivo JSON para guardar el resultado
    archivo_destino = os.path.join(carpeta_files, "municipi.json")

    # Buscar y guardar el municipio
    resultado = buscar_y_guardar_municipio(nombre, archivo_origen, archivo_destino)
    
    # Imprimir en pantalla el mismo mensaje que el de "missatge"
    print(resultado)
