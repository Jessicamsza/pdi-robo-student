# modos de desenvolvimento

## video

Use para testar o processamento sem hardware. A fonte pode ser uma imagem ou vídeo local.

```bash
PDI_MODE=video PDI_MEDIA_SOURCE=./arquivo.mp4 python pc_app/main.py
```

## robot

Use para integração com uma ESP32-CAM de bancada.

```bash
PDI_MODE=robot PDI_ROBOT_IP=micromouse.local python pc_app/main.py
```

## gateway

Use durante a atividade oficial.

```bash
PDI_MODE=gateway PDI_GATEWAY_HOST=<ip-fornecido> python pc_app/main.py
```

O arquivo `pc_app/image_processing.py` é compartilhado pelos três modos.
