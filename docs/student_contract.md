# contrato do pipeline do estudante

## entrada

`process_frame(frame_bgr)` recebe um `numpy.ndarray` com a observação disponível naquele modo de execução.

- em `video`, a entrada vem de um arquivo local;
- em `robot`, a entrada vem diretamente da ESP32-CAM usada em desenvolvimento;
- em `gateway`, a entrada vem da infraestrutura da atividade e não existe garantia de equivalência com o frame capturado originalmente pelo sensor.

## saída

A função deve retornar uma imagem válida para exibição. São aceitas representações usuais em escala de cinza ou múltiplos canais, desde que possuam dimensões coerentes e dados numéricos interpretáveis pela camada de visualização.

## responsabilidade

O estudante deve manter no próprio pipeline as decisões de processamento necessárias à missão. A infraestrutura não seleciona automaticamente a técnica que deve ser usada.

## invariância entre modos

O objetivo dos três modos é permitir que o mesmo `process_frame()` seja desenvolvido com arquivos, validado em hardware de bancada e usado depois na missão oficial sem alteração estrutural.

## falha segura

Quando existe controle de robô, se a função lançar exceção ou retornar `None`, o console envia comando de parada.
