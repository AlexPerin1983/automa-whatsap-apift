# Agent Handoff

## O que e este projeto

Este projeto e uma pagina publica de vendas para comercializar criacao de sites com checkout da AbacatePay.

Ele foi criado para coexistir com o `ProspectLocal`, mas sem depender dele em runtime.

## O que nao fazer

- nao misturar esse app com o Flask local do `ProspectLocal`
- nao expor scraping, kanban ou configuracoes internas na mesma hospedagem
- nao mover a chave secreta da AbacatePay para o frontend

## Decisao de arquitetura

- workspace compartilhada
- projetos separados
- deploy separado
- pagamento hospedado na AbacatePay
- webhook server-side no proprio Next.js

## Estrutura principal

- `app/page.tsx`: landing page de venda
- `app/obrigado/page.tsx`: pagina de retorno simples
- `app/api/checkout/route.ts`: cria checkout na AbacatePay
- `app/api/webhooks/abacatepay/route.ts`: recebe eventos de pagamento
- `components/checkout-form.tsx`: formulario de lead + escolha de plano
- `lib/site-config.ts`: catalogo dos planos
- `lib/abacatepay.ts`: cliente da API e validacao de assinatura

## Como o checkout foi pensado

- o cliente escolhe um plano
- o frontend envia os dados para `POST /api/checkout`
- o backend cria o checkout hospedado
- a resposta devolve `checkoutUrl`
- o frontend redireciona o cliente para a AbacatePay

## Dependencias externas

- AbacatePay
- Vercel

## Variaveis de ambiente

- `ABACATEPAY_API_KEY`
- `ABACATEPAY_API_VERSION`
- `ABACATEPAY_WEBHOOK_SECRET`
- `NEXT_PUBLIC_SITE_URL`
- `CHECKOUT_PRODUCT_ID_START`
- `CHECKOUT_PRODUCT_ID_PRO`
- `CHECKOUT_PRODUCT_ID_PREMIUM`

## Fontes oficiais

- [Criar checkout](https://docs.abacatepay.com/pages/payment/create)
- [Webhooks](https://docs.abacatepay.com/pages/webhooks)
- [Autenticacao e chaves](https://docs.abacatepay.com/pages/authentication)

## Estado atual

- estrutura inicial pronta
- build validado com `npm run build`
- fluxo atual de testes usa `ABACATEPAY_API_VERSION=v1`
- webhook usa `secret` simples e registra evento
- falta persistencia de pedidos aprovados
- landing reposicionada para vender sites a empresas locais sem identidade profissional no Google
- falta configurar IDs reais dos produtos

## Melhor proximo passo

1. criar variacoes da landing por nicho local
2. cadastrar os produtos na AbacatePay
3. preencher `.env.local`
4. testar checkout em ambiente real
5. salvar eventos aprovados em banco ou CRM
6. subir na Vercel

## Observacoes para continuidade

- se o projeto evoluir para multi-oferta, manter os planos centralizados em `lib/site-config.ts`
- se houver onboarding automatico, criar uma camada propria apos o webhook
- se houver integracao com o `ProspectLocal`, prefira webhook ou API dedicada em vez de acoplamento direto
