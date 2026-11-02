# SOLAR ANALYTICS

**Inteligência que transforma energia em economia.**

Aplicação para acompanhar geração fotovoltaica, consumo residencial, energia injetada/compensada e faturas da Neoenergia Pernambuco. O backend é Python/FastAPI com SQLite e PyMuPDF; a interface é React + TypeScript, Tailwind CSS e Recharts. A execução principal no Windows é local, em `127.0.0.1`, sem sincronizar dados para serviços externos. A publicação opcional no Render Free é apenas para demonstração: o sistema exibe um alerta e os dados não têm persistência garantida nesse plano.

## Executar no Windows

1. Instale Python 3.11 ou 3.12 e Node.js 20.19+ ou 22.12+ (Vite 8), incluindo npm. No terminal, confira `py --version` e `npm --version`.
2. Extraia a pasta para um local gravável. Na primeira execução, `iniciar.bat` cria o ambiente virtual Python, instala os pacotes, instala as dependências React e compila a interface.
3. Execute `iniciar.bat`. Ele abre `http://127.0.0.1:8000` no navegador. Mantenha a janela aberta enquanto usa o sistema; feche-a para encerrar o servidor.

O backend usa Uvicorn básico, sem o extra opcional que instala PyYAML; para Python 3.11/3.12 no Windows não é necessário instalar Visual C++ Build Tools. Se uma tentativa anterior deixou a instalação parcial, feche a janela, extraia a versão atualizada, apague apenas `.venv` e execute `iniciar.bat` novamente. **Não apague `data` nem `backups`** se quiser manter os dados locais.

Na primeira execução são gerados registros **fictícios** de demonstração, marcados na interface e no histórico. Use **Remover dados fictícios** para apagá-los sem tocar em medições ou faturas reais. Essa remoção não é desfeita e a demonstração não volta a ser carregada automaticamente. Para cadastrar dados reais em uso local, use **Leituras de energia** e **Faturas Neoenergia**.

## Login administrativo

O serviço público usa uma única conta administrativa: não há cadastro aberto, múltiplos usuários nem redefinição de senha no site. O login usa cookie de sessão assinado, `HttpOnly`, `Secure` e `SameSite=None` em HTTPS no Render, com expiração de 12 horas. As rotas de leituras, faturas, configurações, exportações, backups e GoodWe exigem sessão; `/api/health` e `/api/auth/status` ficam disponíveis para health check e inicialização da tela. Operações mutáveis também exigem origem confiável. Oito tentativas inválidas no endereço de cliente observado pelo servidor bloqueiam novos logins por 15 minutos.

No modo local, o login fica desativado por padrão porque o servidor só aceita conexões no próprio computador. Para ativá-lo localmente, configure em `.env` `SOLAR_AUTH_REQUIRED=true`, `SOLAR_ADMIN_USERNAME`, `SOLAR_ADMIN_PASSWORD` (mínimo 16 caracteres), `SOLAR_SESSION_SECRET` (mínimo 32 caracteres aleatórios) e `SOLAR_COOKIE_SECURE=false`. Gere uma chave de sessão com `python -c "import secrets; print(secrets.token_urlsafe(48))"`. **Não adicione `.env`, senhas ou chaves de sessão ao GitHub.** Se login for obrigatório e faltar qualquer valor, o servidor interrompe a inicialização.

## Publicação opcional no Render Free

O arquivo `render.yaml` define um Web Service `docker` no plano `free`, na região de Virgínia, com login obrigatório, um segredo de sessão gerado pelo Render, documentation API desligada e alerta de armazenamento volátil. **Nenhum disco persistente é definido ou cobrado.** Para usar esse Blueprint, primeiro a branch `main` do repositório GitHub precisa conter o código atualizado, o `Dockerfile` e `render.yaml`; no Render, crie um Blueprint, selecione o repositório e preencha `SOLAR_ADMIN_USERNAME` e `SOLAR_ADMIN_PASSWORD` quando solicitado. Use senha exclusiva com pelo menos 16 caracteres. O Render gera `SOLAR_SESSION_SECRET` automaticamente. Sem as credenciais válidas, a aplicação falha fechada e não inicia aberta ao público.

**Limitação do Free:** o sistema de arquivos do serviço é efêmero e não há Persistent Disk. O banco SQLite e os arquivos locais/backup podem desaparecer em uma suspensão, reinicialização ou novo deploy; a disponibilidade também pode incluir período de espera após suspensão. Não use essa instância gratuita para guardar faturas, credenciais GoodWe nem dados reais. Ela serve para experimentar com a demonstração fictícia. Baixar um ZIP de backup para o próprio computador não transforma o serviço gratuito em armazenamento durável. Se precisa preservar dados reais na web, não implante esta configuração Free: escolha uma infraestrutura com armazenamento persistente e revise a arquitetura antes.

Antes de iniciar o Blueprint no GitHub, substitua os arquivos antigos pela versão atualizada do projeto. Nesta configuração não foi criado disco, banco gerenciado pago ou serviço pago.

## Desenvolvimento local

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
copy .env.example .env
```

Em dois terminais, na raiz do projeto:

```bash
# Terminal 1 — API
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — interface React/Vite
npm run dev
```

A interface de desenvolvimento fica em `http://localhost:3000`, com chamadas `/api` encaminhadas ao FastAPI local. Para testar e compilar:

```bash
.venv\Scripts\python.exe -m pytest -q
npm run build
```

A API expõe documentação em `http://127.0.0.1:8000/docs` no modo local e verificação de saúde em `/api/health`. A documentação fica desativada no Blueprint Render.

## Energia, contas e estimativas

