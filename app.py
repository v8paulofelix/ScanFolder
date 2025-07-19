"""
ScanFolder - Aplicación Web para Catalogación de Discos
======================================================

Una aplicación Flask que permite escanear unidades de almacenamiento y mantener
un catálogo de directorios para búsquedas rápidas, incluso cuando los discos
no están conectados.

Arquitectura:
- Flask: Servidor web y API REST
- SQLite: Base de datos para catálogos y metadatos  
- Multiplataforma: Windows, Linux, macOS

Autor: Paulo Felix
Versión: 1.0.0
Licencia: MIT
"""

import os
import subprocess
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, abort
import platform
import re

# Importar el nuevo sistema de almacenamiento SQLite
from storage import get_storage

app = Flask(__name__)

# Configuración
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Inicializar el sistema de almacenamiento
storage = get_storage()

print("Sistema de almacenamiento SQLite inicializado correctamente")

@app.route('/')
def index():
    """
    Renderiza la página principal de la aplicación.
    
    Carga el historial de escaneos desde la base de datos SQLite y las unidades
    disponibles en el sistema para mostrar en la interfaz web.
    
    Returns:
        str: HTML renderizado de la página principal con historial y unidades
    """
    history = storage.get_scan_history()
    drives = get_drives()
    now = datetime.now()
    return render_template('index.html', history=history, drives=drives, now=now)

@app.route('/search', methods=['GET'])
def search():
    """
    Realiza búsquedas de directorios en todos los catálogos almacenados.
    
    Busca el término especificado en el parámetro 'q' dentro de todas las rutas
    de directorios catalogadas, utilizando búsqueda case-insensitive.
    
    Args:
        q (str): Término de búsqueda obtenido de query parameter
        
    Returns:
        JSON: Lista de resultados con formato compatible con el frontend
        [
            {
                'catalog': str,     # Nombre del volumen/catálogo
                'path': str,        # Nombre del directorio
                'full_path': str    # Ruta completa del directorio
            }
        ]
    """
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])

    results = storage.search_directories(query)
    
    # Formatear resultados para compatibilidad con el frontend
    formatted_results = []
    for result in results:
        formatted_results.append({
            'catalog': result.get('volume_name', 'Desconocido'),
            'path': result['directory_path'].split('\\')[-1] if '\\' in result['directory_path'] else result['directory_path'].split('/')[-1],
            'full_path': result['directory_path']
        })

    return jsonify(formatted_results[:100])  # Limitar resultados para evitar sobrecarga

def get_volume_info_windows(drive_letter):
    """
    Obtiene información del volumen de Windows usando el comando 'vol'.
    
    Extrae el número de serie único del volumen y su etiqueta/descripción
    ejecutando el comando 'vol' del sistema y parseando su salida con
    expresiones regulares.
    
    Args:
        drive_letter (str): Letra de la unidad (ej: 'C', 'D', 'E')
        
    Returns:
        tuple: (descripción, serial) donde:
            - descripción (str|None): Etiqueta del volumen o None si no se encuentra
            - serial (str|None): Número de serie del volumen o None si no se encuentra
            
    Note:
        Específico para Windows. Usa codificación 'latin-1' para manejar
        caracteres especiales en etiquetas de volumen.
    """
    try:
        # Ejecutar comando 'vol' con codificación 'latin-1'
        cmd = f'vol {drive_letter}:'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='latin-1', errors='ignore')
        
        print("=== Salida del comando 'vol' ===")
        print(result.stdout)
        print("================================")

        if result.returncode != 0:
            print("Error: Comando 'vol' falló.")
            return None, None

        # Extraer serial (ej: "44FA-62AA")
        serial_match = re.search(r'([A-Z0-9]{4}-[A-Z0-9]{4})', result.stdout)
        serial = serial_match.group(0) if serial_match else None

        # Extraer descripción (ej: "Fotograf¡a DobleA")
        desc_match = re.search(r'(?:es\s|is\s)(.+)', result.stdout)
        description = desc_match.group(1).strip() if desc_match else None

        print(f"Descripción extraída: {description}")
        print(f"Serial extraído: {serial}")
        return description, serial

    except Exception as e:
        print(f"Error en get_volume_info_windows: {str(e)}")
        return None, None

