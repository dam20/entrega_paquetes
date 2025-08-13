from PyQt5.QtWidgets import QWidget, QDialog
from typing import Optional, Tuple
from config_dialog import ConfigurationDialog
from config import ConfigurationManager, ServerConfig


class ConfigurationService:
    """Servicio para manejar la configuración de la aplicación"""
    
    def __init__(self):
        self._config_manager = ConfigurationManager()
    
    def ensure_configuration(self, parent: Optional[QWidget] = None) -> bool:
        """
        Asegura que la aplicación esté configurada.
        Si no lo está, muestra el diálogo de configuración.
        
        Args:
            parent: Widget padre para el diálogo
            
        Returns:
            bool: True si la configuración es válida, False si el usuario canceló
        """
        if self._config_manager.is_configured():
            return True
            
        return self._request_configuration(parent)
    
    def _request_configuration(self, parent: Optional[QWidget] = None) -> bool:
        """
        Solicita configuración al usuario mediante diálogo gráfico
        
        Args:
            parent: Widget padre para el diálogo
            
        Returns:
            bool: True si se configuró correctamente, False si se canceló
        """
        dialog = ConfigurationDialog(parent)
        
        if dialog.exec_() == QDialog.Accepted:
            config_data = dialog.get_configuration()
            
            if config_data:
                ip, port = config_data
                return self._config_manager.update_configuration(ip, port)
                
        return False
    
    def show_configuration_dialog(self, parent: Optional[QWidget] = None) -> bool:
        """
        Muestra el diálogo de configuración
        
        Args:
            parent: Widget padre para el diálogo
            
        Returns:
            bool: True si se guardó la configuración, False si se canceló
        """
        return self._request_configuration(parent)
    
    def get_server_urls(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Obtiene las URLs del servidor y WebSocket
        
        Returns:
            Tuple[str, str]: (server_url, websocket_url) o (None, None) si no está configurado
        """
        if not self._config_manager.is_configured():
            return None, None
            
        return (
            self._config_manager.get_server_url(),
            self._config_manager.get_websocket_url()
        )
    
    def get_configuration_manager(self) -> ConfigurationManager:
        """Obtiene el gestor de configuración"""
        return self._config_manager
    
    def is_configured(self) -> bool:
        """Verifica si la aplicación está configurada"""
        return self._config_manager.is_configured()
    
    def reset_configuration(self) -> None:
        """Resetea la configuración"""
        self._config_manager.reset_configuration()