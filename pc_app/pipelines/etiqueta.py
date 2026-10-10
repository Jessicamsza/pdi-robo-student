import cv2

def processar(frame):
    """
    Módulo: Desafio 02 - leitura de etiqueta.

    Objetivo: Melhorar a imagem para que uma pessoa leia as  informações:produto, lote, fabricação, validade e peso.

    Técnica: Conversão para escala de cinza + CLAHE

    Parâmetros: clipLimit=3.0 (força do contraste), tileGridSize=(8,8) (tamanho dos blocos de análise)
    """

    frame_cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    frame_clahe = clahe.apply(frame_cinza)

    frame_saida = cv2.cvtColor(frame_clahe, cv2.COLOR_GRAY2BGR)
    
    cv2.putText(frame_saida, "MODO: 2 - LEITURA DE ETIQUETA", (5, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 2)
    
    return frame_saida