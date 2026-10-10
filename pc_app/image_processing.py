import cv2
import numpy as np
from pipelines import visao_noturna, etiqueta

modo_atual = 0
def set_modo(mode):
    """Função chamada pelo main.py para trocar o filtro."""
    global modo_atual
    modo_atual = mode


def process_frame(frame_bgr):
    """ponto de implementação das técnicas de processamento digital de imagens.

    entrada:
        frame_bgr: imagem recebida da infraestrutura da atividade.

    saída:
        imagem que será exibida ao operador. a saída pode permanecer bgr,
        ser convertida para escala de cinza ou assumir outra representação
        compatível com a camada de visualização.

    contrato:
        - não altere a camada de aquisição ou de controle para implementar pdi;
        - trate a imagem recebida como a única observação disponível da cena;
        - mantenha o processamento concentrado neste arquivo;
        - retorne uma imagem válida sempre que houver uma entrada válida.
    """
    if frame_bgr is None:
        return None

    # área de trabalho:
    # 1. observe a imagem e formule uma hipótese sobre o problema visual;
    # 2. escolha uma técnica coerente com essa hipótese;
    # 3. ajuste e justifique os parâmetros usados;
    # 4. retorne a imagem que será usada pelo operador.



    if modo_atual == 0:
        #Condições Normais - sem processamento
        frame_saida = frame_bgr.copy()
        cv2.putText(frame_saida, "MODO: 0 - NAVEGACAO", (5, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 2)
        return frame_saida

    elif modo_atual == 1:
        return visao_noturna.processar(frame_bgr)

    elif modo_atual == 2:
        return etiqueta.processar(frame_bgr)

    return frame_bgr.copy()

