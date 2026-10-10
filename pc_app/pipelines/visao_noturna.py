import cv2

def processar(frame):
    """
    Módulo: Desafio 01 - Sub-rotina de Baixa Iluminação.

    Objetivo: Permitir a condução do robô sem colisões em ambientes escuros.

    Técnica: Ajuste linear de brilho

    Parâmetros: alpha 1.3 (contraste), beta 40 (brilho), kernel mediana 5 (borrão leve).
    """
    
    frame_ilu = cv2.convertScaleAbs(frame, alpha=1.3, beta=40)
    frame_limpo = cv2.medianBlur(frame_ilu, 5)
    
    cv2.putText(frame_limpo, "MODO: 1 - VISAO NOTURNA", (5, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 2)
    
    return frame_limpo