Cada leitura tem quatro campos independentes: **produzida**, **consumida**, **injetada** e **compensada**. A aplicação não deduz energia compensada como produção ou injeção. Campos ausentes permanecem vazios, são mostrados como “—” e impedem totais ou estimativas que não possam ser calculados integralmente com segurança.

A extração de faturas usa PyMuPDF localmente. O sistema tenta reconhecer somente rótulos explícitos de consumo faturado, energia injetada, compensada, créditos, valor total, valor pago e vencimento; não existe garantia de reconhecimento para todos os modelos ou PDFs digitalizados. Nenhum campo extraído é gravado automaticamente: a tela de revisão permite corrigir valores e deixar desconhecidos em branco. Confira o documento original antes de salvar.

A economia é uma estimativa bruta de energia de autoconsumo e compensação. Para calculá-la, configure em **Configurações** a tarifa de energia (R$/kWh), o custo de disponibilidade (R$) e o fator de compensação (%). Não há tarifas padrão, regra individual ou valor presumido. O custo de disponibilidade fica separado da economia e é tratado como parcela não compensável; tributos, itens tarifários ou detalhes regulatórios não cadastrados ficam fora da estimativa. O resultado não é o valor garantido da economia líquida nem uma conferência oficial da fatura.

## GoodWe SEMS+

O módulo é uma preparação arquitetural. **A API oficial GoodWe SEMS+ não está conectada**: não são feitas autenticação, consulta ou sincronização, e os campos de geração/consumo/potência não simulam dados GoodWe. O status inicial é “Aguardando credenciais da API GoodWe”.

No Windows local, AppID e identificação da usina são armazenados localmente no SQLite. O AppSecret é enviado ao backend local, armazenado no cofre de credenciais do sistema operacional via `keyring` e nunca devolvido à interface nem gravado no banco. Se o sistema não disponibilizar um cofre seguro, o AppSecret não é salvo. No Render Free, não tente inserir credenciais: o serviço é apenas demonstrativo e a camada de segurança pode rejeitar armazenamento quando não existir cofre de sistema aprovado.

## Exportação, backup e privacidade

Na tela **Configurações & dados**, baixe CSV separado de medições ou faturas. O backup cria um ZIP contendo uma cópia consistente do arquivo SQLite; a restauração aceita ZIP, `.sqlite3` ou `.db`, valida integridade e tabelas antes de substituir os dados atuais. A restauração é destrutiva para o conteúdo vigente — salve um backup antes, se necessário. Os ZIPs de backup **não são criptografados**.

No uso local, o banco ativo fica em `data/solar_analytics.sqlite3` (ou em `SOLAR_DATA_DIR`) e os backups ficam em `backups/` (ou `SOLAR_BACKUP_DIR`). Esses arquivos e `.env` não devem ser compartilhados sem revisar seu conteúdo. O AppSecret GoodWe não faz parte deles.

## Segurança, entrada de arquivos e Preview do Manus

O iniciador Windows mantém o FastAPI em `127.0.0.1`; o Vite local também fica em loopback. O servidor usa allowlist de `Host` e valida `Origin` em operações de escrita. O serviço protegido limita tentativas de login, exige cookie de sessão assinado e não tem rota pública de cadastro. A conta e o segredo são configurados no ambiente de execução, não em código-fonte. Em HTTPS, os cookies usam `SameSite=None; Secure`; no localhost HTTP, a opção segura fica desligada. As respostas `/api` usam `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` e `Referrer-Policy: no-referrer`.

A Preview do Manus roda em sandbox cloud e não equivale a uma instalação local com persistência no computador. Mantenha-a com dados de demonstração; não insira nela credenciais GoodWe ou faturas reais. A configuração free do Render também deve permanecer somente com registros fictícios devido ao armazenamento efêmero.

Uploads PDF são limitados a 20 MB, 100 páginas e 1 milhão de caracteres extraídos. Restauração de backup aceita arquivos até 100 MB, verifica SQLite, limita ZIP a 1.000 entradas e o tamanho descompactado. Em sistemas POSIX, diretórios de dados/backups e banco/ZIPs recebem permissões restritas; no Windows, `iniciar.bat` restringe as ACLs dessas pastas ao usuário atual. Campos textuais exportados em CSV são neutralizados contra fórmulas de planilha.

## Estrutura

```text
app/                    FastAPI, configuração, esquemas, modelos e rotas
app/routers/            API de dashboard, medições, faturas, autenticação e backup
app/services/           Parser PDF, demonstração, login e credenciais GoodWe
frontend/src/           Interface React/TypeScript, telas e gráficos Recharts
frontend/public/        Manifesto de rota
static/                 Build do React servido pelo FastAPI
 data/                  SQLite local; efêmero no Render Free
backups/                Backups SQLite locais
render.yaml             Blueprint público no plano Free, sem disco persistente
Dockerfile              Build multi-stage opcional
iniciar.bat             Preparação e inicialização para Windows
requirements.txt        Dependências Python fixadas
package.json            Dependências React/Vite/Tailwind/Recharts fixadas
.env.example            Variáveis locais de exemplo, sem segredos
SECURITY.md             Relatório e limitações da auditoria
```

## Contêiner local opcional

Para testar o mesmo frontend e FastAPI em um contêiner com persistência local, use: `docker build -t solar-analytics .` e `docker run --rm -p 127.0.0.1:8000:8000 -v solar-data:/app/data -v solar-backups:/app/backups solar-analytics`. O fluxo recomendado no Windows continua sendo `iniciar.bat`, sem Docker ou hospedagem externa. O Blueprint do Render Free **não cria os volumes deste comando**.

A futura integração GoodWe permanece isolada em `app/services/goodwe.py` e `app/routers/goodwe.py`. Uma implantação web adequada a dados reais requer armazenamento remoto persistente e nova revisão de segurança antes de habilitar o uso.
