# PDI Robot — Student Console

Baseline público do Projeto Integrador de Processamento Digital de Imagens.

O repositório foi separado para permitir desenvolvimento completo sem expor a configuração usada na avaliação. Pode-se trabalhar com vídeos, imagens e um robô próprio/de bancada. Na missão oficial, o mesmo `process_frame()` roda sobre o stream entregue pelo gateway docente.

## objetivo

A responsabilidade de PDI continua concentrada em:

```text
pc_app/image_processing.py
```

O console possui três modos de execução:

```text
video    -> imagem ou vídeo local, sem robô
robot    -> conexão direta com uma ESP32-CAM de desenvolvimento
gateway  -> infraestrutura oficial da atividade
```

O pipeline acadêmico é o mesmo nos três casos:

```text
fonte de imagem
      │
      ▼
process_frame()
      │
      ▼
console
```

## modos de execução

### 1. vídeo ou imagem local

Use este modo para desenvolver filtros sem depender de hardware:

```bash
PDI_MODE=video \
PDI_MEDIA_SOURCE=./examples/media/meu_video.mp4 \
python pc_app/main.py
```

Também pode ser usada uma imagem:

```bash
PDI_MODE=video \
PDI_MEDIA_SOURCE=./minha_imagem.png \
python pc_app/main.py
```

Por padrão, vídeos reiniciam ao chegar ao final. Para executar somente uma vez:

```bash
PDI_MEDIA_LOOP=0
```

Nesse modo não existe envio de comandos para motores.

### 2. robô direto de desenvolvimento

Use este modo com uma ESP32-CAM própria ou com um robô liberado para bancada:

```bash
PDI_MODE=robot \
PDI_ROBOT_IP=<IP_DA_ESP> \
python pc_app/main.py
```

O console acessa diretamente:

```text
http://<robô>:81/stream
udp <robô>:4210
```

Esse modo existe para desenvolvimento e depuração. Ele não deve ser usado para contornar a infraestrutura da missão oficial.

### 3. gateway da atividade

Na avaliação, o professor vai fornecer o endereço do gateway:

```bash
PDI_MODE=gateway \
PDI_GATEWAY_HOST=<iP> \
python pc_app/main.py
```

Se houver token de sessão:

```bash
PDI_MODE=gateway \
PDI_GATEWAY_HOST=<IP> \
PDI_SESSION_TOKEN="token-fornecido-em-aula" \
python pc_app/main.py
```
Nesse modo não precisa conhecer o endereço real do robô usado na missão.

## arquitetura

### desenvolvimento com arquivo

```text
vídeo/imagem
    │
    ▼
MediaFileSource
    │
    ▼
process_frame()
    │
    ▼
console
```

### desenvolvimento com robô

```text
ESP32-CAM
   ├── MJPEG
   └── UDP
       │
       ▼
Student Console
       │
       ▼
process_frame()
```

### missão oficial

```text
ESP32-CAM oficial
       │
       ▼
instructor gateway
       │
       ├── stream da atividade
       └── proxy de controle
              │
              ▼
       Student Console
              │
              ▼
       process_frame()
```

A diferença entre os modos está na infraestrutura de entrada e controle. O código de PDI não precisa mudar.

## onde implementar o PDI

Edite:

```text
pc_app/image_processing.py
```

A função possui o contrato:

```python
process_frame(frame_bgr) -> imagem_processada
```

A entrada é a observação disponível naquele modo de execução. A saída pode ser BGR, BGRA, escala de cinza, booleana, inteira ou de ponto flutuante, desde que possa ser interpretada pela camada de visualização.

## firmware de desenvolvimento

O firmware genérico da ESP32-CAM fica em:

```text
firmware/ESP32CAM_L298N_Web/
```

Ele contém somente infraestrutura de hardware:

- conexão Wi-Fi;
- stream MJPEG;
- controle diferencial dos motores;
- flash;
- watchdog/fail-safe embarcado.

Ele não contém a lógica dos desafios da disciplina.

Antes de compilar:

```bash
cp firmware/ESP32CAM_L298N_Web/wifi_secrets.example.h \
   firmware/ESP32CAM_L298N_Web/wifi_secrets.h
```

Preencha a rede usada pelo robô. `wifi_secrets.h` não deve ser versionado.

## instalação

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## controles

| tecla | ação |
|---|---|
| `W`, `A`, `S`, `D` ou setas | movimentação manual quando há robô |
| `Espaço` | parada imediata |
| `+` / `-` | aumenta ou diminui a velocidade |
| `L` | liga ou desliga o flash |
| `Esc` | encerra o console |

No modo `video`, os controles de movimento não enviam nada para hardware.

## configuração

| variável | padrão | função |
|---|---:|---|
| `PDI_MODE` | `gateway` | `gateway`, `robot` ou `video` |
| `PDI_MEDIA_SOURCE` | vazio | imagem/vídeo usado em `video` |
| `PDI_MEDIA_LOOP` | `1` | reinicia vídeos ao final |
| `PDI_ROBOT_IP` | `micromouse.local` | robô usado em `robot` |
| `PDI_ROBOT_UDP_PORT` | `4210` | controle direto de desenvolvimento |
| `PDI_ROBOT_CAMERA_URL` | derivada do IP | stream direto de desenvolvimento |
| `PDI_GATEWAY_HOST` | `127.0.0.1` | gateway usado na atividade |
| `PDI_GATEWAY_STREAM_PORT` | `8090` | stream da atividade |
| `PDI_GATEWAY_CONTROL_PORT` | `4211` | proxy de controle |
| `PDI_SESSION_TOKEN` | vazio | token opcional da sessão |
| `PDI_ANGULAR_SIGN` | `-1` | adapta o sentido angular ao chassi |
| `PDI_DEFAULT_SPEED` | `230` | velocidade inicial |
| `PDI_CONTROL_SEND_HZ` | `20` | frequência de atualização do comando |
| `PDI_CONTROL_COMMAND_TIMEOUT_SEC` | `0.80` | timeout do fail-safe local |
| `PDI_CONSOLE_FPS` | `30` | limite da interface |
| `PDI_LOG_LEVEL` | `INFO` | nível de logging |

## estrutura

```text
pdi-robo-student/
├── firmware/
│   └── ESP32CAM_L298N_Web/
├── pc_app/
│   ├── camera_viewer.py
│   ├── config.py
│   ├── gateway_client.py
│   ├── image_processing.py
│   ├── main.py
│   ├── media_source.py
│   ├── null_robot_client.py
│   └── robot_client.py
├── docs/
├── examples/
├── scripts/
├── tests/
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## testes

```bash
python -m unittest discover -s tests -v
```

## licença

MIT. Consulte `LICENSE`.
