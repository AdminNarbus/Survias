# Scraper Autónomo de Tránsitos - Survías

Este es un script autónomo diseñado para automatizar el inicio de sesión en la oficina virtual de Survías, descargar los tránsitos facturados de cada una de las patentes registradas (para el periodo del mes en curso hasta el día anterior, `d-1`) e importarlos a una base de datos PostgreSQL local controlando duplicados.

## Requisitos Previos

1. **Python 3.8+** instalado.
2. **Google Chrome** instalado en el sistema.
3. Base de datos **PostgreSQL** iniciada.

## Estructura de la Carpeta

*   `survias_scraper.py`: El script principal de automatización.
*   `.env`: Archivo de configuración para las credenciales y URL de base de datos.
*   `requirements.txt`: Dependencias requeridas para ejecutar el script.

## Configuración y Ejecución

1. **Crear y activar un entorno virtual (opcional pero recomendado):**
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En Linux/macOS:
   source venv/bin/activate
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verificar el archivo `.env`:**
   Asegúrate de que las credenciales de Survías y la URL de Postgres estén correctas en el archivo `.env`:
   ```env
   SURVIAS_RUT1=RUT_PRIMERA_CUENTA
   SURVIAS_PASSWORD1=CLAVE_PRIMERA_CUENTA

   SURVIAS_RUT2=RUT_SEGUNDA_CUENTA
   SURVIAS_PASSWORD2=CLAVE_SEGUNDA_CUENTA

   DATABASE_URL=postgresql://USUARIO:CLAVE@localhost:5432/BASE_DE_DATOS
   ```

   Puedes agregar más cuentas siguiendo la misma numeración (`RUT3`,
   `PASSWORD3`, etc.). Cada cuenta se procesa en una sesión nueva de Chrome.

4. **Ejecutar el script:**
   ```bash
   python survias_scraper.py
   ```

## Detalles de Operación
* **Descarga local**: Los archivos Excel descargados se guardan localmente en una carpeta autogenerada llamada `downloads/{patente}/{fecha_consulta}/`.
* **Carga en Base de Datos**: El script crea automáticamente la tabla `raw.pasajes_survias`.
* **Control de Duplicados**: Utiliza una restricción única basada en `(patente, fecha, hora, punto_cobro)` con `ON CONFLICT DO NOTHING` para asegurar que el script pueda correr múltiples veces sin duplicar la información.
