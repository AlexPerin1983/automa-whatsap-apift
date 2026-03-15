# Prompts Prontos para Lovable — Por Tipo de Negócio

Estes são prompts-base que podem ser adaptados. A chave é: SEMPRE personalizar com dados reais do negócio antes de enviar ao Lovable.

---

## Prompt Base: Serviço Local (Insulfilm, Elétrica, Reforma, etc.)

```
Crie um site profissional para [NOME DA EMPRESA], empresa de [SERVIÇO] em [CIDADE].

## Design System

### Paleta de Cores
- Primária: [HEX] (usar em botões, headers, destaques)
- Primária escura: [HEX] (hover states, footer)
- Secundária: [HEX] (badges, ícones, acentos)
- Background: [HEX] (fundo principal — NÃO usar branco puro)
- Surface: #FFFFFF (cards)
- Texto: [HEX]
- Texto secundário: [HEX]

### Tipografia
- Títulos: [FONTE] — peso 700, tamanhos: Hero 56px, Seção 40px, Sub 24px
- Corpo: [FONTE] — peso 400, tamanho 17px, line-height 1.65
- Nunca usar fonte menor que 16px em mobile

### Estilo Visual
- Border-radius: 16px em cards, 12px em botões, 9999px em badges
- Sombras suaves: 0 4px 6px -1px rgba(0,0,0,0.07)
- Sombra no hover: 0 10px 25px -3px rgba(0,0,0,0.08)
- Espaço entre seções: 96px desktop, 64px mobile
- Container max-width: 1200px com padding lateral 24px mobile / 64px desktop

### Animações
- Cards: hover translate-y -4px com transição 300ms
- Botões: hover scale 1.03 com sombra aumentada
- Seções: fade-in de baixo ao entrar na viewport (Intersection Observer)
- Números: counter animation de 0 até o valor final

---

## Estrutura do Site

### Hero Section (Layout split 55/45)
Lado esquerdo: Foto real do serviço com border-radius 24px e sombra colorida sutil
Lado direito:
- Badge: "🏆 [DIFERENCIAL] em [CIDADE]" (bg secundária com opacidade 10%, texto secundária, border-radius pill)
- Headline (h1, 56px, peso 800): "[BENEFÍCIO PRINCIPAL PARA O CLIENTE]"
  Exemplo: "Proteção e Conforto Para Sua Casa o Ano Inteiro"
- Subheadline (20px, texto secundário): "[EXPLICAÇÃO DO SERVIÇO EM 1 FRASE]"
  Exemplo: "Instalação profissional de insulfilm residencial e automotivo com garantia de 5 anos"
- Prova social inline: "★★★★★ [NÚMERO]+ clientes satisfeitos em [CIDADE]"
- CTA primário: botão grande bg primária, texto branco, radius 12px: "[AÇÃO] — É Grátis"
  Exemplo: "Solicitar Orçamento Grátis"
- CTA secundário: botão ghost/outline: "Ver Nossos Trabalhos ↓"

### Seção: Números (bg: surface, padding: 48px)
4 cards em row com:
- Número grande (40px, peso 800, cor primária) com animação counter
- Label pequeno (14px, texto secundário)
Dados: "[X]+ Projetos" | "[X] Anos de Experiência" | "[X]% Garantia" | "★ [X] Avaliação Google"

### Seção: Serviços (bg: background)
Título: "Nossos Serviços"
Subtítulo: "[FRASE SOBRE VARIEDADE]"
Layout: Bento Grid — 1 card grande à esquerda (ocupa 2 rows), 4 cards menores à direita (2x2)
Cada card:
- Ícone do Lucide React (tamanho 32px, cor primária, bg primária/10%)
- Nome do serviço (peso 600)
- Descrição curta (2 linhas max, texto secundário)
- Hover: translate-y -4px + sombra cresce
Cards com dados REAIS:
1. [SERVIÇO 1] — [DESCRIÇÃO]
2. [SERVIÇO 2] — [DESCRIÇÃO]
3. [SERVIÇO 3] — [DESCRIÇÃO]
4. [SERVIÇO 4] — [DESCRIÇÃO]
5. [SERVIÇO 5] — [DESCRIÇÃO]

### Seção: Como Funciona (bg: primária escura, texto branco)
Título: "Como Funciona" (branco)
4 steps horizontais com linha conectora SVG:
Step 1: [ÍCONE] "[PASSO 1]" — [DESCRIÇÃO CURTA]
Step 2: [ÍCONE] "[PASSO 2]" — [DESCRIÇÃO CURTA]
Step 3: [ÍCONE] "[PASSO 3]" — [DESCRIÇÃO CURTA]
Step 4: [ÍCONE] "[PASSO 4]" — [DESCRIÇÃO CURTA]
Em mobile: vertical com linha à esquerda (timeline)

### Separador: SVG wave (da cor primária escura para background)

### Seção: Galeria / Antes e Depois (bg: background)
Título: "Nossos Trabalhos"
Grid de 6 fotos com hover overlay mostrando descrição
OU slider antes/depois interativo (se aplicável ao serviço)
Imagens com border-radius 16px e sombra sutil

### Seção: Depoimentos (bg: surface)
Título: "O Que Nossos Clientes Dizem"
3 cards de depoimento:
- ★★★★★ (5 estrelas em cor secundária)
- Texto do depoimento entre aspas
- Nome — 📍 Cidade
- Foto circular do cliente (se disponível)
Cards com borda top de 3px na cor primária

### Seção: FAQ (bg: background)
Título: "Perguntas Frequentes"
Accordion com 5-7 perguntas reais:
1. "[PERGUNTA]?" — "[RESPOSTA]"
2. "[PERGUNTA]?" — "[RESPOSTA]"
...
Estilo: cards com sombra sutil, ícone ChevronDown que gira 180° ao abrir

### Seção: CTA Final (bg: gradiente primária → primária escura)
Headline (branco, 40px): "[CHAMADA PARA AÇÃO]"
Subheadline (branco/80%): "[FRASE DE URGÊNCIA SUTIL]"
Botão grande: bg branco, texto primária: "Falar no WhatsApp"
Link: https://wa.me/55[DDD][NÚMERO]?text=[MENSAGEM CODIFICADA]

### Footer (bg: #0F172A ou primária escura)
Coluna 1: Logo + descrição curta + redes sociais (ícones)
Coluna 2: Links rápidos (Serviços, Galeria, Depoimentos, Contato)
Coluna 3: Contato (endereço, telefone, email, horário)
Bottom: "© 2026 [EMPRESA]. Todos os direitos reservados."

---

## Regras Finais
- Mobile-first, responsivo em 375px, 768px, 1024px, 1440px
- Usar shadcn/ui components customizados com as cores da paleta
- Todas as animações com prefers-reduced-motion respect
- WhatsApp button flutuante fixo no canto inferior direito (verde #25D366, radius full, sombra)
- Meta tags: title, description, og:image para compartilhamento
- Favicon com a cor primária
```

