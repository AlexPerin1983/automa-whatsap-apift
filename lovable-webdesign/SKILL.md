---
name: lovable-webdesign
description: >
  Skill profissional de Web Design para criar sites no Lovable que realmente impressionam.
  Gera prompts otimizados com design system completo (paletas, tipografia, espaçamento,
  micro-interações, hero sections de alta conversão, layouts orgânicos e únicos).
  USE ESTA SKILL sempre que o usuário mencionar: criar site, fazer landing page,
  montar página web, site para empresa, site profissional, portfolio, site de serviços,
  Lovable, design de site, layout de site, redesign, melhorar site, site bonito,
  ou qualquer criação de presença web. Também use quando o resultado visual de um site
  estiver "genérico", "feio", "artificial" ou "igual a todos os outros".
---

# Web Design Profissional para Lovable

Este skill transforma prompts genéricos em briefings de design de nível agência,
produzindo sites únicos que não parecem "template de IA".

## Filosofia: Por que sites de IA ficam genéricos?

A maioria dos prompts para Lovable falha em 3 pontos:

1. **Sem personalidade visual** — não definem paleta, tipografia, nem mood. O Lovable usa defaults seguros (cinza, branco, azul genérico) que geram aquele visual "template Wix 2019".

2. **Estrutura previsível** — Hero com imagem stock > 3 cards de features > seção "sobre" > footer. Todo site fica igual.

3. **Sem micro-detalhes** — Faltam sombras sutis, bordas arredondadas intencionais, gradientes, espaçamento generoso, e animações que dão vida.

A solução: construir um **Design System completo ANTES** de mandar qualquer prompt de código.

---

## Workflow: Do Briefing ao Site Pronto

### ETAPA 1 — Entender o Negócio (Entrevista Rápida)

Antes de qualquer design, entender:

- Qual o negócio? (ex: insulfilm residencial, hamburgueria, escritório de advocacia)
- Quem é o cliente ideal? (ex: donos de casa classe B/C, idade 30-55)
- Qual a ação principal que o visitante deve tomar? (ex: chamar no WhatsApp, pedir orçamento)
- Qual o "tom" desejado? (ex: profissional confiável, moderno e sofisticado, jovem e ousado)
- Existem cores da marca? Logo? Fotos reais?
- Quais são os 3 maiores diferenciais do negócio?

Se o usuário não souber responder tudo, sugerir opções inteligentes baseadas no segmento.

### ETAPA 2 — Criar o Design System

Montar um bloco de especificações visuais que vai na **Knowledge Base do Lovable** ou no início do prompt.

O Design System tem 7 pilares:

#### 2.1 — Paleta de Cores (5-7 cores)

Nunca usar cores genéricas. Cada negócio tem uma "energia cromática" que transmite confiança no segmento.

