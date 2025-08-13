import json
import os
from typing import Optional

class ConfigManager:
    """Gestor de configuración de la aplicación"""
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Carga la configuración desde el archivo"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error al leer el archivo de configuración: {e}")
                return {}
        return {}

    def save_config(self) -> None:
        """Guarda la configuración actual en el archivo"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error al guardar la configuración: {e}")

    def _parse_url(self, url: str) -> tuple[str, int]:
        """Extrae la IP y el puerto de una URL"""
        try:
            # Elimina 'http://' y '/pedido' si existen
            url = url.replace('http://', '').replace('/pedido', '')
            # Separa IP y puerto
            ip, port_str = url.split(':')
            return ip, int(port_str)
        except:
            return 'localhost', 8000

    def get_server_url(self) -> Optional[str]:
        """Obtiene la URL del servidor desde la configuración"""
        if 'ip' in self.config and 'puerto' in self.config:
            return f"http://{self.config['ip']}:{self.config['puerto']}/pedido"
        return None

    def set_server_url(self, url: str) -> None:
        """Establece la URL del servidor en la configuración"""
        ip, puerto = self._parse_url(url)
        self.config['ip'] = ip
        self.config['puerto'] = puerto
        self.save_config()

    def get_server_ip(self) -> str:
        """Obtiene la IP del servidor"""
        return self.config.get('ip', 'localhost')

    def get_server_port(self) -> int:
        """Obtiene el puerto del servidor"""
        return self.config.get('puerto', 8000)

    def request_server_url(self) -> str:
        """Solicita al usuario la IP y puerto del servidor"""
        while True:
            print("\nConfiguración del servidor")
            print("-------------------------")
            ip = input("Ingrese la IP del servidor (ej: localhost o 192.168.1.100): ").strip()
            if not ip:
                print("La IP no puede estar vacía. Por favor, intente nuevamente.")
                continue

            try:
                puerto = input("Ingrese el puerto del servidor (ej: 8000): ").strip()
                if not puerto:
                    print("El puerto no puede estar vacío. Por favor, intente nuevamente.")
                    continue
                
                puerto = int(puerto)
                if puerto < 1 or puerto > 65535:
                    print("El puerto debe estar entre 1 y 65535.")
                    continue

                url = f"http://{ip}:{puerto}/pedido"
                self.set_server_url(url)
                return url

            except ValueError:
                print("El puerto debe ser un número válido.")
                continue
