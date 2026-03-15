# Site de Vendas + AbacatePay

Projeto publico separado do `ProspectLocal`, pensado para:

- apresentar a oferta do site
- redirecionar o cliente para checkout PIX/cartao
- rodar na Vercel
- manter o CRM/operacao local e privado

## Resumo arquitetural

Voce fica com dois projetos independentes na mesma workspace:

- `ProspectLocal`: operacao interna, scraping, CRM e WhatsApp
- `site-vendas-abacatepay`: pagina publica de venda e pagamento

Isso permite publicar so a parte comercial, sem expor o sistema local.

## Estrutura

- `app/page.tsx`: landing page comercial
- `components/checkout-form.tsx`: formulario para escolher plano e iniciar checkout
- `app/api/checkout/route.ts`: cria checkout hospedado na AbacatePay
- `app/api/webhooks/abacatepay/route.ts`: recebe eventos da AbacatePay
- `lib/abacatepay.ts`: integracao com API e validacao de assinatura
- `lib/site-config.ts`: planos, precos e variaveis de produto
- `docs/IMPLEMENTACAO.md`: contexto para outro agente continuar

## Como rodar

1. Crie o arquivo `.env.local` a partir de `.env.example`
2. Preencha:
   - `ABACATEPAY_API_KEY`
   - `ABACATEPAY_API_VERSION`
   - `ABACATEPAY_WEBHOOK_SECRET` (opcional para testes, recomendado para webhook)
   - `NEXT_PUBLIC_SITE_URL`
   - `CHECKOUT_PRODUCT_ID_START`
   - `CHECKOUT_PRODUCT_ID_PRO`
   - `CHECKOUT_PRODUCT_ID_PREMIUM`
3. Instale dependencias:

```bash
npm install
```

4. Rode local:

```bash
npm run dev
```

5. Build de validacao:

```bash
npm run build
```

## Como funciona o checkout

Este projeto usa **checkout hospedado** da AbacatePay.

Baseado na documentacao oficial:

- Criar checkout: [AbacatePay - Criar um Checkout](https://docs.abacatepay.com/pages/payment/create)
- Webhooks v2: [AbacatePay - Webhooks](https://docs.abacatepay.com/pages/webhooks)
- Chaves de API: [AbacatePay - Chaves de API](https://docs.abacatepay.com/pages/authentication)

Fluxo:

1. O cliente escolhe o plano na landing page
2. O frontend chama `POST /api/checkout`
3. A rota server-side cria o checkout em `https://api.abacatepay.com/v2/checkouts/create`
4. A API devolve uma `url`
5. O cliente e redirecionado para o checkout da AbacatePay

### Observacao sobre versao da API

Hoje o projeto suporta dois modos:

- `ABACATEPAY_API_VERSION=v1`: cria cobranca hospedada com os dados do plano direto no payload
- `ABACATEPAY_API_VERSION=v2`: usa `product IDs` cadastrados na AbacatePay

Para a chave `abc_dev_...` usada nos testes atuais, o modo correto e `v1`.

## Produtos na AbacatePay

O endpoint `checkouts/create` trabalha com `items[].id`, entao voce precisa cadastrar os produtos na sua conta da AbacatePay e colocar os IDs no `.env.local`.

No modo `v1`, isso nao e obrigatorio para testar, porque os dados do produto sao enviados no payload.

Sugestao:

- `CHECKOUT_PRODUCT_ID_START`
- `CHECKOUT_PRODUCT_ID_PRO`
- `CHECKOUT_PRODUCT_ID_PREMIUM`

## Webhook

O endpoint `/api/webhooks/abacatepay`:

- recebe os eventos
- pode validar um `secret` simples via query string
- hoje apenas registra no log

Exemplo de URL para configurar no painel:

`https://seu-dominio.vercel.app/api/webhooks/abacatepay?secret=seu-secret`

Depois voce pode evoluir para:

- salvar pedido em banco
- disparar mensagem no WhatsApp
- liberar um onboarding interno
- enviar e-mail automatico

## Fluxo de venda sugerido

1. Qualifique o lead no `ProspectLocal`
2. Quando houver interesse real, mande a URL publica desse projeto
3. O cliente escolhe o plano e segue para o checkout hospedado
4. A AbacatePay confirma o pagamento
5. Voce inicia entrega/onboarding fora do checkout

## Deploy na Vercel

1. Suba apenas a pasta `site-vendas-abacatepay`
2. Configure as variaveis de ambiente na Vercel
3. Cadastre a URL publica do webhook no dashboard da AbacatePay:

`https://seu-dominio.vercel.app/api/webhooks/abacatepay?secret=seu-secret`

## Observacao arquitetural

Esse projeto foi criado de forma independente do `ProspectLocal`, mas dentro da mesma workspace.

Isso permite:

- manter o sistema interno local
- publicar so a parte comercial
- preservar contexto para agentes que ja conhecem o seu fluxo

## Handoff rapido para outro agente

Se outro agente continuar esse projeto, ele precisa saber:

- esse app nao substitui o `ProspectLocal`
- esse app deve ser deployado separadamente na Vercel
- o checkout atual e hospedado, nao transparente
- os produtos reais precisam existir na AbacatePay
- a documentacao detalhada esta em `docs/IMPLEMENTACAO.md`
- o contexto operacional resumido esta em `docs/AGENT_HANDOFF.md`
