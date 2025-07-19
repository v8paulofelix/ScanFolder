# 🤝 Guía de Contribución - ScanFolder

¡Gracias por tu interés en contribuir a ScanFolder! Este documento te guiará paso a paso para hacer una contribución exitosa al proyecto.

## 📋 Tabla de Contenidos

- [🐛 Reportar un Bug](#-reportar-un-bug)
- [💡 Sugerir una Mejora](#-sugerir-una-mejora)
- [🔧 Contribuir con Código](#-contribuir-con-código)
- [📝 Estándares de Código](#-estándares-de-código)
- [🧪 Pruebas](#-pruebas)
- [📚 Documentación](#-documentación)

## 🐛 Reportar un Bug

Si encuentras un error en ScanFolder, ayúdanos a solucionarlo:

### Antes de Reportar
1. **Busca en [Issues existentes](https://github.com/v8paulofelix/ScanFolder/issues)** para evitar duplicados
2. **Actualiza** a la última versión para confirmar que el bug persiste
3. **Reproduce** el error de manera consistente

### Cómo Reportar
1. Ve a [GitHub Issues](https://github.com/v8paulofelix/ScanFolder/issues/new)
2. Selecciona **"Bug Report"**
3. Completa la plantilla con:

```markdown
**Descripción del Bug**
Descripción clara y concisa del problema.

**Pasos para Reproducir**
1. Ve a '...'
2. Haz clic en '...'
3. Desplázate hacia abajo '...'
4. Ve el error

**Comportamiento Esperado**
Qué esperabas que pasara.

**Capturas de Pantalla**
Si es aplicable, adjunta capturas de pantalla.

**Entorno**
- OS: [ej. Windows 11, Ubuntu 22.04]
- Python: [ej. 3.11.2]
- Navegador: [ej. Chrome 118]
- Versión ScanFolder: [ej. 1.0.0]

**Logs/Errores**
```
Pega aquí cualquier mensaje de error o logs relevantes
```
```

## 💡 Sugerir una Mejora

¿Tienes una idea para hacer ScanFolder aún mejor?

### Tipos de Mejoras
- **Nuevas características** (ej: soporte para filtros avanzados)
- **Mejoras de UI/UX** (ej: mejor visualización de resultados)
- **Optimizaciones de rendimiento** (ej: búsquedas más rápidas)
- **Mejoras de documentación** (ej: tutoriales, ejemplos)

### Proceso
1. **Revisa el [Roadmap](README.md#roadmap)** para ver si ya está planeado
2. **Abre un [Feature Request](https://github.com/v8paulofelix/ScanFolder/issues/new)**
3. Describe:
   - **Problema que resuelve** tu sugerencia
   - **Solución propuesta** con detalles técnicos
   - **Alternativas consideradas**
   - **Beneficios** para los usuarios

## 🔧 Contribuir con Código

### Configuración del Entorno de Desarrollo

1. **Fork** el repositorio en GitHub
2. **Clona** tu fork:
   ```bash
   git clone https://github.com/TU_USUARIO/ScanFolder.git
   cd ScanFolder
   ```
3. **Configura el remoto original**:
   ```bash
   git remote add upstream https://github.com/v8paulofelix/ScanFolder.git
   ```
4. **Crea entorno virtual**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```
5. **Instala dependencias de desarrollo**:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov black flake8 mypy
   ```

### Flujo de Trabajo (Workflow)

1. **Sincroniza** con la rama principal:
   ```bash
   git checkout main
   git pull upstream main
   ```

2. **Crea una rama** para tu feature:
   ```bash
   git checkout -b feature/mi-nueva-caracteristica
   # o
   git checkout -b fix/correccion-bug
   ```

3. **Desarrolla** tu código siguiendo los [estándares](#-estándares-de-código)

4. **Ejecuta pruebas** localmente:
   ```bash
   python -m pytest
   black . --check
   flake8 .
   ```

5. **Commit** con mensajes descriptivos:
   ```bash
   git add .
   git commit -m "feat: agregar filtro de búsqueda por fecha
   
   - Implementa filtrado por rango de fechas en búsquedas
   - Agrega interfaz de calendario en el frontend  
   - Incluye validación de fechas en el backend
   
   Closes #123"
   ```

6. **Push** a tu fork:
   ```bash
   git push origin feature/mi-nueva-caracteristica
   ```

7. **Abre Pull Request** en GitHub con:
   - **Título descriptivo**
   - **Descripción detallada** del cambio
   - **Referencias a issues** relacionados
   - **Screenshots** si hay cambios visuales

### Tipos de Commits

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` Nueva característica
- `fix:` Corrección de bug  
- `docs:` Solo cambios en documentación
- `style:` Cambios de formato (espacios, punto y coma, etc)
- `refactor:` Cambio de código que no corrige bug ni agrega característica
- `perf:` Cambio que mejora rendimiento
- `test:` Agregar o corregir pruebas
- `chore:` Cambios en el proceso de build o herramientas auxiliares

## 📝 Estándares de Código

### Python (PEP 8)

- **Longitud de línea**: Máximo 88 caracteres (Black default)
- **Indentación**: 4 espacios (nunca tabs)
- **Imports**: Agrupados y ordenados (isort)
- **Nombres**:
  - Variables y funciones: `snake_case`
  - Clases: `PascalCase`
  - Constantes: `UPPER_CASE`

### Docstrings

Usa formato Google Style para funciones públicas:

```python
def scan_directory(path: str, recursive: bool = True) -> List[str]:
    """Escanea un directorio y retorna lista de subdirectorios.
    
    Args:
        path: Ruta del directorio a escanear
        recursive: Si debe escanear subdirectorios recursivamente
        
    Returns:
        Lista de rutas de directorios encontrados
        
    Raises:
        FileNotFoundError: Si la ruta no existe
        PermissionError: Si no hay permisos de lectura
    """
```

### Herramientas de Calidad

Ejecuta antes de cada commit:

```bash
# Formatear código
black . --line-length 88

# Verificar estilo
flake8 . --max-line-length=88

# Verificar tipos (opcional pero recomendado)
mypy app.py storage.py

# Ordenar imports
isort .
```

## 🧪 Pruebas

### Ejecutar Pruebas

```bash
# Todas las pruebas
python -m pytest

# Con cobertura
python -m pytest --cov=. --cov-report=html

# Pruebas específicas
python -m pytest tests/test_storage.py
```

### Escribir Pruebas

- **Ubicación**: Carpeta `tests/`
- **Nomenclatura**: `test_*.py`
- **Cobertura**: Mínimo 80% para nuevas características

```python
def test_add_scan_success():
    """Test que verifica que se puede agregar un escaneo exitosamente."""
    storage = ScanStorage(":memory:")
    result = storage.add_scan("TEST-123", "Test Drive", "C:\\", ["C:\\Test"])
    assert result is True
```

## 📚 Documentación

### Cambios que Requieren Documentación
- Nuevas características
- Cambios en la API
- Nuevos parámetros de configuración
- Modificaciones en la instalación

### Actualizar Documentación
- **README.md**: Características principales y guía de uso
- **Docstrings**: Funciones y clases públicas
- **CHANGELOG.md**: Historial de cambios (se actualiza automáticamente)

## ❓ ¿Necesitas Ayuda?

- 💬 **Discusiones**: [GitHub Discussions](https://github.com/v8paulofelix/ScanFolder/discussions)
- 🐛 **Issues**: [GitHub Issues](https://github.com/v8paulofelix/ScanFolder/issues)
- 📧 **Email**: Contacta al mantenedor directamente

## 🎉 Reconocimiento

Todos los contribuidores son reconocidos en:
- **README.md** - Sección de contribuidores
- **CONTRIBUTORS.md** - Lista detallada
- **Releases** - Notas de lanzamiento

---

**¡Gracias por contribuir a ScanFolder!** 🙏 Cada contribución, sin importar el tamaño, hace que el proyecto sea mejor para todos.
