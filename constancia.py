# constancia.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import os
import time
import json
from PyPDF2 import PdfMerger
import logging
import requests
from datetime import datetime
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def configure_selenium_driver(output_dir):
    """
    Configura el driver de Selenium con las opciones necesarias
    """
    try:
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
        
        logging.info("Driver de Selenium configurado exitosamente")
        return driver
    
    except Exception as e:
        logging.error(f"Error al configurar el driver de Selenium: {e}")
        return None
    
def descargar_constancias(ruc, dni, output_dir):
    """
    Función principal para descargar constancias RNP, RUC y RNSSC
    """
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Crear directorio de salida si no existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Configurar driver
        driver = configure_selenium_driver(output_dir)
        
        if not driver:
            login.error("No se pudo configurar el driver de Selenium")
            return None
        
        try:
            # 1. Descargar RNP
            login.info("Descargando constancia RNP...")
            download_rnp_certificate(ruc, output_dir, driver)
            
            # 2. Descargar RUC SUNAT
            login.info("Descargando constancia RUC...")
            download_sunat_ruc_pdf(ruc, output_dir, driver)
            
            # 3. Descargar RNSSC
            login.info("Descargando constancia RNSSC...")
            download_rnssc_pdf(dni, output_dir)
            
            # 4. Combinar PDFs
            login.info("Combinando PDFs...")
            output_filename = '5. RNP, RUC, RNSSC.pdf'
            combinar_pdfs(output_dir, output_filename)
            
            login.success("Proceso de descarga completado exitosamente")
            
            # Devolver la ruta del PDF combinado
            return os.path.join(output_dir, output_filename)
        
        finally:
            # Cerrar el driver
            if driver:
                driver.quit()
    
    except Exception as e:
        login.error(f"Error en la descarga de constancias: {e}")
        return None

def download_rnp_certificate(ruc, output_dir, driver):
    """
    Descarga el certificado RNP para un número de RUC dado
    """
    try:
        # Navegar a la página del certificado RNP con el RUC
        url = f"https://www.rnp.gob.pe/Constancia/RNP_Constancia/default_Todos.asp?RUC={ruc}"
        driver.get(url)
        
        # Esperar alerta si está presente y aceptarla
        try:
            WebDriverWait(driver, 5).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            alert.accept()
        except:
            print(f"No hay alerta presente para el RUC {ruc}")
        
        # Esperar a que el botón de imprimir esté presente
        print_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "btnPrint"))
        )
        
        # Activar impresión (que guardará como PDF con nuestras opciones)
        print_button.click()
        
        # Esperar a que se complete la descarga
        time.sleep(3)
        
    except Exception as e:
        print(f"Error detallado para RUC {ruc} en RNP: {str(e)}")
        raise

def download_sunat_ruc_pdf(ruc, output_dir, driver):
    """
    Descarga el PDF de SUNAT para un número de RUC dado
    """
    try:
        # Navegar a la página de consulta RUC de SUNAT
        url = 'https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp'
        driver.get(url)
        
        # Esperar a que el campo de RUC esté presente
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'txtRuc'))
        )
        
        # Asegurarse de que la opción "Por RUC" esté seleccionada
        btn_por_ruc = driver.find_element(By.ID, 'btnPorRuc')
        if 'active' not in btn_por_ruc.get_attribute('class'):
            btn_por_ruc.click()
        
        # Ingresar el número de RUC
        txt_ruc = driver.find_element(By.ID, 'txtRuc')
        txt_ruc.clear()
        txt_ruc.send_keys(ruc)
        
        # Hacer clic en el botón "Buscar"
        btn_buscar = driver.find_element(By.ID, 'btnAceptar')
        btn_buscar.click()
        
        # Esperar a que la página de resultados cargue
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'panel-primary'))
        )
        
        # Hacer clic en el botón "Imprimir"
        btn_imprimir = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@onclick='imprimir()']"))
        )
        btn_imprimir.click()
        
        # Esperar a que se complete la descarga
        time.sleep(3)
        
    except Exception as e:
        print(f"Error detallado para RUC {ruc} en SUNAT: {str(e)}")
        raise

