import os
import requests

# Configuración básica
GL_TOKEN = os.getenv("GL_TOKEN")  # Token de GitLab
PROJECT_ID = os.getenv("GL_PROJECT_ID")  # ID del proyecto en GitLab
VERSION_FILE = "release_version.txt"  # Archivo con la próxima versión
DESCRIPTION = "Release generado automáticamente desde el pipeline de GitLab."

def read_next_version(file_path):
    """
    Lee la próxima versión desde el archivo generado por `semantic-release`.
    """
    try:
        with open(file_path, "r") as f:
            for line in f:
                if "The next version is:" in line:
                    return line.split(":")[-1].strip()
    except FileNotFoundError:
        raise ValueError(f"No se encontró el archivo {file_path}. Asegúrate de que 'version_job' lo genere.")
    return None

def create_gitlab_release(tag_name, release_name, description):
    """
    Crea un release en GitLab con el tag especificado.
    """
    url = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}/releases"
    headers = {"PRIVATE-TOKEN": GL_TOKEN}
    data = {
        "name": release_name,
        "tag_name": tag_name,
        "description": description,
    }

    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        print(f"Release creado exitosamente: {tag_name}")
    else:
        print(f"Error al crear el release: {response.status_code} - {response.text}")
        response.raise_for_status()

if __name__ == "__main__":
    if not GL_TOKEN or not PROJECT_ID:
        raise ValueError("GL_TOKEN y PROJECT_ID deben estar configurados en las variables de entorno.")

    # Leer la próxima versión desde el archivo
    next_version = read_next_version(VERSION_FILE)
    if not next_version:
        raise ValueError("No se pudo determinar la próxima versión.")

    # Crear el release en GitLab
    tag_name = f"v{next_version}"
    release_name = f"Release {tag_name}"
    create_gitlab_release(tag_name, release_name, DESCRIPTION)
