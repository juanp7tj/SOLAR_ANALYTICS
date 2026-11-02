# SOLAR ANALYTICS

**Inteligência que transforma energia em economia.**

Aplicação local para acompanhar geração fotovoltaica, consumo residencial, energia injetada/compensada e faturas da Neoenergia Pernambuco. O backend é Python/FastAPI com SQLite e PyMuPDF; a interface é React + TypeScript, Tailwind CSS e Recharts. No Windows, o serviço fica vinculado a `127.0.0.1` e não sincroniza dados para serviços externos. A Preview do Manus, quando usada, executa no sandbox cloud do Manus; mantenha-a com dados de demonstração e não insira faturas ou segredos reais nela.

## Executar no Windows

1. Instale Python 3.11 ou 3.12 e Node.js 20.19+ ou 22.12+ (Vite 8), incluindo npm. No terminal, confira `py --version` e `npm --version`.
2. Extraia a pasta do projeto para um local gravável. Na primeira execução, `iniciar.bat` cria o ambiente virtual Python, instala os pacotes, instala as dependências do React e compila a interface.
3. Execute `iniciar.bat`. Ele abre `http://127.0.0.1:8000` no navegador. Mantenha a janela do terminal aberta enquanto usa o sistema; feche-a para encerrar o servidor.

O backend usa Uvicorn básico, sem o extra opcional que instala PyYAML; para Python 3.11/3.12 no Windows não é necessário instalar Visual C++ Build Tools. Se uma tentativa antiga deixou a instalação parcial, feche a janela, extraia a versão atualizada, apague apenas a pasta `.venv` e execute `iniciar.bat` novamente. **Não apague `data` nem `backups`** se quiser manter os dados locais.

Na primeira execução são gerados registros **fictícios** de demonstração, marcados na interface e no histórico. Use **Remover dados fictícios** para apagá-los sem tocar em medições ou faturas reais. Essa remoção não é desfeita e a demonstração não volta a ser carregada automaticamente. Para cadastrar dados verdadeiros, use **Leituras de energia** e **Faturas Neoenergia**.

O arquivo `.env.example` documenta as opções locais. Se necessário, copie-o para `.env` antes de iniciar. `SOLAR_DATA_DIR` escolhe o diretório do SQLite (por padrão `./data/solar_analytics.sqlite3`) e `SOLAR_DEMO_AUTOLOAD` define a carga inicial de demonstração (`true` por padrão, somente na primeira inicialização do banco).

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

A API também expõe documentação local em `http://127.0.0.1:8000/docs` e verificação de saúde em `/api/health`.

## Energia, contas e estimativas

Cada leitura tem quatro campos independentes: **produzida**, **consumida**, **injetada** e **compensada**. A aplicação não deduz energia compensada como se fosse produção ou injeção. Campos ausentes permanecem vazios, são mostrados como “—” e impedem totais ou estimativas que não possam ser calculados integralmente com segurança.

A extração de faturas usa PyMuPDF localmente. O sistema tenta reconhecer somente rótulos explícitos de consumo faturado, energia injetada, compensada, créditos, valor total, valor pago e vencimento; não existe garantia de reconhecimento para todos os modelos ou PDFs digitalizados. Nenhum campo extraído é gravado automaticamente: a tela de revisão permite corrigir valores e deixar desconhecidos em branco. Confira o documento original antes de salvar.

A economia é uma estimativa bruta de energia de autoconsumo e compensação. Para calculá-la, configure em **Configurações** a tarifa de energia (R$/kWh), o custo de disponibilidade (R$) e o fator de compensação (%). Não há tarifas padrão, regra individual ou valor presumido. O custo de disponibilidade fica separado da economia e é tratado como parcela não compensável; tributos, itens tarifários ou detalhes regulatórios não cadastrados ficam fora da estimativa. O resultado não é o valor garantido da economia líquida nem uma conferência oficial da fatura.

## GoodWe SEMS+

O módulo é uma preparação arquitetural. Nesta versão, **a API oficial GoodWe SEMS+ não está conectada**: não são feitas autenticação, consulta ou sincronização, e os campos de geração/consumo/potência não simulam dados GoodWe. O status inicial é “Aguardando credenciais da API GoodWe”.

AppID e identificação da usina são armazenados localmente no SQLite. O AppSecret é enviado apenas ao backend em `127.0.0.1`, armazenado no cofre de credenciais do sistema operacional via `keyring` e nunca devolvido à interface nem gravado no banco. No Windows, isso usa o armazenamento de credenciais do Windows. Se o sistema não disponibilizar um cofre seguro, o AppSecret não é salvo e a API informa o problema. As credenciais não são inseridas no `.env` nem no backup SQLite.

