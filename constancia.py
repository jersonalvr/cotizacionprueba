# constancia.py
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

# Configuración de logging minimalista
def setup_logging(debug=False):
    """
    Configurar logging con control de verbosidad
    """
    log_level = logging.DEBUG if debug else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    # Desactivar logs verbosos de librerías externas
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('pyppeteer').setLevel(logging.WARNING)

def log_with_condition(logger, level, message, condition=False):
    """
    Loggea solo si se cumple una condición o en modo debug
    """
    debug_mode = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
    
    if condition or debug_mode:
        if level == 'info':
            logger.info(message)
        elif level == 'warning':
            logger.warning(message)
        elif level == 'error':
            logger.error(message)

def timed_operation(func):
    """
    Decorador para medir tiempo de operaciones
    """
    def wrapper(*args, **kwargs):
        logger = logging.getLogger('performance')
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        # Solo loggeará si tarda más de 5 segundos
        if end_time - start_time > 5:
            logger.warning(f"{func.__name__} tardó {end_time - start_time:.2f} segundos")
        
        return result
    return wrapper

def safe_download(download_func):
    """
    Decorador para manejar errores de descarga
    """
    def wrapper(*args, **kwargs):
        logger = logging.getLogger('download')
        try:
            return download_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error en {download_func.__name__}: {e}")
            return None
    return wrapper

def configure_selenium_driver(output_dir):
    """
    Configuración de driver Selenium optimizada
    """
    logger = logging.getLogger('selenium')
    
    try:
        log_with_condition(logger, 'info', "Configurando driver Selenium")
        
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

        # Inicializar driver con timeout
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=chrome_options
        )
        
        # Configurar timeouts
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        log_with_condition(logger, 'info', "Driver Selenium configurado exitosamente")
        return driver
    
    except Exception as e:
        log_with_condition(logger, 'error', f"Error al configurar Selenium: {e}", condition=True)
        return None

@safe_download
@timed_operation
def download_rnp_certificate(ruc, output_dir, driver):
    """
    Descarga de certificado RNP con manejo de errores
    """
    logger = logging.getLogger('rnp_download')
    
    try:
        log_with_condition(logger, 'info', f"Iniciando descarga RNP para RUC: {ruc}")
        
        url = f"https://www.rnp.gob.pe/Constancia/RNP_Constancia/default_Todos.asp?RUC={ruc}"
        driver.get(url)
        
        # Manejar alertas
        try:
            WebDriverWait(driver, 5).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            log_with_condition(logger, 'info', f"Alerta: {alert.text}")
            alert.accept()
        except:
            pass
        
        # Descargar
        print_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "btnPrint"))
        )
        print_button.click()
        
        time.sleep(3)
        
        # Buscar archivo descargado
        archivos = os.listdir(output_dir)
        pdf_rnp = [f for f in archivos if 'RNP_' in f and f.endswith('.pdf')]
        
        return os.path.join(output_dir, pdf_rnp[0]) if pdf_rnp else None
    
    except Exception as e:
        log_with_condition(logger, 'error', f"Error en descarga RNP: {e}", condition=True)
        return None

def download_sunat_ruc_pdf(ruc, output_dir, driver):
    """
    Descarga de PDF de RUC SUNAT
    """
    logger = logging.getLogger('sunat_download')
    
    try:
        log_with_condition(logger, 'info', f"Iniciando descarga RUC para: {ruc}")
        
        url = 'https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp'
        driver.get(url)
        
        # Llenar formulario y buscar
        txt_ruc = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'txtRuc'))
        )
        txt_ruc.clear()
        txt_ruc.send_keys(ruc)
        
        btn_buscar = driver.find_element(By.ID, 'btnAceptar')
        btn_buscar.click()
        
        # Esperar resultados
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'panel-primary'))
        )
        
        # Imprimir
        btn_imprimir = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@onclick='imprimir()']"))
        )
        btn_imprimir.click()
        
        time.sleep(3)
        
        # Buscar archivo descargado
        archivos = os.listdir(output_dir)
        pdf_ruc = [f for f in archivos if 'SUNAT_' in f and f.endswith('.pdf')]
        
        return os.path.join(output_dir, pdf_ruc[0]) if pdf_ruc else None
    
    except Exception as e:
        log_with_condition(logger, 'error', f"Error en descarga RUC: {e}", condition=True)
        return None

