## 🎯 Descripción

Implementar un sistema de búsqueda avanzada que permita a los usuarios aplicar filtros múltiples para refinar sus resultados de búsqueda. Esta funcionalidad convertirá a ScanFolder en una herramienta más potente para la gestión de archivos distribuidos.

## 🚀 Motivación

Los usuarios manejan grandes volúmenes de datos distribuidos en múltiples discos. Con la búsqueda básica actual, encontrar directorios específicos puede generar demasiados resultados. Los filtros avanzados permitirán búsquedas más precisas y eficientes.

## ✨ Funcionalidades Propuestas

### Filtros de Búsqueda:
- 📅 **Por fecha de escaneo**: Buscar solo en catálogos recientes o específicos
- 💿 **Por disco/volumen**: Filtrar resultados de discos particulares
- 📏 **Por profundidad de ruta**: Limitar búsqueda por niveles de carpeta
- 🏷️ **Por tipo de dispositivo**: USB, HDD, SSD, Red
- 🔤 **Operadores de texto**: Exacto, contiene, empieza con, termina con

### Funcionalidades Técnicas:
- **Interfaz expandible** con acordeón para filtros avanzados
- **Búsqueda combinada** con operadores AND/OR
- **Guardado de filtros** como búsquedas favoritas
- **URLs compartibles** con filtros aplicados

## 🛠️ Implementación Técnica

### Backend (Flask/SQLite):
```sql
SELECT DISTINCT d.path, s.disk_name, s.scan_date, s.volume_serial
FROM directories d
JOIN scans s ON d.scan_id = s.id
WHERE d.path LIKE ?
  AND s.scan_date BETWEEN ? AND ?
  AND s.disk_name IN (?)
  AND (LENGTH(d.path) - LENGTH(REPLACE(d.path, '/', ''))) BETWEEN ? AND ?
ORDER BY s.scan_date DESC, d.path;
```

### Frontend (JavaScript/HTML):
```html
<div class="advanced-search-panel">
  <div class="accordion" id="filtersAccordion">
    <div class="card">
      <div class="card-header">
        <h2 class="mb-0">
          <button class="btn btn-link" data-toggle="collapse" data-target="#dateFilters">
            📅 Filtros de Fecha
          </button>
        </h2>
      </div>
      <div id="dateFilters" class="collapse">
        <div class="card-body">
          <input type="date" id="date-from" class="form-control mb-2">
          <input type="date" id="date-to" class="form-control">
        </div>
      </div>
    </div>
  </div>
</div>
```

### API Endpoints:
```python
@app.route('/api/search/advanced', methods=['POST'])
def advanced_search():
    filters = request.get_json()
    query = build_dynamic_query(filters)
    results = execute_filtered_search(query, filters)
    return jsonify(results)

@app.route('/api/filters/save', methods=['POST'])
def save_filter():
    filter_config = request.get_json()
    # Guardar en base de datos o localStorage
    return jsonify({"status": "saved"})
```

## ✅ Criterios de Aceptación

- [ ] Panel de filtros avanzados funcional en la interfaz
- [ ] Filtros por fecha, disco, profundidad y tipo de texto
- [ ] Combinación de múltiples filtros simultáneamente
- [ ] Guardado y carga de filtros favoritos
- [ ] URLs compartibles con filtros aplicados
- [ ] Rendimiento optimizado para grandes conjuntos de datos (<2 segundos)
- [ ] Interfaz responsive para dispositivos móviles
- [ ] Validación de entrada en todos los campos de filtro

## 🧪 Tests de Aceptación

1. **Filtro básico**: Buscar 'Documents' solo en discos USB
2. **Filtro combinado**: Carpetas escaneadas en últimos 30 días con profundidad máxima 3
3. **Guardado**: Crear filtro favorito 'Fotos Recientes' y reutilizar
4. **Performance**: Aplicar filtros en <2 segundos con 50,000+ directorios
5. **Compartir**: URL con filtros funciona al copiar/pegar
6. **Mobile**: Funcionalidad completa en dispositivos móviles

## 🎯 Definición de Hecho (Definition of Done)

- [ ] Código implementado y testeado
- [ ] Tests unitarios y de integración
- [ ] Documentación actualizada
- [ ] UI/UX validado por usuarios
- [ ] Performance benchmark completado
- [ ] Code review aprobado

## 🏷️ Prioridad: Alta
Este feature es fundamental para la experiencia de usuario y diferenciará ScanFolder de herramientas similares.
