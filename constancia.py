import logging
import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PyPDF2 import PdfMerger
from datetime import datetime

# Configurar logging más detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Muestra logs en consola
        logging.FileHandler('constancia_scraping.log')  # Guarda logs en archivo
    ]
)
logger = logging.getLogger('constancia')

def configure_selenium_driver(output_dir):
    """
    Configura el driver de Selenium con logging detallado
    """
    try:
        logger.info("Iniciando configuración del driver de Selenium")
        
        # Configurar opciones de Chrome
        chrome_options = webdriver.ChromeOptions()
        
        # Configuraciones para Streamlit Cloud
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--headless')
        
        # Preferencias de descarga
        prefs = {
            'download.default_directory': output_dir,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'plugins.always_open_pdf_externally': True
        }
        chrome_options.add_experimental_option('prefs', prefs)

        # Inicializar el driver
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=chrome_options
        )
        
        logger.info("Driver de Selenium configurado exitosamente")
        return driver
    
    except Exception as e:
        logger.error(f"Error al configurar el driver de Selenium: {e}", exc_info=True)
        return None

def download_rnp_certificate(ruc, output_dir, driver):
    """
    Descarga el certificado RNP con logging detallado
    """
    try:
        logger.info(f"Iniciando descarga de certificado RNP para RUC: {ruc}")
        
        # Navegar a la página del certificado RNP con el RUC
        url = f"https://www.rnp.gob.pe/Constancia/RNP_Constancia/default_Todos.asp?RUC={ruc}"
        driver.get(url)
        logger.debug(f"URL de RNP accedida: {url}")
        
        # Esperar alerta si está presente y aceptarla
        try:
            WebDriverWait(driver, 5).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            alert_text = alert.text
            logger.info(f"Alerta detectada: {alert_text}")
            alert.accept()
        except Exception as e:
            logger.debug(f"No hay alerta presente: {e}")
        
        # Esperar a que el botón de imprimir esté presente
        print_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "btnPrint"))
        )
        logger.info("Botón de impresión encontrado")
        
        # Activar impresión (que guardará como PDF con nuestras opciones)
        print_button.click()
        
        # Esperar a que se complete la descarga
        time.sleep(3)
        
        # Verificar archivos descargados
        archivos = os.listdir(output_dir)
        pdf_rnp = [f for f in archivos if 'RNP_' in f and f.endswith('.pdf')]
        
        if pdf_rnp:
            logger.info(f"Certificado RNP descargado: {pdf_rnp[0]}")
            return os.path.join(output_dir, pdf_rnp[0])
        else:
            logger.warning("No se encontró archivo PDF de RNP después de la descarga")
            return None
        
    except Exception as e:
        logger.error(f"Error detallado para RUC {ruc} en RNP: {str(e)}", exc_info=True)
        raise

def download_sunat_ruc_pdf(ruc, output_dir, driver):
    """
    Descarga el PDF de SUNAT con logging detallado
    """
    try:
        logger.info(f"Iniciando descarga de RUC para número: {ruc}")
        
        # Navegar a la página de consulta RUC de SUNAT
        url = 'https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp'
        driver.get(url)
        logger.debug(f"URL de SUNAT accedida: {url}")
        
        # Esperar a que el campo de RUC esté presente
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'txtRuc'))
        )
        
        # Asegurarse de que la opción "Por RUC" esté seleccionada
        btn_por_ruc = driver.find_element(By.ID, 'btnPorRuc')
        if 'active' not in btn_por_ruc.get_attribute('class'):
            btn_por_ruc.click()
            logger.debug("Seleccionado búsqueda por RUC")
        
        # Ingresar el número de RUC
        txt_ruc = driver.find_element(By.ID, 'txtRuc')
        txt_ruc.clear()
        txt_ruc.send_keys(ruc)
        
        # Hacer clic en el botón "Buscar"
        btn_buscar = driver.find_element(By.ID, 'btnAceptar')
        btn_buscar.click()
        logger.info("Búsqueda de RUC iniciada")
        
        # Esperar a que la página de resultados cargue
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'panel-primary'))
        )
        
        # Hacer clic en el botón "Imprimir"
        btn_imprimir = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@onclick='imprimir()']"))
        )
        btn_imprimir.click()
        logger.info("Botón de impresión RUC clickeado")
        
        # Esperar a que se complete la descarga
        time.sleep(3)
        
        # Verificar archivos descargados
        archivos = os.listdir(output_dir)
        pdf_ruc = [f for f in archivos if 'SUNAT_' in f and f.endswith('.pdf')]
        
        if pdf_ruc:
            logger.info(f"Certificado RUC descargado: {pdf_ruc[0]}")
            return os.path.join(output_dir, pdf_ruc[0])
        else:
            logger.warning("No se encontró archivo PDF de RUC después de la descarga")
            return None
        
    except Exception as e:
        logger.error(f"Error detallado para RUC {ruc} en SUNAT: {str(e)}", exc_info=True)
        raise