@app.route('/scan', methods=['POST'])
def scan_disk():
    """
    Escanea una unidad de disco y guarda su estructura de directorios.
    
    Realiza un escaneo completo de la unidad especificada, extrae información
    del volumen (nombre y número de serie), cataloga todos los directorios
    encontrados y los almacena en la base de datos SQLite.
    
    Form Parameters:
        drive_path (str): Ruta de la unidad a escanear (ej: 'C:\\', 'D:\\')
        catalog_name (str, optional): Nombre personalizado para el catálogo
        
    Returns:
        JSON: Respuesta con el resultado de la operación
        Success: {"success": True, "serial": str}
        Error: {"error": str}, HTTP status 400/500
        
    Note:
        - Usa comandos del sistema específicos por plataforma
        - Windows: 'dir /s /b /ad' para listar solo directorios  
        - Linux/macOS: 'find -type d' para búsqueda recursiva
        - Actualiza escaneos existentes basándose en el número de serie del volumen
    """
    try:
        drive_path = request.form.get('drive_path')
        catalog_name = request.form.get('catalog_name', f"Disco_{datetime.now().strftime('%Y%m%d')}")

        # Validar unidad
        if not drive_path or not os.path.exists(drive_path):
            return jsonify({"error": "Unidad no válida o no accesible"}), 400

        # Obtener información del volumen
        description, serial = get_volume_info_windows(drive_path[0].upper())
        if not serial:
            return jsonify({"error": "No se pudo obtener el serial"}), 400

        # Escanear la estructura de carpetas
        system = platform.system()
        if system == 'Windows':
            command = f'dir "{drive_path}" /s /b /ad'  # Solo directorios
        elif system in ('Linux', 'Darwin'):
            command = f'find "{drive_path}" -type d -print'
        else:
            return jsonify({"error": "Sistema no soportado"}), 400

        result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='latin-1')
        folders = [line.strip() for line in result.stdout.splitlines() if line.strip()]

        # Guardar el escaneo usando el nuevo sistema de almacenamiento
        success = storage.add_scan(
            serial_number=serial,
            volume_name=description or catalog_name,
            drive_path=drive_path,
            directories=folders
        )

        if success:
            return jsonify({"success": True, "serial": serial})
        else:
            return jsonify({"error": "Error al guardar el escaneo"}), 500

    except Exception as e:
        print(f"Error en /scan: {e}")
        return jsonify({"error": str(e)}), 500

def get_drives():
    """
    Detecta y obtiene información de todas las unidades de disco disponibles.
    
    Escanea todas las letras de unidad posibles (A-Z) en sistemas Windows
    y recopila información detallada de cada unidad accesible, incluyendo
    etiqueta del volumen, espacio libre y otros metadatos.
    
    Returns:
        list: Lista de diccionarios con información de cada unidad
        [
            {
                'letter': str,      # Letra de la unidad (ej: 'C')
                'path': str,        # Ruta completa (ej: 'C:\\')
                'name': str,        # Nombre base de la unidad
                'free_gb': float,   # Espacio libre en GB (None si no disponible)
                'description': str  # Etiqueta del volumen (None si no disponible)
            }
        ]
        
    Note:
        - Específico para sistemas Windows
        - Usa subprocess para ejecutar comando 'vol' y obtener etiquetas
        - Maneja errores de permisos y timeouts automáticamente
    """
    drives = []
    import platform
    system = platform.system()
    for drive_letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        drive_path = f"{drive_letter}:\\"
        if os.path.exists(drive_path):
            try:
                drive_name = os.path.basename(drive_path)
                # Obtener información de espacio libre
                stat = os.statvfs(drive_path) if hasattr(os, 'statvfs') else None
                free_gb = round(stat.f_bfree * stat.f_frsize / (1024 ** 3), 1) if stat else None
                description = None
                if system == 'Windows':
                    try:
                        import subprocess
                        result = subprocess.run(["cmd", "/c", f"vol {drive_letter}:"], capture_output=True, text=True, timeout=2)
                        print("Salida comando vol:", result.stdout)
                        lines = result.stdout.splitlines()
                        for line in lines:
                            print("Línea:", line)
                            if "Etiqueta del volumen en la unidad" in line or "Volume in drive" in line:
                                description = line.split('es ')[-1] if 'es ' in line else line.split('is ')[-1]
                                break
                    except Exception:
                        description = None
                drives.append({
                    "letter": drive_letter,
                    "path": drive_path,
                    "name": drive_name,
                    "free_gb": free_gb,
                    "description": description
                })
            except:
                continue
    return drives

@app.route('/catalog/<serial>')
def view_catalog(serial):
    """Ver detalles de un catálogo específico"""
    try:
        # Obtener información del escaneo
        scan_info = storage.get_scan_by_serial(serial)
        if not scan_info:
            return jsonify({
                "status": "error",
                "message": "Catálogo no encontrado",
                "data": None
            }), 404

        # Obtener algunos directorios de muestra
        directories = storage.get_directories_by_scan(scan_info['id'])
        sample_directories = directories[:10]  # Primeras 10 carpetas

        # Estructura de respuesta
        normalized_data = {
            "name": scan_info.get("volume_name", "Sin nombre"),
            "path": scan_info.get("drive_path", ""),
            "serial": serial,
            "scan_date": scan_info.get("scan_date", ""),
            "total_folders": scan_info.get("total_directories", 0),
            "sample_folders": sample_directories
        }

        return jsonify({
            "status": "success",
            "message": "Catálogo cargado",
            "data": normalized_data
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error al procesar el catálogo: {str(e)}",
            "data": None
        }), 500

