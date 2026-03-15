# Exemplo: Prompt Gerado pela Skill para Insulfilm em João Pessoa

> Este é um exemplo de como a skill transforma um pedido simples
> como "cria um site para minha empresa de insulfilm" num briefing
> profissional completo para o Lovable.

---

## Prompt para Lovable (copiar e colar)

Crie um site profissional e moderno para uma empresa de insulfilm residencial e automotivo em João Pessoa - PB. O site deve parecer premium, único, e NÃO genérico.

## Design System

### Paleta de Cores (Proteção Solar)
- Primária: #0F766E (teal escuro — proteção + modernidade)
- Primária escura: #0A5C56 (para hover states, footer, seção CTA)
- Secundária: #F97316 (laranja vibrante — remetendo ao sol/calor que o insulfilm bloqueia)
- Background: #F0FDFA (verde-água claríssimo — NÃO usar branco puro)
- Surface: #FFFFFF (para cards)
- Texto principal: #134E4A
- Texto secundário: #5E8B87
- Accent/Alerta: #EF4444 (para badges de destaque como "Promoção")

### Tipografia
- Títulos: Space Grotesk — peso 700-800
  - Hero headline: 56px desktop, 36px mobile
  - Section title: 40px desktop, 28px mobile
  - Subtítulo: 22px
- Corpo: DM Sans — peso 400, 17px, line-height 1.65
- Nunca menor que 16px em mobile

### Estilo Visual
- Border-radius: 16px em cards, 12px em botões, 24px na imagem hero, 9999px em badges
- Sombras suaves: 0 4px 6px -1px rgba(0,0,0,0.07) (padrão), 0 10px 25px rgba(15,118,110,0.15) (hover — sombra colorida teal)
- Espaço entre seções: 96px desktop, 64px mobile
- Container max-width: 1200px, padding lateral 24px mobile, 64px desktop
- Gradientes: de #0F766E para #0A5C56 em botões; radial glow sutil de #0F766E com 10% opacidade atrás do hero

### Animações
- Hover em cards: translate-y -4px + sombra cresce (transição 300ms ease)
- Hover em botões: scale 1.03 + sombra colorida aumenta
- Seções: fade-in de baixo (20px) ao entrar na viewport com Intersection Observer
- Números: counter animation de 0 até o valor final (duration 2s)

---

## Estrutura do Site

### Navbar
Fixa no topo com backdrop-blur. Bg: white/80% com backdrop-blur-md.
Logo à esquerda. Links: Serviços | Galeria | Depoimentos | Contato
Botão CTA à direita: "Orçamento Grátis" (bg primária, texto branco, radius 9999px)
Em mobile: hamburger menu com drawer lateral

### Hero Section (Layout split 55% esquerda / 45% direita)

