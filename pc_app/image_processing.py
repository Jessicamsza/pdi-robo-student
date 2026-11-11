"""Operações clássicas de PDI; não altera aquisição nem controle do robô."""
from datetime import datetime
from pathlib import Path
import cv2
import numpy as np
from pipelines import etiqueta, visao_noturna

MODO_NAVEGACAO, MODO_VISAO_NOTURNA, MODO_ETIQUETA = range(3)
CONFIG_PADRAO = {
    'filtro': 'Nenhum', 'tamanho_filtro': 5, 'repeticoes_filtro': 1,
    'brilho': 0, 'contraste': 1.0, 'gamma': 1.0,
    'normalizacao': False, 'clahe': False, 'clahe_clip': 2.0, 'clahe_grade': 4,
    'agucamento': False, 'nitidez': False, 'intensidade_nitidez': 1.0,
    'cinza': False, 'binarizacao': 'Nenhuma', 'limiar': 127,
    'janela_adaptativa': 15, 'constante_c': 4, 'sauvola_k': 0.2,
    'realce_morfologico': 'Nenhum', 'kernel_realce': 15,
    'bordas': 'Nenhuma', 'direcao_sobel': 'Magnitude',
    'kernel_bordas': 3, 'canny_min': 50, 'canny_max': 150,
    'morfologia': 'Nenhuma', 'kernel_morfologia': 3,
    'fft_raio': 4, 'fft_exclusao': 15,
}
config_pdi = CONFIG_PADRAO.copy()
modo_atual = MODO_NAVEGACAO
ultimo_frame = None
ultimo_limiar_otsu = None


def set_modo(mode):
    global modo_atual
    modo_atual = int(mode)


def set_config_pdi(nova_config):
    config_pdi.update(nova_config)


def obter_frame_atual():
    return None if ultimo_frame is None else ultimo_frame.copy()


def salvar_frame(frame=None, prefixo='frame'):
    """Salva um frame original ou processado em capturas_pdi/."""
    imagem = obter_frame_atual() if frame is None else frame
    if imagem is None:
        return None
    pasta = Path(__file__).resolve().parent / 'capturas_pdi'
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f'{prefixo}_{datetime.now():%Y%m%d_%H%M%S_%f}.png'
    return destino if cv2.imwrite(str(destino), imagem) else None


def para_cinza(imagem):
    return cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY) if imagem.ndim == 3 else imagem.copy()


def inteiro_impar(valor, minimo=3, maximo=51):
    valor = max(minimo, min(maximo, int(valor)))
    return valor if valor % 2 else valor + 1 if valor < maximo else valor - 1


def filtro_mediana(imagem, tamanho=5):
    return cv2.medianBlur(imagem, inteiro_impar(tamanho))


def filtro_gaussiano(imagem, tamanho=5):
    t = inteiro_impar(tamanho)
    return cv2.GaussianBlur(imagem, (t, t), 0)


def ajustar_brilho(imagem, valor=30):
    return np.clip(imagem.astype(np.float32) + valor, 0, 255).astype(np.uint8)


def ajustar_contraste(imagem, fator=1.2):
    return np.clip((imagem.astype(np.float32) - 127.5) * fator + 127.5, 0, 255).astype(np.uint8)


def correcao_gamma(imagem, gamma=1.5):
    if gamma <= 0:
        raise ValueError('Gamma deve ser maior que zero.')
    lut = np.clip(255 * (np.arange(256) / 255) ** (1 / gamma), 0, 255).astype(np.uint8)
    return cv2.LUT(imagem, lut)


def normalizar_intensidade(imagem):
    """Normaliza intensidades pelo mínimo e máximo globais."""
    imagem_float = imagem.astype(np.float32)
    valor_min, valor_max = np.min(imagem_float), np.max(imagem_float)
    if valor_min == valor_max:
        return imagem.copy()
    resultado = (imagem_float - valor_min) * (255.0 / (valor_max - valor_min))
    return np.clip(resultado, 0, 255).astype(np.uint8)


