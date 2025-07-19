## 🎯 Descripción

Implementar paginación tanto en el backend como en el frontend para manejar eficientemente grandes volúmenes de directorios, mejorando el rendimiento y la experiencia del usuario al mostrar resultados de escaneos.

## 🚀 Motivación

Actualmente, cuando se escanean directorios con miles de carpetas, todos los resultados se cargan de una vez, causando problemas de rendimiento en el navegador y dificultando la navegación. La paginación mejorará significativamente la usabilidad.

## ✨ Funcionalidades Propuestas

### Sistema de Paginación:
- 📄 **Páginas configurables**: 25, 50, 100, 200 resultados por página
- ⬅️➡️ **Navegación intuitiva**: Botones Anterior/Siguiente
- 🔢 **Salto directo**: Ir a página específica
- 📊 **Información clara**: "Página X de Y" y "Mostrando X-Y de Z"

### Funcionalidades Técnicas:
- **Paginación server-side** para mejor rendimiento
- **Conservación de filtros** al cambiar páginas
- **URLs con estado** para bookmarking
- **Loading indicators** durante navegación

## 🛠️ Implementación Técnica

### Backend (Flask/SQLite):
```python
def get_directories_paginated(search_query, page=1, per_page=50):
    offset = (page - 1) * per_page
    
    # Query principal con LIMIT y OFFSET
    query = '''
    SELECT d.path, s.disk_name, s.scan_date 
    FROM directories d 
    JOIN scans s ON d.scan_id = s.id 
    WHERE d.path LIKE ? 
    ORDER BY s.scan_date DESC, d.path
    LIMIT ? OFFSET ?
    '''
    
    # Query para contar total de resultados
    count_query = '''
    SELECT COUNT(*) 
    FROM directories d 
    JOIN scans s ON d.scan_id = s.id 
    WHERE d.path LIKE ?
    '''
    
    total = db.execute(count_query, [f'%{search_query}%']).fetchone()[0]
    results = db.execute(query, [f'%{search_query}%', per_page, offset]).fetchall()
    
    return {
        'results': results,
        'pagination': {
            'current_page': page,
            'total_pages': math.ceil(total / per_page),
            'total_results': total,
            'has_next': page < math.ceil(total / per_page),
            'has_prev': page > 1,
            'per_page': per_page
        }
    }

@app.route('/api/search')
def paginated_search():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Validar parámetros
    per_page = min(max(per_page, 10), 200)  # Entre 10 y 200
    
    return jsonify(get_directories_paginated(query, page, per_page))
```

### Frontend (JavaScript):
```javascript
class PaginationManager {
    constructor() {
        this.currentPage = 1;
        this.perPage = 50;
        this.totalPages = 1;
        this.totalResults = 0;
    }
    
    loadPage(page) {
        const url = `/api/search?q=${encodeURIComponent(this.currentQuery)}&page=${page}&per_page=${this.perPage}`;
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                this.updateResults(data.results);
                this.updatePaginationControls(data.pagination);
                this.updateURL(page);
            })
            .catch(error => console.error('Error loading page:', error));
    }
    
    updatePaginationControls(pagination) {
        this.currentPage = pagination.current_page;
        this.totalPages = pagination.total_pages;
        this.totalResults = pagination.total_results;
        
        // Actualizar botones
        document.getElementById('prev-page').disabled = !pagination.has_prev;
        document.getElementById('next-page').disabled = !pagination.has_next;
        document.getElementById('first-page').disabled = !pagination.has_prev;
        document.getElementById('last-page').disabled = !pagination.has_next;
        
        // Actualizar información
        this.updatePageInfo();
        this.generatePageNumbers();
    }
    
    generatePageNumbers() {
        const pageNumbersDiv = document.querySelector('.page-numbers');
        pageNumbersDiv.innerHTML = '';
        
        // Algoritmo para mostrar números inteligentes
        // Ejemplo: 1 2 3 ... 8 9 [10] 11 12 ... 24 25
        const range = this.calculatePageRange();
        range.forEach(page => {
            if (typeof page === 'number') {
                const span = document.createElement('span');
                span.className = `page-number ${page === this.currentPage ? 'active' : ''}`;
                span.textContent = page;
                span.onclick = () => this.loadPage(page);
                pageNumbersDiv.appendChild(span);
            } else {
                const span = document.createElement('span');
                span.className = 'page-ellipsis';
                span.textContent = '...';
                pageNumbersDiv.appendChild(span);
            }
        });
    }
    
    updateURL(page) {
        const url = new URL(window.location);
        url.searchParams.set('page', page);
        window.history.replaceState({}, '', url);
    }
}
```