def download_rnssc_pdf(dni, output_directory):
    """
    Descarga el PDF de RNSSC utilizando la URL REST con logging detallado.
    """
    try:
        logger.info(f"Iniciando descarga de RNSSC para DNI: {dni}")
        
        # Obtener la fecha y hora actual en el formato requerido
        now = datetime.now()
        fecha_hora = now.strftime("%d-%m-%Y %H:%M:%S")
        logger.debug(f"Fecha y hora de solicitud: {fecha_hora}")
        
        # Construir la URL de descarga
        url = f"https://www.sanciones.gob.pe/rnssc-rest/rest/sancion/descargar/Usuario%20consulta/NINGUNO/NINGUNO/NINGUNO/DOCUMENTO%20NACIONAL%20DE IDENTIDAD/{dni}/{fecha_hora}"
        logger.debug(f"URL de descarga RNSSC: {url}")
        
        # Realizar la solicitud GET
        response = requests.get(url, timeout=30)
        logger.info(f"Código de respuesta HTTP: {response.status_code}")
        
        # Verificar si la solicitud fue exitosa
        if response.status_code == 200:
            # Definir el nombre del archivo siguiendo el patrón
            # Extraer sancionID del contenido si es posible, o generar uno
            sancion_id = f"{int(time.time() * 1000)}"  # Ejemplo de ID basado en timestamp
            filename = f"ConsultaSinResultados_sancionID{sancion_id}.pdf"
            filepath = os.path.join(output_directory, filename)
            
            # Guardar el contenido PDF
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            # Verificar el tamaño del archivo descargado
            file_size = os.path.getsize(filepath)
            logger.info(f"RNSSC descargado exitosamente para DNI {dni} en {filepath}")
            logger.debug(f"Tamaño del archivo: {file_size} bytes")
            
            return filepath
        else:
            logger.error(f"Error al descargar RNSSC para DNI {dni}. Estado HTTP: {response.status_code}")
            logger.debug(f"Contenido de la respuesta: {response.text}")
            return None
    
    except requests.exceptions.RequestException as req_error:
        logger.error(f"Error de red al descargar RNSSC para DNI {dni}: {str(req_error)}", exc_info=True)
        return None
    
    except Exception as e:
        logger.error(f"Error al descargar RNSSC para DNI {dni}: {str(e)}", exc_info=True)
        return None

