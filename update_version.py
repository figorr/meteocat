import re
import sys

def update_version(file_path, new_version):
    with open(file_path, "r") as file:
        content = file.read()

    content = re.sub(r'version = "[0-9]+\.[0-9]+\.[0-9]+"', f'version = "{new_version}"', content)

    with open(file_path, "w") as file:
        file.write(content)

if __name__ == "__main__":
    file_path = "pyproject.toml"  # Cambia la ruta si es necesario
    new_version = sys.argv[1]  # La nueva versión se pasa como argumento
    update_version(file_path, new_version)