### HTML Template:
```html
<div class="pagination-container">
    <div class="pagination-info">
        <span>Mostrando <strong id="start-item">1</strong> a <strong id="end-item">50</strong> 
        de <strong id="total-items">1,245</strong> directorios</span>
    </div>
    
    <div class="pagination-controls">
        <button id="first-page" class="page-btn">⏮️ Primera</button>
        <button id="prev-page" class="page-btn">⬅️ Anterior</button>
        
        <div class="page-numbers">
            <!-- Números de página generados dinámicamente -->
        </div>
        
        <button id="next-page" class="page-btn">➡️ Siguiente</button>
        <button id="last-page" class="page-btn">⏭️ Última</button>
    </div>
    
    <div class="per-page-selector">
        <label for="per-page-select">Resultados por página:</label>
        <select id="per-page-select">
            <option value="25">25</option>
            <option value="50" selected>50</option>
            <option value="100">100</option>
            <option value="200">200</option>
        </select>
    </div>
</div>
```

## ✅ Criterios de Aceptación

- [ ] Sistema carga inicialmente solo primeros 50 resultados
- [ ] Controles de paginación se muestran cuando hay >50 resultados
- [ ] Navegación funcional con botones Anterior/Siguiente
- [ ] Salto directo a página específica funciona
- [ ] Cambio de elementos por página (25, 50, 100, 200)
- [ ] Información clara de estado: "Página X de Y"
- [ ] Paginación funciona correctamente con filtros aplicados
- [ ] Estado de página se mantiene al aplicar/quitar filtros
- [ ] URLs incluyen parámetros de paginación para bookmarking
- [ ] Interfaz responsive en dispositivos móviles

## 🧪 Tests de Aceptación

1. **Carga inicial**: 1,000+ directorios → mostrar solo primeros 50
2. **Navegación básica**: Ir a página 5 → mostrar resultados 201-250  
3. **Cambio de tamaño**: Cambiar a 100 por página → recalcular páginas
4. **Filtros + paginación**: Aplicar filtro → mantener paginación en resultados
5. **Límites**: Primera página → botón "Anterior" deshabilitado
6. **Performance**: Cambio de página en <500ms
7. **URLs**: Copiar URL de página 3 → al pegarla, ir directamente a página 3
8. **Mobile**: Funcionalidad completa en dispositivos móviles

## 💡 Perfect for First Contributors!

Este issue es **ideal para empezar a contribuir** porque:

- ✅ **Alcance bien definido**: Funcionalidad específica y acotada
- ✅ **Tecnologías básicas**: HTML, CSS, JavaScript, Python básico
- ✅ **Múltiples niveles**: Se puede implementar gradualmente
- ✅ **Impacto visible**: Mejora inmediata en la experiencia de usuario
- ✅ **Tests claros**: Casos de prueba fáciles de verificar
- ✅ **Documentación**: Recursos abundantes disponibles online

### 🚀 Pasos Sugeridos para Comenzar:

1. **Fork el repositorio** y crear branch `feature/pagination`
2. **Implementar backend**: Función `get_directories_paginated()`
3. **Crear HTML básico**: Controles de paginación
4. **Agregar JavaScript**: Clase `PaginationManager`
5. **Styling CSS**: Hacer responsive y atractivo
6. **Tests**: Verificar todos los casos de aceptación

### 📚 Recursos Útiles:
- [Flask Pagination Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-ix-pagination)
- [SQLite LIMIT and OFFSET](https://www.sqlitetutorial.net/sqlite-limit/)
- [JavaScript Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [Bootstrap Pagination Components](https://getbootstrap.com/docs/4.6/components/pagination/)

## 🏷️ Prioridad: Media
Feature esencial para usabilidad, perfecto para primeras contribuciones.
