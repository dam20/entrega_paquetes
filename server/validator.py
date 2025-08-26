import re
from typing import Tuple, Optional

class PiezaValidator:
    """Validador para números de pieza con formato específico"""
    
    # Códigos válidos para las primeras dos letras
    CODIGOS_VALIDOS = {
        'CU', 'SU', 'EU', 'PU', 'XU', 'CC', 'CD', 'CL', 'CM', 'CO', 'CP', 
        'DE', 'DI', 'EC', 'EE', 'EO', 'EP', 'GC', 'GD', 'GE', 'GF', 'GO', 
        'GR', 'GS', 'HC', 'HD', 'HE', 'HU', 'IN', 'IS', 'JP', 'LC', 'LS', 
        'ND', 'MD', 'ME', 'MC', 'MS', 'MU', 'MX', 'OL', 'PC', 'PP', 'RD', 
        'RE', 'RP', 'RR', 'SD', 'SL', 'SP', 'SR', 'TC', 'TD', 'TL', 'UP', 
        'CX', 'XP', 'XX', 'XR'
    }
    
    @classmethod
    def validar_formato_completo(cls, pieza: str) -> bool:
        """
        Valida que la pieza tenga el formato completo: 2 letras + 9 dígitos + AR
        
        Args:
            pieza (str): Número de pieza a validar
            
        Returns:
            bool: True si cumple el formato completo
        """
        if not pieza or len(pieza) != 13:
            return False
            
        # Patrón: 2 letras mayúsculas + 9 dígitos + AR
        patron = re.compile(r'^([A-Z]{2})(\d{9})(AR)$')
        match = patron.match(pieza.upper())
        
        if not match:
            return False
            
        codigo_inicial = match.group(1)
        return codigo_inicial in cls.CODIGOS_VALIDOS
    
    @classmethod
    def corregir_pieza_ocr(cls, texto_ocr: str) -> str:
        """
        Intenta corregir errores comunes del OCR en números de pieza.
        Ajusta estas correcciones basándote en los errores típicos de EasyOCR.
        
        Args:
            texto_ocr (str): Texto extraído por OCR
            
        Returns:
            str: Pieza corregida o texto original si no se puede corregir
        """
        if not texto_ocr:
            return texto_ocr

        # Limpiar espacios y convertir a mayúsculas
        texto_limpio = re.sub(r'\s+', '', texto_ocr.upper())

        # Si no tiene la longitud esperada, devolver original
        if len(texto_limpio) != 13:
            return texto_ocr

        caracteres = list(texto_limpio)

        # Corregir primeras 2 posiciones (deben ser letras)
        for i in range(2):
            caracteres[i] = cls.corregir_caracter_letra(caracteres[i])

        # Corregir siguientes 9 posiciones (deben ser números)
        for i in range(2, 11):
            caracteres[i] = cls.corregir_caracter_numero(caracteres[i])

        # Corregir los últimos 2 caracteres (deben ser letras: 'AR')
        caracteres[-2] = cls.corregir_caracter_letra(caracteres[-2])
        caracteres[-1] = cls.corregir_caracter_letra(caracteres[-1])

        resultado = ''.join(caracteres)

        # Validar formato final
        if cls.validar_formato_completo(resultado):
            return resultado

        return texto_ocr


    @classmethod
    def corregir_caracter_letra(cls, caracter: str) -> str:
        """
        Corrige un carácter que debería ser una letra (por errores comunes de OCR).
        """
        correcciones = {
            '0': 'O', '1': 'I', '5': 'S', '6': 'G', '8': 'B', '4': 'A', '0': 'D'
        }
        return correcciones.get(caracter, caracter)

    @classmethod
    def corregir_caracter_numero(cls, caracter: str) -> str:
        """
        Corrige un carácter que debería ser un número (por errores comunes de OCR).
        """
        correcciones = {
            'O': '0', 'I': '1', 'L': '1', 'S': '5', 'B': '8', 'G': '6', 'Z': '2', 'D': '0'
        }
        return correcciones.get(caracter, caracter)


