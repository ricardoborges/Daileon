# Plugins drop-in

Esta pasta é montada dentro do container em `/app/plugins`. A intenção é que
instalar um plugin seja copiar uma pasta para cá e reiniciar o Daileon, sem
editar o código do portal.

> **Estado atual:** o diretório está reservado, mas o carregador ainda não foi
> escrito — nada aqui é lido por enquanto. Os plugins existentes (GitLab,
> Jenkins, LDAP, Portainer) continuam embutidos em `backend/app/plugins/`.

O formato previsto:

```
plugins/
  meu-plugin/
    plugin.yml      # identidade, categoria e campos de configuração
    backend/        # opcional — rotas e serviços em Python
    ui/             # opcional — telas próprias em Svelte
```

Plugins que só declaram `plugin.yml` (a maioria: um formulário de endereço e
credencial, mais uma aba que consulta um endpoint) valem com um restart.
Plugins com `ui/` própria exigem reconstruir a imagem.
