import subprocess
import os

def generate_file_tree():
    # Ruta donde se generará el archivo
    output_file = 'filetree.txt'

    # Ejecutar el comando git ls-files para obtener los archivos no ignorados
    git_command = ['git', 'ls-files']
    try:
        # Captura de la salida del comando git
        git_files = subprocess.check_output(git_command).decode('utf-8').splitlines()

        # Crear una estructura de árbol
        tree = {}

        # Construir el árbol de directorios
        for file in git_files:
            parts = file.split('/')  # Separar la ruta del archivo por '/'
            current = tree
            for part in parts[:-1]:  # Recorremos todos los directorios
                current = current.setdefault(part, {})
            current[parts[-1]] = None  # El archivo final se marca como 'None'
        
        # Función recursiva para imprimir el árbol con la indentación correcta
        def print_tree(directory, indent=""):
            for name, subdirectory in directory.items():
                if subdirectory is None:
                    # Si es un archivo, lo imprimimos
                    f.write(f"{indent}├── {name}\n")
                else:
                    # Si es un directorio, lo imprimimos y recursivamente llamamos a print_tree
                    f.write(f"{indent}└── {name}/\n")
                    print_tree(subdirectory, indent + "    ")

        # Crear el archivo y escribir la estructura del árbol con codificación UTF-8
        with open(output_file, 'w', encoding='utf-8') as f:
            print_tree(tree)

        print(f"Árbol de directorios generado en: {os.path.abspath(output_file)}")

    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar el comando: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    generate_file_tree()
