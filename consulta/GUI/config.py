import json
import os
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class ServerConfig:
    """Configuración del servidor"""
    ip: str
    port: int
    
    @property
    def server_url(self) -> str:
        """URL del servidor HTTP"""
        return f"http://{self.ip}:{self.port}/"
    
    @property
    def websocket_url(self) -> str:
        """URL del WebSocket"""
        return f"ws://{self.ip}:{self.port}/ws"


class ConfigurationManager:
    """Gestor de configuración de la aplicación siguiendo el patrón Singleton"""
    
    _instance = None
    _config = None
    
    def __new__(cls, config_file: str = "config.json"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config_file = config_file
            cls._instance._load_configuration()
        return cls._instance

    def _load_configuration(self) -> None:
        """Carga la configuración desde el archivo"""
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._config = ServerConfig(
                        ip=data.get('ip', 'localhost'),
                        port=data.get('puerto', 8000)
                    )
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"Error al leer el archivo de configuración: {e}")
                self._config = None
        else:
            self._config = None

    def save_configuration(self, server_config: ServerConfig) -> bool:
        """Guarda la configuración en el archivo"""
        try:
            config_data = {
                'ip': server_config.ip,
                'puerto': server_config.port
            }
            
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            
            self._config = server_config
            return True
            
        except Exception as e:
            print(f"Error al guardar la configuración: {e}")
            return False

    def is_configured(self) -> bool:
        """Verifica si la aplicación está configurada"""
        return self._config is not None

    def get_server_config(self) -> Optional[ServerConfig]:
        """Obtiene la configuración del servidor"""
        return self._config

    def get_server_url(self) -> Optional[str]:
        """Obtiene la URL del servidor"""
        return self._config.server_url if self._config else None
    
    def get_websocket_url(self) -> Optional[str]:
        """Obtiene la URL del WebSocket"""
        return self._config.websocket_url if self._config else None

    def update_configuration(self, ip: str, port: int) -> bool:
        """Actualiza la configuración con nuevos valores"""
        server_config = ServerConfig(ip=ip, port=port)
        return self.save_configuration(server_config)

    def reset_configuration(self) -> None:
        """Resetea la configuración"""
        if os.path.exists(self._config_file):
            try:
                os.remove(self._config_file)
                self._config = None
            except Exception as e:
                print(f"Error al eliminar el archivo de configuración: {e}")


# Clase de compatibilidad con el código existente
class ConfigManager(ConfigurationManager):
    """Clase de compatibilidad para mantener la API existente"""
    
    def __init__(self, config_file: str = "config.json"):
        super().__init__(config_file)

    def get_server_port(self) -> int:
        """Obtiene el puerto del servidor (compatibilidad)"""
        return self._config.port if self._config else 8000

    def get_server_ip(self) -> str:
        """Obtiene la IP del servidor (compatibilidad)"""
        return self._config.ip if self._config else 'localhost'

    def set_server_url(self, url: str) -> None:
        """Establece la URL del servidor (compatibilidad)"""
        ip, port = self._parse_url(url)
        self.update_configuration(ip, port)

    def _parse_url(self, url: str) -> Tuple[str, int]:
        """Extrae la IP y el puerto de una URL (compatibilidad)"""
        try:
            url = url.replace('http://', '')
            if '/' in url:
                url = url.split('/')[0]
            ip, port_str = url.split(':')
            return ip, int(port_str)
        except:
            return 'localhost', 8000