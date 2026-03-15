# Layouts Modernos — Estruturas que Quebram o Genérico

## O Problema dos Templates

O layout genérico de IA segue sempre:
```
[Nav]
[Hero centralizado com texto + botão]
[3 cards iguais lado a lado]
[Seção texto esquerda + imagem direita]
[3 cards iguais de novo]
[Footer]
```

Sites profissionais quebram esse padrão com variação visual entre seções.

---

## Layout 1: "Assimétrico Respirante" (Serviços Locais)

Ideal para: Insulfilm, elétrica, reformas, limpeza, jardinagem.

```
┌─────────────────────────────────────────────────┐
│ [Logo]                    [Tel] [WhatsApp btn]  │  ← Nav compacta
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────────┐  ┌──────────────────────┐  │
│  │                 │  │  HEADLINE BOLD        │  │  ← Hero split 55/45
│  │   FOTO REAL     │  │  Subheadline          │  │     Foto à esquerda
│  │   do serviço    │  │  ★★★★★ 500+ clientes │  │     (com borda-radius
│  │   (com radius   │  │                      │  │      grande: 24px)
│  │    e sombra)    │  │  [CTA GRANDE]         │  │
│  │                 │  │  [CTA secundário]     │  │
│  └─────────────────┘  └──────────────────────┘  │
│                                                 │
├─────────────────────────────────────────────────┤
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│  │ 500+ │ │  8   │ │ 100% │ │  ★5  │          │  ← Barra de números
│  │projts│ │ anos │ │garant│ │avalia│          │     animados (counters)
│  └──────┘ └──────┘ └──────┘ └──────┘          │     bg: surface sutil
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  "Nossos Serviços"                              │
│                                                 │
│  ┌────────────────┐ ┌─────────┐ ┌─────────┐   │  ← Bento Grid
│  │                │ │         │ │         │   │     Card grande à esq.
│  │  CARD GRANDE   │ │ CARD 2  │ │ CARD 3  │   │     2 pequenos à dir.
│  │  com imagem    │ │         │ │         │   │     Hover: escala +
│  │  de fundo      │ ├─────────┤ ├─────────┤   │     sombra colorida
│  │                │ │ CARD 4  │ │ CARD 5  │   │
│  └────────────────┘ └─────────┘ └─────────┘   │
│                                                 │
├── SVG wave divider ────────────────────────────┤  ← Separador orgânico
│                                                 │     (não linha reta)
│  ┌─────────────────────────────────────────┐   │
│  │  "Como Funciona" — 4 Steps              │   │  ← Processo em steps
│  │                                         │   │     com linha conectora
│  │  ①────②────③────④                       │   │     SVG animada
│  │  Contato Visita  Orçam. Instalação     │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────┐  ┌────────────────────┐  │
│  │  ANTES           │  │  DEPOIS            │  │  ← Antes/Depois
│  │  [foto]          │  │  [foto]            │  │     com slider
│  │       ◄─── drag ────►                    │  │     interativo
│  └──────────────────┘  └────────────────────┘  │
│                                                 │
│  [mais 2-3 exemplos em carrossel]              │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  "O que nossos clientes dizem"                 │
│                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐       │  ← Depoimentos
│  │  ★★★★★  │ │  ★★★★★  │ │  ★★★★★  │       │     com foto real
│  │  "Texto" │ │  "Texto" │ │  "Texto" │       │     + nome + cidade
│  │  — João  │ │  — Maria │ │  — Pedro │       │
│  │  📍 JP   │ │  📍 JP   │ │  📍 Rec  │       │
│  └──────────┘ └──────────┘ └──────────┘       │
│                                                 │
├── bg: primária escura ──────────────────────────┤
│                                                 │
│  "Solicite seu orçamento grátis"               │  ← CTA Final
│  [Subtexto de urgência sutil]                  │     bg diferente
│  [BOTÃO WHATSAPP GRANDE]                       │     texto claro
│                                                 │
├─────────────────────────────────────────────────┤
│  [Logo] [Endereço] [Tel] [Redes]  [WhatsApp]  │  ← Footer
│  © 2026 — Todos os direitos reservados         │
└─────────────────────────────────────────────────┘
```

---

## Layout 2: "Dark Premium" (Restaurantes, Bares, Barbearias)

