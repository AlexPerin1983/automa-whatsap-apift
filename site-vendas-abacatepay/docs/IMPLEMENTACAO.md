# Contexto Para Outro Agente

## Objetivo

Criar uma pagina publica de venda de sites com checkout via AbacatePay, sem subir o `ProspectLocal`.

## Decisao de arquitetura

- `ProspectLocal`: continua local e privado
- `site-vendas-abacatepay`: projeto publico separado, deployavel na Vercel

Motivo:

- nao expor scraping, kanban e automacoes internas
- manter o fechamento comercial em uma URL publica
- preservar o contexto da operacao na mesma workspace

## Stack escolhida

- Next.js App Router
- API routes server-side para nao expor a chave da AbacatePay no browser
- checkout hospedado da AbacatePay em vez de checkout transparente
- webhook simplificado por `secret` para nao depender de uma chave publica ambigua do painel

## Fontes oficiais usadas

- Checkout v2: https://docs.abacatepay.com/pages/payment/create
- Webhooks v2: https://docs.abacatepay.com/pages/webhooks
- Chaves de API: https://docs.abacatepay.com/pages/authentication

## O que ja esta pronto

- Landing page base em `app/page.tsx`
- Planos em `lib/site-config.ts`
- Rota `POST /api/checkout`
- Webhook `POST /api/webhooks/abacatepay`
- Validacao HMAC em `lib/abacatepay.ts`
- README de setup e deploy

## O que falta personalizar

- copy final da oferta
- IDs reais dos produtos na AbacatePay
- branding final
- armazenamento dos pedidos aprovados
- automacao pos-pagamento

## Variaveis obrigatorias

- `ABACATEPAY_API_KEY`
- `ABACATEPAY_API_VERSION`
- `ABACATEPAY_WEBHOOK_SECRET`
- `NEXT_PUBLIC_SITE_URL`
- `CHECKOUT_PRODUCT_ID_START`
- `CHECKOUT_PRODUCT_ID_PRO`
- `CHECKOUT_PRODUCT_ID_PREMIUM`

## Proximos passos recomendados

1. Instalar dependencias e rodar localmente
2. Definir se o ambiente vai usar `v1` ou `v2`
3. Se for `v2`, cadastrar produtos na AbacatePay
4. Preencher `.env.local`
5. Testar em Dev mode
6. Conectar webhook a alguma persistencia
7. Subir na Vercel
