export type PlanKey = "start" | "pro" | "premium";

export type SitePlan = {
  key: PlanKey;
  badge: string;
  title: string;
  subtitle: string;
  priceLabel: string;
  originalPriceLabel?: string;
  priceCents: number;
  delivery: string;
  productEnv: string;
  bullets: string[];
  featured?: boolean;
  urgencyLabel?: string;
};

export const sitePlans: SitePlan[] = [
  {
    key: "start",
    badge: "Entrada local",
    title: "Site Essencial",
    subtitle: "Para a empresa que precisa parar de parecer improvisada e entrar no ar rapido.",
    priceLabel: "R$ 99",
    priceCents: 9900,
    delivery: "Entrega em ate 3 dias uteis",
    productEnv: "CHECKOUT_PRODUCT_ID_START",
    bullets: [
      "Landing page profissional para apresentar o negocio",
      "Sessao de servicos, regiao atendida e CTA para WhatsApp",
      "Layout responsivo para celular e computador",
      "Link proprio para divulgar no Google e nas redes"
    ]
  },
  {
    key: "pro",
    badge: "Mais indicado",
    title: "Site Autoridade Local",
    subtitle: "A oferta ideal para a empresa que quer ganhar presenca profissional e passar mais confianca.",
    priceLabel: "R$ 99",
    originalPriceLabel: "De R$ 497",
    priceCents: 9900,
    delivery: "Entrega em ate 5 dias uteis",
    productEnv: "CHECKOUT_PRODUCT_ID_PRO",
    featured: true,
    urgencyLabel: "Condicao de entrada",
    bullets: [
      "Copy agressiva para converter quem chegou do Google",
      "Visual premium para empresa local parecer mais estruturada",
      "Blocos de confianca, diferenciais e CTA forte",
      "Melhor custo-beneficio para sair do improviso rapido"
    ]
  },
  {
    key: "premium",
    badge: "Escala comercial",
    title: "Site Dominio Regional",
    subtitle: "Para empresas que querem parecer maiores, vender melhor e sustentar campanhas com mais forca.",
    priceLabel: "R$ 1.497",
    priceCents: 149900,
    delivery: "Entrega em ate 10 dias uteis",
    productEnv: "CHECKOUT_PRODUCT_ID_PREMIUM",
    bullets: [
      "Estrutura mais completa com secoes comerciais estrategicas",
      "Design premium, blocos personalizados e narrativa de autoridade",
      "FAQ, provas, argumentos de conversao e CTA em varios pontos",
      "Ajustes finos apos a primeira entrega"
    ]
  }
];

export function getPlanByKey(key: string | undefined) {
  return sitePlans.find((plan) => plan.key === key);
}
