#!/usr/bin/env python3
"""
Atualiza todos os 15 templates Lovable no banco de dados do ProspectLocal
com design system profissional baseado em tendências 2025-2026.

Cada template agora inclui:
- Design System completo (paleta HEX, tipografia, espaçamento, sombras)
- Layouts únicos por segmento (não genéricos)
- Micro-interações e animações específicas
- Hero sections de alta conversão
- Seções anti-genérico (bento grid, antes/depois, steps animados)
- Separadores orgânicos SVG
- Mobile-first obrigatório
"""

import sqlite3
import os

DB_PATH = '/sessions/funny-compassionate-hawking/mnt/GOOGLE RASPAGEM AUTOMAÇÃO E PROPECÇÃO/ProspectLocal/prospeccao.db'

print(f"DB Path: {DB_PATH}")
print(f"Exists: {os.path.exists(DB_PATH)}")

DESIGN_SYSTEM_BASE = """
## DESIGN SYSTEM OBRIGATÓRIO

### Paleta de Cores
{paleta}

### Tipografia
- **Títulos**: {fonte_titulo} — peso 700-800
  - Hero headline: 56px desktop / 36px mobile
  - Section title: 40px desktop / 28px mobile
  - Subtítulo: 22px
- **Corpo**: {fonte_corpo} — peso 400, 17px, line-height 1.65
- NUNCA menor que 16px em mobile

### Estilo Visual
- Border-radius: 16px em cards, 12px em botões, 24px na imagem hero, 9999px em badges/pills
- Sombra padrão: `0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05)`
- Sombra hover: `0 10px 25px -3px rgba(0,0,0,0.08)`
- Sombra colorida (premium): `0 10px 25px -5px {sombra_cor}`
- Background NUNCA branco puro (#FFFFFF) — usar o off-white da paleta
- Container max-width: 1200px, padding lateral: 24px mobile / 64px desktop
- Espaço entre seções: 96px desktop / 64px mobile (GENEROSO — sites premium respiram)

### Animações (Framer Motion ou Tailwind animate)
- Hover botões: scale 1.03 + sombra aumenta (transition 300ms ease)
- Hover cards: translate-y -4px + sombra cresce
- Scroll reveal: fade-in de baixo (20px) com Intersection Observer (stagger 100ms entre elementos)
- Contadores numéricos: animação de 0 até valor final (2s, ease-out)
- Transições de seção: suaves, sem saltos bruscos
- RESPEITAR prefers-reduced-motion
"""

REQUISITOS_TECNICOS = """
## REQUISITOS TÉCNICOS OBRIGATÓRIOS
- React + TypeScript + Vite
- Tailwind CSS + shadcn/ui components CUSTOMIZADOS com a paleta acima
- Mobile-first em todos os breakpoints (375px, 768px, 1024px, 1440px)
- Botão WhatsApp flutuante fixo canto inferior direito: círculo verde (#25D366), ícone branco, 56x56px, sombra `0 4px 12px rgba(37,211,102,0.3)`, hover scale 1.1
- SEO: meta title, description, og:image, schema markup LocalBusiness
- Performance: lazy loading imagens, fontes otimizadas, target LCP < 2.5s
- Favicon com cor primária da paleta
- Link WhatsApp: wa.me/55{telefone_limpo}?text=Olá! Vim pelo site e gostaria de mais informações.
- Navbar fixa com backdrop-blur (bg white/80% + backdrop-blur-md)
- SEPARADORES ENTRE SEÇÕES: usar SVG wave ou clip-path polygon — NUNCA linha reta
- Cada seção adjacente deve variar em pelo menos 2 de: background / layout / alinhamento / decoração
"""

templates = []

# ══════════════════════════════════════════════════════════════════════════════
# 1. RESTAURANTE / LANCHONETE / PIZZARIA
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Restaurante / Lanchonete / Pizzaria",
"restaurante,lanchonete,pizzaria,pizza,hamburguer,bar,comida,cozinha,churrascaria,sushi,japonês,italiano,self service,marmitaria,fast food,bistrô",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site gastronômico que desperte desejo e fome para **{nome}**, {categoria} em {cidade}. Não pode parecer template genérico — deve ter a personalidade de um restaurante real, com calor humano e apetite visual. O visitante precisa sentir o aroma saindo da tela.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #8B1A1A (vermelho vinho — apetite, tradição)
- Primária escura: #6B1010 (hover, footer)
- Secundária: #C9A84C (dourado — sofisticação, sabor premium)
- Background: #FFFBEB (creme quente — NÃO branco puro)
- Surface: #FFFFFF (cards)
- Texto: #1C1917 (quase-preto quente)
- Texto secundário: #78716C""",
    fonte_titulo="Playfair Display ou Cormorant Garamond (serif elegante — tradição e sofisticação)",
    fonte_corpo="DM Sans ou Inter",
    sombra_cor="rgba(139,26,26,0.15)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE (landing page, scroll contínuo)

