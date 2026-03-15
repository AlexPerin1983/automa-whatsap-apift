# GOOGLE RASPAGEM AUTOMACAO E PROPECCAO

Workspace com dois projetos principais:

- `ProspectLocal`: sistema local de prospeccao, scraping no Google Maps, CRM simples e automacao via WhatsApp
- `site-vendas-abacatepay`: landing page comercial separada para vender o servico online

O objetivo desta estrutura e manter a operacao interna local e privada, enquanto a parte comercial pode ser publicada separadamente.

## Estrutura

```text
.
|-- ProspectLocal/
|   |-- app.py
|   |-- iniciar.py
|   `-- whatsapp-service/
|-- site-vendas-abacatepay/
|-- gerar_diagnostico.py
`-- README.md
```

## Requisitos

Antes de rodar, instale:

- Python 3.10+ recomendado
- Node.js 18+ recomendado
- npm
- Git

## Projeto 1: ProspectLocal

Aplicacao local em Flask para buscar empresas, organizar leads e operar campanhas de WhatsApp.

### O que ele faz

- busca empresas locais usando Apify + Google Maps
- salva empresas em banco SQLite local
- permite filtrar leads com ou sem site
- organiza contatos em fluxo de prospeccao
- integra com um servico Node.js para conexao com WhatsApp

### Requisitos especificos

- conta na [Apify](https://apify.com/)
- token de API da Apify
- WhatsApp para conectar os numeros no modulo `whatsapp-service`

### Como rodar o ProspectLocal

1. Entre na pasta:

```bash
cd ProspectLocal
```

2. Crie um ambiente virtual:

```bash
python -m venv .venv
```

3. Ative o ambiente virtual:

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Windows CMD:

```bat
.venv\Scripts\activate.bat
```

4. Instale as dependencias:

```bash
pip install -r requirements.txt
```

5. Use o arquivo `.env.example` apenas como referencia de setup:

```bash
cp .env.example .env
```

No Windows, se preferir, voce pode apenas abrir o arquivo e usar como checklist.

Importante:

- a versao atual do `ProspectLocal` nao le `.env` automaticamente
- o token da Apify e configurado pela interface do sistema
- o arquivo existe para facilitar onboarding e documentacao

6. Rode a aplicacao:

```bash
python iniciar.py
```

7. Abra no navegador:

```text
http://localhost:5000
```

### Configuracao inicial do ProspectLocal

Depois de abrir o sistema:

1. entre em Configuracoes
2. cole o token da Apify
3. salve
4. faca uma busca de teste com poucos resultados

### Como rodar o servico de WhatsApp

Esse modulo e separado do Flask e precisa de Node.js.

1. Entre na pasta:

```bash
cd ProspectLocal/whatsapp-service
```

2. Instale as dependencias:

```bash
npm install
```

3. Rode o servico:

```bash
npm start
```

4. O servico sobe em:

```text
http://localhost:3001
```

Observacao:

- o Flask deve estar rodando em `http://localhost:5000`
- o servico do WhatsApp conversa com o Flask localmente
- as sessoes do WhatsApp ficam locais e nao devem ser publicadas

### Fluxo recomendado para usar o ProspectLocal

1. iniciar o Flask
2. configurar o token da Apify
3. buscar empresas por nicho e cidade
4. revisar os leads encontrados
5. iniciar o servico WhatsApp
6. conectar um numero
7. fazer testes antes de disparos maiores

## Projeto 2: site-vendas-abacatepay

Landing page comercial em Next.js para apresentar a oferta e gerar checkout.

### O que ele faz

- mostra a pagina de vendas
- cria checkout pela AbacatePay
- pode receber webhook de pagamento
- foi pensado para deploy separado, por exemplo na Vercel

### Como rodar

1. Entre na pasta:

```bash
cd site-vendas-abacatepay
```

2. Instale as dependencias:

```bash
npm install
```

3. Crie o arquivo `.env.local` a partir de `.env.example`

4. Preencha as variaveis necessarias:

- `ABACATEPAY_API_KEY`
- `ABACATEPAY_API_VERSION`
- `ABACATEPAY_WEBHOOK_SECRET`
- `NEXT_PUBLIC_SITE_URL`
- `CHECKOUT_PRODUCT_ID_START`
- `CHECKOUT_PRODUCT_ID_PRO`
- `CHECKOUT_PRODUCT_ID_PREMIUM`

5. Rode localmente:

```bash
npm run dev
```

6. Abra no navegador:

```text
http://localhost:3000
```

### Build de validacao

```bash
npm run build
```

## Ordem mais simples para um amigo testar

Se ele for testar so a parte principal:

1. clonar o repositorio
2. rodar o `ProspectLocal`
3. depois rodar o `whatsapp-service`, se precisar de WhatsApp

Se ele for testar a pagina comercial:

1. entrar em `site-vendas-abacatepay`
2. configurar `.env.local`
3. rodar `npm install`
4. rodar `npm run dev`

## O que nao vai para o Git

Este repositorio esta configurado para nao publicar:

- bancos `.db`
- arquivos `.env`
- sessoes do WhatsApp
- caches e arquivos temporarios
- `node_modules`

## Dicas para compartilhar com seguranca

- nao commitar tokens da Apify
- nao commitar chaves da AbacatePay
- nao commitar sessoes autenticadas do WhatsApp
- use `.env.example` para mostrar configuracao sem expor segredo

## Observacoes

- o `ProspectLocal` e local e focado na operacao
- o `site-vendas-abacatepay` e publico e focado em vendas
- os dois projetos podem ser usados separadamente
