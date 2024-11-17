from setuptools import setup

# Leer la versión desde el archivo version.py
with open("meteocat/version.py") as f:
    exec(f.read())  # Ejecuta el archivo version.py para cargar la variable __version__

setup(
    name="meteocat",
    version=__version__,  # Usa la versión cargada dinámicamente # type: ignore
)
