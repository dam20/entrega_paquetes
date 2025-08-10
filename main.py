import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from deposito.app import DepositoApp
from entrega.app import EntregaApp

class SectorSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Selección de Sector")
        self.setGeometry(300, 300, 300, 150)
        
        layout = QVBoxLayout()
        
        # Título
        titulo = QLabel("Seleccione el sector:")
        titulo.setStyleSheet("font-size: 14pt; margin-bottom: 10px;")
        layout.addWidget(titulo)
        
        # Botón para Depósito
        btn_deposito = QPushButton("Depósito")
        btn_deposito.setStyleSheet("font-size: 12pt; padding: 10px;")
        btn_deposito.clicked.connect(self.abrir_deposito)
        layout.addWidget(btn_deposito)
        
        # Botón para Entrega
        btn_entrega = QPushButton("Entrega")
        btn_entrega.setStyleSheet("font-size: 12pt; padding: 10px;")
        btn_entrega.clicked.connect(self.abrir_entrega)
        layout.addWidget(btn_entrega)
        
        self.setLayout(layout)
    
    def abrir_deposito(self):
        self.close()
        self.window = DepositoApp()
        self.window.show()
    
    def abrir_entrega(self):
        self.close()
        self.window = EntregaApp()
        self.window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    selector = SectorSelector()
    selector.show()
    sys.exit(app.exec())
