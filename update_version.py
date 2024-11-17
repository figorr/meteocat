import re
import sys

def update_version(file_path, new_version, version_pattern):
    """
    Actualiza la versión en el archivo especificado basado en un patrón.

    :param file_path: Ruta al archivo que contiene la versión.
    :param new_version: Nueva versión que se va a aplicar.
    :param version_pattern: Patrón regex para encontrar la versión en el archivo.
    """
    with open(file_path, "r") as file:
        content = file.read()

    # Reemplaza la versión en el contenido del archivo
    updated_content = re.sub(version_pattern, f'\\1{new_version}\\2', content)

    with open(file_path, "w") as file:
        file.write(updated_content)

if __name__ == "__main__":
    # Recibe los argumentos: nueva versión
    new_version = sys.argv[1]

    # Actualiza la versión en pyproject.toml
    pyproject_path = "pyproject.toml"  # Cambia la ruta si es necesario
    pyproject_pattern = r'(version = ")([0-9]+\.[0-9]+\.[0-9]+)(")'
    update_version(pyproject_path, new_version, pyproject_pattern)

    # Actualiza la versión en __init__.py
    init_file_path = "meteocat/__init__.py"  # Cambia la ruta si es necesario
    init_file_pattern = r'(__version__ = ")([0-9]+\.[0-9]+\.[0-9]+)(")'
    update_version(init_file_path, new_version, init_file_pattern)
