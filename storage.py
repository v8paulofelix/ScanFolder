"""
Módulo de gestión de almacenamiento para ScanFolder
==================================================

Este módulo maneja toda la persistencia de datos utilizando SQLite en lugar de archivos JSON.
Proporciona una interfaz limpia para almacenar y consultar información sobre escaneos de discos
y directorios encontrados.

Arquitectura de la Base de Datos:
    - scans: Información de cada disco escaneado (metadatos)
    - directories: Rutas de directorios encontrados en cada escaneo
    - Relación 1:N con claves foráneas y CASCADE para integridad

Características:
    - Transacciones ACID para consistencia de datos
    - Índices optimizados para búsquedas rápidas
    - Soporte para operaciones CRUD completas
    - Logging completo para debugging y monitoreo
    - Patrón Singleton para gestión de instancias

Autor: Paulo Felix
Versión: 1.0.0
Licencia: MIT
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ruta de la base de datos
DB_PATH = 'scandata.db'


class ScanStorage:
    """
    Clase principal para manejar el almacenamiento de datos de escaneos.
    Encapsula todas las operaciones de base de datos y proporciona una interfaz limpia.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        """
        Inicializa la conexión a la base de datos.
        
        Args:
            db_path (str): Ruta al archivo de base de datos SQLite
        """
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """
        Inicializa la base de datos creando las tablas necesarias si no existen.
        
        Esquema de tablas:
        - scans: Almacena información de cada disco escaneado
          * id: Clave primaria autoincremental
          * serial_number: Número de serie único del volumen
          * volume_name: Nombre del volumen del disco
          * drive_path: Ruta de la unidad escaneada (ej: C:\\, D:\\)
          * scan_date: Fecha y hora del escaneo
          * total_directories: Número total de directorios encontrados
        
        - directories: Almacena cada ruta de directorio encontrada
          * id: Clave primaria autoincremental
          * scan_id: Clave foránea que referencia scans.id
          * directory_path: Ruta completa del directorio
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Habilitar claves foráneas
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Tabla para almacenar información de escaneos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    serial_number TEXT NOT NULL UNIQUE,
                    volume_name TEXT,
                    drive_path TEXT NOT NULL,
                    scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_directories INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla para almacenar directorios encontrados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS directories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER NOT NULL,
                    directory_path TEXT NOT NULL,
                    FOREIGN KEY (scan_id) REFERENCES scans (id) ON DELETE CASCADE
                )
            """)
            
            # Crear índices para mejorar el rendimiento de las búsquedas
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_serial_number 
                ON scans (serial_number)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scan_id 
                ON directories (scan_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_directory_path 
                ON directories (directory_path)
            """)
            
            conn.commit()
            conn.close()
            logger.info("Base de datos inicializada correctamente")
            
        except sqlite3.Error as e:
            logger.error(f"Error al inicializar la base de datos: {e}")
            if 'conn' in locals():
                conn.close()
            raise
    
    def add_scan(self, serial_number: str, volume_name: str, drive_path: str, 
                 directories: List[str]) -> bool:
        """
        Añade un nuevo escaneo a la base de datos junto con todos sus directorios.
        
        Args:
            serial_number (str): Número de serie único del volumen
            volume_name (str): Nombre del volumen del disco
            drive_path (str): Ruta de la unidad escaneada
            directories (List[str]): Lista de rutas de directorios encontrados
        
        Returns:
            bool: True si el escaneo se guardó correctamente, False en caso contrario
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Verificar si ya existe un escaneo con este número de serie
                cursor.execute("""
                    SELECT id FROM scans WHERE serial_number = ?
                """, (serial_number,))
                
                existing_scan = cursor.fetchone()
                
                if existing_scan:
                    # Actualizar escaneo existente
                    scan_id = existing_scan[0]
                    
                    # Eliminar directorios antiguos
                    cursor.execute("""
                        DELETE FROM directories WHERE scan_id = ?
                    """, (scan_id,))
                    
                    # Actualizar información del escaneo
                    cursor.execute("""
                        UPDATE scans 
                        SET volume_name = ?, drive_path = ?, scan_date = ?, 
                            total_directories = ?
                        WHERE id = ?
                    """, (volume_name, drive_path, datetime.now(), 
                          len(directories), scan_id))
                    
                    logger.info(f"Escaneo actualizado para el disco {serial_number}")
                    
                else:
                    # Crear nuevo escaneo
                    cursor.execute("""
                        INSERT INTO scans (serial_number, volume_name, drive_path, 
                                         scan_date, total_directories)
                        VALUES (?, ?, ?, ?, ?)
                    """, (serial_number, volume_name, drive_path, 
                          datetime.now(), len(directories)))
                    
                    scan_id = cursor.lastrowid
                    logger.info(f"Nuevo escaneo creado para el disco {serial_number}")
                
                # Insertar todos los directorios
                directory_data = [(scan_id, directory) for directory in directories]
                cursor.executemany("""
                    INSERT INTO directories (scan_id, directory_path)
                    VALUES (?, ?)
                """, directory_data)
                
                conn.commit()
                logger.info(f"Se guardaron {len(directories)} directorios para el escaneo {scan_id}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error al guardar el escaneo: {e}")
            return False
    
    def get_scan_history(self) -> List[Dict]:
        """
        Obtiene el historial completo de escaneos realizados.
        
        Returns:
            List[Dict]: Lista de diccionarios con información de cada escaneo
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, serial_number, volume_name, drive_path, 
                           scan_date, total_directories
                    FROM scans 
                    ORDER BY scan_date DESC
                """)
                
                scans = []
                for row in cursor.fetchall():
                    scan_data = {
                        'id': row[0],
                        'serial_number': row[1],
                        'volume_name': row[2] or 'Desconocido',
                        'drive_path': row[3],
                        'scan_date': row[4],
                        'total_directories': row[5],
                        # Mantener compatibilidad con el formato anterior
                        'catalog_name': row[1],  # usar serial_number como catalog_name
                        'fecha': row[4],
                        'ruta': row[3]
                    }
                    scans.append(scan_data)
                
                logger.info(f"Se encontraron {len(scans)} escaneos en el historial")
                return scans
                
        except sqlite3.Error as e:
            logger.error(f"Error al obtener el historial de escaneos: {e}")
            return []
    
    def search_directories(self, search_term: str) -> List[Dict]:
        """
        Busca directorios que contengan el término especificado en todos los escaneos.
        
        Args:
            search_term (str): Término de búsqueda para filtrar directorios
        
        Returns:
            List[Dict]: Lista de diccionarios con información de directorios encontrados
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Búsqueda case-insensitive usando LIKE con comodines
                search_pattern = f"%{search_term.lower()}%"
                
                cursor.execute("""
                    SELECT s.serial_number, s.volume_name, s.drive_path, 
                           d.directory_path, s.scan_date
                    FROM directories d
                    JOIN scans s ON d.scan_id = s.id
                    WHERE LOWER(d.directory_path) LIKE ?
                    ORDER BY s.volume_name, d.directory_path
                """, (search_pattern,))
                
                results = []
                for row in cursor.fetchall():
                    result_data = {
                        'serial_number': row[0],
                        'volume_name': row[1] or 'Desconocido',
                        'drive_path': row[2],
                        'directory_path': row[3],
                        'scan_date': row[4],
                        # Mantener compatibilidad con el formato anterior
                        'catalog_name': row[0],  # usar serial_number como catalog_name
                        'ruta': row[3]
                    }
                    results.append(result_data)
                
                logger.info(f"Búsqueda '{search_term}': {len(results)} resultados encontrados")
                return results
                
        except sqlite3.Error as e:
            logger.error(f"Error al buscar directorios: {e}")
            return []
    
    def get_scan_by_serial(self, serial_number: str) -> Optional[Dict]:
        """
        Obtiene información de un escaneo específico por su número de serie.
        
        Args:
            serial_number (str): Número de serie del volumen a buscar
        
        Returns:
            Optional[Dict]: Información del escaneo o None si no se encuentra
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, serial_number, volume_name, drive_path, 
                           scan_date, total_directories
                    FROM scans 
                    WHERE serial_number = ?
                """, (serial_number,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'serial_number': row[1],
                        'volume_name': row[2],
                        'drive_path': row[3],
                        'scan_date': row[4],
                        'total_directories': row[5]
                    }
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Error al buscar escaneo por serial {serial_number}: {e}")
            return None
    
    def get_directories_by_scan(self, scan_id: int) -> List[str]:
        """
        Obtiene todos los directorios de un escaneo específico.
        
        Args:
            scan_id (int): ID del escaneo
        
        Returns:
            List[str]: Lista de rutas de directorios
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT directory_path 
                    FROM directories 
                    WHERE scan_id = ?
                    ORDER BY directory_path
                """, (scan_id,))
                
                return [row[0] for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error al obtener directorios del escaneo {scan_id}: {e}")
            return []
    
    def delete_scan(self, serial_number: str) -> bool:
        """
        Elimina un escaneo y todos sus directorios asociados.
        
        Args:
            serial_number (str): Número de serie del volumen a eliminar
        
        Returns:
            bool: True si se eliminó correctamente, False en caso contrario
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Obtener el ID del escaneo
                cursor.execute("""
                    SELECT id FROM scans WHERE serial_number = ?
                """, (serial_number,))
                
                scan_row = cursor.fetchone()
                if not scan_row:
                    logger.warning(f"No se encontró escaneo con serial {serial_number}")
                    return False
                
                scan_id = scan_row[0]
                
                # Eliminar directorios (la clave foránea con CASCADE debería hacer esto automáticamente)
                cursor.execute("""
                    DELETE FROM directories WHERE scan_id = ?
                """, (scan_id,))
                
                # Eliminar el escaneo
                cursor.execute("""
                    DELETE FROM scans WHERE id = ?
                """, (scan_id,))
                
                conn.commit()
                logger.info(f"Escaneo {serial_number} eliminado correctamente")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error al eliminar escaneo {serial_number}: {e}")
            return False
    
    def get_database_stats(self) -> Dict:
        """
        Obtiene estadísticas generales de la base de datos.
        
        Returns:
            Dict: Diccionario con estadísticas de la base de datos
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Contar escaneos totales
                cursor.execute("SELECT COUNT(*) FROM scans")
                total_scans = cursor.fetchone()[0]
                
                # Contar directorios totales
                cursor.execute("SELECT COUNT(*) FROM directories")
                total_directories = cursor.fetchone()[0]
                
                # Obtener el escaneo más reciente
                cursor.execute("""
                    SELECT scan_date FROM scans 
                    ORDER BY scan_date DESC LIMIT 1
                """)
                latest_scan = cursor.fetchone()
                latest_scan_date = latest_scan[0] if latest_scan else None
                
                # Obtener el tamaño del archivo de base de datos
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                return {
                    'total_scans': total_scans,
                    'total_directories': total_directories,
                    'latest_scan_date': latest_scan_date,
                    'database_size_bytes': db_size,
                    'database_size_mb': round(db_size / (1024 * 1024), 2)
                }
                
        except sqlite3.Error as e:
            logger.error(f"Error al obtener estadísticas de la base de datos: {e}")
            return {}


# Instancia global del almacenamiento para mantener compatibilidad con el código existente
_storage = None


def get_storage() -> ScanStorage:
    """
    Obtiene la instancia singleton del almacenamiento.
    
    Returns:
        ScanStorage: Instancia del almacenamiento
    """
    global _storage
    if _storage is None:
        _storage = ScanStorage()
    return _storage


# Funciones de compatibilidad para mantener la interfaz anterior
def init_db():
    """Inicializa la base de datos (función de compatibilidad)"""
    get_storage().init_db()


def save_scan_history(scan_data: Dict) -> bool:
    """
    Guarda un escaneo en el historial (función de compatibilidad).
    
    Args:
        scan_data (Dict): Datos del escaneo con las claves necesarias
    
    Returns:
        bool: True si se guardó correctamente
    """
    storage = get_storage()
    return storage.add_scan(
        serial_number=scan_data.get('catalog_name', ''),
        volume_name=scan_data.get('volume_name', ''),
        drive_path=scan_data.get('ruta', ''),
        directories=scan_data.get('directories', [])
    )


def load_scan_history() -> List[Dict]:
    """
    Carga el historial de escaneos (función de compatibilidad).
    
    Returns:
        List[Dict]: Lista de escaneos
    """
    return get_storage().get_scan_history()


def search_in_catalogs(search_term: str) -> List[Dict]:
    """
    Busca en todos los catálogos (función de compatibilidad).
    
    Args:
        search_term (str): Término de búsqueda
    
    Returns:
        List[Dict]: Resultados de la búsqueda
    """
    return get_storage().search_directories(search_term)


if __name__ == "__main__":
    # Código de prueba para verificar que todo funciona correctamente
    storage = ScanStorage("test_storage.db")  # Base de datos de prueba en archivo
    
    # Datos de prueba
    test_directories = [
        "C:\\Users\\Test\\Documents",
        "C:\\Users\\Test\\Pictures",
        "C:\\Users\\Test\\Videos",
        "C:\\Program Files\\TestApp"
    ]
    
    # Probar añadir escaneo
    success = storage.add_scan(
        serial_number="TEST-1234",
        volume_name="Test Drive",
        drive_path="C:\\",
        directories=test_directories
    )
    
    print(f"Escaneo añadido: {success}")
    
    # Probar búsqueda
    results = storage.search_directories("Test")
    print(f"Resultados de búsqueda: {len(results)}")
    
    # Probar historial
    history = storage.get_scan_history()
    print(f"Escaneos en historial: {len(history)}")
    
    # Mostrar estadísticas
    stats = storage.get_database_stats()
    print(f"Estadísticas: {stats}")
    
    # Limpiar archivo de prueba
    import os
    if os.path.exists("test_storage.db"):
        os.remove("test_storage.db")
        print("Archivo de prueba limpiado")