class LugarGuardaValidator:
    """Validador para lugares de guarda"""

    @classmethod
    def corregir_lugar_guarda_ocr(cls, texto_ocr: str) -> str:
        """
        Corrige errores comunes del OCR en lugares de guarda (solo numéricos).
        
        Args:
            texto_ocr (str): Texto reconocido por OCR

        Returns:
            str: Texto corregido si es válido, o el original si no se pudo corregir
        """
        if not texto_ocr:
            return texto_ocr

        # Limpiar espacios y convertir a mayúsculas
        texto_limpio = re.sub(r'\s+', '', texto_ocr.upper())

        # Corregir cada carácter individualmente usando la función numérica
        caracteres_corregidos = [
            PiezaValidator.corregir_caracter_numero(c) for c in texto_limpio
        ]

        resultado = ''.join(caracteres_corregidos)

        # Validar que el resultado final sea numérico
        if resultado.isdigit():
            return resultado

        return texto_ocr  # Si no se pudo corregir completamente, devolver el original
    
    @classmethod
    def validar_lugar_guarda(cls, lugar: str) -> bool:
        """
        Valida que el lugar de guarda sea válido. Acepta:
        - Solo números (hasta 3 dígitos)
        - Números precedidos por '#' (ej: '#104', '#58')
        
        Args:
            lugar (str): Lugar de guarda a validar
            
        Returns:
            bool: True si es válido
        """
        if not lugar:
            return False

        lugar_limpio = lugar.strip().upper()

        # Caso 1: Solo numérico (hasta 3 dígitos)
        if lugar_limpio.isdigit() and len(lugar_limpio) <= 3:
            return True

        # Caso 2: Comienza con '#' seguido de 1 a 3 dígitos
        if re.fullmatch(r'#\d{1,3}', lugar_limpio):
            return True

        return False
    
    @classmethod
    def normalizar_lugar_guarda(cls, lugar: str) -> Tuple[str, bool]:
        """
        Normaliza el lugar de guarda a un formato estándar.
        Esta función debe ser el último paso de corrección.

        Args:
            lugar (str): Lugar de guarda original

        Returns:
            Tuple[str, bool]: (Lugar normalizado como str, True si tenía #, False si no)
        """
        if not lugar:
            return lugar, False

        lugar_limpio = lugar.strip().upper()

        # Caso 1: Solo numérico (hasta 3 dígitos)
        if lugar_limpio.isdigit() and len(lugar_limpio) <= 3:
            return lugar_limpio, False

        # Caso 2: Comienza con '#' seguido de 1 a 3 dígitos
        if re.fullmatch(r'#\d{1,3}', lugar_limpio):
            return lugar_limpio[1:], True

        return lugar, False


def test_validator():
    """Función de prueba para los validadores"""
    print("=== PRUEBAS DE VALIDACIÓN ===")
    
    # Pruebas de piezas
    piezas_prueba = [
        "SD279101126AR", "CU123456789AR", "XX999888777AR", "C01231231234R",
        "ZZ123456789AR",  # Código inválido
        "SD27910112AR",   # Muy corto
        "SD2791011268AR", # Muy largo
        "SD279101126AR", # con espacios
        "SD279101126AR ", # con espacios al final
        "SD279101126AR", # con espacios
        "S0279101126AR", # 0 -> O
        "SD279101126AAR", # AR error
    ]
    
    print("\n🔧 VALIDADOR DE PIEZAS:")
    for pieza in piezas_prueba:
        corregido = PiezaValidator.corregir_pieza_ocr(pieza)
        valida = PiezaValidator.validar_formato_completo(corregido)
        print(f"  Original: '{pieza}' -> Corregido: '{corregido}' -> {'✅ Válida' if valida else '❌ Inválida'}")
    
    # Pruebas de lugares
    lugares_prueba = [
        "84", "123", "MESA", 
        "123MESA",
        "58", "B40", # Error OCR
        "1234", "INVALID",
        "58 P. RESTANTE", # Nueva variación
        "#58",
        "84A", # Número seguido de letra
    ]
    
    print("\n📍 VALIDADOR DE LUGARES DE GUARDA:")
    for lugar in lugares_prueba:
        corregido = LugarGuardaValidator.corregir_lugar_guarda_ocr(lugar)
        # normalizado = LugarGuardaValidator.normalizar_lugar_guarda(corregido) # Aplica normalización a lo corregido
        valido = LugarGuardaValidator.validar_lugar_guarda(corregido) # Valida lo normalizado
        print(f"  Original: '{lugar}' -> Corregido: '{corregido}' -> {'✅ Válido' if valido else '❌ Inválido'}")

if __name__ == "__main__":
    test_validator()