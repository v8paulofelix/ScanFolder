# app.py
import os
import subprocess
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, abort

app = Flask(__name__)

# Configuración
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOGS_DIR = os.path.join(BASE_DIR, 'catalogos')
SCAN_HISTORY_FILE = os.path.join(BASE_DIR, 'scan_history.json')

# Crear directorios necesarios
os.makedirs(CATALOGS_DIR, exist_ok=True)

# Cargar historial de escaneos
def load_scan_history():
    if os.path.exists(SCAN_HISTORY_FILE):
        with open(SCAN_HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_scan_history(history):
    with open(SCAN_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    history = load_scan_history()
    drives = get_drives()
    now = datetime.now()
    return render_template('index.html', history=history, drives=drives, now=now)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').lower()
    results = []

    if not query:
        return jsonify([])  # Devuelve una lista vacía si no hay query
    
    # Buscar en todos los archivos TXT
    for filename in os.listdir(CATALOGS_DIR):
        if filename.endswith('.txt'):
            filepath = os.path.join(CATALOGS_DIR, filename)
            with open(filepath, 'r', encoding='latin-1') as file:
                for line in file:
                    if query in line.lower():
                        disk_name = filename.replace('.txt', '')
                        results.append({
                            'disk': disk_name,
                            'path': line.strip()
                        })
    
    return jsonify(results)

@app.route('/scan', methods=['POST'])
def scan_disk():
    drive_path = request.form.get('drive_path')
    catalog_name = request.form.get('catalog_name', f"Disco_{datetime.now().strftime('%Y%m%d')}")
    
    if not drive_path:
        return jsonify({"error": "Debe seleccionar una unidad"}), 400
    
    # Crear el comando para generar el árbol de directorios
    output_file = os.path.join(CATALOGS_DIR, f"{catalog_name}.txt")
    
    try:
        # Usar el comando tree de Windows
        command = f'tree "{drive_path}" /A /F > "{output_file}"'
        subprocess.run(command, shell=True, check=True)
        
        # Actualizar el historial
        history = load_scan_history()
        history.insert(0, {
            "name": catalog_name,
            "path": drive_path,
            "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "file": f"{catalog_name}.txt"
        })
        save_scan_history(history)
        
        return jsonify({
            "success": True,
            "message": f"Catálogo '{catalog_name}' creado exitosamente"
        })
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Error al escanear el disco: {str(e)}"}), 500

def get_drives():
    """Obtener las unidades disponibles en Windows"""
    drives = []
    for drive_letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        drive_path = f"{drive_letter}:\\"
        if os.path.exists(drive_path):
            try:
                drive_name = os.path.basename(drive_path)
                # Obtener información de espacio libre
                stat = os.statvfs(drive_path) if hasattr(os, 'statvfs') else None
                free_gb = round(stat.f_bfree * stat.f_frsize / (1024 ** 3), 1) if stat else None
                
                drives.append({
                    "letter": drive_letter,
                    "path": drive_path,
                    "name": drive_name,
                    "free_gb": free_gb
                })
            except:
                continue
    return drives

@app.route('/catalog/<filename>')
def view_catalog(filename):
    print(f"Recibido filename: '{filename}'")
    # Seguridad básica: solo permite archivos .txt y sin rutas
    if not filename.endswith('.txt') or '/' in filename or '\\' in filename:
        print("Nombre de archivo inválido")
        abort(404)
    filepath = os.path.join(CATALOGS_DIR, filename)
    print(f"Ruta buscada: '{filepath}'")
    if not os.path.exists(filepath):
        print("Archivo no encontrado en el sistema de archivos")
        abort(404)
    try:
        with open(filepath, 'r', encoding='latin-1') as f:
            content = f.read()
        return jsonify({"content": content, "filename": filename})
    except Exception as e:
        print(f"Error al abrir el archivo: {e}")
        abort(500)

@app.route('/delete_catalog', methods=['POST'])
def delete_catalog():
    filename = request.form.get('filename')
    if not filename or not filename.endswith('.txt') or '/' in filename or '\\' in filename:
        return jsonify({'success': False, 'error': 'Nombre de archivo inválido'}), 400
    filepath = os.path.join(CATALOGS_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'error': 'El archivo no existe'}), 404
    try:
        os.remove(filepath)
        # Quitar del historial
        history = load_scan_history()
        history = [h for h in history if h.get('file') != filename]
        save_scan_history(history)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)