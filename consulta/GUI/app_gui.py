import cv2
import numpy as np
import pytesseract
import requests
import time
from PIL import ImageGrab
import keyboard
import argparse
import re
import sys
from datetime import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Tuple
import logging
from threading import Thread, Event
import signal

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QSystemTrayIcon, 
                               QMenu, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QFont, QIcon, QPixmap

# Importar la función de extracción mejorada
from fieldExtractor import procesarImagen

# Configuración de logging
logging.basicConfig(
    filename='envios.log',
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

@dataclass
class CampoTexto:
    """Clase para representar un campo de texto extraído de la imagen"""
    y: int
    x: int
    texto: str

@dataclass
class DatosPaquete:
    """Clase para representar los datos del paquete"""
    pieza: str
    guarda: str

    def validar_formato_pieza(self) -> bool:
        """Valida que el número de pieza tenga el formato correcto: 2 letras + 9 números + 2 letras"""
        patron = re.compile(r'^[A-Z]{2}\d{9}[A-Z]{2}$')
        return bool(patron.match(self.pieza))

    def es_valido(self) -> bool:
        """Verifica si los datos del paquete son válidos"""
        pieza_limpia = self.limpiar().pieza
        return self.validar_formato_pieza() and self.guarda.isdigit()

    def limpiar(self) -> 'DatosPaquete':
        """Limpia y formatea los datos del paquete"""
        pieza_limpia = re.sub(r'\W+$', '', self.pieza.replace(" ", "").upper())
        guarda_limpia = ''.join(filter(str.isdigit, self.guarda))
        return DatosPaquete(pieza_limpia, guarda_limpia)

class ServerCommunicator:
    """Clase para manejar la comunicación con el servidor"""
    def __init__(self, server_url: str):
        self.server_url = server_url

    def enviar_datos(self, datos: DatosPaquete) -> bool:
        """Envía los datos al servidor y retorna si fue exitoso"""
        try:
            payload = {"pieza": datos.pieza, "guarda": datos.guarda}
            response = requests.post(self.server_url, json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"Error al enviar datos: {e}")
            return False

class ConfirmationWindow(QWidget):
    """Ventana de confirmación para mostrar los datos capturados"""
    
    data_confirmed = pyqtSignal(object)  # Señal emitida cuando se confirman los datos
    
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
        
        # Posicionar en la esquina superior derecha
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 320, 20)
        
        # Mantener siempre visible
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Estilo
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

        # Título
        title_label = QLabel("📦 Datos Capturados")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Campo Pieza
        pieza_layout = QHBoxLayout()
        pieza_label = QLabel("Pieza:")
        pieza_label.setFixedWidth(60)
        self.pieza_edit = QLineEdit()
        self.pieza_edit.setReadOnly(True)
        self.pieza_edit.mouseDoubleClickEvent = self.edit_pieza
        pieza_layout.addWidget(pieza_label)
        pieza_layout.addWidget(self.pieza_edit)
        layout.addLayout(pieza_layout)

        # Campo Guarda
        guarda_layout = QHBoxLayout()
        guarda_label = QLabel("Guarda:")
        guarda_label.setFixedWidth(60)
        self.guarda_edit = QLineEdit()
        self.guarda_edit.setReadOnly(True)
        self.guarda_edit.mouseDoubleClickEvent = self.edit_guarda
        guarda_layout.addWidget(guarda_label)
        guarda_layout.addWidget(self.guarda_edit)
        layout.addLayout(guarda_layout)

        # Contador
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
        self.pieza_edit.setText(datos.pieza)
        self.guarda_edit.setText(datos.guarda)
        self.remaining_seconds = 5
        
        self.show()
        self.activateWindow()
        self.raise_()
        
        self.countdown_timer.start(1000)  # Actualizar cada segundo
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
        # Actualizar los datos con los valores actuales
        pieza_actual = self.pieza_edit.text().strip()
        guarda_actual = self.guarda_edit.text().strip()
        
        datos_actualizados = DatosPaquete(pieza_actual, guarda_actual).limpiar()
        
        self.data_confirmed.emit(datos_actualizados)
        self.hide()  # Ocultar en lugar de cerrar

    def closeEvent(self, event):
        """Se ejecuta al cerrar la ventana"""
        self.countdown_timer.stop()
        # No cerrar la aplicación, solo ocultar la ventana
        event.accept()
        self.hide()

