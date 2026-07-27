import time
import os
import sys
import shutil
import datetime
import zipfile
import re
import io
import openpyxl
import psycopg2
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from account_runner import load_survias_accounts, run_accounts

# Cargar variables de entorno del archivo .env local
load_dotenv()

# Cargar credenciales y configuración desde .env
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Astaroth312@localhost:5432/LocalNarbus")

def clean_directory(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory)

def wait_for_download(download_dir, timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        files = os.listdir(download_dir)
        valid_files = [f for f in files if not f.endswith('.crdownload') and not f.endswith('.tmp')]
        if valid_files:
            return os.path.join(download_dir, valid_files[0])
        time.sleep(1)
    return None

def save_excel_to_postgres(file_path, db_url):
    print(f"Leyendo archivo Excel para importar: {file_path}")
    
    # Solución al error de openpyxl con los márgenes de página en el XML
    with zipfile.ZipFile(file_path) as z_in:
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, 'w') as z_out:
            for item in z_in.infolist():
                content = z_in.read(item.filename)
                if 'worksheets/sheet' in item.filename:
                    content_str = content.decode('utf-8')
                    content_str = re.sub(r'<pageMargins[^>]*/>', '', content_str)
                    z_out.writestr(item.filename, content_str.encode('utf-8'))
                else:
                    z_out.writestr(item.filename, content)
        mem.seek(0)

    # Cargar workbook desde el buffer en memoria
    wb = openpyxl.load_workbook(mem)
    ws = wb.active

    # Conectar a Postgres
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        # Asegurar la creación del esquema raw y la tabla pasajes_survias
        cur.execute("CREATE SCHEMA IF NOT EXISTS raw;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw.pasajes_survias (
                id SERIAL PRIMARY KEY,
                patente VARCHAR(50) NOT NULL,
                fecha VARCHAR(50) NOT NULL,
                hora TIME NOT NULL,
                punto_cobro VARCHAR(150) NOT NULL,
                categoria VARCHAR(100),
                monto NUMERIC(10, 2),
                fecha_importacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_transito UNIQUE (patente, fecha, hora, punto_cobro)
            );
        """)
        conn.commit()

        row_count = 0
        inserted_count = 0
        
        # Leer filas (omitiendo la cabecera en fila 1)
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
                
            patente = str(row[0]).strip()
            fecha_str = str(row[1]).strip()
            hora_str = str(row[2]).strip()
            punto_cobro = str(row[3]).strip()
            categoria = str(row[4]).strip() if row[4] is not None else None
            monto = float(row[5]) if row[5] is not None else 0.0

            # Parsear hora (HH:MM)
            hora = datetime.datetime.strptime(hora_str, "%H:%M").time()

            # Insertar en base de datos previniendo duplicados
            cur.execute("""
                INSERT INTO raw.pasajes_survias (patente, fecha, hora, punto_cobro, categoria, monto)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (patente, fecha, hora, punto_cobro) DO NOTHING;
            """, (patente, fecha_str, hora, punto_cobro, categoria, monto))
            
            row_count += 1
            if cur.rowcount > 0:
                inserted_count += 1

        conn.commit()
        print(f"Importación completa de {os.path.basename(file_path)}. Filas procesadas: {row_count}. Nuevas: {inserted_count}.")
        return row_count, inserted_count

    except Exception as ex:
        conn.rollback()
        print(f"Error al importar archivo {file_path} a Postgres: {ex}")
        raise ex
    finally:
        cur.close()
        conn.close()

def scrape_survias_transitos(rut, password):
    base_dir = os.getcwd()
    temp_download_dir = os.path.join(base_dir, "temp_downloads")
    final_download_dir = os.path.join(base_dir, "downloads")
    
    print(f"Limpiando directorio temporal de descargas: {temp_download_dir}")
    clean_directory(temp_download_dir)

    chrome_options = Options()
    # chrome_options.add_argument("--headless=new") # Descomentar para modo headless en producción/servidor
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1280,800")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    prefs = {
        "download.default_directory": temp_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    print("Iniciando navegador Chrome...")
    driver = webdriver.Chrome(options=chrome_options)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    try:
        wait = WebDriverWait(driver, 15)

        # 1. Ingresar a la página principal de Survías
        print("Cargando landing page: https://www.survias.cl/...")
        driver.get("https://www.survias.cl/")
        
        # 2. Hacer clic en "Oficina virtual"
        print("Buscando el botón 'Oficina virtual'...")
        xpath_oficina_virtual = "//span[contains(@class, 'elementor-button-text') and (translate(text(), 'Ó','o') = 'Oficina virtual' or contains(text(), 'Oficina virtual'))]"
        oficina_virtual_btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_oficina_virtual)))
        
        print("Haciendo clic en el botón 'Oficina virtual'...")
        oficina_virtual_btn.click()
        
        # 3. Esperar a cambiar de pestaña
        time.sleep(2)
        handles = driver.window_handles
        if len(handles) > 1:
            driver.switch_to.window(handles[-1])
            print("Cambiando al foco de la nueva pestaña de la Oficina Virtual...")

        # Esperar a que cargue el formulario de login
        print("Esperando la carga del formulario de login (#auth_home)...")
        rut_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#auth_home #rut_login")))
        password_input = driver.find_element(By.CSS_SELECTOR, "#auth_home #password")

        # Habilitar campos de entrada
        driver.execute_script("document.querySelector('#auth_home #rut_login').removeAttribute('disabled');")
        driver.execute_script("document.querySelector('#auth_home #password').removeAttribute('disabled');")
        time.sleep(1)

        # Rellenar credenciales
        print(f"Ingresando credenciales... RUT: {rut}")
        rut_input.clear()
        rut_input.send_keys(rut)
        password_input.clear()
        password_input.send_keys(password)
        time.sleep(1)

        # Enviar formulario de login
        print("Enviando formulario de login...")
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, "#auth_home button[type='submit']")
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
            time.sleep(0.5)
            submit_btn.click()
        except Exception as e_click:
            print(f"Click tradicional falló ({e_click}). Intentando envío mediante JavaScript...")
            driver.execute_script("document.querySelector('#auth_home').submit();")

        # 4. Esperar login exitoso
        print("Esperando verificación de inicio de sesión exitoso...")
        time.sleep(5)
        
        # Verificar alertas
        alerts = driver.find_elements(By.CLASS_NAME, "alert")
        if alerts:
            for alert in alerts:
                if alert.is_displayed():
                    print(f"Error detectado en el sitio: {alert.text}")
                    return False

        dashboard_detected = False
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Cerrar sesión') or contains(text(), 'Cerrar Sesión') or contains(@href, 'logout')]")))
            dashboard_detected = True
        except:
            if "detalle-transitos" in driver.page_source or "transitos" in driver.current_url:
                dashboard_detected = True

        if not dashboard_detected:
            inputs = driver.find_elements(By.CSS_SELECTOR, "#auth_home #rut_login")
            if inputs and inputs[0].is_displayed():
                print("El inicio de sesión falló.")
                return False
        
        print("¡Login completado con éxito!")

        # 5. Navegar a Tránsitos para identificar los convenios disponibles
        transitos_url = "https://oficina-virtual.survias.cl/oficina-virtual/detalle-transitos"
        print(f"Navegando a la sección de Tránsitos: {transitos_url}...")
        driver.get(transitos_url)
        wait.until(EC.presence_of_element_located((By.ID, "cambio_convenio")))

        # Obtener los convenios disponibles en el dropdown lateral
        convenio_select_element = driver.find_element(By.ID, "cambio_convenio")
        select_convenio = Select(convenio_select_element)
        convenios = [opt.get_attribute("value") for opt in select_convenio.options if opt.get_attribute("value")]
        print(f"Convenios detectados en la cuenta: {convenios}")

        downloaded_files = []

        # Bucle principal por cada convenio
        for c_idx, convenio in enumerate(convenios, 1):
            print(f"\n==================================================")
            print(f" PROCESANDO CONVENIO [{c_idx}/{len(convenios)}]: {convenio}")
            print(f"==================================================")
            
            # Volver a cargar selector de convenio
            convenio_select_element = driver.find_element(By.ID, "cambio_convenio")
            select_convenio = Select(convenio_select_element)
            current_selected = select_convenio.first_selected_option.get_attribute("value")
            
            # Si el convenio de la iteración no es el seleccionado actualmente, cambiamos de convenio
            if current_selected != convenio:
                print(f"Cambiando al convenio {convenio}...")
                select_convenio.select_by_value(convenio)
                time.sleep(0.5)
                # Enviar formulario de cambio de convenio
                driver.execute_script("document.getElementById('cambio_convenio_form').submit();")
                # Esperar redirección y recarga de página
                time.sleep(5)
                # Volver a ir a la URL de tránsitos (Laravel puede redirigir al resumen por defecto)
                driver.get(transitos_url)
                wait.until(EC.presence_of_element_located((By.ID, "tipo_transito")))

            # 6. Seleccionar "FACTURADO" en Tipo de tránsitos
            print("Seleccionando tipo de tránsito: FACTURADO...")
            tipo_transito_select = Select(driver.find_element(By.ID, "tipo_transito"))
            tipo_transito_select.select_by_value("FACTURADO")

            # Calcular fechas: del mes actual hasta el día anterior (d-1)
            today = datetime.date.today()
            yesterday = today - datetime.timedelta(days=1)
            start_of_period = yesterday.replace(day=1)
            fecha_desde = start_of_period.strftime('%d-%m-%Y')
            fecha_hasta = yesterday.strftime('%d-%m-%Y')
            fecha_hoy_str = today.strftime('%Y-%m-%d')

            print(f"Configurando rango de fechas: Desde {fecha_desde} hasta {fecha_hasta} (d-1)...")
            driver.execute_script("document.getElementById('transito_desde').removeAttribute('readonly');")
            driver.execute_script("document.getElementById('transito_hasta').removeAttribute('readonly');")
            driver.execute_script(f"document.getElementById('transito_desde').value = '{fecha_desde}';")
            driver.execute_script(f"document.getElementById('transito_hasta').value = '{fecha_hasta}';")

            # 7. Obtener todas las patentes de la lista del convenio actual
            patente_select_element = driver.find_element(By.ID, "patente_vehiculo")
            select_patente = Select(patente_select_element)
            patentes = [opt.get_attribute("value") for opt in select_patente.options if opt.get_attribute("value")]
            
            print(f"Se encontraron {len(patentes)} patentes en este convenio: {patentes}")

            # 8. Bucle para procesar cada patente del convenio actual
            for idx, patente in enumerate(patentes, 1):
                print(f"\n[{idx}/{len(patentes)}] Procesando patente: {patente} (Convenio: {convenio})...")
                
                select_patente.select_by_value(patente)
                time.sleep(0.5)

                # Hacer clic en Consultar
                print(f"Consultando tránsitos para patente {patente}...")
                consultar_btn = driver.find_element(By.XPATH, "//button[text()='Consultar']")
                driver.execute_script("arguments[0].scrollIntoView(true);", consultar_btn)
                time.sleep(0.5)
                consultar_btn.click()

                # Esperar a que cargue la consulta
                time.sleep(3)

                # Buscar botón de descarga de Excel
                download_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Descargar') or .//i[contains(@class, 'fa-file-excel')]]")
                
                if download_buttons:
                    download_btn = download_buttons[0]
                    print(f"Botón de descarga encontrado para patente {patente}. Iniciando descarga...")
                    
                    # Limpiar temporal
                    clean_directory(temp_download_dir)
                    
                    # Clic descarga
                    driver.execute_script("arguments[0].scrollIntoView(true);", download_btn)
                    time.sleep(0.5)
                    download_btn.click()

                    # Esperar descarga
                    downloaded_file_path = wait_for_download(temp_download_dir, timeout=20)
                    
                    if downloaded_file_path:
                        # Crear directorio final: downloads/{patente}/{fecha_hoy}
                        dest_dir = os.path.join(final_download_dir, patente, fecha_hoy_str)
                        if not os.path.exists(dest_dir):
                            os.makedirs(dest_dir)
                        
                        filename = os.path.basename(downloaded_file_path)
                        dest_file_path = os.path.join(dest_dir, filename)
                        
                        # Mover archivo
                        shutil.move(downloaded_file_path, dest_file_path)
                        print(f"¡Descarga exitosa! Guardado en: {dest_file_path}")
                        downloaded_files.append(dest_file_path)
                    else:
                        print(f"[Advertencia] Descarga falló o expiró para la patente {patente}.")
                else:
                    print(f"Sin resultados o botón de descarga ausente para patente {patente}. Omitiendo...")

                # Volver a referenciar el selector de patentes
                patente_select_element = driver.find_element(By.ID, "patente_vehiculo")
                select_patente = Select(patente_select_element)

        print("\n¡Bucle de descargas de todos los convenios completado con éxito!")
        
        # 9. Importar los archivos descargados a Postgres
        if downloaded_files:
            print(f"\nIniciando importación a la base de datos Postgres ({DB_URL})...")
            totales_leidos = 0
            totales_nuevos = 0
            for file_path in downloaded_files:
                try:
                    leidos, nuevos = save_excel_to_postgres(file_path, DB_URL)
                    totales_leidos += leidos
                    totales_nuevos += nuevos
                except Exception as ex_import:
                    print(f"Error al importar {file_path}: {ex_import}")
            print(f"\n¡Importación completada! Total registros procesados: {totales_leidos}. Nuevos registros agregados: {totales_nuevos}.")
            
            # ELIMINAR LOS ARCHIVOS EXCEL DESCARGADOS DESPUÉS DE GUARDARLOS EN LA BASE DE DATOS
            try:
                print(f"Eliminando directorio de descargas local ({final_download_dir}) para limpieza...")
                shutil.rmtree(final_download_dir)
                print("Directorio de descargas eliminado con éxito.")
            except Exception as e_clean:
                print(f"No se pudo eliminar el directorio de descargas: {e_clean}")
        else:
            print("\nNo se descargaron nuevos reportes en esta ejecución. Nada que importar.")

        return True

    except Exception as e:
        print(f"Ocurrió un error durante la ejecución del script: {e}")
        return False
    finally:
        print("Cerrando navegador...")
        driver.quit()
        if os.path.exists(temp_download_dir):
            shutil.rmtree(temp_download_dir)

if __name__ == "__main__":
    try:
        configured_accounts = load_survias_accounts()
    except ValueError as config_error:
        print(f"Error de configuración: {config_error}")
        sys.exit(1)

    all_accounts_succeeded = run_accounts(
        configured_accounts,
        scrape_survias_transitos,
    )
    sys.exit(0 if all_accounts_succeeded else 1)
