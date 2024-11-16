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
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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
        chrome_options.add_argument('--disable-gpu')  # Añadir esta línea
        chrome_options.add_argument('--remote-debugging-port=9222')  # Añadir esta línea
        
        # Preferencias de descarga
        prefs = {
            'download.default_directory': output_dir,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'plugins.always_open_pdf_externally': True,
            'safebrowsing.enabled': True  # Añadir esta línea
        }
        chrome_options.add_experimental_option('prefs', prefs)

        # Usar ChromeDriverManager con manejo de errores
        try:
            driver_path = ChromeDriverManager().install()
        except Exception as e:
            logger.error(f"Error al instalar ChromeDriverManager: {e}")
            driver_path = '/usr/local/bin/chromedriver'  # Ruta predeterminada en algunos entornos

        # Inicializar el driver
        driver = webdriver.Chrome(
            service=Service(driver_path), 
            options=chrome_options
        )
        
        logger.info("Driver de Selenium configurado exitosamente")
        return driver
    
    except Exception as e:
        logger.error(f"Error al configurar el driver de Selenium: {e}", exc_info=True)
        return None

def download_rnp_certificate(ruc, output_dir, driver):
    try:
        logger.info(f"Iniciando descarga de certificado RNP para RUC: {ruc}")
        
        # URL de RNP
        url = f"https://www.rnp.gob.pe/Constancia/RNP_Constancia/default_Todos.asp?RUC={ruc}"
        driver.get(url)
        
        # Esperar y hacer clic en botón de impresión
        print_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "btnPrint"))
        )
        print_button.click()
        
        # Esperar a que se complete la descarga
        time.sleep(3)
        
        # Verificar archivos descargados
        archivos = os.listdir(output_dir)
        pdf_rnp = [f for f in archivos if 'RNP_' in f and f.endswith('.pdf')]
        
        if pdf_rnp:
            logger.warning(f"Certificado RNP descargado: {pdf_rnp[0]}")
            return os.path.join(output_dir, pdf_rnp[0])
        else:
            logger.error("No se encontró archivo PDF de RNP")
            return None
        
    except Exception as e:
        logger.error(f"Error en descarga RNP para RUC {ruc}: {str(e)}")
        raise

def download_sunat_ruc_pdf(ruc, output_dir, driver=None):
    if driver is None:
        driver = configure_selenium_driver(output_dir)
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
        archivos = os.listdir(output_directory)
        pdf_ruc = [f for f in archivos if 'SUNAT_' in f and f.endswith('.pdf')]
        
        if pdf_ruc:
            logger.info(f"Certificado RUC descargado: {pdf_ruc[0]}")
            return os.path.join(output_directory, pdf_ruc[0])
        else:
            logger.warning("No se encontró archivo PDF de RUC después de la descarga")
            return None
    except Exception as e:
        logger.error(f"Error detallado para RUC {ruc} en SUNAT: {str(e)}", exc_info=True)
        raise
def download_rnssc_pdf(dni, output_dir):
    try:
        logger.info(f"Iniciando descarga de RNSSC para DNI: {dni}")
        
        # Configurar headers y session para mejorar la conexión
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/pdf',
            'Connection': 'keep-alive'
        })
        
        # Aumentar timeout y agregar reintentos
        url = f"https://www.sanciones.gob.pe/rnssc-rest/rest/sancion/descargar/Usuario%20consulta/NINGUNO/NINGUNO/NINGUNO/DOCUMENTO%20NACIONAL%20DE IDENTIDAD/{dni}/{fecha_hora}"
        
        # Configurar reintentos
        retries = Retry(
            total=3,  # Número de reintentos
            backoff_factor=0.3,  # Tiempo entre reintentos
            status_forcelist=[500, 502, 503, 504]  # Códigos de error que disparan reintento
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('https://', adapter)
        
        # Realizar solicitud con mayor timeout
        response = session.get(url, timeout=(10, 30))  # (connect timeout, read timeout)
        
        # Verificar si la solicitud fue exitosa
        if response.status_code == 200:
            # Guardar PDF
            filename = f"ConsultaSinResultados_sancionID_{int(time.time())}.pdf"
            filepath = os.path.join(output_directory, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"PDF RNSSC descargado: {filename}")
            return filepath
        else:
            logger.error(f"Error al descargar RNSSC. Código de estado: {response.status_code}")
            return None
    
    except (requests.exceptions.RequestException, IOError) as e:
        logger.error(f"Error de red al descargar RNSSC: {e}")
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
            import traceback
            logger = logging.getLogger('constancia')
            logger.error(f"Error al combinar PDFs: {e}")
            logger.error(traceback.format_exc())
    else:
        logger.warning("No hay PDFs para combinar.")

def descargar_constancias(ruc, dni, output_dir):
    """
    Función principal para descargar constancias RNP, RUC y RNSSC
    """
    # Asegurar permisos de escritura
    os.makedirs(output_dir, exist_ok=True)
    os.chmod(output_dir, 0o777)  # Dar permisos completos
    
    try:
        # Logging más detallado
        logger.info(f"Directorio de descarga: {output_dir}")
        logger.info(f"Contenido inicial del directorio: {os.listdir(output_dir)}")
        
        # Configurar driver
        driver = configure_selenium_driver(output_dir)
        
        if not driver:
            logger.error("No se pudo configurar el driver de Selenium")
            return None
        
        try:
            # 1. Descargar RNP
            logger.info("Descargando constancia RNP...")
            rnp_file = download_rnp_certificate(ruc, output_dir, driver)
            logger.info(f"Archivo RNP: {rnp_file}")
            
            # 2. Descargar RUC SUNAT
            logger.info("Descargando constancia RUC...")
            ruc_file = download_sunat_ruc_pdf(ruc, output_dir, driver)
            logger.info(f"Archivo RUC: {ruc_file}")
            
            # 3. Descargar RNSSC
            logger.info("Descargando constancia RNSSC...")
            rnssc_file = download_rnssc_pdf(dni, output_dir)
            logger.info(f"Archivo RNSSC: {rnssc_file}")
            
            # Logging de archivos encontrados
            logger.info(f"Archivos en directorio después de descargas: {os.listdir(output_dir)}")
            
            # 4. Combinar PDFs
            logger.info("Combinando PDFs...")
            output_filename = '5. RNP, RUC, RNSSC.pdf'
            combinar_pdfs(output_dir, output_filename)
            
            logger.info("Proceso de descarga completado exitosamente")
            
            # Devolver la ruta del PDF combinado
            combined_path = os.path.join(output_dir, output_filename)
            logger.info(f"Ruta del PDF combinado: {combined_path}")
            return combined_path
        
        finally:
            # Cerrar el driver
            if driver:
                driver.quit()
    
    except Exception as e:
        logger.error(f"Error en la descarga de constancias: {e}", exc_info=True)
        return None
