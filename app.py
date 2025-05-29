# app.py
import os
import subprocess
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, abort
import platform
import re

app = Flask(__name__)

# Configuración
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOGS_DIR = os.path.join(BASE_DIR, 'catalogos')
SCAN_HISTORY_FILE = os.path.join(BASE_DIR, 'scan_history.json')

# Crear directorios necesarios
os.makedirs(CATALOGS_DIR, exist_ok=True)

print(f"Ruta de CATALOGS_DIR: {os.path.abspath(CATALOGS_DIR)}")  # Verifica la ruta absoluta
print(f"Contenido de catalogos/: {os.listdir(CATALOGS_DIR)}")  # Lista archivos en la carpeta

# Cargar historial de escaneos
def load_scan_history():
    """Cargar el historial desde el archivo JSON."""
    try:
        if os.path.exists(SCAN_HISTORY_FILE):
            with open(SCAN_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []  # Si el archivo no existe, retorna una lista vacía
    except Exception as e:
        print(f"Error al cargar el historial: {e}")
        return []  # En caso de error, retorna una lista vacía

def save_scan_history(history):
    """Guardar el historial en el archivo JSON."""
    try:
        with open(SCAN_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        print("Historial guardado correctamente.")
    except Exception as e:
        print(f"Error al guardar el historial: {e}")

@app.route('/')
def index():
    history = load_scan_history()
    # Completar descripción y serie desde el archivo si falta
    for entry in history:
        # Descripción
        if not entry.get('description'):
            file_path = os.path.join(CATALOGS_DIR, entry.get('file', ''))
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        first_line = f.readline().strip()
                        desc = None
                        if 'volumen' in first_line:
                            parts = first_line.split('volumen', 1)
                            if len(parts) > 1:
                                desc = parts[1].strip()
                        elif 'volume' in first_line.lower():
                            parts = first_line.lower().split('volume', 1)
                            if len(parts) > 1:
                                desc = parts[1].strip()
                        if desc:
                            entry['description'] = desc
                        # Serie
                        second_line = f.readline().strip()
                        serial = None
                        if "serie del volumen" in second_line.lower() or "serial number" in second_line.lower():
                            if ':' in second_line:
                                serial = second_line.split(':')[-1].strip()
                        if serial:
                            entry['serial'] = serial
                except Exception:
                    pass
    drives = get_drives()
    now = datetime.now()
    return render_template('index.html', history=history, drives=drives, now=now)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').lower().strip()
    if not query or len(query) < 2:
        return jsonify([])

    history = load_scan_history()
    results = []
    for entry in history:
        if not entry.get('serial'):
            continue

        file_path = os.path.join(CATALOGS_DIR, f"{entry['serial']}.json")
        if not os.path.exists(file_path):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
                for folder_path in catalog.get('folders', []):
                    if query in folder_path.lower():
                        results.append({
                            'catalog': entry['name'],
                            'path': folder_path.split('\\')[-1] if '\\' in folder_path else folder_path.split('/')[-1],
                            'full_path': folder_path
                        })
        except Exception:
            continue

    return jsonify(results[:100])  # Limitar resultados para evitar sobrecarga

def get_volume_info_windows(drive_letter):
    """Obtener información del volumen en Windows con manejo robusto de errores."""
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

        # Crear el archivo JSON del catálogo
        catalog_data = {
            "serial": serial,
            "name": catalog_name,
            "path": drive_path,
            "scan_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "description": description,
            "folders": folders  # Lista de carpetas escaneadas
        }

        output_file = os.path.join(CATALOGS_DIR, f"{serial}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(catalog_data, f, ensure_ascii=False, indent=2)
        print(f"Catálogo guardado en: {output_file}")

        # Actualizar historial
        history = load_scan_history()
        history.insert(0, {
            "name": catalog_name,
            "path": drive_path,
            "date": catalog_data['scan_date'],
            "file": f"{serial}.json",  # Nombre del archivo JSON
            "description": description,
            "serial": serial
        })
        save_scan_history(history)

        return jsonify({"success": True, "serial": serial})

    except Exception as e:
        print(f"Error en /scan: {e}")
        return jsonify({"error": str(e)}), 500

def get_drives():
    """Obtener las unidades disponibles en Windows, incluyendo el nombre del volumen como descripción"""
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
    try:
        file_path = os.path.join(CATALOGS_DIR, f"{serial}.json")
        
        if not os.path.exists(file_path):
            return jsonify({
                "status": "error",
                "message": "Catálogo no encontrado",
                "data": None
            }), 404


        with open(file_path, 'r', encoding='utf-8') as f:
            catalog_data = json.load(f)

        # Normalizar caracteres especiales
        def normalize_text(text):
            return text.encode('latin-1').decode('utf-8', errors='replace') if text else text

        normalized_data = {
            "name": normalize_text(catalog_data.get("name")),
            "path": catalog_data.get("path"),
            "serial": serial,
            "scan_date": catalog_data.get("scan_date"),
            "total_folders": len(catalog_data.get("folders", [])),
            "sample_folders": [normalize_text(f) for f in catalog_data.get("folders", [])[:10]]
        }

        # Estructura de respuesta mejorada
        response = {
            "success": True,
            "catalog": {
                "name": catalog_data.get("name", "Sin nombre"),
                "serial": serial,
                "path": catalog_data.get("path", ""),
                "scan_date": catalog_data.get("scan_date", ""),
                "total_folders": len(catalog_data.get("folders", [])),
                "sample_folders": catalog_data.get("folders", [])[:10]  # Primeras 10 carpetas
            }
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
    serial = request.form.get('serial')
    if not serial:
        return jsonify({'success': False, 'error': 'Serial no especificado'}), 400
    history = load_scan_history()
    entry = next((h for h in history if h.get('serial') == serial), None)
    if not entry:
        return jsonify({'success': False, 'error': 'Catálogo no encontrado en el historial'}), 404
    file_path = os.path.join(CATALOGS_DIR, f"{serial}.json")
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        history = [h for h in history if h.get('serial') != serial]
        save_scan_history(history)
        return jsonify({'success': True})
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
    serial = request.form.get('serial')
    if not serial:
        return jsonify({'success': False, 'error': 'Serial no especificado'}), 400
    history = load_scan_history()
    entry = next((h for h in history if h.get('serial') == serial), None)
    if not entry:
        return jsonify({'success': False, 'error': 'Catálogo no encontrado en el historial'}), 404
    drive_path = entry.get('path')
    if not drive_path or not os.path.exists(drive_path):
        return jsonify({'success': False, 'error': 'La unidad original no está conectada'}), 400
    output_file = os.path.join(CATALOGS_DIR, f"{serial}.json")
    try:
        import platform
        system = platform.system()
        if system == 'Windows':
            command = f'tree "{drive_path}" /A /F > "{output_file}"'
        elif system == 'Linux' or system == 'Darwin':
            command = f'find "{drive_path}" -print > "{output_file}"'
        else:
            return jsonify({'success': False, 'error': 'Sistema operativo no soportado'}), 500
        import subprocess
        subprocess.run(command, shell=True, check=True)
        entry['date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_scan_history(history)
        return jsonify({'success': True, 'message': f'Catálogo actualizado correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error al actualizar el catálogo: {str(e)}'}), 500

@app.route('/rename_catalog', methods=['POST'])
def rename_catalog():
    serial = request.form.get('serial')
    new_name = request.form.get('new_name')
    if not serial:
        return jsonify({'success': False, 'error': 'Serial no especificado'}), 400
    if not new_name or any(c in new_name for c in '/\\:*?"<>|'):
        return jsonify({'success': False, 'error': 'Nombre de catálogo inválido'}), 400
    history = load_scan_history()
    entry = next((h for h in history if h.get('serial') == serial), None)
    if not entry:
        return jsonify({'success': False, 'error': 'Catálogo no encontrado en el historial'}), 404
    # Solo actualizar el nombre en el historial
    entry['name'] = new_name
    save_scan_history(history)
    return jsonify({'success': True, 'new_name': new_name})

if __name__ == '__main__':
    app.run(debug=True)