def aplicar_clahe(imagem, clip=2.0, grade=4):
    """Realce local de contraste; preserva a representação BGR quando aplicável."""
    grade = max(1, int(grade))
    clahe = cv2.createCLAHE(clipLimit=max(0.1, float(clip)), tileGridSize=(grade, grade))
    if imagem.ndim == 2:
        return clahe.apply(imagem)
    lab = cv2.cvtColor(imagem, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    return cv2.cvtColor(cv2.merge((clahe.apply(l), a, b)), cv2.COLOR_LAB2BGR)


def filtro_agucamento(imagem):
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], np.float32)
    return cv2.filter2D(imagem, -1, kernel)


def melhorar_nitidez(imagem, intensidade=1.0):
    suavizada = cv2.GaussianBlur(imagem, (5, 5), 0)
    return cv2.addWeighted(imagem, 1 + intensidade, suavizada, -intensidade, 0)


def realce_top_black_hat(imagem, metodo='Black-hat', tamanho=15):
    """Top-hat realça detalhes claros; Black-hat, detalhes escuros."""
    cinza = para_cinza(imagem)
    t = inteiro_impar(tamanho)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (t, t))
    operacao = cv2.MORPH_TOPHAT if metodo == 'Top-hat' else cv2.MORPH_BLACKHAT
    return cv2.morphologyEx(cinza, operacao, kernel)


def binarizar_sauvola(imagem, janela=15, k=0.2, r=128.0):
    """Sauvola com média e desvio-padrão locais; saída binária uint8."""
    cinza = para_cinza(imagem).astype(np.float32)
    t = inteiro_impar(janela)
    media = cv2.boxFilter(cinza, cv2.CV_32F, (t, t), normalize=True)
    quadrados = cv2.boxFilter(cinza * cinza, cv2.CV_32F, (t, t), normalize=True)
    desvio = np.sqrt(np.maximum(quadrados - media * media, 0))
    limiar = media * (1 + float(k) * (desvio / r - 1))
    return np.where(cinza > limiar, 255, 0).astype(np.uint8)


def filtro_fft_periodico(imagem, raio=4, exclusao=15):
    """Rejeita um par de picos espectrais fora do centro (heurística experimental)."""
    gray = para_cinza(imagem)
    h, w = gray.shape
    if min(h, w) < 32:
        return imagem.copy()
    espectro = np.fft.fftshift(np.fft.fft2(gray.astype(np.float32)))
    amplitude = np.log1p(np.abs(espectro))
    cy, cx = h // 2, w // 2
    y, x = np.ogrid[:h, :w]
    dist_centro = (y-cy)**2 + (x-cx)**2
    amplitude[dist_centro < int(exclusao)**2] = 0
    py, px = np.unravel_index(np.argmax(amplitude), amplitude.shape)
    sy, sx = (2*cy-py) % h, (2*cx-px) % w
    mascara = np.ones((h, w), np.float32)
    for a, b in ((py, px), (sy, sx)):
        mascara[(y-a)**2 + (x-b)**2 <= int(raio)**2] = 0
    restaurada = np.real(np.fft.ifft2(np.fft.ifftshift(espectro * mascara)))
    resultado = np.clip(restaurada, 0, 255).astype(np.uint8)
    return cv2.cvtColor(resultado, cv2.COLOR_GRAY2BGR) if imagem.ndim == 3 else resultado


