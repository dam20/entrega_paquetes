"""
Wrapper para ejecutar la aplicación como servicio en Windows
Requiere: pip install pywin32

Para instalar como servicio:
python service_wrapper.py install

Para iniciar/detener:
python service_wrapper.py start
python service_wrapper.py stop

Para desinstalar:
python service_wrapper.py remove
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import time
import subprocess
from pathlib import Path

class ConsultaAppService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ConsultaAppService"
    _svc_display_name_ = "Consulta App - Captura de Pantalla"
    _svc_description_ = "Servicio para captura y procesamiento de pantalla con F4"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        if self.process:
            self.process.terminate()

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def main(self):
        try:
            # Obtener el directorio donde está el servicio
            service_dir = Path(__file__).parent
            app_script = service_dir / "app_gui.py"
            
            # Ejecutar la aplicación principal
            self.process = subprocess.Popen([
                sys.executable, 
                str(app_script)
            ], cwd=str(service_dir))
            
            # Esperar hasta que el servicio sea detenido
            while True:
                if win32event.WaitForSingleObject(self.hWaitStop, 1000) == win32event.WAIT_OBJECT_0:
                    break
                
                # Verificar si el proceso sigue ejecutándose
                if self.process.poll() is not None:
                    # El proceso terminó, reiniciarlo
                    time.sleep(5)
                    self.process = subprocess.Popen([
                        sys.executable, 
                        str(app_script)
                    ], cwd=str(service_dir))
                    
        except Exception as e:
            servicemanager.LogErrorMsg(f"Error en servicio: {e}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        # Ejecutado por el Service Control Manager
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ConsultaAppService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Ejecutado desde línea de comandos
        win32serviceutil.HandleCommandLine(ConsultaAppService)