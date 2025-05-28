# app.py
import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Configuración (cambia esto a tu ruta de archivos TXT)
CATALOGS_DIR = r"C:\Tus\Carpeta\Con\Catalogos"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').lower()
    results = []

    # Buscar en todos los archivos TXT
    for filename in os.listdir(CATALOGS_DIR):
        if filename.endswith('.txt'):
            filepath = os.path.join(CATALOGS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as file:
                for line in file:
                    if query in line.lower():
                        disk_name = filename.replace('.txt', '')
                        results.append({
                            'disk': disk_name,
                            'path': line.strip()
                        })

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)