## Exportação, backup e privacidade

Na tela **Configurações & dados**, baixe CSV separado de medições ou faturas. O backup cria um ZIP contendo uma cópia consistente do arquivo SQLite; a restauração aceita ZIP, `.sqlite3` ou `.db`, valida integridade e tabelas antes de substituir os dados atuais. A restauração é destrutiva para o conteúdo vigente — salve um backup antes, se necessário.

O banco ativo permanece em `data/solar_analytics.sqlite3` (ou em `SOLAR_DATA_DIR`). Backups feitos pela aplicação ficam na pasta `backups/`. Esses arquivos e `.env` não devem ser compartilhados sem revisar seu conteúdo. O AppSecret GoodWe não faz parte deles.

## Segurança e limites de exposição

O fluxo Windows é local e vincula o FastAPI a `127.0.0.1`; o Vite usado em desenvolvimento também fica em loopback. A API **não possui autenticação**: não execute o backend com `--host 0.0.0.0` em uma rede nem publique o container/Preview como aplicação para outras pessoas. Operações mutáveis rejeitam `Origin` não autorizado e o servidor aplica allowlist de `Host`. O script `npm run dev:cloud-preview` existe somente para a Preview do Manus; ela roda dentro do sandbox cloud, não no Windows, e deve permanecer em demonstração até haver autenticação e uma decisão explícita sobre dados. Ao iniciá-la, autorize apenas a origem HTTPS exata com `SOLAR_TRUSTED_WRITE_ORIGINS` e configure `SOLAR_DISABLE_API_DOCS=true`.

O ZIP de distribuição contém código-fonte e arquivos de exemplo, mas não contém `.env`, o SQLite local, sidecars SQLite nem backups. O AppSecret nunca é devolvido pela API; ele só é salvo quando `keyring` identifica um backend aprovado do sistema operacional (Windows Credential Manager, macOS Keychain ou Linux Secret Service). As respostas `/api` usam `Cache-Control: no-store`; o servidor também envia `X-Content-Type-Options: nosniff` e `Referrer-Policy: no-referrer`. Campos textuais exportados em CSV são neutralizados contra fórmulas de planilha. A documentação OpenAPI pode ser desativada com `SOLAR_DISABLE_API_DOCS=true`.

Uploads PDF são limitados a 20 MB, 100 páginas e 1 milhão de caracteres extraídos. Restauro de backup aceita arquivos até 100 MB, verifica SQLite, limita ZIP a 1.000 entradas e lê o banco descompactado com limite. Em sistemas POSIX, pastas de dados/backups e banco/ZIPs recebem permissões restritas; no Windows, `iniciar.bat` restringe as ACLs dessas pastas ao usuário atual. Se `SOLAR_DATA_DIR` apontar para outro diretório, revise suas permissões/ACL. Esses controles reduzem riscos, mas não substituem login/autorização caso a aplicação deixe de ser single-user local.

## Estrutura

```text
app/                    FastAPI, esquemas, modelos e rotas
app/routers/            API de dashboard, medições, faturas, tarifas, GoodWe e backup
app/services/           Parser PDF, demonstração e serviço de credenciais GoodWe
frontend/src/           Interface React/TypeScript e gráficos Recharts
frontend/public/        Manifesto de rota
data/                   SQLite persistente (criado na primeira execução)
backups/                Destino dos backups locais
tests/                  Testes do parser PDF, limites de entrada, somas e períodos
iniciar.bat             Preparação e inicialização para Windows
requirements.txt        Dependências Python fixadas
package.json            Dependências React/Vite/Tailwind/Recharts fixadas
.env.example            Variáveis de exemplo
```

## Container opcional

O `Dockerfile` é um caminho opcional para testar o mesmo frontend e FastAPI em um contêiner. Para manter dados entre execuções, use volumes persistentes: `docker build -t solar-analytics .` e `docker run --rm -p 127.0.0.1:8000:8000 -v solar-data:/app/data -v solar-backups:/app/backups solar-analytics`. O fluxo recomendado no Windows continua sendo `iniciar.bat`, sem Docker ou hospedagem externa. Este contêiner não adiciona login: não o exponha à Internet. Uma publicação pública/multiusuário precisa de autenticação, infraestrutura de banco persistente e gestão de segredos antes de ser liberada.

A futura integração GoodWe fica isolada em `app/services/goodwe.py` e `app/routers/goodwe.py`. A atualização para publicação web requer escolher e configurar conscientemente uma infraestrutura de persistência remota; o comportamento desta entrega permanece local.