@app.route('/delete_catalog', methods=['POST'])
def delete_catalog():
    """Eliminar un catálogo específico"""
    serial = request.form.get('serial')
    if not serial:
        return jsonify({'success': False, 'error': 'Serial no especificado'}), 400
    
    # Verificar que el escaneo existe
    scan_info = storage.get_scan_by_serial(serial)
    if not scan_info:
        return jsonify({'success': False, 'error': 'Catálogo no encontrado'}), 404
    
    try:
        # Eliminar el escaneo y todos sus directorios asociados
        success = storage.delete_scan(serial)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Error al eliminar el catálogo'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/eject_drive', methods=['POST'])
def eject_drive():
    drive_path = request.form.get('drive_path')
    if not drive_path:
        return jsonify({'success': False, 'error': 'Unidad no especificada'}), 400

    # Seguridad: no permitir expulsar C: ni /
    if drive_path.strip().upper().startswith('C:') or drive_path.strip() == '/':
        return jsonify({'success': False, 'error': 'No se puede expulsar la unidad del sistema'}), 400

    system = platform.system()
    try:
        if system == 'Windows':
            # Quitar barra final si existe
            drive_letter = drive_path.rstrip('\\/').replace(':', '')
            # Usar powershell para expulsar (solo funciona con USB extraíbles)
            # El comando puede variar según el dispositivo, intentamos con mountvol primero
            import subprocess
            cmd = f'powershell -Command "[void](mountvol {drive_letter}: /p)"'
            result = subprocess.run(cmd, shell=True)
            if result.returncode == 0:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'No se pudo expulsar la unidad (Windows)'}), 500
        elif system == 'Linux':
            # udisksctl es el método más estándar para USB
            import subprocess
            cmd_unmount = f'udisksctl unmount -b {drive_path}'
            cmd_poweroff = f'udisksctl power-off -b {drive_path}'
            subprocess.run(cmd_unmount, shell=True)
            result = subprocess.run(cmd_poweroff, shell=True)
            if result.returncode == 0:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'No se pudo expulsar la unidad (Linux)'}), 500
        elif system == 'Darwin':  # Mac
            # diskutil para Mac
            import subprocess
            cmd = f'diskutil unmountDisk {drive_path}'
            result = subprocess.run(cmd, shell=True)
            if result.returncode == 0:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'No se pudo expulsar la unidad (Mac)'}), 500
        else:
            return jsonify({'success': False, 'error': 'Sistema operativo no soportado'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_drives')
def get_drives_api():
    drives = get_drives()
    return jsonify(drives)

@app.route('/update_catalog', methods=['POST'])
def update_catalog():
    """Actualizar un catálogo existente reescaneando la unidad"""
    serial = request.form.get('serial')
    if not serial:
        return jsonify({'success': False, 'error': 'Serial no especificado'}), 400
    
    # Obtener información del escaneo existente
    scan_info = storage.get_scan_by_serial(serial)
    if not scan_info:
        return jsonify({'success': False, 'error': 'Catálogo no encontrado'}), 404
    
    drive_path = scan_info.get('drive_path')
    if not drive_path or not os.path.exists(drive_path):
        return jsonify({'success': False, 'error': 'La unidad original no está conectada'}), 400
    
    try:
        # Rescanear la unidad
        system = platform.system()
        if system == 'Windows':
            command = f'dir "{drive_path}" /s /b /ad'
        elif system in ('Linux', 'Darwin'):
            command = f'find "{drive_path}" -type d -print'
        else:
            return jsonify({'success': False, 'error': 'Sistema operativo no soportado'}), 500
        
        result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='latin-1')
        folders = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        
        # Actualizar el escaneo con los nuevos directorios
        success = storage.add_scan(
            serial_number=serial,
            volume_name=scan_info.get('volume_name', ''),
            drive_path=drive_path,
            directories=folders
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Catálogo actualizado correctamente'})
        else:
            return jsonify({'success': False, 'error': 'Error al actualizar el catálogo'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error al actualizar el catálogo: {str(e)}'}), 500

@app.route('/rename_catalog', methods=['POST'])
def rename_catalog():
    """Renombrar un catálogo"""
    serial = request.form.get('serial')
    new_name = request.form.get('new_name')
    
    if not serial:
        return jsonify({'success': False, 'error': 'Serial no especificado'}), 400
    if not new_name or any(c in new_name for c in '/\\:*?"<>|'):
        return jsonify({'success': False, 'error': 'Nombre de catálogo inválido'}), 400
    
    # Obtener información del escaneo existente
    scan_info = storage.get_scan_by_serial(serial)
    if not scan_info:
        return jsonify({'success': False, 'error': 'Catálogo no encontrado'}), 404
    
    try:
        # Obtener todos los directorios del escaneo actual
        directories = storage.get_directories_by_scan(scan_info['id'])
        
        # Actualizar el escaneo con el nuevo nombre
        success = storage.add_scan(
            serial_number=serial,
            volume_name=new_name,
            drive_path=scan_info.get('drive_path', ''),
            directories=directories
        )
        
        if success:
            return jsonify({'success': True, 'new_name': new_name})
        else:
            return jsonify({'success': False, 'error': 'Error al renombrar el catálogo'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)