---

## Prompt Base: Restaurante / Hamburgueria / Bar

```
Crie um site para [NOME], [TIPO] em [CIDADE].
Vibe: [premium/artesanal/casual] — design dark mode com fotos de alta qualidade.

## Design System
[Usar paleta "Dark Gourmet" ou "Sabor Quente" de paletas-por-segmento.md]

### Tipografia
- Títulos: Playfair Display ou Sora — peso 700
- Corpo: DM Sans ou Inter — peso 400, 17px

### Estilo
- Dark mode: background escuro (#0C0A09), texto claro (#FAFAF9)
- Cards com glassmorphism: backdrop-blur-md, bg white/5%, border white/10%
- Fotos com overlay gradiente (de baixo: preto 60% → transparente)
- Animações: fade-in suaves, parallax sutil no hero

## Estrutura
### Hero: Foto full-width com overlay + headline gigante (72px) + CTA "Reserve / Peça"
### Galeria: Grid assimétrica de fotos (3 colunas, alturas variadas)
### Cardápio: Tabs por categoria, items com nome + descrição + preço
### Sobre: Split — foto do chef/equipe + história resumida
### Localização: Mapa + horários + botão "Como Chegar"
### Footer: Dark, minimalista, redes sociais em destaque
```

---

## Prompt Base: Clínica / Consultório / Saúde

```
Crie um site para [NOME], [ESPECIALIDADE] em [CIDADE].
Tom: profissional, acolhedor, que transmite confiança e cuidado.

## Design System
[Usar paleta "Cuidado Sereno" ou "Wellness Natural"]

### Tipografia
- Títulos: Plus Jakarta Sans — peso 700
- Corpo: Inter — peso 400, 17px

### Estilo
- Clean e arejado: muito espaço em branco
- Fotos reais do consultório e equipe (NADA de fotos stock genéricas)
- Ícones suaves e orgânicos
- Cards com radius 20px (friendly)
- Cores suaves, sem contrastes agressivos

## Estrutura
### Hero: Split — foto do profissional sorrindo + headline focado no paciente
### Especialidades/Serviços: Grid de cards com ícones
### Sobre o Profissional: Bio + formação + CRM/CRO + foto profissional
### Depoimentos: Carrossel com foto do paciente
### Convênios: Logos dos planos aceitos em row
### Agendamento: Formulário simples (nome + tel + especialidade) OU botão WhatsApp
### Localização: Mapa + endereço + estacionamento
### Footer: Clean, com selos de especialização
```

---

## Dicas Universais para Qualquer Prompt

1. **Substituir TUDO** entre [COLCHETES] com dados reais antes de enviar
2. **Nunca** enviar o prompt inteiro de uma vez se for muito grande — dividir em 2-3 etapas
3. **Primeira etapa**: Design System + Hero + Navbar
4. **Segunda etapa**: Seções de conteúdo (serviços, galeria, depoimentos)
5. **Terceira etapa**: CTA final + Footer + Responsividade + Animações
6. **Sempre testar** mobile (375px) depois de cada etapa
7. **Usar "Select"** no Lovable para ajustar componentes específicos ao invés de reescrever tudo
