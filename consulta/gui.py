import numpy as np
import cv2
import signal
import time
import sys
import logging
import re
from PIL import ImageGrab

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QSystemTrayIcon, 
                               QMenu, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QIcon, QPixmap

# Se importan las clases de otros módulos
from core import DatosPaquete, ServerCommunicator
from workers import KeyboardWorker, OcrRequestWorker # Importamos el nuevo worker

# Se importa la función de procesamiento de imagen
from procesarImagen import procesarImagen


# Configuración de logging
logging.basicConfig(
    filename='envios.log',
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class ConfirmationWindow(QWidget):
    """Ventana de confirmación para mostrar los datos capturados"""
    
    data_confirmed = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self.datos = None
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.remaining_seconds = 5
        
        self.setup_ui()
        self.setup_window()

    def setup_window(self):
        """Configura las propiedades de la ventana"""
        self.setWindowTitle("Confirmación de Datos")
        self.setFixedSize(300, 150)
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 320, 20)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: white;
                border: 2px solid #0078d4;
                border-radius: 8px;
            }
            QLabel {
                font-size: 12px;
                border: none;
                padding: 2px;
            }
            QLineEdit {
                background-color: #404040;
                border: 1px solid #666;
                border-radius: 4px;
                padding: 5px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #0078d4;
            }
            #title {
                font-size: 14px;
                font-weight: bold;
                color: #0078d4;
            }
            #countdown {
                font-size: 11px;
                color: #ffa500;
            }
        """)

    def setup_ui(self):
        """Configura la interfaz de usuario"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 10, 15, 10)
        title_label = QLabel("📦 Datos Capturados")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        pieza_layout = QHBoxLayout()
        pieza_label = QLabel("Pieza:")
        pieza_label.setFixedWidth(60)
        self.pieza_edit = QLineEdit()
        self.pieza_edit.setReadOnly(True)
        self.pieza_edit.mouseDoubleClickEvent = self.edit_pieza
        pieza_layout.addWidget(pieza_label)
        pieza_layout.addWidget(self.pieza_edit)
        layout.addLayout(pieza_layout)
        guarda_layout = QHBoxLayout()
        guarda_label = QLabel("Guarda:")
        guarda_label.setFixedWidth(60)
        self.guarda_edit = QLineEdit()
        self.guarda_edit.setReadOnly(True)
        self.guarda_edit.mouseDoubleClickEvent = self.edit_guarda
        guarda_layout.addWidget(guarda_label)
        guarda_layout.addWidget(self.guarda_edit)
        layout.addLayout(guarda_layout)
        self.countdown_label = QLabel()
        self.countdown_label.setObjectName("countdown")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.countdown_label)

    def edit_pieza(self, event):
        """Permite editar el campo pieza"""
        self.pieza_edit.setReadOnly(False)
        self.pieza_edit.setFocus()
        self.pieza_edit.selectAll()
        self.countdown_timer.stop()
        
    def edit_guarda(self, event):
        """Permite editar el campo guarda"""
        self.guarda_edit.setReadOnly(False)
        self.guarda_edit.setFocus()
        self.guarda_edit.selectAll()
        self.countdown_timer.stop()

    def keyPressEvent(self, event):
        """Maneja los eventos de teclado"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.confirm_data()
        elif event.key() == Qt.Key_Escape:
            self.close()
        super().keyPressEvent(event)

    def show_data(self, datos: DatosPaquete):
        """Muestra los datos en la ventana"""
        self.datos = datos
        self.poste_restante = datos.poste_restante
        self.pieza_edit.setText(datos.pieza)
        self.guarda_edit.setText(datos.guarda)
        self.remaining_seconds = 5
        self.show()
        self.activateWindow()
        self.raise_()
        self.countdown_timer.start(1000)
        self.update_countdown()

    def update_countdown(self):
        """Actualiza el contador regresivo"""
        if self.remaining_seconds > 0:
            self.countdown_label.setText(f"⏱️ Enviando en {self.remaining_seconds} segundos (Enter para confirmar)")
            self.remaining_seconds -= 1
        else:
            self.countdown_timer.stop()
            self.confirm_data()

    def confirm_data(self):
        """Confirma los datos y los envía"""
        pieza_actual = self.pieza_edit.text().strip()
        guarda_actual = self.guarda_edit.text().strip()
        poste_restante = self.poste_restante
        datos_actualizados = DatosPaquete(pieza_actual, guarda_actual, poste_restante).limpiar()
        self.data_confirmed.emit(datos_actualizados)
        self.hide()

    def closeEvent(self, event):
        """Se ejecuta al cerrar la ventana"""
        self.countdown_timer.stop()
        event.accept()
        self.hide()


class ConsultaApp(QObject):
    """Clase principal de la aplicación con interfaz gráfica"""
    
    def __init__(self, server_url: str, config_service=None):
        super().__init__()
        # ServerCommunicator ahora recibe la URL base
        self.server = ServerCommunicator(server_url) 
        self.config_service = config_service
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)
        
        self.confirmation_window = ConfirmationWindow()
        # Conexión para enviar datos *después* de que el usuario confirma en la ventana
        self.confirmation_window.data_confirmed.connect(self.enviar_datos_servidor)
        
        self.keyboard_worker = KeyboardWorker()
        self.keyboard_worker.f4_pressed.connect(self.manejar_captura)
        
        # Propiedad para mantener la referencia al worker de OCR
        self.ocr_worker = None 

        if not self.setup_system_tray():
            print("⚠️ Sistema sin soporte para bandeja del sistema")
            self.app.setQuitOnLastWindowClosed(True)
        
        print(f"🚀 Aplicación iniciada en background")
        # Mostrar la URL base del servidor aquí
        print(f"📡 Servidor base: {server_url}") 
        print(f"⌨️ Presiona F4 para capturar pantalla")

    def setup_system_tray(self):
        """Configura el icono en la bandeja del sistema"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(None, "System Tray", "No se detectó soporte para System Tray en este sistema.")
            return False
        
        self.tray_icon = QSystemTrayIcon()
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.blue)
        icon = QIcon(pixmap)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Consulta App - Presiona F4 para capturar")
        tray_menu = QMenu()
        show_action = tray_menu.addAction("📊 Estado")
        show_action.triggered.connect(self.show_log)
        if self.config_service:
            tray_menu.addSeparator()
            config_action = tray_menu.addAction("⚙️ Configurar Servidor")
            config_action.triggered.connect(self.show_configuration_dialog)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("❌ Salir")
        quit_action.triggered.connect(self.quit_application)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        return True
    
    def show_configuration_dialog(self):
        """Muestra el diálogo de configuración del servidor"""
        if self.config_service and self.config_service.show_configuration_dialog():
            server_url_base, _ = self.config_service.get_server_urls()
            if server_url_base:
                # Actualizamos ServerCommunicator con la URL base
                self.server = ServerCommunicator(server_url_base) 
                print(f"🔄 Configuración actualizada: {server_url_base}")
                msg = QMessageBox()
                msg.setWindowTitle("Configuración Actualizada")
                msg.setText(f"✅ Nueva configuración guardada:\n{server_url_base}")
                msg.setIcon(QMessageBox.Information)
                msg.exec()
    
    def tray_icon_activated(self, reason):
        """Maneja la activación del icono del tray"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_log()

    def show_log(self):
        """Muestra información del log"""
        status = "🟢 En línea" if self.keyboard_worker.isRunning() else "🔴 Desconectado"
        msg = QMessageBox()
        msg.setWindowTitle("Estado de la Aplicación")
        msg.setText(f"{status} - Aplicación funcionando\n\n"
                   "📋 Controles:\n"
                   "• F4: Capturar pantalla\n"
                   "• Doble click: Editar campos\n"
                   "• Enter: Confirmar envío\n"
                   "• Escape: Cancelar\n\n"
                   f"🌐 Servidor: {self.server.server_url}") # server_url ahora es la URL base
        msg.setIcon(QMessageBox.Information)
        msg.exec()

    def quit_application(self):
        """Cierra la aplicación"""
        print("👋 Cerrando aplicación...")
        
        if hasattr(self, 'keyboard_worker') and self.keyboard_worker.isRunning():
            self.keyboard_worker.stop()
            self.keyboard_worker.quit()
            if not self.keyboard_worker.wait(3000):
                self.keyboard_worker.terminate()
        
        # Detener cualquier worker de OCR que esté corriendo
        if hasattr(self, 'ocr_worker') and self.ocr_worker and self.ocr_worker.isRunning():
            self.ocr_worker.quit()
            self.ocr_worker.wait() # Esperar a que el hilo termine
            print("🛑 Worker de OCR detenido.")


        if hasattr(self, 'confirmation_window'):
            self.confirmation_window.close()
        
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
            
        QApplication.quit()

    def capturar_pantalla(self) -> np.ndarray:
        """Captura la pantalla completa"""
        imagen = ImageGrab.grab()
        img_np = np.array(imagen)
        return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)


    def procesar_datos_extraidos(self, datos_json: dict):
        """Procesa los datos extraídos del JSON"""
        try:
            pieza_texto = datos_json.get('pieza', '').strip()
            guarda_texto = datos_json.get('guarda', '').strip()
            poste_restante = datos_json.get('poste_restante', False)
            
            if pieza_texto.startswith('Error:') or guarda_texto.startswith('Error:'):
                logging.error(f"Error en extracción: pieza='{pieza_texto}', guarda='{guarda_texto}', poste_restante='{poste_restante}'")
                return None
            
            if pieza_texto and guarda_texto:
                datos = DatosPaquete(pieza=pieza_texto, guarda=guarda_texto, poste_restante=poste_restante)
                return datos.limpiar()
            else:
                logging.warning(f"Datos incompletos: pieza='{pieza_texto}', guarda='{guarda_texto}', poste_restante='{poste_restante}'")
                return None
        except Exception as e:
            logging.error(f"Error al procesar datos extraídos: {e}")
            return None

    def manejar_captura(self):
        """Maneja el proceso de captura, recorte y envía las imágenes para OCR."""
        logging.info("Iniciando captura de pantalla y recorte de imágenes.")
        print("📸 Capturando pantalla y recortando imágenes...")
        
        try:
            img = self.capturar_pantalla()
            
            # procesarImagen retorna las imágenes recortadas (numpy arrays codificados en base64)
            # Asegúrate de que procesarImagen.py realmente devuelva los strings base64 aquí
            base64_pieza_str, base64_guarda_str = procesarImagen(img)

            if base64_pieza_str is None or base64_guarda_str is None:
                print("⚠️ No se pudieron obtener todos los recortes requeridos (Base64).")
                QMessageBox.warning(None, "Error de Recorte", "No se pudieron obtener todos los recortes de imagen necesarios.")
                return

            print("✅ Imágenes recortadas y codificadas con éxito. Iniciando envío al servidor para OCR...")
            
            # Crear y arrancar el worker para la solicitud de OCR
            # Pasamos las cadenas Base64 directamente, ya que procesarImagen ya las generó
            self.ocr_worker = OcrRequestWorker(base64_pieza_str, base64_guarda_str, self.server)
            self.ocr_worker.ocr_result.connect(self.handle_ocr_response)
            self.ocr_worker.ocr_error.connect(self.handle_ocr_error)
            self.ocr_worker.start() # Inicia el hilo en segundo plano

        except Exception as e:
            logging.error(f"Error en manejar_captura (captura/recorte): {e}")
            print(f"❌ Error durante la captura y recorte: {e}")
            QMessageBox.critical(None, "Error Crítico", f"Ocurrió un error inesperado durante la captura: {e}")

    def handle_ocr_response(self, datos_json: dict):
        """Maneja la respuesta exitosa del worker de OCR."""
        print("✅ Respuesta de OCR recibida del servidor.")
        datos_paquete = self.procesar_datos_extraidos(datos_json)

        if datos_paquete is None:
            print("⚠️ El servidor devolvió datos no válidos o incompletos para OCR.")
            QMessageBox.warning(None, "Error de OCR", "El servidor devolvió datos no válidos o incompletos.")
            return

        if not datos_paquete.es_valido():
            logging.warning(f"Datos inválidos después de OCR: {datos_paquete}")
            print(f"⚠️ Datos inválidos: Pieza={datos_paquete.pieza}, Guarda={datos_paquete.guarda}, Poste Restante={datos_paquete.poste_restante}")
            print("💡 Mostrando ventana de confirmación para edición manual...")
            QMessageBox.information(None, "Datos Inválidos", "Los datos extraídos no cumplen el formato esperado. Revise y edite.")
            self.confirmation_window.show_data(datos_paquete)
            return

        print(f"📋 Datos detectados: Pieza={datos_paquete.pieza}, Guarda={datos_paquete.guarda}, Poste Restante={datos_paquete.poste_restante}")
        self.confirmation_window.show_data(datos_paquete)

    def handle_ocr_error(self, error_message: str):
        """Maneja los errores del worker de OCR."""
        logging.error(f"Error del worker de OCR: {error_message}")
        print(f"❌ Error al procesar OCR en el servidor: {error_message}")
        QMessageBox.critical(None, "Error de OCR", f"No se pudo procesar la imagen en el servidor: {error_message}")


    def enviar_datos_servidor(self, datos: DatosPaquete):
        """Envía los datos (ya validados y posiblemente editados por el usuario) al servidor."""
        try:
            # Aquí llamamos al método de ServerCommunicator para enviar los datos finales del paquete
            if self.server.enviar_datos(datos): 
                logging.info(f"✅ Datos finales enviados correctamente: {datos}")
                print(f"✅ Datos finales enviados: {datos}")
                #QMessageBox.information(None, "Envío Exitoso", "Los datos han sido enviados correctamente.")
            else:
                logging.error(f"❌ Error al enviar datos finales: {datos}")
                print(f"❌ Error al enviar datos finales: {datos}")
                QMessageBox.critical(None, "Error de Envío", "Hubo un error al enviar los datos finales al servidor.")
        except Exception as e:
            logging.error(f"❌ Excepción al enviar datos finales: {e}")
            print(f"❌ Excepción al enviar datos finales: {e}")
            QMessageBox.critical(None, "Error de Envío", f"Ocurrió una excepción al enviar los datos finales: {e}")
        
    def run(self):
        """Ejecuta la aplicación"""
        self.app.setQuitOnLastWindowClosed(False)
        self.keyboard_worker.start()
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        return self.app.exec()

    def signal_handler(self, signum, frame):
        """Maneja las señales del sistema"""
        print("\n👋 Cerrando aplicación...")
        self.quit_application()