def download_rnssc_pdf(dni, output_directory):
    """
    Descarga el PDF de RNSSC utilizando la URL REST.
    """
    try:
        logging.info(f"Descargando RNSSC para DNI: {dni}")
        
        # Obtener la fecha y hora actual en el formato requerido
        now = datetime.now()
        fecha_hora = now.strftime("%d-%m-%Y %H:%M:%S")
        
        # Construir la URL de descarga
        url = f"https://www.sanciones.gob.pe/rnssc-rest/rest/sancion/descargar/Usuario%20consulta/NINGUNO/NINGUNO/NINGUNO/DOCUMENTO%20NACIONAL%20DE IDENTIDAD/{dni}/{fecha_hora}"
        
        # Realizar la solicitud GET
        response = requests.get(url)
        
        # Verificar si la solicitud fue exitosa
        if response.status_code == 200:
            # Definir el nombre del archivo siguiendo el patrón
            # Extraer sancionID del contenido si es posible, o generar uno
            sancion_id = f"{int(time.time() * 1000)}"  # Ejemplo de ID basado en timestamp
            filename = f"ConsultaSinResultados_sancionID{sancion_id}.pdf"
            filepath = os.path.join(output_dir, filename)
            
            # Guardar el contenido PDF
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logging.info(f"RNSSC descargado exitosamente para DNI {dni} en {filepath}")
            return filepath
        else:
            logging.error(f"Error al descargar RNSSC para DNI {dni}. Estado HTTP: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error al descargar RNSSC para DNI {dni}: {str(e)}")
        return None

def combinar_pdfs(output_directory, output_filename):
    """
    Combina los archivos PDF en un solo PDF y elimina los archivos temporales.
    """
    # Esperar unos segundos para asegurarse de que los archivos hayan sido generados
    time.sleep(5)

    # Obtener la lista de archivos PDF en el directorio de salida
    pdf_files = os.listdir(output_directory)
    pdf_files = [f for f in pdf_files if f.endswith('.pdf')]
    
    # Identificar los archivos PDF individuales
    pdf_rnp = None
    pdf_ruc = None
    pdf_rnssc = None

    for filename in pdf_files:
        if 'CONSTANCIA DEL RNP' in filename or 'RNP_' in filename:
            pdf_rnp = os.path.join(output_directory, filename)
        elif 'SUNAT - Consulta RUC' in filename or 'SUNAT_' in filename:
            pdf_ruc = os.path.join(output_directory, filename)
        elif 'ConsultaSinResultados_sancionID' in filename:
            pdf_rnssc = os.path.join(output_directory, filename)
    
    # Verificar que se encontraron todos los PDFs
    pdf_list = []
    if pdf_rnp:
        pdf_list.append(pdf_rnp)
    else:
        print("No se encontró el PDF de RNP.")
    if pdf_ruc:
        pdf_list.append(pdf_ruc)
    else:
        print("No se encontró el PDF de RUC.")
    if pdf_rnssc:
        pdf_list.append(pdf_rnssc)
    else:
        print("No se encontró el PDF de RNSSC.")
    
    # Ruta del PDF combinado de salida
    output_pdf = os.path.join(output_directory, output_filename)
    
    # Combinar los PDFs
    if pdf_list:
        merger = PdfMerger()
        for pdf in pdf_list:
            merger.append(pdf)
        merger.write(output_pdf)
        merger.close()
        print(f"PDF combinado guardado como {output_pdf}")
        
        # Eliminar los archivos PDF temporales
        for pdf in pdf_list:
            try:
                os.remove(pdf)
                print(f"Archivo temporal eliminado: {pdf}")
            except Exception as e:
                print(f"Error al eliminar el archivo {pdf}: {str(e)}")
    else:
        print("No hay PDFs para combinar.")
