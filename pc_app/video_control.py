"""Ponte local entre o painel PDI e a fonte de vídeo, sem alterar main.py."""

_fonte = None


def registrar(fonte):
    global _fonte
    _fonte = fonte


def liberar(fonte):
    global _fonte
    if _fonte is fonte:
        _fonte = None


def estado():
    if _fonte is None:
        return None
    return _fonte.obter_progresso()


def pausar_ou_reproduzir():
    if _fonte is not None:
        _fonte.alternar_pausa()


def deslocar(segundos):
    if _fonte is not None:
        _fonte.deslocar(segundos)


def posicionar(fracao):
    if _fonte is not None:
        _fonte.posicionar(fracao)