Estrutura da paleta:
- **Primária**: Cor dominante da marca (botões, destaques, CTAs)
- **Primária escura**: Para hover states e headers
- **Secundária**: Cor de contraste/complementar (badges, ícones, acentos)
- **Background**: Fundo principal (evitar branco puro #FFFFFF — usar off-whites como #FAFAF8 ou tons sutis)
- **Surface**: Cards e containers (ligeiramente diferente do background)
- **Texto principal**: Quase preto mas não #000000 (usar #1A1A2E ou #2D2D3A)
- **Texto secundário**: Para subtítulos e descrições (#6B7280 ou similar)

Regras de ouro:
- Background NUNCA branco puro (#FFF). Usar off-whites com sutil tom quente (#FAFAF8, #F8F7F4) ou frio (#F0F4F8, #EEF2FF)
- Primária com saturação suficiente para destacar mas sem "queimar os olhos"
- Mínimo 4.5:1 de contraste para texto (WCAG AA)
- Fornecer os códigos HEX exatos — nunca deixar o Lovable escolher

Consultar `references/paletas-por-segmento.md` para paletas prontas por tipo de negócio.

#### 2.2 — Tipografia

A tipografia é responsável por 60% da personalidade visual de um site.

Regras:
- **2 fontes no máximo**: Uma para títulos, outra para corpo
- **Títulos**: Fontes com personalidade (Inter, Space Grotesk, Outfit, Plus Jakarta Sans, Sora, Manrope, Cabinet Grotesk)
- **Corpo**: Fontes de alta legibilidade (Inter, DM Sans, Plus Jakarta Sans, Nunito Sans)
- **Escala tipográfica**:
  - Hero headline: 48-72px (mobile: 32-40px)
  - Section title: 36-48px (mobile: 28-32px)
  - Subtítulo: 20-24px
  - Corpo: 16-18px (nunca menor que 16px em mobile)
  - Caption/small: 14px
- **Line-height**: 1.2 para títulos, 1.6-1.7 para corpo
- **Font-weight**: Títulos em 600-800, corpo em 400-500

Evitar: Times New Roman, Arial, Helvetica (genéricos demais), fontes decorativas/script no corpo.

#### 2.3 — Espaçamento e Ritmo Visual

O espaçamento é o que separa um site profissional de um amador.

Sistema de 8px:
- Micro: 4px, 8px (dentro de componentes)
- Pequeno: 12px, 16px (entre elementos próximos)
- Médio: 24px, 32px (entre blocos relacionados)
- Grande: 48px, 64px (entre seções)
- Extra: 80px, 96px, 120px (padding de seção em desktop)

Regra fundamental: **quando em dúvida, MAIS espaço**. Sites genéricos pecam por amontoar elementos. Sites premium respiram.

- Padding lateral do container: 24px mobile, 48-64px tablet, 80-120px desktop
- Max-width do conteúdo: 1200px (nunca deixar texto se espalhar por tela inteira)
- Espaço entre seções: mínimo 80px, ideal 96-120px

#### 2.4 — Componentes e Estilo Visual

Definir o "flavor" dos componentes:

**Bordas (border-radius)**:
- Suave/Premium: 12-16px (a maioria dos sites modernos)
- Arredondado/Friendly: 20-24px
- Sharp/Corporativo: 4-8px
- Pill: 9999px (para badges e tags)

**Sombras (box-shadow)**:
- Sutil/Elegante: `0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)`
- Cards flutuantes: `0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05)`
- Destaque/Hover: `0 10px 25px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.03)`
- Colorida (premium): `0 10px 25px -5px rgba(COR_PRIMÁRIA, 0.2)`
- NUNCA usar sombras pesadas pretas com alta opacidade

**Gradientes**:
- De primária para primária-escura em botões
- Gradientes sutis no background de seções (do background para surface)
- Gradiente radial sutil como "glow" atrás de elementos hero
- Mesh gradients para backgrounds de seção premium

**Ícones**:
- Lucide React (já incluído no Lovable) — estilo consistente
- Tamanho: 20-24px inline, 32-48px em feature cards
- Cor: usar primária ou secundária, nunca preto puro

#### 2.5 — Layout e Estrutura de Página

**A regra anti-genérico**: Nunca seguir a estrutura padrão de template. Cada seção deve ter uma "surpresa visual" que quebre a monotonia.

Técnicas de layout moderno:
- **Bento Grid**: Inspirado no Apple — cards de tamanhos variados numa grid assimétrica
- **Overlap**: Elementos que sobrepõem seções (imagem que "invade" a próxima seção)
- **Split screen**: Hero dividido em 2 colunas com alturas desiguais
- **Floating elements**: Badges, ícones ou shapes decorativos flutuando com posição absoluta
- **Section dividers orgânicos**: SVG curves ao invés de linhas retas entre seções
- **Asymmetric columns**: 60/40 ou 70/30 ao invés de sempre 50/50

Consultar `references/layouts-modernos.md` para exemplos de estrutura por tipo de site.

#### 2.6 — Micro-interações e Animações

Animações dão vida ao site e transmitem qualidade. O Lovable entende bem Tailwind animate e Framer Motion.

Essenciais:
- **Hover em botões**: Scale 1.02-1.05 + sombra aumenta + cor escurece
- **Hover em cards**: Translate-y -4px + sombra cresce
- **Scroll reveal**: Elementos entram de baixo com fade (usar Intersection Observer)
- **Números contadores**: Contadores animados para estatísticas
- **Typing effect**: Para headlines no hero (com cuidado — usar apenas 1x)
- **Parallax sutil**: Background se move mais lento que foreground no scroll

Proibido:
- Animações que atrasam a interação do usuário
- Efeitos que causam motion sickness (muita rotação/zoom)
- Mais de 3 animações visíveis ao mesmo tempo

#### 2.7 — Responsividade

Mobile-first OBRIGATÓRIO:
- Testar em 375px (iPhone SE), 390px (iPhone 14), 768px (tablet), 1024px, 1440px
- Hamburger menu em mobile (nunca mostrar nav completa em tela pequena)
- Botão de CTA fixo no bottom em mobile (sticky bottom bar)
- Imagens com aspect-ratio definido para evitar layout shift
- Touch targets mínimo 44x44px

---

### ETAPA 3 — Estrutura do Prompt para Lovable

O prompt para o Lovable deve seguir esta estrutura:

```
## Design System
[Todo o bloco da Etapa 2 — paleta, tipografia, espaçamento, componentes]

## Estrutura do Site

### Hero Section
[Descrição detalhada com textos reais, CTA principal, estilo visual]

### Seção 2: [Nome descritivo]
[Descrição com layout específico, conteúdo real]

### Seção 3: [Nome descritivo]
[...]

### Footer
[...]

## Regras Globais
- Mobile-first, responsivo em todos os breakpoints
- Usar shadcn/ui components customizados com a paleta definida
- Animações suaves com Framer Motion ou Tailwind animate
- Performance: imagens otimizadas, lazy loading
- SEO: meta tags, alt texts, heading hierarchy (h1 > h2 > h3)
```

Regras do prompt:
- SEMPRE incluir textos REAIS, nunca "Lorem ipsum" ou "Texto aqui"
- Descrever cada seção com layout visual específico (não apenas conteúdo)
- Referenciar as cores pela role (primária, surface) não pelo hex
- Uma tarefa por prompt — se o site tem 5 seções, pode ser 2-3 prompts iterativos

---

### ETAPA 4 — Hero Section (A Seção Mais Importante)

O hero é responsável por 80% da primeira impressão. Receitas de hero que convertem:

**Hero Tipo 1 — "Impact Statement"** (Para serviços locais)
- Headline bold com benefício principal (não o nome da empresa)
- Subheadline com prova social ou diferencial
- CTA primário grande e contrastante ("Solicitar Orçamento Grátis")
- CTA secundário discreto ("Ver nossos trabalhos")
- Background com gradiente sutil + shape decorativo (blob ou circle)
- Opcional: foto real do serviço com overlay de gradiente

**Hero Tipo 2 — "Visual Showcase"** (Para portfólios e criativos)
- Imagem ou vídeo full-width com overlay escuro (60-70% opacidade)
- Texto centralizado sobre a imagem
- Tipografia extra-large (64-80px desktop)
- Um único CTA centralizado

**Hero Tipo 3 — "Bento Dashboard"** (Para SaaS e tech)
- Grid assimétrica com cards mostrando features
- Headline à esquerda, grid à direita
- Cada card com ícone + dado/estatística
- Animação de entrada escalonada nos cards

**Hero Tipo 4 — "Social Proof First"** (Para alta conversão)
- Linha de avatares/logos de clientes no topo
- "★★★★★ Mais de 500 clientes satisfeitos"
- Headline com resultado concreto
- Formulário inline (nome + WhatsApp + botão)

---

### ETAPA 5 — Seções que Fazem a Diferença

Seções que elevam um site de "genérico" para "profissional":

**Prova Social Visual**
- Não apenas texto: fotos reais, vídeos curtos, prints de conversas
- Carrossel de depoimentos com foto + nome + cidade
- Números grandes animados: "500+ projetos", "8 anos no mercado"

**Antes/Depois** (para serviços visuais)
- Slider interativo com arraste
- 3-4 exemplos lado a lado
- Funciona MUITO bem para instalações, reformas, design

**Processo em Steps**
- 3-4 passos com ícones numerados
- Linha conectora entre os passos (SVG path)
- Mostra transparência e gera confiança

**FAQ Accordion**
- Respostas reais às objeções mais comuns
- Ajuda no SEO com perguntas que as pessoas pesquisam
- Estilo: cards com sombra sutil, ícone de + que gira

**CTA Final (Bottom)**
- Repetir o CTA principal antes do footer
- Background diferente (primária escura ou gradiente)
- Texto de urgência sutil ("Orçamento gratuito e sem compromisso")

---

### ETAPA 6 — Revisão e Polimento

Checklist final antes de considerar o site pronto:

- [ ] Paleta aplicada consistentemente (nenhuma cor fora do sistema)
- [ ] Tipografia com hierarquia clara (h1 > h2 > h3 sem pular)
- [ ] Espaçamento generoso entre seções (mínimo 80px)
- [ ] Todos os textos são reais e relevantes
- [ ] CTAs visíveis e com cor contrastante
- [ ] Mobile testado em 375px (nada cortado ou sobreposto)
- [ ] Imagens com alt text descritivo
- [ ] Animações suaves (sem lag ou salto)
- [ ] Links do WhatsApp funcionando com mensagem pré-preenchida
- [ ] Favicon e meta tags definidos
- [ ] Velocidade: sem imagens gigantes não-otimizadas

---

## Referências Complementares

Para paletas de cores específicas por segmento de negócio:
→ Ler `references/paletas-por-segmento.md`

Para estruturas de layout modernas com exemplos:
→ Ler `references/layouts-modernos.md`

Para prompts prontos por tipo de negócio:
→ Ler `references/prompts-prontos.md`
