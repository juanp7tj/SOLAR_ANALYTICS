# Relatório de segurança — SOLAR ANALYTICS

**Verificação:** 2 de novembro de 2026. **Código publicado:** `89e84cb952ed926897acc13e6dbded8b01eeef48`. **Estado:** demonstração pública ativa no Render Free em [solar-analytics-public-demo.onrender.com](https://solar-analytics-public-demo.onrender.com), com login único de administrador. A senha inicial foi entregue separadamente em arquivo privado; ela não está no repositório, no ZIP de código nem no README. A instância foi configurada para iniciar somente com demonstração fictícia. Não inserir faturas residenciais, dados reais nem credenciais GoodWe.

## Escopo e resultado

Foram revisados o código atual em `main`, arquivos locais e ZIP de entrega, FastAPI/React, autenticação, middleware ASGI, upload e restauração, CSV, banco SQLite de teste, credenciais GoodWe, Blueprint Render e respostas HTTP da instância implantada. Não foram encontrados segredos de GoodWe, senha de administrador, `.env` ou banco de dados no commit/pacote de código. A senha é mantida como variável protegida do serviço Render e foi fornecida ao usuário por arquivo separado com permissão local restrita. A verificação não varreu todo o histórico remoto do GitHub nem configurações secretas da conta Render.

Uma revisão independente encontrou riscos concretos no upload multipart antes da autenticação e no crescimento ilimitado do estado de rate limit; ambos foram corrigidos e cobertos por regressões automatizadas. Também há testes persistentes para flags de cookie HTTPS e ordem do middleware.

**Testes locais:** 17 testes Python passaram; `compileall` passou; TypeScript e build Vite passaram; `pip-audit -r requirements.txt` retornou **No known vulnerabilities found** e `npm audit --audit-level=low` encontrou **0 vulnerabilidades**. O build Vite ainda imprime um aviso de chunk JavaScript acima de 500 kB sem gzip (aprox. 164 kB gzip), sem falha de build. PyMuPDF emite avisos SWIG de depreciação sem falha de execução.

**Smoke test Render:** página `200`, health `200`, status de autenticação `200`, leitura privada sem sessão `401`, login válido `200`, leitura privada após login `200`. O cookie observado trouxe `HttpOnly`, `Secure`, `SameSite=None` e `Max-Age=43200`. Nenhuma senha foi impressa pelo teste.

## Controles e evidências

| Área | Implementação e evidência |
|---|---|
| Conta administrativa | Conta única; variáveis de ambiente, senha mínima de 16 caracteres e chave de sessão de pelo menos 32 caracteres; inicialização pública falha fechada se faltarem credenciais; sem cadastro público. |
| Sessão | Cookie assinado e `HttpOnly`, expiração de 12 h; teste Render HTTPS verifica `Secure`, `SameSite=None` e `Max-Age=43200`; teste localhost confirma `SameSite=Lax` sem `Secure`. Logout e rotas de dados protegidos. |
| Upload antes do parser | Middleware ASGI valida sessão antes de entregar corpos de requisição ao FastAPI. Teste confirma resposta 401 sem invocar `receive` para upload não autenticado; corpos excessivos são rejeitados antes da leitura; limite de streaming cobre fragmentação e ausência de `Content-Length`. Teste de ordem assegura SessionMiddleware e TrustedHostMiddleware antes do gate. |
| Tamanho dos corpos | PDF: arquivo até 20 MiB, corpo até 22 MiB para overhead multipart. Backup: arquivo até 100 MiB, corpo até 102 MiB. Outras rotas API: até 1 MiB. Handlers mantêm limites próprios. |
| Tentativas de login | Oito falhas por endereço de cliente em janela de 15 minutos; expurgo de tentativas expiradas; estado em memória limitado a 4.096 endereços. Teste cobre teto e expiração. O contador reinicia com o processo e não substitui WAF/rate limit distribuído. |
| CSRF e host | `TrustedHostMiddleware` precede o gate; `SessionMiddleware` valida sessão assinada antes do middleware pré-parser. A origem HTTPS canônica Render é confiável e localhost não é adicionado por padrão em produção. Smoke ASGI bloqueia origem local/atacante. Nenhum `X-Frame-Options` quebra o Preview Manus. |
| Arquivos, backup e CSV | PDF limitado a 20 MiB, 100 páginas e 1 milhão de caracteres extraídos; backup validado até 100 MiB, ZIP até 1.000 entradas e expansão limitada. CSV neutraliza fórmulas. Permissões POSIX 0700/0600; `iniciar.bat` restringe ACL Windows. ZIP de backup não é criptografado. |
| GoodWe e documentação | SEMS+ não está conectada e não faz chamadas fictícias. AppSecret só é salvo com cofre `keyring` aprovado. OpenAPI/Docs desligadas na configuração Render; `/api` usa `no-store`, `nosniff` e política de referência restritiva. |
| Dependências | `pip-audit` e `npm audit` sem vulnerabilidades conhecidas nas versões fixadas verificadas nesta data. |

## Limitações e serviços anteriores

**Render Free não oferece disco persistente.** O SQLite e outros arquivos locais podem desaparecer em suspensão, reinicialização ou deploy. A instância pública serve somente para demonstração e seus dados podem ser recriados; ZIPs de backup não são criptografados e devem ser mantidos localmente, em dispositivo protegido.

A conta administrativa não inclui MFA, recuperação por e-mail nem múltiplos usuários. O limitador de login é de processo único e não protege contra campanhas distribuídas; uma camada global é indicada antes de uso mais amplo. ACL `icacls`, Windows Credential Manager e o comportamento do app em Windows não puderam ser executados neste sandbox Linux.

A conta Render já continha dois serviços anteriores vinculados ao mesmo repositório. Um serviço Docker Free estava suspenso pelo usuário e foi deixado suspenso; o serviço Python `SOLAR_ANALYTICS-1` tinha dois deploys falhos e foi deixado sem alterações. O novo serviço demonstrativo criado é `solar-analytics-public-demo`. A auditoria não alterou nem apagou esses recursos preexistentes.

Esta é uma verificação pontual, não substitui monitoramento contínuo ou revisão antes de eventual uso com dados reais. Para utilizar dados reais na web, será necessário escolher armazenamento persistente, mudar o plano/arquitetura e fazer nova revisão de segurança.

## Referências

- [Render — serviços no plano gratuito](https://render.com/docs/free)
- [Render — discos persistentes](https://render.com/docs/disks)
- [Render — Web Services](https://render.com/docs/web-services)
- [Starlette — middleware](https://www.starlette.io/middleware/)
- [Starlette — sessões](https://www.starlette.io/middleware/#sessionmiddleware)
- [OSV — base pública consultada pelo `pip-audit`](https://osv.dev/)
