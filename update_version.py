import re
import sys
import os

def update_version(file_path, new_version):
    # Leer el contenido del archivo
    with open(file_path, "r") as file:
        content = file.read()

    # Patrón para encontrar la línea de la versión en pyproject.toml
    version_pattern = r'(version = ")([0-9]+\.[0-9]+\.[0-9]+)(")'

    # Sustituir la versión en el archivo
    updated_content = re.sub(version_pattern, r'\g<1>' + new_version + r'\3', content)

    # Escribir el contenido actualizado de nuevo en el archivo
    with open(file_path, "w") as file:
        file.write(updated_content)

def update_init_version(file_path, new_version):
    # Verifica si el archivo existe
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"El archivo {file_path} no se encontró en la ruta especificada.")

    # Leer el contenido del archivo __init__.py
    with open(file_path, "r") as file:
        content = file.read()

    # Patrón para encontrar la línea de la versión en __init__.py
    init_version_pattern = r'__version__ = "([0-9]+\.[0-9]+\.[0-9]+)"'

    # Sustituir la versión en el archivo
    updated_content = re.sub(init_version_pattern, r'__version__ = "' + new_version + '"', content)

    # Escribir el contenido actualizado de nuevo en el archivo
    with open(file_path, "w") as file:
        file.write(updated_content)

if __name__ == "__main__":
    # Archivos a modificar y la nueva versión a asignar
    pyproject_path = "pyproject.toml"
    init_path = "meteocat/__init__.py"  # Ruta correcta para __init__.py
    new_version = sys.argv[1]  # Obtener la nueva versión desde los argumentos

    # Actualizar la versión en pyproject.toml
    update_version(pyproject_path, new_version)

    # Actualizar la versión en __init__.py
    update_init_version(init_path, new_version)