def download_rnssc_pdf(dni, output_dir):
    """
    Descarga de PDF de RNSSC
    """
    logger = logging.getLogger('rnssc_download')
    
    try:
        log_with_condition(logger, 'info', f"Iniciando descarga RNSSC para DNI: {dni}")
        
        # Obtener fecha actual
        now = datetime.now()
        fecha_hora = now.strftime("%d-%m-%Y %H:%M:%S")
        
        # URL de descarga
        url = f"https://www.sanciones.gob.pe/rnssc-rest/rest/sancion/descargar/Usuario%20consulta/NINGUNO/NINGUNO/NINGUNO/DOCUMENTO%20NACIONAL%20DE IDENTIDAD/{dni}/{fecha_hora}"
        
        # Realizar solicitud
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            # Generar nombre de archivo
            filename = f"ConsultaSinResultados_sancionID{int(time.time() * 1000)}.pdf"
            filepath = os.path.join(output_dir, filename)
            
            # Guardar PDF
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            log_with_condition(logger, 'info', f"RNSSC descargado: {filepath}")
            return filepath
        else:
            log_with_condition(logger, 'error', f"Error en descarga RNSSC. Estado: {response.status_code}", condition=True)
            return None
    
    except Exception as e:
        log_with_condition(logger, 'error', f"Error en descarga RNSSC: {e}", condition=True)
        return None
        
def combinar_pdfs(output_directory, output_filename):
    """
    Combinación de PDFs con logging mínimo
    """
    logger = logging.getLogger('pdf_merger')
    
    try:
        # Esperar a que se generen archivos
        time.sleep(5)
        
        # Buscar PDFs con patrones flexibles
        pdf_files = [
            f for f in os.listdir(output_directory) 
            if f.endswith('.pdf') and any(
                keyword in f.upper() for keyword in 
                ['RNP', 'SUNAT', 'RNSSC', 'CONSULTA']
            )
        ]
        
        log_with_condition(logger, 'info', f"PDFs encontrados: {pdf_files}")
        
        # Combinar PDFs
        if pdf_files:
            merger = PdfMerger()
            for pdf in pdf_files:
                full_path = os.path.join(output_directory, pdf)
                merger.append(full_path)
            
            output_path = os.path.join(output_directory, output_filename)
            merger.write(output_path)
            merger.close()
            
            log_with_condition(logger, 'info', f"PDF combinado: {output_path}")
            return output_path
        
        return None
    
    except Exception as e:
        log_with_condition(logger, 'error', f"Error combinando PDFs: {e}", condition=True)
        return None

def descargar_constancias(ruc, dni, output_dir):
    """
    Función principal de descarga de constancias
    """
    logger = logging.getLogger('constancias')
    
    try:
        # Preparar directorio
        os.makedirs(output_dir, exist_ok=True)
        
        # Configurar driver
        driver = configure_selenium_driver(output_dir)
        
        if not driver:
            log_with_condition(logger, 'error', "No se pudo configurar Selenium Driver", condition=True)
            return None
        
        try:
            # Intentar descargas
            log_with_condition(logger, 'info', f"Iniciando descargas para RUC: {ruc}, DNI: {dni}")
            
            # Descargar RNP
            rnp_result = download_rnp_certificate(ruc, output_dir, driver)
            log_with_condition(logger, 'info', f"Resultado RNP: {rnp_result}", 
                               condition=rnp_result is None)
            
            # Descargar RUC SUNAT
            ruc_result = download_sunat_ruc_pdf(ruc, output_dir, driver)
            log_with_condition(logger, 'info', f"Resultado RUC: {ruc_result}", 
                               condition=ruc_result is None)
            
            # Descargar RNSSC
            rnssc_result = download_rnssc_pdf(dni, output_dir)
            log_with_condition(logger, 'info', f"Resultado RNSSC: {rnssc_result}", 
                               condition=rnssc_result is None)
            
            # Combinar PDFs
            output_filename = '5. RNP, RUC, RNSSC.pdf'
            combined_pdf = combinar_pdfs(output_dir, output_filename)
            
            if combined_pdf:
                log_with_condition(logger, 'info', f"PDF combinado generado: {combined_pdf}")
                return combined_pdf
            else:
                log_with_condition(logger, 'warning', "No se pudo combinar PDFs", condition=True)
                return None
        
        finally:
            # Siempre cerrar el driver
            if driver:
                driver.quit()
    
    except Exception as e:
        log_with_condition(logger, 'error', f"Error en descarga de constancias: {e}", condition=True)
        return None
