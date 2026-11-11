import tkinter as tk
import base64
from typing import Any
import cv2
import image_processing
import video_control


class PainelPDI:
    """Painel separado do console, com abas e rolagem."""
    FUNDO = "#23272f"
    BARRA = "#303741"
    BORDA = "#414854"
    BOTAO = "#4b505a"
    SELECIONADO = "#2d7d5f"
    VERDE = "#46b991"
    TEXTO = "#f0f0f0"
    TRILHO = "#5a5f69"
    VERMELHO = "#784141"

    def __init__(self):
        self.aberto = False
        self._lab_original = None
        self._lab_config: dict[str, Any] = {}
        self.config: dict[str, Any] = {
            "filtro": "Nenhum", "repeticoes_filtro": 1,
            "brilho": 0, "contraste": 1.0, "gamma": 1.0,
            "normalizacao": False, "clahe": False, "clahe_clip": 2.0, "clahe_grade": 4,
            "agucamento": False, "nitidez": False, "intensidade_nitidez": 1.0,
            "cinza": False, "binarizacao": "Nenhuma",
            "limiar": 127, "janela_adaptativa": 15, "constante_c": 4,
            "sauvola_k": 0.2, "realce_morfologico": "Nenhum", "kernel_realce": 15,
            "bordas": "Nenhuma", "direcao_sobel": "Magnitude",
            "kernel_bordas": 3, "canny_min": 50, "canny_max": 150,
            "morfologia": "Nenhuma", "kernel_morfologia": 3,
            "tamanho_filtro": 5, "fft_raio": 4, "fft_exclusao": 15,
        }
        self.limites = {
            "brilho": (-100, 100), "contraste": (0.2, 3.0),
            "gamma": (0.2, 3.0), "intensidade_nitidez": (0.0, 2.0),
            "limiar": (0, 255), "janela_adaptativa": (3, 51),
            "constante_c": (-20, 20), "sauvola_k": (0.0, 0.5),
            "clahe_clip": (0.5, 8.0), "clahe_grade": (2, 16),
            "kernel_realce": (3, 51), "kernel_bordas": (3, 7),
            "canny_min": (0, 255), "canny_max": (0, 255),
            "kernel_morfologia": (1, 15), "tamanho_filtro": (3, 15),
            "fft_raio": (1, 15), "fft_exclusao": (5, 80),
        }
        self.filtros = ["Nenhum", "Mediana", "Gaussiano"]
        self.janela = tk.Tk()
        self.janela.title("Painel de Processamento PDI")
        self.janela.geometry("530x620")
        self.janela.resizable(False, False)
        self.janela.configure(bg=self.FUNDO)
        self.janela.protocol("WM_DELETE_WINDOW", self.fechar)
        cabecalho = tk.Canvas(self.janela, height=65, bg=self.BARRA,
                             highlightthickness=0, borderwidth=0)
        cabecalho.pack(fill="x")
        cabecalho.create_text(25, 20, text="PAINEL DE PROCESSAMENTO PDI",
                             anchor="nw", fill=self.TEXTO, font=("Arial", 19))
        abas = tk.Frame(self.janela, bg=self.FUNDO)
        abas.pack(fill="x", padx=25, pady=(12, 6))
        self.botoes_abas = {}
        for nome in ("Principal", "Segmentacao", "Ruidos", "Video", "Laboratorio"):
            botao = tk.Button(
                abas, text=nome, font=("Arial", 10), fg=self.TEXTO,
                bg=self.BOTAO, activeforeground=self.TEXTO,
                activebackground=self.SELECIONADO, relief="flat", bd=0,
                command=lambda aba=nome: self._trocar_aba(aba)
            )
            botao.pack(side="left", fill="x", expand=True, padx=(0, 5))
            self.botoes_abas[nome] = botao
        self.areas = {}
        for nome, altura in (("Principal", 840), ("Segmentacao", 1560),
                            ("Ruidos", 650), ("Video", 350), ("Laboratorio", 550)):
            area = tk.Frame(self.janela, bg=self.FUNDO)
            canvas = tk.Canvas(area, bg=self.FUNDO, highlightthickness=0,
                               borderwidth=0, scrollregion=(0, 0, 505, altura))
            barra = tk.Scrollbar(area, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=barra.set)
            canvas.pack(side="left", fill="both", expand=True)
            barra.pack(side="right", fill="y")
            canvas.bind("<MouseWheel>", lambda e, c=canvas: self._rolar(e, c))
            canvas.bind("<Button-1>", self._pressionar)
            canvas.bind("<B1-Motion>", self._mover)
            canvas.bind("<ButtonRelease-1>", self._soltar)
            self.areas[nome] = (area, canvas)
        self.aba_atual = "Principal"
        self.canvas = self.areas["Principal"][1]
        self.botoes = {}
        self.sliders = {}
        self.arrastando = None
        self._arrastando_video = False
        self._trocar_aba("Principal")
        self.janela.withdraw()

    def _rolar(self, evento, canvas):
        canvas.yview_scroll(-1 if evento.delta > 0 else 1, "units")

    def _trocar_aba(self, nome):
        self.aba_atual = nome
        self.arrastando = None
        self._arrastando_video = False
        for aba, (area, _) in self.areas.items():
            area.pack_forget()
            self.botoes_abas[aba].configure(
                bg=self.SELECIONADO if aba == nome else self.BOTAO
            )
        self.areas[nome][0].pack(fill="both", expand=True)
        self.canvas = self.areas[nome][1]
        self._desenhar()

    def _texto(self, x, y, texto, tamanho=16, negrito=False, cor=None):
        self.canvas.create_text(x, y, text=texto, anchor="nw",
                                fill=cor or self.TEXTO,
                                font=("Arial", tamanho, "bold" if negrito else "normal"))

    def _retangulo(self, x1, y1, x2, y2, cor, raio=6, contorno=""):
        r = min(raio, (x2-x1)/2, (y2-y1)/2)
        pontos = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r,
                  x2,y2-r, x2,y2, x2-r,y2, x1+r,y2,
                  x1,y2, x1,y2-r, x1,y1+r, x1,y1]
        return self.canvas.create_polygon(pontos, smooth=True,
                                          splinesteps=12, fill=cor,
                                          outline=contorno, width=1)

    def _botao(self, chave, texto, x1, y1, x2, y2, ativo=False):
        self.botoes[chave] = (x1, y1, x2, y2)
        self._retangulo(x1, y1, x2, y2, self.SELECIONADO if ativo else self.BOTAO)
        self._texto(x1+10, y1+7, texto, 15)

    def _check(self, chave, texto, y):
        self.botoes[chave] = (25, y, 480, y+28)
        self.canvas.create_rectangle(25, y+2, 45, y+22,
                                     outline="#dcdcdc", width=2)
        if self.config[chave]:
            self.canvas.create_rectangle(31, y+8, 39, y+16,
                                         fill=self.VERDE, outline=self.VERDE)
        self._texto(57, y, texto, 16)

    def _slider(self, chave, texto, y):
        minimo, maximo = self.limites[chave]
        valor = self.config[chave]
        self._texto(25, y-35, f"{texto}: {valor:g}", 18)
        self._retangulo(25, y, 470, y+7, self.TRILHO, 3)
        proporcao = (valor-minimo)/(maximo-minimo)
        px = 25 + round(proporcao*445)
        self.canvas.create_oval(px-10, y-7, px+10, y+13,
                                fill=self.VERDE, outline="")
        self.sliders[chave] = (25, y-15, 470, y+23)

    def _opcoes(self, chave, opcoes, y, colunas=2):
        largura = 445 / colunas
        for i, valor in enumerate(opcoes):
            x = 25 + (i % colunas) * largura
            yy = y + (i // colunas) * 43
            self._botao(f"set:{chave}:{valor}", valor, x, yy,
                        x + largura - 8, yy + 34, self.config[chave] == valor)

    def _desenhar(self):
        self.canvas.delete("all")
        self.botoes = {}
        self.sliders = {}
        if self.aba_atual == "Principal":
            self._desenhar_principal()
        elif self.aba_atual == "Segmentacao":
            self._desenhar_segmentacao()
        elif self.aba_atual == "Ruidos":
            self._desenhar_ruidos()
        elif self.aba_atual == "Video":
            self._desenhar_video()
        else:
            self._desenhar_laboratorio()

    def _desenhar_principal(self):
        self._texto(25, 20, "Iluminacao", 19)
        self._slider("brilho", "Brilho", 100)
        self._slider("contraste", "Contraste", 175)
        self._slider("gamma", "Gamma", 250)
        self._check("normalizacao", "Normalizacao", 285)
        self._check("clahe", "CLAHE", 320)
        self._slider("clahe_clip", "CLAHE clip limit", 405)
        self._slider("clahe_grade", "CLAHE grade", 485)
        self._texto(25, 525, "Nitidez", 19)
        self._check("agucamento", "Agucamento", 565)
        self._check("nitidez", "Unsharp Masking", 600)
        self._slider("intensidade_nitidez", "Intensidade", 675)
        self._botao("restaurar", "Restaurar tudo", 270, 730, 470, 765)

    def _desenhar_segmentacao(self):
        self._texto(25, 20, "Binarizacao", 19)
        self._check("cinza", "Escala de cinza", 54)
        self._opcoes("binarizacao", ("Nenhuma", "Manual", "Otsu", "Adaptativa Gaussiana", "Sauvola"), 99)
        self._slider("limiar", "Limiar manual", 300)
        self._slider("janela_adaptativa", "Janela local", 375)
        self._slider("constante_c", "Constante C (gaussiana)", 450)
        self._slider("sauvola_k", "Sauvola k", 525)
        self._texto(25, 565, "Otsu calcula um limiar global automaticamente.", 13)
        self._texto(25, 615, "Realce morfologico", 19)
        self._opcoes("realce_morfologico", ("Nenhum", "Top-hat", "Black-hat"), 655)
        self._slider("kernel_realce", "Janela do realce", 780)
        self._texto(25, 825, "Deteccao de bordas", 19)
        self._opcoes("bordas", ("Nenhuma", "Sobel", "Laplaciano", "Canny"), 865)
        self._opcoes("direcao_sobel", ("X", "Y", "Magnitude"), 958, 3)
        self._slider("kernel_bordas", "Kernel Sobel/Laplaciano", 1085)
        self._slider("canny_min", "Canny minimo", 1160)
        self._slider("canny_max", "Canny maximo", 1235)
        self._texto(25, 1280, "Morfologia", 19)
        self._opcoes("morfologia", ("Nenhuma", "Erosao", "Dilatacao", "Abertura", "Fechamento"), 1320)
        self._slider("kernel_morfologia", "Kernel morfologia", 1490)

    def _desenhar_ruidos(self):
        self._texto(25, 20, "Filtros de ruido", 19)
        self._opcoes("filtro", ("Nenhum", "Mediana", "Gaussiano", "FFT (periodico)"), 65)
        self._texto(25, 174, "Sal e pimenta: Mediana", 14)
        self._texto(25, 197, "Ruido leve: Gaussiano", 14)
        self._texto(25, 220, "Faixas periodicas: FFT experimental", 14)
        self._slider("tamanho_filtro", "Tamanho do filtro", 290)
        self._texto(25, 325, "Repeticoes", 16)
        self._botao("rep_menos", "-", 255, 325, 305, 360)
        self._texto(337, 329, str(self.config["repeticoes_filtro"]), 18)
        self._botao("rep_mais", "+", 405, 325, 460, 360)
        self._slider("fft_raio", "Raio notch FFT", 425)
        self._slider("fft_exclusao", "Exclusao central FFT", 505)
        self._texto(25, 550, "Desfoque nao e recuperado por suavizacao.", 13)

    def _desenhar_laboratorio(self):
        self._texto(25, 20, "Laboratorio de imagens", 19)
        self._texto(25, 70, "A imagem fica congelada para os testes.", 14)
        self._botao("lab_capturar", "Capturar frame", 25, 125, 230, 160)
        self._botao("lab_abrir", "Abrir imagem", 255, 125, 470, 160)
        self._botao("lab_previa", "Comparar antes / depois", 25, 192, 470, 228)
        self._botao("lab_salvar", "Salvar processada", 25, 260, 235, 296)
        self._botao("lab_aplicar", "Aplicar no video", 255, 260, 470, 296)
        self._texto(25, 345, "Parametros do laboratorio sao independentes", 14)
        self._texto(25, 370, "ate clicar em 'Aplicar no video'.", 14)
        self._texto(25, 425, "Os controles das outras abas ajustam o video.", 13)
        self._texto(25, 450, "No laboratorio, use as opcoes na previa.", 13)

    def _desenhar_video(self):
        self._texto(25, 20, "Controle do video", 19)
        estado = video_control.estado()
        self.barra_video = (25, 77, 480, 99)
        self._retangulo(25, 84, 480, 92, self.TRILHO, 3)
        if estado:
            p = max(0.0, min(1.0, estado["posicao"]))
            px = 25 + round(p*455)
            self.canvas.create_oval(px-9, 79, px+9, 97,
                                    fill=self.VERDE, outline="")
            self._texto(25, 55,
                        f"{self._tempo(estado['segundos'])} / {self._tempo(estado['duracao'])}", 13)
        else:
            self._texto(25, 55, "Disponivel apenas para video local", 13)
        self._botao("voltar_video", "-5 s", 25, 115, 130, 150)
        self._botao("pausar_video", "Reproduzir" if estado and estado["pausado"] else "Pausar",
                    155, 115, 350, 150)
        self._botao("avancar_video", "+5 s", 375, 115, 480, 150)
    @staticmethod

    def _tempo(segundos):
        segundos = max(0, int(segundos))
        return f"{segundos // 60:02d}:{segundos % 60:02d}"
    @staticmethod

    def _dentro(pos, area):
        x, y = pos
        x1, y1, x2, y2 = area
        return x1 <= x <= x2 and y1 <= y <= y2

    def _pressionar(self, evento):
        pos = (evento.x, self.canvas.canvasy(evento.y))
        if self.aba_atual == "Video" and self._dentro(pos, self.barra_video):
            if video_control.estado() is not None:
                self._arrastando_video = True
                self._buscar_video(evento.x)
            return
        for nome, area in self.botoes.items():
            if not self._dentro(pos, area):
                continue
            if nome.startswith("set:"):
                _, chave, valor = nome.split(":", 2)
                self.config[chave] = valor
            elif nome == "rep_menos":
                self.config["repeticoes_filtro"] = max(1, self.config["repeticoes_filtro"]-1)
            elif nome == "rep_mais":
                self.config["repeticoes_filtro"] = min(20, self.config["repeticoes_filtro"]+1)
            elif nome == "restaurar":
                self.restaurar()
            elif nome == "voltar_video":
                video_control.deslocar(-5)
            elif nome == "pausar_video":
                video_control.pausar_ou_reproduzir()
            elif nome == "avancar_video":
                video_control.deslocar(5)
            elif nome.startswith("lab_"):
                self._laboratorio(nome[4:])
            else:
                self.config[nome] = not self.config[nome]
            self._desenhar()
            return
        for chave, area in self.sliders.items():
            if self._dentro(pos, area):
                self.arrastando = chave
                self._atualizar_slider(evento.x)
                return

    def _atualizar_slider(self, x):
        if self.arrastando is None:
            return
        minimo, maximo = self.limites[self.arrastando]
        proporcao = max(0, min(1, (x-25)/445))
        valor = minimo + proporcao*(maximo-minimo)
        if self.arrastando in ("brilho", "limiar", "janela_adaptativa", "constante_c",
                               "kernel_bordas", "kernel_morfologia", "kernel_realce", "clahe_grade", "canny_min",
                               "canny_max", "tamanho_filtro", "fft_raio", "fft_exclusao"):
            valor = int(round(valor))
            if self.arrastando in ("janela_adaptativa", "kernel_bordas", "tamanho_filtro", "kernel_realce"):
                valor = image_processing.inteiro_impar(valor, 3, int(maximo))
        self.config[self.arrastando] = valor
        self._desenhar()

    def _buscar_video(self, x):
        video_control.posicionar(max(0.0, min(1.0, (x-25)/455)))
        self._desenhar()

    def _mover(self, evento):
        if self._arrastando_video:
            self._buscar_video(evento.x)
        else:
            self._atualizar_slider(evento.x)

    def _soltar(self, _evento):
        self.arrastando = None
        self._arrastando_video = False

    def _laboratorio(self, acao):
        from tkinter import filedialog, messagebox
        if acao == "capturar":
            self._lab_original = image_processing.obter_frame_atual()
            if self._lab_original is None:
                messagebox.showwarning("Laboratorio", "Nenhum frame recebido ainda.")
                return
            self._lab_config = self.config.copy()
        elif acao == "abrir":
            caminho = filedialog.askopenfilename(filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp")])
            if not caminho:
                return
            from pathlib import Path
            import numpy as np
            self._lab_original = cv2.imdecode(np.fromfile(caminho, dtype=np.uint8), cv2.IMREAD_COLOR)
            if self._lab_original is None:
                messagebox.showerror("Laboratorio", "Nao foi possivel abrir a imagem.")
                return
            self._lab_config = self.config.copy()
        elif self._lab_original is None:
            messagebox.showwarning("Laboratorio", "Capture ou abra uma imagem primeiro.")
            return
        if self._lab_original is None:
            messagebox.showwarning("Laboratorio", "Capture ou abra uma imagem primeiro.")
            return
        if acao == "aplicar":
            self.config.update(self._lab_config)
            self._desenhar()
            return
        if acao == "salvar":
            imagem = image_processing.aplicar_ajustes_pdi(self._lab_original, self._lab_config)
            destino = image_processing.salvar_frame(imagem, "laboratorio")
            messagebox.showinfo("Laboratorio", f"Salvo em: {destino}" if destino else "Falha ao salvar")
            return
        self._abrir_previa_lab()

    def _abrir_previa_lab(self):
        if self._lab_original is None or not self._lab_config:
            return
        if hasattr(self, "_janela_lab") and self._janela_lab.winfo_exists():
            self._janela_lab.destroy()
        self._janela_lab = tk.Toplevel(self.janela)
        self._janela_lab.title("Laboratorio: antes e depois")
        self._janela_lab.configure(bg=self.FUNDO)
        self._janela_lab.geometry("740x510")
        topo = tk.Frame(self._janela_lab, bg=self.FUNDO)
        topo.pack(fill="x", pady=8)
        tk.Label(topo, text="Metodo", bg=self.FUNDO, fg=self.TEXTO).pack(side="left")
        metodo = tk.StringVar(value=self._lab_config["binarizacao"])
        tk.OptionMenu(topo, metodo, "Nenhuma", "Manual", "Otsu", "Adaptativa Gaussiana").pack(side="left")
        tk.Label(topo, text="Limiar", bg=self.FUNDO, fg=self.TEXTO).pack(side="left")
        limiar = tk.IntVar(value=self._lab_config["limiar"])
        tk.Spinbox(topo, from_=0, to=255, width=4, textvariable=limiar).pack(side="left")
        tk.Label(topo, text="Janela", bg=self.FUNDO, fg=self.TEXTO).pack(side="left")
        janela = tk.IntVar(value=self._lab_config["janela_adaptativa"])
        tk.Spinbox(topo, from_=3, to=51, increment=2, width=4, textvariable=janela).pack(side="left")
        tk.Label(topo, text="C", bg=self.FUNDO, fg=self.TEXTO).pack(side="left")
        constante = tk.IntVar(value=self._lab_config["constante_c"])
        tk.Spinbox(topo, from_=-20, to=20, width=4, textvariable=constante).pack(side="left")
        imagens = tk.Frame(self._janela_lab, bg=self.FUNDO)
        imagens.pack(fill="both", expand=True)
        original_lbl = tk.Label(imagens, bg=self.FUNDO, fg=self.TEXTO)
        original_lbl.pack(side="left", expand=True)
        proc_lbl = tk.Label(imagens, bg=self.FUNDO, fg=self.TEXTO)
        proc_lbl.pack(side="left", expand=True)
        self._imagens_lab = []
        def atualizar():
            try:
                self._lab_config.update(binarizacao=metodo.get(), limiar=int(limiar.get()),
                    janela_adaptativa=image_processing.inteiro_impar(janela.get()),
                    constante_c=int(constante.get()))
                proc = image_processing.aplicar_ajustes_pdi(self._lab_original, self._lab_config)
                self._imagens_lab = []
                for lbl, frame in ((original_lbl, self._lab_original), (proc_lbl, proc)):
                    if frame is None:
                        continue
                    altura, largura = frame.shape[:2]
                    escala = min(330 / largura, 350 / altura, 1.0)
                    destino: tuple[int, int] = (
                        max(1, int(largura * escala)),
                        max(1, int(altura * escala)),
                    )
                    mini = cv2.resize(src=frame, dsize=destino)
                    ok, dados = cv2.imencode(".png", mini)
                    if ok:
                        foto = tk.PhotoImage(data=base64.b64encode(dados.tobytes()).decode("ascii"))
                        lbl.configure(image=foto)
                        self._imagens_lab.append(foto)
            except (ValueError, tk.TclError) as e:
                print("Parametro invalido no laboratorio:", e)
        tk.Button(self._janela_lab, text="Atualizar comparacao", command=atualizar,
                  bg=self.BOTAO, fg=self.TEXTO).pack(pady=10)
        atualizar()

    def restaurar(self):
        self.config.clear()
        self.config.update(image_processing.CONFIG_PADRAO)
        self._desenhar()

    def abrir(self):
        self.aberto = True
        self.janela.deiconify()
        self.janela.lift()

    def fechar(self):
        self.aberto = False
        self.arrastando = None
        self._arrastando_video = False
        self.janela.withdraw()

    def alternar(self):
        if self.aberto:
            self.fechar()
        else:
            self.abrir()

    def atualizar(self):
        self.janela.update()
        if self.aberto and self.aba_atual == "Video" and not self._arrastando_video:
            self._desenhar()

    def encerrar(self):
        self.janela.destroy()