class KeyboardWorker(QThread):
    """Worker thread para manejar la captura de teclas"""
    
    f4_pressed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.running = True
        self._stop_event = False

    def run(self):
        """Ejecuta el bucle de detección de teclas"""
        print("🎯 Detector de teclas iniciado (F4 para capturar)")
        last_f4_time = 0
        
        while self.running and not self._stop_event:
            try:
                if keyboard.is_pressed('f4'):
                    current_time = time.time()
                    # Anti-rebote: solo permitir F4 cada 2 segundos
                    if current_time - last_f4_time > 2.0:
                        self.f4_pressed.emit()
                        last_f4_time = current_time
                        
                time.sleep(0.1)  # Reducir uso de CPU
            except Exception as e:
                print(f"⚠️ Error en detección de teclas: {e}")
                time.sleep(1)  # Pausa más larga en caso de error

    def stop(self):
        """Detiene el worker"""
        print("🛑 Deteniendo detector de teclas...")
        self.running = False
        self._stop_event = True

class ConsultaApp(QObject):
    """Clase principal de la aplicación con interfaz gráfica"""
    
    def __init__(self, server_url: str, config_service=None):
        super().__init__()
        self.server = ServerCommunicator(server_url)
        self.config_service = config_service
        
        # Interfaz gráfica
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)
        
        self.confirmation_window = ConfirmationWindow()
        self.confirmation_window.data_confirmed.connect(self.enviar_datos_servidor)
        
        # Worker para captura de teclas
        self.keyboard_worker = KeyboardWorker()
        self.keyboard_worker.f4_pressed.connect(self.manejar_captura)
        
        # System tray
        if not self.setup_system_tray():
            print("⚠️ Sistema sin soporte para bandeja del sistema")
            # Si no hay system tray, mantener la aplicación visible de alguna manera
            self.app.setQuitOnLastWindowClosed(True)
        
        print(f"🚀 Aplicación iniciada en background")
        print(f"📡 Servidor destino: {server_url}")
        print(f"⌨️ Presiona F4 para capturar pantalla")

    def setup_system_tray(self):
        """Configura el icono en la bandeja del sistema"""
        # Verificar si el sistema soporta system tray
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(None, "System Tray",
                               "No se detectó soporte para System Tray en este sistema.")
            return False
        
        self.tray_icon = QSystemTrayIcon()
        
        # Crear un icono simple si no existe uno
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.blue)
        icon = QIcon(pixmap)
        
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Consulta App - Presiona F4 para capturar")
        
        # Menú del tray
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("📊 Estado")
        show_action.triggered.connect(self.show_log)
        
        # Agregar opción para reconfigurar servidor si tenemos el servicio
        if self.config_service:
            tray_menu.addSeparator()
            config_action = tray_menu.addAction("⚙️ Configurar Servidor")
            config_action.triggered.connect(self.show_configuration_dialog)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("❌ Salir")
        quit_action.triggered.connect(self.quit_application)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Conectar doble click para mostrar estado
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        return True
    
    def show_configuration_dialog(self):
        """Muestra el diálogo de configuración del servidor"""
        if self.config_service and self.config_service.show_configuration_dialog():
            # Configuración actualizada, reiniciar el servidor comunicador
            server_url, _ = self.config_service.get_server_urls()
            if server_url:
                if not server_url.endswith('/'):
                    server_url += '/'
                server_url += 'pedido'
                self.server = ServerCommunicator(server_url)
                print(f"🔄 Configuración actualizada: {server_url}")
                
                # Mostrar mensaje de confirmación
                msg = QMessageBox()
                msg.setWindowTitle("Configuración Actualizada")
                msg.setText(f"✅ Nueva configuración guardada:\n{server_url}")
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
                   f"🌐 Servidor: {self.server.server_url}")
        msg.setIcon(QMessageBox.Information)
        msg.exec()

    def quit_application(self):
        """Cierra la aplicación"""
        print("👋 Cerrando aplicación...")
        
        # Detener el keyboard worker
        if hasattr(self, 'keyboard_worker') and self.keyboard_worker.isRunning():
            self.keyboard_worker.stop()
            self.keyboard_worker.quit()
            if not self.keyboard_worker.wait(3000):  # Esperar máximo 3 segundos
                self.keyboard_worker.terminate()
        
        # Cerrar ventana de confirmación
        if hasattr(self, 'confirmation_window'):
            self.confirmation_window.close()
        
        # Ocultar tray icon
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
            
        QApplication.quit()

    def capturar_pantalla(self) -> np.ndarray:
        """Captura la pantalla completa"""
        imagen = ImageGrab.grab()
        img_np = np.array(imagen)
        return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    def procesar_datos_extraidos(self, datos_json: dict) -> Optional[DatosPaquete]:
        """
        Procesa los datos extraídos del JSON devuelto por procesarImagen
        
        Args:
            datos_json (dict): JSON con keys 'pieza' y 'guarda'
            
        Returns:
            Optional[DatosPaquete]: Objeto DatosPaquete o None si hay errores
        """
        try:
            pieza_texto = datos_json.get('pieza', '').strip()
            guarda_texto = datos_json.get('guarda', '').strip()
            
            # Verificar si hay errores en la extracción
            if pieza_texto.startswith('Error:') or guarda_texto.startswith('Error:'):
                logging.error(f"Error en extracción: pieza='{pieza_texto}', guarda='{guarda_texto}'")
                return None
            
            # Crear y limpiar los datos
            if pieza_texto and guarda_texto:
                datos = DatosPaquete(pieza=pieza_texto, guarda=guarda_texto)
                return datos.limpiar()
            else:
                logging.warning(f"Datos incompletos: pieza='{pieza_texto}', guarda='{guarda_texto}'")
                return None
                
        except Exception as e:
            logging.error(f"Error al procesar datos extraídos: {e}")
            return None

    def manejar_captura(self):
        """Maneja el proceso de captura y procesamiento de imagen"""
        logging.info("Iniciando captura de pantalla")
        print("📸 Capturando pantalla...")
        
        try:
            # Capturar pantalla
            img = self.capturar_pantalla()
            
            # Procesar imagen usando el método mejorado de fieldExtractor
            print("🔍 Procesando imagen con método mejorado...")
            datos_json = procesarImagen(img)
            
            # Procesar los datos extraídos
            datos = self.procesar_datos_extraidos(datos_json)
            
            if datos is None:
                print("⚠️ No se pudieron extraer los datos requeridos")
                print(f"📋 Respuesta del procesador: {datos_json}")
                return

            if not datos.es_valido():
                logging.warning(f"Datos inválidos: {datos}")
                print(f"⚠️ Datos inválidos: Pieza={datos.pieza}, Guarda={datos.guarda}")
                print("💡 Mostrando ventana de confirmación para edición manual...")
                # Mostrar la ventana de confirmación incluso con datos inválidos
                # para que el usuario pueda corregirlos manualmente
                self.confirmation_window.show_data(datos)
                return

            # Mostrar ventana de confirmación
            print(f"📋 Datos detectados: Pieza={datos.pieza}, Guarda={datos.guarda}")
            self.confirmation_window.show_data(datos)
            
        except Exception as e:
            logging.error(f"Error en manejar_captura: {e}")
            print(f"❌ Error durante la captura: {e}")

    def enviar_datos_servidor(self, datos: DatosPaquete):
        """Envía los datos al servidor"""
        try:
            if self.server.enviar_datos(datos):
                logging.info(f"✅ Datos enviados correctamente: {datos}")
                print(f"✅ Datos enviados: {datos}")
            else:
                logging.error(f"❌ Error al enviar datos: {datos}")
                print(f"❌ Error al enviar: {datos}")
        except Exception as e:
            logging.error(f"❌ Excepción al enviar datos: {e}")
            print(f"❌ Excepción al enviar: {e}")
        
        # La ventana ya se oculta automáticamente en confirm_data()

    def run(self):
        """Ejecuta la aplicación"""
        # Configurar para que no cierre al cerrar la última ventana
        self.app.setQuitOnLastWindowClosed(False)
        
        self.keyboard_worker.start()
        
        # Manejar señales del sistema para cierre limpio
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        return self.app.exec()

    def signal_handler(self, signum, frame):
        """Maneja las señales del sistema"""
        print("\n👋 Cerrando aplicación...")
        self.quit_application()

def main():
    # Inicializar QApplication tempormente para el diálogo de configuración
    temp_app = QApplication.instance()
    if temp_app is None:
        temp_app = QApplication(sys.argv)
    
    from configuration_service import ConfigurationService
    
    config_service = ConfigurationService()
    
    # Asegurar que la aplicación esté configurada
    if not config_service.ensure_configuration():
        print("❌ Configuración cancelada por el usuario")
        return 1
    
    # Obtener la URL del servidor
    server_url, _ = config_service.get_server_urls()
    
    if server_url is None:
        print("❌ Error: No se pudo obtener la configuración del servidor")
        return 1
    
    # Ajustar la URL para incluir el endpoint /pedido
    if not server_url.endswith('/'):
        server_url += '/'
    server_url += 'pedido'
    
    app = ConsultaApp(server_url, config_service)
    sys.exit(app.run())

if __name__ == "__main__":
    main()