### NAVBAR
Fixa, backdrop-blur, bg: rgba(28,25,23,0.9) com blur. Logo à esquerda. Links: Cardápio | Sobre | Avaliações | Contato. Botão CTA: "Reservar Mesa" (bg secundária #C9A84C, texto escuro). Mobile: hamburger com drawer.

### HERO — Layout "Dark Cinematic"
- Background: foto full-width do prato principal ou ambiente (placeholder com aspect-ratio 16/9)
- Overlay gradiente de baixo: `linear-gradient(to top, #1C1917 0%, transparent 60%)`
- Headline GIGANTE (64px desktop, 40px mobile, peso 800, serif, branco): "{nome}"
- Subheadline (22px, #C9A84C): "{categoria} • {cidade}"
- Badge flutuante: "⭐ {rating} no Google • {reviews_count} avaliações" (bg white/10%, backdrop-blur, border white/20%, radius pill)
- 2 CTAs lado a lado: "Reservar Mesa" (bg #C9A84C, texto escuro, peso 600) + "Ver Cardápio ↓" (ghost: border branco/30%, texto branco)
- Decorativo: círculo dourado sutil (#C9A84C/8%) de 300px atrás do headline, position absolute

### SEÇÃO: Números (bg: #1C1917, padding 48px, texto branco)
4 métricas em row (mobile: grid 2x2):
- "{rating}⭐" + "Nota no Google" | "{reviews_count}+" + "Avaliações" | "X+" + "Anos de Tradição" | "🍽️" + "Pratos no Cardápio"
- Números em 40px, peso 800, cor #C9A84C, animação counter
- Labels em 14px, branco/60%

### SVG wave separator (de #1C1917 para #FFFBEB)

### SEÇÃO: Especialidades (bg: #FFFBEB)
- Título (serif): "Nossas Especialidades"
- Subtítulo: "Os pratos que fazem nossos clientes voltar"
- Layout: Bento Grid — 1 card grande à esquerda (foto de prato com overlay, título sobre a foto), 4 cards menores à direita em grid 2x2
- Cada card: foto placeholder com radius 16px, nome do prato em peso 600, descrição curta em texto secundário
- Cards com hover: scale 1.03 + sombra colorida vermelha
- Botão abaixo: "Ver Cardápio Completo"

### SEÇÃO: Nossa História (bg: surface, layout split 40% foto / 60% texto)
- Foto do ambiente/equipe à esquerda (radius 24px, sombra)
- Título: "Nossa História"
- Texto: {descricao} (expandir com tom acolhedor)
- 4 ícones de diferenciais em grid: "🥩 Ingredientes Selecionados" + "👨‍🍳 Chef Premiado" + "🍷 Ambiente Aconchegante" + "⚡ Delivery Rápido"
- Cada diferencial: ícone com bg #8B1A1A/10%, radius 12px

### SEÇÃO: Avaliações (bg: #FFFBEB)
- Título: "O Que Nossos Clientes Dizem"
- Subtítulo: "⭐ {rating}/5 — {reviews_count} avaliações no Google"
- 3 cards de depoimento: borda top 3px #C9A84C, radius 16px, sombra sutil
- Cada card: ★★★★★ em #C9A84C, texto entre aspas, nome do cliente
- Reviews reais:
{reviews_texto}
- Botão: "Ver Todas no Google"

### SEÇÃO: Horário e Localização (bg: #1C1917, texto branco, padding 96px)
- Layout split: coluna esquerda (horário formatado bonito + telefone) / coluna direita (mapa embed ou imagem)
- Endereço: {endereco}, {cidade}
- Botão: "📍 Como Chegar" (bg #C9A84C)

### FOOTER (bg: #0F0E0D)
- Logo + descrição curta + redes sociais (Instagram, Facebook, iFood)
- Links: Cardápio | Sobre | Avaliações | Contato
- "© 2026 {nome}. Todos os direitos reservados."

""" + REQUISITOS_TECNICOS))

# ══════════════════════════════════════════════════════════════════════════════
# 2. BARBEARIA / SALÃO DE BELEZA
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Barbearia / Salão de Beleza",
"barbearia,salão,cabeleireiro,beleza,cabelo,barba,manicure,pedicure,estética,spa,nail,beauty,hair",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site com identidade visual marcante para **{nome}**, {categoria} em {cidade}. Se for barbearia: visual masculino, dark, premium. Se for salão feminino: elegante, sofisticado, rosé/dourado. O site deve converter em agendamentos pelo WhatsApp.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #1C1917 (preto quente — elegância, estilo)
- Primária escura: #0C0A09
- Secundária: #D4AF37 (dourado — premium, prestígio)
- Accent: #B45309 (cobre/bronze — masculinidade vintage)
- Background: #F5F0EB (bege vintage — NÃO branco puro)
- Surface: #FFFFFF
- Texto: #1C1917
- Texto secundário: #78716C
Nota: Se for salão FEMININO, trocar para: Primária #BE185D (rosa), Secundária #C9A84C (dourado rosé), Background #FDF2F8 (rosa claríssimo)""",
    fonte_titulo="Bebas Neue ou Oswald (bold impactante — atitude e estilo)",
    fonte_corpo="Inter ou DM Sans",
    sombra_cor="rgba(212,175,55,0.2)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### NAVBAR
Bg escuro (#1C1917) fixo com backdrop-blur. Logo à esquerda (tipografia bold). Links: Serviços | Equipe | Avaliações | Agendar. Botão CTA: "✂️ Agendar" (bg dourado #D4AF37, texto escuro).

### HERO — Layout "Dark Premium"
- Background: foto do barbeiro em ação / ambiente (placeholder escuro)
- Overlay: gradient de baixo (#0C0A09 80% → transparente)
- Headline (64px, all-caps, tracking wide, branco): "{nome}"
- Tagline (22px, #D4AF37, italic): "Seu estilo, nossa arte. Em {cidade}."
- Badge: "⭐ {rating} • {reviews_count} clientes satisfeitos" (glassmorphism: bg white/10%, backdrop-blur, border white/20%)
- CTA: "✂️ Agendar Horário" (bg #D4AF37, texto preto, peso 700, padding 16px 40px)
- Shapes decorativos: linhas diagonais sutis em dourado/5% no canto

### SEÇÃO: Serviços e Preços (bg: #F5F0EB, padding 96px)
- Título: "Nossos Serviços"
- Grid 3 colunas (mobile: 1 coluna) de cards premium:
  - Cada card: bg branco, radius 16px, borda top 3px #D4AF37, padding 32px
  - Ícone do serviço (Lucide React) em #D4AF37 com bg #D4AF37/10%, radius 12px
  - Nome: peso 700, 20px
  - Descrição: texto secundário, 2 linhas
  - Preço: "a partir de R$ XX" em #D4AF37, peso 700
- Serviços sugeridos: Corte Masculino, Barba, Combo Corte+Barba, Pigmentação, Hidratação, Tratamento Capilar
- Hover: translate-y -4px + sombra dourada
- CTA: "Agendar pelo WhatsApp"

### SEÇÃO: Equipe (bg: #1C1917, texto branco, padding 96px)
- Título: "Nossos Profissionais" (branco, 40px)
- Cards 3 colunas: foto circular (placeholder) com borda 3px #D4AF37, nome, especialidade
- Hover: borda cresce + glow dourado

### SVG wave separator (de #1C1917 para #F5F0EB)

### SEÇÃO: Antes e Depois (bg: #F5F0EB, padding 96px)
- Título: "Transformações"
- Grid de 3 pares antes/depois lado a lado
- Cada par: radius 16px, label "Antes" / "Depois" em badge escuro

### SEÇÃO: Avaliações (bg: surface, padding 96px)
- Título: "O Que Nossos Clientes Falam"
- Subtítulo: "⭐ {rating}/5 — {reviews_count} avaliações"
{reviews_texto}
- Cards com glassmorphism escuro se dark theme

### SEÇÃO: CTA Final (bg: gradiente #1C1917 → #0C0A09, padding 80px)
- "Agende Agora — É Rápido!" (branco, 40px)
- "Marque pelo WhatsApp e garanta seu horário" (branco/70%)
- Botão grande: bg #D4AF37, texto preto: "💬 Agendar pelo WhatsApp"
- Horário: {horario_formatado} (branco/60%)

### FOOTER
- Bg: #0C0A09, logo, links, redes, copyright

""" + REQUISITOS_TECNICOS))

# ══════════════════════════════════════════════════════════════════════════════
# 3. OFICINA MECÂNICA / AUTOMOTIVO
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Oficina Mecânica / Automotivo",
"oficina,mecânica,mecânico,auto,automóvel,carro,veículo,funilaria,pintura,elétrica automotiva,pneu,freio,suspensão,motor,troca de óleo",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site sólido e confiável para **{nome}**, {categoria} em {cidade}. O site deve transmitir competência técnica, agilidade e transparência. O cliente precisa sentir que pode confiar seu carro ali. Visual industrial moderno, direto ao ponto.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #1B2A4A (azul mecânico profundo — confiança técnica)
- Primária escura: #0F1A2E
- Secundária: #F59E0B (amber energético — atenção, urgência, ação)
- Background: #F1F5F9 (cinza-azulado claro)
- Surface: #FFFFFF
- Texto: #0F172A
- Texto secundário: #64748B""",
    fonte_titulo="Barlow ou Rajdhani (bold, industrial, legível — transmite força e competência)",
    fonte_corpo="Inter ou DM Sans",
    sombra_cor="rgba(27,42,74,0.15)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### HERO — Layout split 55/45
- Lado esquerdo: foto de mecânico trabalhando (placeholder, radius 24px, sombra azul)
- Lado direito:
  - Badge: "🔧 Oficina Especializada em {cidade}" (bg #F59E0B/10%, texto #F59E0B, pill)
  - Headline (56px): "Seu Carro em Boas Mãos — Sempre"
  - Subheadline: "{descricao}" ou "Manutenção preventiva e corretiva com diagnóstico preciso e preço justo"
  - ★★★★★ "{rating}/5 no Google"
  - CTA: "Agendar Serviço" (bg #F59E0B, texto escuro) + "Ligar Agora" (ghost)

### Barra de Números (bg: #1B2A4A, texto branco)
- "X+ Veículos Atendidos" | "X Anos" | "100% Garantia" | "⭐ {rating}"

### Serviços (bg: background) — Bento Grid
- 1 card destaque grande + 4 menores
- Serviços: Motor, Freios/Suspensão, Elétrica, Troca de Óleo, Injeção Eletrônica, Ar-condicionado
- Ícones Lucide em #F59E0B com bg amber/10%

### Como Funciona (bg: #1B2A4A, texto branco) — 4 Steps
① Contato → ② Diagnóstico → ③ Orçamento → ④ Serviço
Linha SVG conectora entre steps

### Avaliações
{reviews_texto}

### CTA Final (bg: gradiente #1B2A4A → #0F1A2E)
"Não Espere Seu Carro Parar — Agende Agora"

""" + REQUISITOS_TECNICOS))

# ══════════════════════════════════════════════════════════════════════════════
# 4. ELETRICISTA / INSTALAÇÕES
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Eletricista / Instalações",
"eletricista,elétrica,instalação elétrica,eletrotécnico,automação,ar condicionado,climatização,energia solar,painel elétrico,quadro de energia",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site profissional para **{nome}**, {categoria} em {cidade}. O eletricista precisa de um site que transmita segurança, certificação e competência técnica. O cliente precisa confiar que o serviço será feito com qualidade e normas de segurança.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #1B4965 (azul petróleo — confiança + segurança técnica)
- Primária escura: #0D2B3E
- Secundária: #F59E0B (amber — energia elétrica, atenção, ação)
- Background: #FAFAF8 (off-white quente)
- Surface: #FFFFFF
- Texto: #1A1A2E
- Texto secundário: #64748B""",
    fonte_titulo="Space Grotesk ou Outfit (moderna, técnica, confiável)",
    fonte_corpo="Inter",
    sombra_cor="rgba(27,73,101,0.15)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### HERO — Split 55/45 com badge de certificação
- Badge: "⚡ Eletricista Certificado em {cidade}" (bg amber/10%)
- Headline: "Segurança Elétrica Para Sua Casa e Empresa"
- Subheadline com menção a normas técnicas
- CTA: "Solicitar Orçamento" + "Emergência 24h" (se aplicável)
- Imagem de eletricista trabalhando com equipamento profissional

### Números: Projetos | Anos | Certificações | Nota Google

### Serviços — Grid 3x2 com ícones Lucide
Instalações residenciais, Instalações comerciais, Manutenção preventiva, Quadros elétricos, Automação, Energia solar (se aplicável)
Cada card com ícone ⚡ em amber e descrição real

### Como Funciona — 4 Steps com timeline
① Orçamento grátis → ② Visita técnica → ③ Aprovação → ④ Execução com garantia

### Avaliações
{reviews_texto}

### CTA Final (bg: gradiente primária)
"Precisa de um Eletricista? Fale Conosco Agora"
Botão WhatsApp + Telefone

""" + REQUISITOS_TECNICOS))

# ══════════════════════════════════════════════════════════════════════════════
# 5. CLÍNICA / SAÚDE
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Clínica / Consultório / Saúde",
"clínica,consultório,médico,medicina,dentista,odontologia,fisioterapia,psicólogo,nutricionista,dermatologista,oftalmologista,ortopedista,pediatra,ginecologista,cardiologista,saúde",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site acolhedor e profissional para **{nome}**, {categoria} em {cidade}. O paciente precisa sentir confiança e cuidado desde o primeiro contato visual. Visual limpo, sereno, que transmita competência médica sem ser frio.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #0891B2 (ciano calmante — saúde, serenidade, confiança médica)
- Primária escura: #0E7490
- Secundária: #6366F1 (indigo — competência, ciência)
- Background: #F0F9FF (azul claríssimo — NÃO branco puro)
- Surface: #FFFFFF
- Texto: #0C4A6E
- Texto secundário: #64748B""",
    fonte_titulo="Plus Jakarta Sans (moderna, amigável, profissional)",
    fonte_corpo="Inter",
    sombra_cor="rgba(8,145,178,0.12)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### HERO — Split acolhedor (50/50)
- Lado direito: foto do profissional sorrindo (placeholder, radius 24px)
- Lado esquerdo:
  - Badge: "🩺 {categoria} em {cidade}" (bg primária/10%)
  - Headline: "Cuidando da Sua Saúde com Carinho e Expertise"
  - Subheadline acolhedor
  - CTA: "Agendar Consulta" + "Falar no WhatsApp"
- Decorativo: blob orgânico ciano sutil atrás da imagem

### Especialidades — Grid de cards com ícones orgânicos
- Cards com radius 20px (friendly), sombra suave
- Ícone com bg primária/10%, hover com borda ciano

### Sobre o Profissional — Split texto + foto
- Bio resumida, formação, CRM/CRO, especializações
- Foto profissional com radius 24px

### Convênios Aceitos — Row de logos em grayscale, hover mostra cor

### Avaliações com destaque em cuidado e atendimento
{reviews_texto}

### CTA Final (bg: gradiente ciano)
"Agende Sua Consulta — Cuidar da Saúde é Prioridade"

""" + REQUISITOS_TECNICOS))

# ══════════════════════════════════════════════════════════════════════════════
# 6. ACADEMIA / FITNESS
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Academia / Personal Trainer / Pilates",
"academia,gym,fitness,personal,personal trainer,pilates,crossfit,musculação,yoga,funcional,treino,ginástica,spinning,natação",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site energético e motivacional para **{nome}**, {categoria} em {cidade}. O site deve transmitir energia, resultados e transformação. O visitante precisa sentir vontade de começar a treinar AGORA.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #DC2626 (vermelho energético — força, paixão, intensidade)
- Primária escura: #991B1B
- Secundária: #1E293B (slate escuro — seriedade, profissionalismo)
- Accent: #F59E0B (amber para destaques de resultado)
- Background: #0F172A (dark — energia, foco, contraste)
- Surface: #1E293B
- Texto: #F1F5F9 (branco-azulado)
- Texto secundário: #94A3B8""",
    fonte_titulo="Sora ou Outfit (geométrica, forte, moderna — transmite energia)",
    fonte_corpo="Inter",
    sombra_cor="rgba(220,38,38,0.2)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE (DARK MODE — todo o site em fundo escuro)

### HERO — Full-width cinematic
- Foto de pessoa treinando com overlay gradiente vermelho/escuro
- Headline IMPACTANTE (64px, all-caps): "TRANSFORME SEU CORPO. TRANSFORME SUA VIDA."
- Subheadline em amber: "{categoria} em {cidade}"
- CTA: "Começar Agora — Aula Experimental Grátis" (bg vermelho #DC2626)

### Números animados (bg: surface)
- "X+ Alunos" | "X Modalidades" | "X Anos" | "⭐ {rating} Google"

### Modalidades — Bento Grid escuro com fotos
- Cards com foto de fundo + overlay + texto branco
- Hover: overlay clareia + scale 1.03

### Resultados / Transformações — Antes e Depois
- Fotos lado a lado com slider

### Planos / Preços — 3 cards
- Card destaque (mais popular) com borda vermelha + scale 1.05

### Avaliações
{reviews_texto}

### CTA Final (bg: vermelho #DC2626)
"Sua Primeira Aula é Por Nossa Conta"

""" + REQUISITOS_TECNICOS))

# ══════════════════════════════════════════════════════════════════════════════
# 7. ADVOCACIA
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Advocacia / Escritório Jurídico",
"advocacia,advogado,escritório jurídico,direito,justiça,tribunal,processo,trabalhista,cível,criminal,família,empresarial,tributário,previdenciário",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site de autoridade e confiança para **{nome}**, {categoria} em {cidade}. O site deve transmitir expertise, seriedade e credibilidade. O cliente está em um momento delicado — ele precisa sentir que está nas mãos certas.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #1E3A5F (azul marinho — autoridade, tradição jurídica)
- Primária escura: #0F2440
- Secundária: #B8860B (dourado clássico — prestígio, excelência)
- Background: #FAF9F7 (off-white papiro — elegância discreta)
- Surface: #FFFFFF
- Texto: #1A1A2E
- Texto secundário: #6B7280""",
    fonte_titulo="Cormorant Garamond ou Libre Baskerville (serif clássica — tradição, autoridade)",
    fonte_corpo="Inter ou Source Sans Pro",
    sombra_cor="rgba(30,58,95,0.12)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### HERO — Clean e Autoritário (split 50/50)
- Lado esquerdo: headline + CTA
  - Badge: "⚖️ Escritório de Advocacia em {cidade}" (bg dourado/10%)
  - Headline (serif, 48px): "Seu Problema Jurídico Tem Solução"
  - Subheadline: "Atendimento humanizado com experiência e resultados comprovados"
  - CTA: "Consulta Inicial Gratuita" (bg #1E3A5F) + "Falar com Advogado" (ghost)
- Lado direito: foto do escritório ou do advogado (profissional, formal)
- Tom sóbrio, elegante, sem exagero visual

### Áreas de Atuação — Grid com ícones
- Cards com borda left 3px dourada
- Áreas: Trabalhista, Cível, Família, Empresarial, Criminal, Tributário (adaptar)

### Sobre / Equipe — Bio + foto + OAB + formação

### Processo de Atendimento — 4 Steps
① Contato → ② Análise do Caso → ③ Estratégia → ④ Acompanhamento

### Avaliações
{reviews_texto}

### CTA Final (bg: #1E3A5F)
"Consulta Inicial Gratuita — Fale Com Um Especialista"

""" + REQUISITOS_TECNICOS))

# ══════════════════════════════════════════════════════════════════════════════
# 8. CONSTRUÇÃO / REFORMA
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Construção / Reforma / Arquitetura",
"construção,reforma,construtora,empreiteira,arquitetura,engenharia,pedreiro,mestre de obras,pintor,gesso,drywall,piso,telhado,impermeabilização",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site sólido e profissional para **{nome}**, {categoria} em {cidade}. O site deve transmitir solidez, qualidade e capacidade de entregar projetos no prazo. O cliente precisa ver obras realizadas e sentir segurança.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #1E40AF (azul forte — confiança, solidez)
- Primária escura: #1E3A8A
- Secundária: #F59E0B (amber — atenção, construção, energia)
- Background: #F1F5F9 (cinza-azulado claro — industrial clean)
- Surface: #FFFFFF
- Texto: #0F172A
- Texto secundário: #64748B""",
    fonte_titulo="Barlow ou Outfit (sólida, moderna, profissional)",
    fonte_corpo="Inter",
    sombra_cor="rgba(30,64,175,0.12)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}  / **Tipo**: {categoria}  / **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}  / **Telefone**: {telefone}
- **Avaliação**: ⭐ {rating}/5 ({reviews_count} avaliações)  / **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### HERO — Split com foto de obra
- Headline: "Construímos Seu Sonho com Qualidade e Prazo"
- CTA: "Solicitar Orçamento"

### Números: Obras entregues | m² construídos | Anos | Nota Google

### Serviços — Bento Grid com fotos de obras
Construção, Reforma, Pintura, Acabamento, Projetos arquitetônicos

### Portfólio / Galeria — Grid de fotos de obras realizadas (antes/depois)

### Como Funciona — 4 Steps: Projeto → Orçamento → Execução → Entrega

### Avaliações
{reviews_texto}

### CTA Final: "Solicite Seu Orçamento Sem Compromisso"

""" + REQUISITOS_TECNICOS))

# ══════════════════════════════════════════════════════════════════════════════
# 9. PET SHOP / VETERINÁRIO
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Pet Shop / Clínica Veterinária",
"pet shop,petshop,veterinário,veterinária,animal,cachorro,gato,banho,tosa,ração,clínica animal",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site acolhedor e fofo para **{nome}**, {categoria} em {cidade}. Os tutores de pets são apaixonados — o site precisa transmitir amor, cuidado e competência. Visual alegre, amigável, com personalidade.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #7C3AED (violeta — carinhoso, lúdico, premium)
- Primária escura: #6D28D9
- Secundária: #F59E0B (amber — alegria, energia animal)
- Accent: #10B981 (esmeralda — saúde, natureza)
- Background: #FAF5FF (violeta claríssimo)
- Surface: #FFFFFF
- Texto: #1A1A2E
- Texto secundário: #6B7280""",
    fonte_titulo="Nunito ou Quicksand (arredondada, amigável — transmite carinho)",
    fonte_corpo="Nunito Sans ou DM Sans",
    sombra_cor="rgba(124,58,237,0.12)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}  / **Tipo**: {categoria}  / **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}  / **Telefone**: {telefone}
- **Avaliação**: ⭐ {rating}/5 ({reviews_count} avaliações)  / **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### HERO — Colorido e alegre
- Headline: "Amor e Cuidado Para Seu Melhor Amigo 🐾"
- Imagem de pets felizes (placeholder)
- CTA: "Agendar Banho & Tosa" + "Emergência Veterinária"
- Shapes decorativos: patinhas de pet em violeta/5%

### Serviços — Grid colorido com ícones fofos
Banho & Tosa, Consulta Veterinária, Vacinação, Petshop/Loja, Hotel Pet, Adestramento
Cards com border-radius 20px (friendly), hover com bounce sutil

### Galeria de Pets — Masonry grid de fotos de animais atendidos

### Avaliações
{reviews_texto}

### CTA Final (bg: gradiente violeta)
"Agende Agora — Seu Pet Merece o Melhor 🐾"

""" + REQUISITOS_TECNICOS))

# ══════════════════════════════════════════════════════════════════════════════
# 10. PADARIA / CONFEITARIA / CAFÉ
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Padaria / Confeitaria / Café",
"padaria,confeitaria,café,bakery,bolo,doce,pão,cafeteria,patisserie,brigadeiro,salgado,coxinha",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site aconchegante e apetitoso para **{nome}**, {categoria} em {cidade}. O visual deve evocar o cheiro de pão fresco e café coado. Quente, artesanal, com charme.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #92400E (marrom café — artesanal, tradição, aconchego)
- Primária escura: #713F12
- Secundária: #65A30D (verde fresco — natural, ingredientes frescos)
- Background: #FEFCE8 (off-white quente amarelado)
- Surface: #FFF7ED (laranja claríssimo)
- Texto: #1C1917
- Texto secundário: #78716C""",
    fonte_titulo="Playfair Display ou Lora (serif aconchegante — tradição e charme)",
    fonte_corpo="DM Sans ou Nunito Sans",
    sombra_cor="rgba(146,64,14,0.12)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}  / **Tipo**: {categoria}  / **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}  / **Telefone**: {telefone}
- **Avaliação**: ⭐ {rating}/5 ({reviews_count} avaliações)  / **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### HERO — Warm e artesanal
- Foto apetitosa de pães/doces com overlay quente
- Headline (serif): "{nome}"
- Tagline: "Feito com amor, todos os dias desde {cidade}"
- CTA: "Encomendas" + "Ver Cardápio"

### Destaques do Dia — Carrossel de produtos em destaque
### Cardápio — Tabs: Pães | Doces | Salgados | Bebidas
### Nossa História — Texto + fotos artesanais
### Avaliações
{reviews_texto}
### Encomendas CTA (bg: marrom) — "Faça Sua Encomenda Pelo WhatsApp"

""" + REQUISITOS_TECNICOS))

# ══════════════════════════════════════════════════════════════════════════════
# 11. IMOBILIÁRIA
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Imobiliária / Corretor de Imóveis",
"imobiliária,imóveis,corretor,venda,aluguel,apartamento,casa,terreno,comercial,loteamento,condomínio",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site premium para **{nome}**, {categoria} em {cidade}. Imóvel é a maior compra da vida — o site precisa transmitir confiança, solidez e facilidade de navegação. Visual moderno e limpo com foco em imóveis.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #1E40AF (azul forte — confiança, estabilidade financeira)
- Primária escura: #1E3A8A
- Secundária: #10B981 (esmeralda — crescimento, investimento inteligente)
- Background: #F8FAFC (slate claríssimo)
- Surface: #FFFFFF
- Texto: #0F172A
- Texto secundário: #64748B""",
    fonte_titulo="Outfit ou Plus Jakarta Sans (moderna, limpa — transmite credibilidade)",
    fonte_corpo="Inter",
    sombra_cor="rgba(30,64,175,0.12)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}  / **Tipo**: {categoria}  / **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}  / **Telefone**: {telefone}
- **Avaliação**: ⭐ {rating}/5 ({reviews_count} avaliações)  / **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### HERO — Busca em destaque
- Background: foto de imóvel bonito com overlay
- Headline: "Encontre o Imóvel dos Seus Sonhos em {cidade}"
- Campo de busca embutido: filtros Tipo/Bairro/Valor
- Ou CTA: "Ver Imóveis Disponíveis"

### Imóveis em Destaque — Grid de cards de imóveis
- Cada card: foto, bairro, preço, m², quartos

### Serviços — Compra | Venda | Aluguel | Avaliação
### Sobre a Imobiliária — equipe + anos de mercado + CRECI
### Avaliações
{reviews_texto}
### CTA: "Encontre Seu Imóvel — Fale com um Corretor"

""" + REQUISITOS_TECNICOS))

# ══════════════════════════════════════════════════════════════════════════════
# 12. ESCOLA / CURSO
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Escola / Curso / Ensino",
"escola,curso,ensino,educação,aula,professor,treinamento,capacitação,idioma,inglês,informática,reforço,vestibular,enem,concurso",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site acolhedor e educativo para **{nome}**, {categoria} em {cidade}. O site deve transmitir competência pedagógica, ambiente seguro e resultados comprovados. Pais e alunos precisam sentir confiança.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #7C3AED (violeta — criatividade, conhecimento, inspiração)
- Primária escura: #6D28D9
- Secundária: #F59E0B (amber — atenção, conquista, resultado)
- Background: #FAF5FF (violeta claríssimo)
- Surface: #FFFFFF
- Texto: #1A1A2E
- Texto secundário: #6B7280""",
    fonte_titulo="Sora ou Plus Jakarta Sans (moderna, amigável, educativa)",
    fonte_corpo="Inter ou Nunito Sans",
    sombra_cor="rgba(124,58,237,0.12)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}  / **Tipo**: {categoria}  / **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}  / **Telefone**: {telefone}
- **Avaliação**: ⭐ {rating}/5 ({reviews_count} avaliações)  / **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### HERO — Inspirador
- Headline: "Onde o Conhecimento Transforma Futuros"
- Foto de alunos/ambiente alegre
- CTA: "Matricule-se" + "Conheça Nossos Cursos"

### Cursos/Turmas — Grid de cards com ícone, nome, carga horária
### Diferenciais — Metodologia, professores, infraestrutura
### Resultados — Números de aprovações, depoimentos
### Avaliações
{reviews_texto}
### CTA: "Garanta Sua Vaga — Matrículas Abertas"

""" + REQUISITOS_TECNICOS))

# ══════════════════════════════════════════════════════════════════════════════
# 13. HOTEL / POUSADA
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Hotel / Pousada / Turismo",
"hotel,pousada,hospedagem,hostel,resort,turismo,viagem,reserva,quarto,suite,diária,airbnb,acomodação",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site convidativo e visual para **{nome}**, {categoria} em {cidade}. O hóspede precisa se imaginar já no local — o site deve ser uma vitrine visual que vende a experiência, não apenas o quarto.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #0D9488 (teal — natureza, relaxamento, escape)
- Primária escura: #0F766E
- Secundária: #F59E0B (amber — sol, praia, aventura)
- Background: #F0FDFA (verde-água claríssimo)
- Surface: #FFFFFF
- Texto: #134E4A
- Texto secundário: #5E8B87""",
    fonte_titulo="Playfair Display ou Lora (serif elegante — luxo e conforto)",
    fonte_corpo="DM Sans",
    sombra_cor="rgba(13,148,136,0.15)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}  / **Tipo**: {categoria}  / **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}  / **Telefone**: {telefone}
- **Avaliação**: ⭐ {rating}/5 ({reviews_count} avaliações)  / **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### HERO — Full-width visual impactante
- Foto panorâmica do local (piscina, vista, fachada)
- Overlay gradiente de baixo
- Headline (serif): "{nome}"
- Subheadline: "Sua experiência em {cidade} começa aqui"
- CTA: "Reservar Agora" + "Ver Acomodações"
- Badge: "⭐ {rating}/5 no Google"

### Acomodações — Cards grandes com foto, tipo, preço, comodidades
### Estrutura — Galeria de fotos: piscina, restaurante, área de lazer
### Localização — Mapa + atrações próximas
### Avaliações
{reviews_texto}
### CTA: "Reserve Direto e Economize — Melhor Preço Garantido"

""" + REQUISITOS_TECNICOS))

# ══════════════════════════════════════════════════════════════════════════════
# 14. CONTABILIDADE
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Contabilidade / Financeiro",
"contabilidade,contador,contábil,financeiro,fiscal,imposto,tributário,abertura de empresa,CNPJ,MEI,declaração,balanço,folha de pagamento",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site profissional e organizado para **{nome}**, {categoria} em {cidade}. Contabilidade exige confiança e organização — o site deve transmitir competência, precisão e facilitar o contato.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #334155 (slate profissional — seriedade, organização)
- Primária escura: #1E293B
- Secundária: #0D9488 (teal — modernidade, crescimento financeiro)
- Background: #F8FAFC (slate claríssimo)
- Surface: #FFFFFF
- Texto: #0F172A
- Texto secundário: #64748B""",
    fonte_titulo="Outfit ou Space Grotesk (moderna, limpa — organização e precisão)",
    fonte_corpo="Inter",
    sombra_cor="rgba(51,65,85,0.1)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}  / **Tipo**: {categoria}  / **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}  / **Telefone**: {telefone}
- **Avaliação**: ⭐ {rating}/5 ({reviews_count} avaliações)  / **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### HERO — Clean e confiável
- Headline: "Contabilidade Que Simplifica Sua Vida Empresarial"
- CTA: "Abrir Minha Empresa" + "Consulta Gratuita"

### Serviços — Grid organizado
Abertura de Empresa, Contabilidade Mensal, Fiscal/Tributário, Folha de Pagamento, Consultoria, Declarações

### Planos — 3 cards (MEI / Simples / Lucro Presumido)
### Números: Empresas atendidas | Anos | Impostos economizados
### Avaliações
{reviews_texto}
### CTA: "Simplifique Sua Contabilidade — Fale Conosco"

""" + REQUISITOS_TECNICOS))

# ══════════════════════════════════════════════════════════════════════════════
# 15. GENÉRICO (FALLBACK)
# ══════════════════════════════════════════════════════════════════════════════
templates.append(("Genérico / Serviços em Geral",
"",
"""# {nome} | {categoria} em {cidade}

## CONTEXTO DO PROJETO
Crie um site profissional e moderno para **{nome}**, {categoria} em {cidade}. Mesmo sem segmento específico, o site DEVE ter personalidade — nada de template genérico. Adaptar a identidade visual ao tipo de negócio com base no nome e categoria.

""" + DESIGN_SYSTEM_BASE.format(
    paleta="""- Primária: #2563EB (azul vivo — universal, confiança, profissionalismo)
- Primária escura: #1D4ED8
- Secundária: #10B981 (esmeralda — sucesso, crescimento)
- Background: #F8FAFC (slate claríssimo — NÃO branco puro)
- Surface: #FFFFFF
- Texto: #0F172A
- Texto secundário: #64748B
NOTA: Se a categoria sugerir outro mood (ex: restaurante → tons quentes, salão → dourado), adaptar a paleta de acordo.""",
    fonte_titulo="Plus Jakarta Sans ou Outfit (versátil, moderna, profissional)",
    fonte_corpo="Inter",
    sombra_cor="rgba(37,99,235,0.12)"
) + """

## DADOS REAIS DA EMPRESA
- **Nome**: {nome}
- **Tipo**: {categoria}
- **Descrição**: {descricao}
- **Endereço**: {endereco}, {cidade} — {estado}
- **Telefone / WhatsApp**: {telefone}
- **Avaliação Google**: ⭐ {rating}/5 ({reviews_count} avaliações)
- **Horário**: {horario_formatado}

## ESTRUTURA DO SITE

### HERO — Split 55/45 (universal, alta conversão)
- Badge: "⭐ {categoria} em {cidade}" (bg primária/10%)
- Headline (56px, peso 800): Benefício principal do serviço (NÃO o nome da empresa)
- Subheadline: {descricao} ou frase que explica o valor entregue
- Prova social: "★★★★★ {reviews_count} clientes satisfeitos"
- CTA primário: "Solicitar Orçamento" (bg primária)
- CTA secundário: "Saiba Mais ↓" (ghost)
- Imagem: placeholder representativo do negócio com radius 24px

### Números animados (counter)
- X+ Clientes | X Anos | 100% Garantia | ⭐ {rating}

### Serviços — Bento Grid (1 grande + 4 pequenos)
- Cada card com ícone Lucide + título + descrição curta
- Adaptar serviços ao tipo real do negócio

### Como Funciona — 4 Steps com timeline SVG
① Contato → ② Avaliação → ③ Proposta → ④ Execução

### Avaliações
{reviews_texto}

### FAQ — 5 perguntas accordion (adaptar ao negócio)

### CTA Final (bg: gradiente primária → primária escura)
- Chamada para ação + botão WhatsApp

### Footer — Logo + links + contato + redes + copyright

""" + REQUISITOS_TECNICOS))


# ══════════════════════════════════════════════════════════════════════════════
# EXECUTAR ATUALIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

def main():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # Buscar templates existentes
    existentes = conn.execute("SELECT id, nome FROM template_segmentos ORDER BY id").fetchall()
    print(f"\nTemplates no banco: {len(existentes)}")
    for e in existentes:
        print(f"  [{e['id']}] {e['nome']}")

    # Atualizar cada template
    atualizados = 0
    nao_encontrados = []

    for nome, keywords, prompt in templates:
        # Buscar pelo nome
        row = conn.execute("SELECT id FROM template_segmentos WHERE nome = ?", (nome,)).fetchone()
        if row:
            conn.execute(
                "UPDATE template_segmentos SET keywords=?, prompt_template=?, atualizado_em=datetime('now') WHERE id=?",
                (keywords, prompt, row['id'])
            )
            atualizados += 1
            print(f"  ✅ Atualizado: [{row['id']}] {nome}")
        else:
            # Template não existe — inserir
            conn.execute(
                "INSERT INTO template_segmentos (nome, keywords, prompt_template) VALUES (?,?,?)",
                (nome, keywords, prompt)
            )
            atualizados += 1
            print(f"  🆕 Inserido: {nome}")

    conn.commit()
    conn.close()
    print(f"\n{'='*50}")
    print(f"✅ {atualizados} templates atualizados com design profissional!")
    print(f"Reinicie o Flask (app.py) para ver as mudanças.")

if __name__ == '__main__':
    main()