def combinar_pdfs(output_directory, output_filename):
    """
    Combina los archivos PDF en un solo PDF y elimina los archivos temporales.
    """
    logger = logging.getLogger('constancia')
    
    # Esperar unos segundos para asegurarse de que los archivos hayan sido generados
    time.sleep(5)

    # Obtener la lista de archivos PDF en el directorio de salida
    pdf_files = os.listdir(output_directory)
    pdf_files = [f for f in pdf_files if f.endswith('.pdf')]
    
    logger.debug(f"Archivos PDF encontrados: {pdf_files}")
    
    # Identificar los archivos PDF individuales
    pdf_rnp = None
    pdf_ruc = None
    pdf_rnssc = None

    for filename in pdf_files:
        logger.debug(f"Analizando archivo: {filename}")
        if 'CONSTANCIA DEL RNP' in filename or 'RNP_' in filename:
            pdf_rnp = os.path.join(output_directory, filename)
            logger.info(f"PDF RNP encontrado: {filename}")
        elif 'SUNAT - Consulta RUC' in filename or 'SUNAT_' in filename:
            pdf_ruc = os.path.join(output_directory, filename)
            logger.info(f"PDF RUC encontrado: {filename}")
        elif 'ConsultaSinResultados_sancionID' in filename:
            pdf_rnssc = os.path.join(output_directory, filename)
            logger.info(f"PDF RNSSC encontrado: {filename}")
    
    # Verificar que se encontraron todos los PDFs
    pdf_list = []
    if pdf_rnp:
        pdf_list.append(pdf_rnp)
    else:
        logger.warning("No se encontró el PDF de RNP.")
    
    if pdf_ruc:
        pdf_list.append(pdf_ruc)
    else:
        logger.warning("No se encontró el PDF de RUC.")
    
    if pdf_rnssc:
        pdf_list.append(pdf_rnssc)
    else:
        logger.warning("No se encontró el PDF de RNSSC.")
    
    # Ruta del PDF combinado de salida
    output_pdf = os.path.join(output_directory, output_filename)
    
    # Combinar los PDFs
    if pdf_list:
        try:
            merger = PdfMerger()
            for pdf in pdf_list:
                logger.debug(f"Agregando PDF a la combinación: {pdf}")
                merger.append(pdf)
            
            merger.write(output_pdf)
            merger.close()
            
            logger.info(f"PDF combinado guardado como {output_pdf}")
            
            # Eliminar los archivos PDF temporales
            for pdf in pdf_list:
                try:
                    os.remove(pdf)
                    logger.info(f"Archivo temporal eliminado: {pdf}")
                except Exception as e:
                    logger.error(f"Error al eliminar el archivo {pdf}: {str(e)}")
        
        except Exception as e:
        logger = logging.getLogger('constancia')
        logger.error(f"Error al combinar PDFs: {e}")
        import traceback
        logger.error(traceback.format_exc())
    else:
        logger.warning("No hay PDFs para combinar.")

def descargar_constancias(ruc, dni, output_dir):
    """
    Función principal para descargar constancias RNP, RUC y RNSSC
    """
    # Configurar logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('constancia')
    
    try:
        # Crear directorio de salida si no existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Configurar driver
        driver = configure_selenium_driver(output_dir)
        
        if not driver:
            logger.error("No se pudo configurar el driver de Selenium")
            return None
        
        try:
            # 1. Descargar RNP
            logger.info("Descargando constancia RNP...")
            download_rnp_certificate(ruc, output_dir, driver)
            
            # 2. Descargar RUC SUNAT
            logger.info("Descargando constancia RUC...")
            download_sunat_ruc_pdf(ruc, output_dir, driver)
            
            # 3. Descargar RNSSC
            logger.info("Descargando constancia RNSSC...")
            download_rnssc_pdf(dni, output_dir)
            
            # 4. Combinar PDFs
            logger.info("Combinando PDFs...")
            output_filename = '5. RNP, RUC, RNSSC.pdf'
            combinar_pdfs(output_dir, output_filename)
            
            logger.info("Proceso de descarga completado exitosamente")
            
            # Devolver la ruta del PDF combinado
            return os.path.join(output_dir, output_filename)
        
        finally:
            # Cerrar el driver
            if driver:
                driver.quit()
    
    except Exception as e:
        logger.error(f"Error en la descarga de constancias: {e}")
        return None

# Configuración adicional para manejar el registro
def setup_logging():
    """
    Configuración avanzada de logging
    """
    # Configurar un formateador más detallado
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configurar manejador de consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Configurar manejador de archivo
    file_handler = logging.FileHandler('constancia_scraping_full.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Configurar el logger principal
    logger = logging.getLogger('constancia')
    logger.setLevel(logging.DEBUG)
    
    # Limpiar cualquier manejador existente
    logger.handlers.clear()
    
    # Agregar los nuevos manejadores
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# Método para agregar un método de éxito personalizado
def add_success_method():
    """
    Agrega un método de registro de éxito personalizado
    """
    def success(self, message, *args, **kwargs):
        return self.log(logging.INFO, f"✅ SUCCESS: {message}", *args, **kwargs)
    
    logging.Logger.success = success

# Configuración inicial
setup_logging()
add_success_method()
