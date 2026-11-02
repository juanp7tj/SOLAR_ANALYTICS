# Relatório de segurança — SOLAR ANALYTICS

**Verificação:** 2 de novembro de 2026. **Ambiente:** sandbox Linux do Manus. **Resultado:** não encontrei credenciais GoodWe, `.env` com segredos nem dados reais nos artefatos verificados. O SQLite usado nesta sessão contém somente registros de demonstração; o AppSecret está sem configuração. A Preview do Manus permanece ativa, mas não foi publicada como site público.

## Escopo e resultado

Foram inspecionados o código da aplicação, configurações de execução, regras de exclusão Git/Docker, SQLite local e pacote de distribuição. O pacote final foi verificado para não conter `.env`, banco SQLite, sidecars (`-wal`, `-shm`, `-journal`) ou backups. A base de demonstração não representa consumo ou contas reais.

Auditorias executadas em 2 de novembro de 2026: `pip-audit -r requirements.txt` e `pip-audit` retornaram **No known vulnerabilities found**; `npm audit --audit-level=low` encontrou **0 vulnerabilidades**. Versões Python fixadas após atualização: FastAPI 0.162.0, Starlette 1.10.0, python-multipart 0.0.33, pytest 9.2.0 e pip 26.2.2 no inicializador Windows/contêiner. As versões podem mudar de segurança após esta data; execute as auditorias novamente antes de uma publicação.

## Mitigações aplicadas

- **Acesso e navegação:** o iniciador Windows mantém o backend em `127.0.0.1`; o desenvolvimento local mantém o Vite em loopback. Operações de escrita rejeitam `Origin` fora da lista permitida e o FastAPI verifica `Host`. O Vite aceita somente o hostname exato da Preview deste projeto, sem wildcard. As respostas `/api` usam `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` e `Referrer-Policy: no-referrer`. A documentação OpenAPI fica desativada quando `SOLAR_DISABLE_API_DOCS=true`, opção usada na Preview.
- **Segredos:** o AppSecret GoodWe não é retornado pelo backend nem persistido em SQLite/`.env`/backup. A gravação só é permitida quando `keyring` identifica Windows Credential Manager, macOS Keychain ou Linux Secret Service. O backend `keyring.backends.fail` observado no sandbox foi recusado; a integração GoodWe continua desligada.
- **Uploads e backups:** PDF até 20 MB, 100 páginas e 1 milhão de caracteres extraídos. Restauração aceita até 100 MB, valida SQLite, limita arquivos ZIP a 1.000 entradas e limita leitura do conteúdo descompactado. Teste com ZIP acima do limite foi rejeitado sem modificar os dados.
- **Armazenamento local:** em POSIX, diretórios de dados/backups ficam em modo `0700` e SQLite/ZIP em `0600`. No Windows, `iniciar.bat` aplica ACL ao usuário atual nas pastas `data` e `backups`. Regras Git/Docker também excluem sidecars SQLite. CSV neutraliza fórmulas de planilha, incluindo marcadores precedidos por caracteres invisíveis.
- **Validação:** `9` testes Python passaram; build TypeScript/Vite concluiu; auditorias pip/npm sem achados; health, manifesto, origem/host, documentação desativada, backup/restauração e limites de ZIP foram verificados por HTTP.

## Limitações importantes

**A aplicação não tem login.** A versão local é single-user e deve permanecer em loopback. A Preview do Manus roda em sandbox cloud e atualmente contém apenas dados fictícios; ela não é uma versão autenticada para uso com faturas reais nem uma publicação pública. Não compartilhe a Preview nem use dados pessoais/financeiros reais nela. O contêiner opcional também não adiciona autenticação. Antes de publicar ou permitir acesso de outras pessoas, implementar autenticação, autorização, proteção CSRF apropriada, armazenamento remoto persistente, gestão de segredos e revisão de exposição.

Os arquivos ZIP de backup **não são criptografados**. Mantenha-os em diretório protegido ou volume criptografado e não os envie a terceiros sem proteção. O código `icacls` e o uso real do Windows Credential Manager não puderam ser executados neste sandbox Linux; confirme as ACLs NTFS na máquina Windows. Se `SOLAR_DATA_DIR` for personalizado, revise manualmente suas permissões. O Docker também não foi executado neste ambiente.

A verificação é pontual e baseada no checkout/ZIP atual; não é garantia de ausência absoluta de vulnerabilidades, nem inclui auditoria de histórico Git, sistema Windows do usuário ou uma implantação pública. Nenhuma chamada ou sincronização com GoodWe foi realizada.

## Referências das versões auditadas

- [FastAPI 0.162.0 — PyPI](https://pypi.org/project/fastapi/0.162.0/)
- [Starlette 1.10.0 — PyPI](https://pypi.org/project/starlette/1.10.0/)
- [python-multipart 0.0.33 — PyPI](https://pypi.org/project/python-multipart/0.0.33/)
- [pytest 9.2.0 — PyPI](https://pypi.org/project/pytest/9.2.0/)
- [pip 26.2.2 — PyPI](https://pypi.org/project/pip/26.2.2/)
- [OSV — base pública consultada pelo `pip-audit`](https://osv.dev/)