def aplicar_ajustes_pdi(frame, config=None, metadados=None):
    """Processa cópia do frame. Config opcional permite testes isolados no laboratório."""
    c = config_pdi if config is None else config
    imagem = frame.copy()
    filtro = c.get('filtro', 'Nenhum')
    t = inteiro_impar(c.get('tamanho_filtro', 5))
    for _ in range(max(1, min(20, int(c.get('repeticoes_filtro', 1))))):
        if filtro == 'Mediana':
            imagem = filtro_mediana(imagem, t)
        elif filtro == 'Gaussiano':
            imagem = filtro_gaussiano(imagem, t)
    if filtro == 'FFT (periodico)':
        imagem = filtro_fft_periodico(imagem, c.get('fft_raio', 4), c.get('fft_exclusao', 15))

    if c.get('brilho', 0):
        imagem = ajustar_brilho(imagem, c['brilho'])
    if c.get('contraste', 1.0) != 1.0:
        imagem = ajustar_contraste(imagem, c['contraste'])
    if c.get('gamma', 1.0) != 1.0:
        imagem = correcao_gamma(imagem, c['gamma'])
    if c.get('normalizacao', False):
        imagem = normalizar_intensidade(imagem)
    if c.get('clahe', False):
        imagem = aplicar_clahe(imagem, c.get('clahe_clip', 2.0), c.get('clahe_grade', 4))
    if c.get('agucamento', False):
        imagem = filtro_agucamento(imagem)
    if c.get('nitidez', False):
        imagem = melhorar_nitidez(imagem, c.get('intensidade_nitidez', 1.0))

    realce = c.get('realce_morfologico', 'Nenhum')
    if realce in ('Top-hat', 'Black-hat'):
        imagem = realce_top_black_hat(imagem, realce, c.get('kernel_realce', 15))

    bin_mode = c.get('binarizacao', 'Nenhuma')
    metodo_bordas = c.get('bordas', 'Nenhuma')
    operacao_morf = c.get('morfologia', 'Nenhuma')
    if c.get('cinza') or bin_mode != 'Nenhuma' or metodo_bordas != 'Nenhuma' or operacao_morf != 'Nenhuma':
        imagem = para_cinza(imagem)
    if bin_mode == 'Manual':
        _, imagem = cv2.threshold(imagem, int(c.get('limiar', 127)), 255, cv2.THRESH_BINARY)
    elif bin_mode == 'Otsu':
        valor, imagem = cv2.threshold(imagem, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if metadados is not None:
            metadados['limiar_otsu'] = valor
    elif bin_mode in ('Adaptativa Gaussiana', 'Adaptativa'):
        imagem = cv2.adaptiveThreshold(imagem, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, inteiro_impar(c.get('janela_adaptativa', 15)),
                                       float(c.get('constante_c', 4)))
    elif bin_mode == 'Sauvola':
        imagem = binarizar_sauvola(imagem, c.get('janela_adaptativa', 15), c.get('sauvola_k', 0.2))

    if metodo_bordas != 'Nenhuma':
        gray = para_cinza(imagem)
        k = inteiro_impar(c.get('kernel_bordas', 3), 3, 7)
        if metodo_bordas == 'Sobel':
            gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=k)
            gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=k)
            direcao = c.get('direcao_sobel', 'Magnitude')
            gradiente = np.abs(gx) if direcao == 'X' else np.abs(gy) if direcao == 'Y' else cv2.magnitude(gx, gy)
            imagem = cv2.convertScaleAbs(gradiente, alpha=255.0 / max(float(gradiente.max()), 1.0))
        elif metodo_bordas == 'Laplaciano':
            imagem = cv2.convertScaleAbs(cv2.Laplacian(gray, cv2.CV_32F, ksize=k))
        elif metodo_bordas == 'Canny':
            imagem = cv2.Canny(gray, int(c.get('canny_min', 50)), int(c.get('canny_max', 150)))
    if operacao_morf != 'Nenhuma':
        k = max(1, int(c.get('kernel_morfologia', 3)))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
        ops = {'Erosao': cv2.MORPH_ERODE, 'Dilatacao': cv2.MORPH_DILATE,
               'Abertura': cv2.MORPH_OPEN, 'Fechamento': cv2.MORPH_CLOSE}
        if operacao_morf in ops:
            imagem = cv2.morphologyEx(imagem, ops[operacao_morf], kernel)
    return imagem


def process_frame(frame_bgr):
    global ultimo_frame, ultimo_limiar_otsu
    if frame_bgr is None:
        return None
    ultimo_frame = frame_bgr.copy()
    if modo_atual == MODO_NAVEGACAO:
        meta = {}
        imagem = aplicar_ajustes_pdi(frame_bgr, metadados=meta)
        ultimo_limiar_otsu = meta.get('limiar_otsu')
        if imagem.ndim == 2:
            imagem = cv2.cvtColor(imagem, cv2.COLOR_GRAY2BGR)
        cv2.putText(imagem, 'MODO: 0 - NAVEGACAO', (5, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        return imagem
    if modo_atual == MODO_VISAO_NOTURNA:
        return visao_noturna.processar(frame_bgr)
    if modo_atual == MODO_ETIQUETA:
        return etiqueta.processar(frame_bgr)
    return frame_bgr.copy()