```
┌─ bg: escuro (#0C0A09) ─────────────────────────┐
│ [Logo]              [Menu] [Reservas] [Contato] │
├─────────────────────────────────────────────────┤
│                                                 │
│         HEADLINE GIGANTE (72px)                 │  ← Hero full-width
│         em dourado/amber sobre fundo escuro     │     com foto parallax
│                                                 │     como background
│  ┌─────────────────────────────────────────┐   │
│  │   FOTO full-width com overlay gradient   │   │
│  │   de baixo (preto 70% → transparente)   │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│         [CTA: "Reserve sua mesa"]               │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────┐  ┌─────────────┐              │
│  │   FOTO 1    │  │   FOTO 2    │              │  ← Gallery Grid
│  │   (tall)    │  │   (square)  │              │     tamanhos variados
│  │             │  ├─────────────┤              │     gap: 8px
│  │             │  │   FOTO 3    │              │     radius: 16px
│  └─────────────┘  └─────────────┘              │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  "Nosso Cardápio" (ou "Nossos Serviços")       │
│                                                 │
│  [Tab: Entradas] [Tab: Pratos] [Tab: Bebidas]  │  ← Menu com tabs
│                                                 │     animação de slide
│  ┌─ Item ──────────────────────── R$ 49 ─┐     │     entre tabs
│  │  Nome do prato                         │     │
│  │  Descrição curta em texto secundário   │     │
│  ├─ Item ──────────────────────── R$ 35 ─┤     │
│  │  ...                                   │     │
│  └────────────────────────────────────────┘     │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│      ┌────────────────────────────┐            │
│      │   MAPA + ENDEREÇO          │            │  ← Localização
│      │   Horário de funcionamento │            │     embed Google Maps
│      │   [Botão: Como chegar]     │            │     ou imagem estática
│      └────────────────────────────┘            │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Layout 3: "Clean SaaS / Tech" (Aplicativos, Startups)

```
┌─────────────────────────────────────────────────┐
│ [Logo]  [Produto] [Preços] [Blog]   [Login/CTA]│
├─────────────────────────────────────────────────┤
│                                                 │
│         HEADLINE com gradient text              │  ← Hero centralizado
│         (text gradient: primária → secundária)  │     mas com elementos
│                                                 │     flutuantes ao redor
│         Subheadline em texto secundário         │
│                                                 │
│    [CTA primário]    [CTA ghost/outline]        │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │                                         │   │  ← Screenshot do app
│  │     SCREENSHOT / DEMO DO PRODUTO        │   │     com borda + sombra
│  │     (com perspective 3D sutil:          │   │     + perspective CSS
│  │      rotateX(2deg) rotateY(-2deg))      │   │     Glow atrás (radial
│  │                                         │   │     gradient da primária)
│  └─────────────────────────────────────────┘   │
│                                                 │
│  "Usado por" [logo1] [logo2] [logo3] [logo4]  │  ← Social proof logos
│                                                 │     em grayscale, hover
│                                                 │     mostra cor original
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ ⚡ Feature│ │ 🔒 Feat. │ │ 📊 Feat. │       │  ← Feature cards
│  │  Título  │ │  Título  │ │  Título  │       │     ícone em destaque
│  │  Texto   │ │  Texto   │ │  Texto   │       │     com bg colorido
│  │  curto   │ │  curto   │ │  curto   │       │     hover: borda primária
│  └──────────┘ └──────────┘ └──────────┘       │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌────────────────────┐ ┌──────────────────┐   │
│  │  TEXTO à esquerda  │ │  SCREENSHOT 2    │   │  ← Feature showcase
│  │                    │ │  do produto      │   │     alternado esq/dir
│  │  Headline feature  │ │  em uso          │   │
│  │  Descrição         │ │                  │   │
│  │  • Bullet 1        │ │                  │   │
│  │  • Bullet 2        │ │                  │   │
│  └────────────────────┘ └──────────────────┘   │
│                                                 │
│  ┌──────────────────┐ ┌────────────────────┐   │  ← INVERTIDO
│  │  SCREENSHOT 3    │ │  TEXTO à direita   │   │
│  │                  │ │  ...               │   │
│  └──────────────────┘ └────────────────────┘   │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐    │  ← Pricing cards
│  │  BÁSICO   │ │ ★ PRO ★   │ │ ENTERPRISE│    │     card do meio
│  │  R$29/mês │ │ R$79/mês  │ │ Sob medida│    │     destacado (scale
│  │           │ │ (destaque)│ │           │    │     1.05 + borda
│  │  • feat 1 │ │ • feat 1  │ │ • tudo    │    │     primária + badge
│  │  • feat 2 │ │ • feat 2  │ │ • feat +  │    │     "Mais popular")
│  │           │ │ • feat 3  │ │ • suporte │    │
│  │  [Botão]  │ │ [BOTÃO]   │ │ [Contato] │    │
│  └───────────┘ └───────────┘ └───────────┘    │
│                                                 │
├── bg: gradient sutil ───────────────────────────┤
│                                                 │
│         "Comece agora — é grátis"              │  ← CTA final
│         [BOTÃO GRANDE]                          │     centralizado
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Técnicas de "Surpresa Visual" por Seção

Para quebrar monotonia, cada seção adjacente deve variar em pelo menos 2 destes:

| Variável | Opções |
|----------|--------|
| Background | Claro / Escuro / Gradiente / Imagem |
| Layout | Centralizado / Split / Grid / Full-width |
| Alinhamento | Esquerda / Centro / Alternado |
| Decoração | Nenhuma / Blob SVG / Dots pattern / Grid lines |
| Animação | Nenhuma / Fade-in / Slide / Counter / Parallax |

**Regra**: Nunca ter 2 seções seguidas com o mesmo bg + mesmo layout.

---

## Separadores de Seção (Section Dividers)

Linhas retas entre seções = genérico. Alternativas:

1. **Wave SVG**: Curva suave entre seções de cores diferentes
2. **Angle**: Seção com `clip-path: polygon(0 0, 100% 4%, 100% 100%, 0 100%)`
3. **Dots/Circles pattern**: Padrão de pontos sutis na transição
4. **Gradiente fade**: Uma seção faz fade gradual para a cor da próxima
5. **Overlap**: Elemento (card, imagem) posicionado -40px sobre a próxima seção