Lado esquerdo:
- Imagem ilustrativa de uma casa moderna com janelas de vidro (com border-radius 24px e sombra teal sutil: 0 20px 40px rgba(15,118,110,0.15))
- Um elemento decorativo: círculo laranja (#F97316) com 20% opacidade, tamanho 200px, posição absoluta atrás da imagem no canto superior direito (decorativo, não interfere no conteúdo)

Lado direito:
- Badge no topo: "☀️ Proteção UV até 99%" — bg #F97316 com 10% opacidade, texto #F97316, border-radius 9999px, padding 6px 16px, font-size 14px
- Headline (h1, 56px, peso 800, cor #134E4A):
  "Proteção e Conforto Para Sua Casa o Ano Inteiro"
- Subheadline (20px, cor #5E8B87, margin-top 16px):
  "Instalação profissional de insulfilm residencial e automotivo em João Pessoa com garantia de 5 anos e atendimento no mesmo dia."
- Prova social (margin-top 20px): ★★★★★ em #F97316, texto: "500+ clientes satisfeitos em João Pessoa" (14px, #5E8B87)
- CTA primário (margin-top 24px): botão grande — bg gradiente de #0F766E para #0A5C56, texto branco, padding 16px 32px, radius 12px, font-size 18px, peso 600: "Solicitar Orçamento Grátis"
- CTA secundário (margin-top 12px): botão ghost — border 2px #0F766E, texto #0F766E, padding 12px 24px: "Ver Nossos Trabalhos ↓"

### Seção: Números (bg: #FFFFFF, padding vertical 48px)
4 cards em row horizontal (mobile: grid 2x2):
Cada card: texto centralizado, sem borda, sem sombra
- "500+" (40px, peso 800, cor #0F766E, counter animation) + "Projetos Realizados" (14px, #5E8B87)
- "8" + "Anos de Experiência"
- "100%" + "Garantia nos Serviços"
- "★ 4.9" + "Avaliação no Google"

### Seção: Serviços (bg: #F0FDFA, padding vertical 96px)
Título centralizado: "Nossos Serviços" (40px, peso 700)
Subtítulo: "Soluções completas em películas para sua casa, empresa e veículo" (18px, #5E8B87)

Layout Bento Grid (margin-top 48px):
- Card Grande (ocupa 2 rows, à esquerda):
  Ícone Sun (Lucide, 32px, bg #F97316/10%, padding 12px, radius 12px)
  Título: "Insulfilm Residencial"
  Texto: "Proteção UV, redução de calor em até 78% e privacidade para sua casa. Trabalhamos com películas de alta performance das melhores marcas."

- Card 2: Ícone Car — "Insulfilm Automotivo"
  "Películas com certificação do CONTRAN. Instalação rápida sem bolhas."

- Card 3: Ícone Building2 — "Insulfilm Comercial"
  "Reduza o custo com ar-condicionado. Películas para escritórios, lojas e clínicas."

- Card 4: Ícone Shield — "Película de Segurança"
  "Proteção contra estilhaçamento. Ideal para vidros de fachada e áreas de risco."

- Card 5: Ícone Sparkles — "Película Decorativa"
  "Jateado, espelhado e colorido. Privacidade com estilo para divisórias e banheiros."

Hover: translate-y -4px, sombra colorida teal

### Separador: SVG wave — de #F0FDFA para #0A5C56

### Seção: Como Funciona (bg: #0A5C56, texto branco, padding 96px)
Título: "Como Funciona" (branco, 40px)
Subtítulo: "Processo simples e sem complicação" (branco/70%)

4 steps horizontais (mobile: vertical timeline):
①  Ícone MessageCircle — "Contato" — "Você nos chama no WhatsApp ou preenche o formulário"
②  Ícone ClipboardCheck — "Visita Técnica" — "Vamos até você para medir e avaliar sem custo"
③  Ícone FileText — "Orçamento" — "Enviamos o orçamento detalhado no mesmo dia"
④  Ícone CheckCircle2 — "Instalação" — "Instalação profissional com garantia de 5 anos"

Linha conectora SVG entre os steps (branco com 30% opacidade)
Ícones: bg branco com 15% opacidade, padding 16px, radius 16px

### Separador: SVG wave invertida — de #0A5C56 para #F0FDFA

### Seção: Galeria (bg: #F0FDFA, padding 96px)
Título: "Nossos Trabalhos"
Subtítulo: "Veja a transformação que o insulfilm faz"

Grid de 6 fotos com:
- 2 colunas em mobile, 3 em desktop
- Border-radius 16px
- Hover: overlay escuro com texto "Ver detalhes" + scale 1.05
- Sombra sutil

(Usar imagens placeholder com alt text descritivo:
"Insulfilm residencial em apartamento no Altiplano - João Pessoa",
"Película automotiva instalada em SUV preto",
"Insulfilm comercial em escritório no Manaíra", etc.)

### Seção: Depoimentos (bg: #FFFFFF, padding 96px)
Título: "O Que Nossos Clientes Dizem"

3 cards de depoimento:
Card estilo: bg white, borda top 3px cor #0F766E, radius 16px, sombra sutil, padding 32px

Card 1:
- ★★★★★ (cor #F97316)
- "Excelente trabalho! A casa ficou muito mais fresca e com uma privacidade incrível. Recomendo demais!"
- — João Silva, 📍 Manaíra - João Pessoa

Card 2:
- ★★★★★
- "Profissionalismo nota 10. Chegaram no horário, fizeram tudo limpo e sem bolhas. Voltaria a contratar com certeza."
- — Maria Santos, 📍 Bancários - João Pessoa

Card 3:
- ★★★★★
- "Melhor custo-benefício da cidade. Fiz em todos os vidros de casa e já senti a diferença na conta de energia."
- — Pedro Costa, 📍 Bessa - João Pessoa

### Seção: FAQ (bg: #F0FDFA, padding 96px)
Título: "Perguntas Frequentes"
Accordion com ícone ChevronDown que gira 180° ao abrir:

1. "Qual a durabilidade do insulfilm?" — "Nossas películas de alta qualidade duram de 10 a 15 anos com manutenção adequada. Oferecemos garantia de 5 anos contra bolhas e descolamento."

2. "O insulfilm escurece muito o ambiente?" — "Não necessariamente. Trabalhamos com diferentes tons e níveis de transparência. Podemos instalar películas que bloqueiam 99% dos raios UV mantendo boa luminosidade."

3. "Quanto tempo leva a instalação?" — "Para residências, a instalação leva de 2 a 4 horas dependendo da quantidade de vidros. Para veículos, entre 1 a 2 horas."

4. "Vocês fazem visita técnica gratuita?" — "Sim! Fazemos visita técnica sem compromisso em toda João Pessoa e região metropolitana para medir e apresentar as opções."

5. "O insulfilm realmente reduz o calor?" — "Sim, películas de controle solar podem reduzir até 78% do calor que entra pelos vidros, gerando economia significativa com ar-condicionado."

6. "Vocês atendem condomínios e empresas?" — "Sim, atendemos projetos de qualquer porte. Fazemos orçamentos especiais para condomínios e empresas com múltiplas unidades."

### Seção: CTA Final (bg: gradiente linear de #0F766E para #0A5C56, padding 80px)
Headline (branco, 40px, peso 700, centralizado): "Transforme o Conforto da Sua Casa Hoje"
Subheadline (branco/80%, 18px): "Orçamento gratuito e sem compromisso. Atendemos toda João Pessoa e região."
Botão grande (bg branco, texto #0F766E, padding 18px 40px, radius 12px, peso 600, font 18px): "Falar no WhatsApp"
Link do botão: https://wa.me/5583XXXXXXXXX?text=Olá!%20Gostaria%20de%20um%20orçamento%20para%20insulfilm

### Footer (bg: #0A5C56, texto branco, padding 64px top, 32px bottom)
3 colunas (mobile: empilhadas):
Coluna 1: Logo + "Especialistas em insulfilm residencial e automotivo em João Pessoa desde 2018." + ícones redes sociais (Instagram, Facebook, WhatsApp)
Coluna 2: "Links" — Serviços | Galeria | Depoimentos | Orçamento | FAQ
Coluna 3: "Contato" — Endereço | Telefone | Email | "Seg-Sáb: 8h às 18h"
Linha divisória (branco/10%)
Bottom: "© 2026 [Nome Empresa]. Todos os direitos reservados." (centralizado, 14px, branco/60%)

### Elemento Flutuante Global
Botão WhatsApp fixo no canto inferior direito:
- Ícone WhatsApp (branco) dentro de círculo verde (#25D366)
- Tamanho: 56x56px
- Sombra: 0 4px 12px rgba(37,211,102,0.3)
- Hover: scale 1.1
- Z-index alto (sempre visível)
- Link: wa.me/55XXXXXXXXXXX

---

## Regras Finais
- Mobile-first, responsivo em 375px, 768px, 1024px, 1440px
- Usar shadcn/ui components customizados com a paleta acima
- Animações suaves que respeitam prefers-reduced-motion
- Imagens otimizadas com lazy loading
- SEO: meta title, description, og:image
- Performance: target LCP < 2.5s
