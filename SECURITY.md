# Relatório de segurança — SOLAR ANALYTICS

**Verificação:** 2 de novembro de 2026. **Ambiente:** sandbox Linux do Manus. **Estado:** login de administrador implementado e endurecido; nenhum serviço público do Render foi criado. A revisão da cópia local e dos arquivos de distribuição não encontrou credenciais GoodWe, senha real ou arquivo `.env` com segredos. O banco SQLite da sessão contém apenas demonstração fictícia. Os valores usados em testes de autenticação são exclusivamente de teste e não configuram acesso de produção.

## Escopo e resultado

Foram inspecionados FastAPI/React, autenticação, middleware ASGI, rotas de upload, limites de arquivos, CSV, backup/restauração, credenciais GoodWe, configuração Render, arquivo de ambiente de exemplo, regras de exclusão e pacote de entrega. Uma revisão independente encontrou riscos concretos no upload multipart antes da autenticação e no crescimento ilimitado do estado de rate limit; ambos foram corrigidos e cobertos por regressões automatizadas. Também foi adicionada uma asserção de integração para flags de cookie em HTTPS e outra para a ordem do middleware.

Validação após as correções: **17 testes Python passaram**; `compileall` passou; TypeScript e build Vite passaram; `pip-audit -r requirements.txt` retornou **No known vulnerabilities found** e `npm audit --audit-level=low` encontrou **0 vulnerabilidades**. O build Vite ainda imprime um aviso de chunk JavaScript acima de 500 kB sem gzip (aprox. 164 kB gzip); não é erro de build. PyMuPDF emite cinco avisos SWIG de depreciação sem falha de execução.

A verificação de exposição cobre os arquivos locais e o ZIP entregue, não o histórico remoto do GitHub, as configurações da conta Render ou os arquivos que o usuário possa ter enviado anteriormente ao GitHub. Marcadores comuns de chave/token não foram encontrados nos arquivos de texto auditados. Não foi inspecionado o conteúdo do `.env`, da base nem dos backups como valores; somente a classificação/escopo necessários para confirmar que dados pessoais não entraram no pacote.

## Controles e validações

| Área | Implementação e evidência |
|---|---|
| Conta administrativa | Conta única; variáveis de ambiente, senha mínima de 16 caracteres e chave de sessão de pelo menos 32 caracteres; inicialização pública falha fechada se faltarem credenciais; sem cadastro público. |
| Sessão | Cookie assinado e `HttpOnly`, expiração de 12 h; teste isolado com host HTTPS Render verifica `Secure`, `SameSite=None` e `Max-Age=43200`; teste localhost confirma `SameSite=Lax` sem `Secure`. Logout e rotas de dados protegidos. |
| Upload antes do parser | Middleware ASGI valida a sessão antes de entregar corpos de requisição ao FastAPI. Teste confirma resposta 401 sem invocar `receive` para upload não autenticado; requisições excessivas com `Content-Length` são rejeitadas sem leitura; o teto de streaming cobre corpos fragmentados/sem `Content-Length`. Teste de ordem assegura `SessionMiddleware` e `TrustedHostMiddleware` antes do gate. |
| Tamanho dos corpos | PDF: arquivo até 20 MiB, corpo de requisição até 22 MiB para overhead multipart. Backup: arquivo até 100 MiB, corpo até 102 MiB. Corpos de outras rotas API: até 1 MiB. Os handlers mantêm limites próprios de arquivo e validação. |
| Tentativas de login | Oito falhas por endereço de cliente em janela de 15 minutos; expurgo local e global de tentativas expiradas; estado em memória limitado a 4.096 endereços. Teste cobre teto e expiração. O contador reinicia com o processo e não substitui WAF/rate limit distribuído. |
| CSRF e host | `TrustedHostMiddleware` precede o gate; `SessionMiddleware` envolve o gate para validar a sessão assinada. A origem HTTPS canônica Render é confiável e localhost não é adicionado por padrão em produção. Smoke ASGI bloqueou origem local/atacante no cenário público. Nenhum cabeçalho `X-Frame-Options` impede o iframe da Preview Manus. |
| Arquivos, backup e CSV | PDF limitado a 20 MiB, 100 páginas e 1 milhão de caracteres extraídos; backup validado até 100 MiB, ZIP até 1.000 entradas e tamanho descompactado limitado. CSV neutraliza fórmulas. Permissões POSIX 0700/0600; `iniciar.bat` tenta restringir ACL Windows ao usuário atual. ZIP de backup não é criptografado. |
| GoodWe e documentação API | GoodWe SEMS+ não está conectada e não faz chamadas fictícias. AppSecret só é salvo quando há cofre `keyring` aprovado. OpenAPI/Docs ficam desligadas no Blueprint; `/api` recebe `no-store`, `nosniff` e política de referência restritiva. |
| Dependências | `pip-audit` e `npm audit` sem vulnerabilidades conhecidas nas versões fixadas verificadas nesta data. |

## Limitações e pendências

**Render Free não oferece disco persistente.** SQLite e arquivos do serviço podem desaparecer após suspensão, reinicialização ou novo deploy. O Blueprint é apenas demonstrativo; não use nele faturas, dados residenciais reais nem credenciais GoodWe. Mantenha qualquer ZIP de backup em armazenamento local protegido.

**A publicação ainda não ocorreu.** A branch `main` do GitHub precisa receber a versão atualizada com login e middleware pré-parser. Depois, é necessário confirmar que aceita uma instância pública gratuita somente para demonstração, sem persistência garantida. O usuário/senha administrativo serão definidos no painel Render e não fazem parte do código nem do pacote.

A conta não inclui MFA, recuperação por e-mail nem múltiplos usuários. O rate limit é de processo único e não protege contra campanhas distribuídas; um proxy com rate limit global é recomendado antes de exposição ampla. A proteção de AppSecret depende de cofre do sistema operacional; no Render Free, não insira credenciais GoodWe. ACL `icacls`, Windows Credential Manager, Docker e uma instância Render real não puderam ser executados neste sandbox Linux. A auditoria é pontual e não substitui monitoramento contínuo ou revisão de produção.

## Referências

- [Render — serviços no plano gratuito](https://render.com/docs/free)
- [Render — discos persistentes](https://render.com/docs/disks)
- [Render — Web Services](https://render.com/docs/web-services)
- [Starlette — middleware](https://www.starlette.io/middleware/)
- [Starlette — sessões](https://www.starlette.io/middleware/#sessionmiddleware)
- [OSV — base pública consultada pelo `pip-audit`](https://osv.dev/)
