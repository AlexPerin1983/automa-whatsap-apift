import { CheckoutForm } from "@/components/checkout-form";
import { PromoCountdown } from "@/components/promo-countdown";
import { sitePlans } from "@/lib/site-config";

const painPoints = [
  "A empresa aparece no Google, mas passa imagem amadora sem um site proprio",
  "O cliente pesquisa, compara e nao encontra uma apresentacao clara da empresa",
  "Instagram e WhatsApp sozinhos nao sustentam autoridade quando o lead quer confiar",
  "Sem pagina profissional, a empresa perde orcamentos para concorrentes que parecem maiores"
];

const conversionBlocks = [
  {
    title: "Seu perfil no Google nao fecha a venda sozinho",
    description:
      "O perfil ajuda a ser encontrado, mas o site e o lugar onde a empresa explica servicos, prova autoridade e conduz a decisao."
  },
  {
    title: "Sem site, o negocio parece improvisado",
    description:
      "Quando o cliente clica e nao encontra uma identidade propria, a confianca cai e a comparacao de preco vira o centro da conversa."
  },
  {
    title: "Com um site certo, o lead chega mais quente",
    description:
      "A empresa passa credibilidade, organiza a oferta e recebe contatos mais prontos para pedir orcamento ou fechar."
  }
];

const deliverySteps = [
  {
    title: "Mapeamos a imagem atual do negocio",
    description:
      "Entendemos o que a empresa vende, como ela aparece hoje no Google e qual impressao precisa transmitir."
  },
  {
    title: "Criamos uma landing local com cara de empresa seria",
    description:
      "Organizamos headline, servicos, provas, CTA e identidade visual para transformar busca em contato."
  },
  {
    title: "Entregamos o link pronto para vender",
    description:
      "A empresa passa a ter um endereco profissional para divulgar no Google, no WhatsApp, no Instagram e nas campanhas."
  }
];

const faqs = [
  {
    question: "Se a empresa ja tem perfil no Google, ainda precisa de site?",
    answer:
      "Sim. O perfil ajuda a aparecer. O site ajuda a convencer. Sem ele, a empresa depende de poucas linhas, fotos soltas e conversas manuais para tentar gerar confianca."
  },
  {
    question: "Isso funciona para negocios pequenos de bairro?",
    answer:
      "Funciona muito bem. Quem procura servico local quer bater o olho e sentir seguranca. Um site bem posicionado faz a empresa parecer mais organizada e mais confiavel."
  },
  {
    question: "O que muda na pratica quando a empresa ganha um site?",
    answer:
      "Ela passa a ter uma identidade propria, mostra servicos com clareza, centraliza os canais de contato e melhora a percepcao de valor antes do atendimento."
  },
  {
    question: "Em quanto tempo a pagina pode estar pronta?",
    answer:
      "Depende do pacote escolhido. A proposta desta landing e justamente colocar uma pagina profissional no ar rapido para o negocio parar de perder oportunidade."
  }
];

export default function HomePage() {
  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">Sites para empresas locais sem identidade profissional no Google</span>
          <h1>Se a sua empresa aparece no Google mas nao tem site, ela esta perdendo confianca e clientes.</h1>
          <p className="hero-lead">
            O cliente pesquisa o nome da empresa, encontra telefone, mapa e talvez um Instagram. Mas
            nao encontra uma apresentacao profissional que mostre servicos, diferenciais e autoridade.
            E nessa lacuna o concorrente leva a venda.
          </p>
          <PromoCountdown />
          <div className="hero-actions">
            <a href="/?plan=pro#checkout" className="primary-link">
              Quero um site que gere confianca
            </a>
            <a href="#oferta" className="secondary-link">
              Ver planos para entrar no ar rapido
            </a>
          </div>
          <div className="hero-microproof">
            <span>Mais credibilidade</span>
            <span>Mais contatos qualificados</span>
            <span>Mais presenca no Google</span>
          </div>
        </div>

        <div className="hero-stage">
          <div className="stage-panel">
            <div className="stage-header">
              <span className="stage-kicker">Diagnostico real de empresa local</span>
              <strong>Sem site, o negocio parece menor do que realmente e</strong>
              <p>
                O problema nao e so estetica. E reputacao, autoridade e conversao. O cliente quer
                validar rapido se esta falando com uma empresa seria.
              </p>
            </div>

            <div className="stage-price-card">
              <div>
                <small>Oferta de entrada para sair do improviso</small>
                <div className="stage-price">
                  <span className="price-strike">De R$ 497</span> R$ 99
                </div>
              </div>
              <span className="stage-chip">Condicao comercial ativa</span>
            </div>

            <div className="stage-metrics">
              <div>
                <strong>Google</strong>
                <span>mais respaldo para a busca</span>
              </div>
              <div>
                <strong>WhatsApp</strong>
                <span>menos atrito no atendimento</span>
              </div>
              <div>
                <strong>Marca</strong>
                <span>mais autoridade local</span>
              </div>
            </div>

            <div className="hero-proof">
              {painPoints.map((item) => (
                <div key={item} className="proof-card">
                  <strong>{item}</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="section-shell section-surface">
        <div className="section-head">
          <span className="eyebrow">Oportunidade escondida</span>
          <h2>Empresas locais perdem venda todos os dias porque sao encontradas, mas nao sao levadas a serio.</h2>
          <p>
            O site nao entra so como vitrine. Ele entra como prova de existencia, organizacao e
            profissionalismo para quem acabou de encontrar a empresa no Google.
          </p>
        </div>
        <div className="trust-grid">
          {conversionBlocks.map((item) => (
            <div key={item.title} className="trust-card">
              <strong>{item.title}</strong>
              <p>{item.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section-shell dark-band">
        <div className="section-head">
          <span className="eyebrow">O que o site resolve</span>
          <h2>Ele tira a empresa do modo improviso e coloca o negocio no modo confianca.</h2>
        </div>
        <div className="steps-grid">
          <div>
            <span className="step-index">01</span>
            <strong>Organiza a oferta</strong>
            <p>Mostra servicos, diferenciais, regioes atendidas e chamadas para contato sem depender de conversa longa.</p>
          </div>
          <div>
            <span className="step-index">02</span>
            <strong>Sustenta autoridade</strong>
            <p>Quando o cliente pesquisa a empresa, ele encontra um endereco proprio e uma identidade mais forte.</p>
          </div>
          <div>
            <span className="step-index">03</span>
            <strong>Aumenta a chance de contato</strong>
            <p>O lead entende melhor o servico e chega mais convencido para falar no WhatsApp ou pedir orcamento.</p>
          </div>
        </div>
      </section>

      <section className="section-shell" id="oferta">
        <div className="section-head">
          <span className="eyebrow">Planos</span>
          <h2>Escolha o nivel ideal para a empresa parar de parecer invisivel ou improvisada no Google.</h2>
          <p>
            Criamos desde uma entrada rapida para o negocio ganhar cara profissional, ate uma entrega
            mais completa para empresas que querem parecer maiores e vender melhor.
          </p>
        </div>
        <div className="plan-grid">
          {sitePlans.map((plan) => (
            <article key={plan.key} className={`plan-card${plan.featured ? " featured-plan" : ""}`}>
              <div className="plan-topline">
                <span className="plan-badge">{plan.badge}</span>
                {plan.urgencyLabel ? <span className="plan-urgency">{plan.urgencyLabel}</span> : null}
              </div>
              <h3>{plan.title}</h3>
              <p className="plan-subtitle">{plan.subtitle}</p>
              <div className="plan-price">{plan.priceLabel}</div>
              {plan.originalPriceLabel ? (
                <div className="plan-original-price">{plan.originalPriceLabel}</div>
              ) : null}
              <p>{plan.delivery}</p>
              <ul>
                {plan.bullets.map((bullet) => (
                  <li key={bullet}>{bullet}</li>
                ))}
              </ul>
              <a
                href={`/?plan=${plan.key}#checkout`}
                className={plan.featured ? "primary-link plan-link" : "secondary-link plan-link"}
              >
                Escolher {plan.title}
              </a>
            </article>
          ))}
        </div>
      </section>

      <section className="section-shell split-band">
        <div className="section-head compact-head">
          <span className="eyebrow">Como entregamos</span>
          <h2>Uma landing local feita para a empresa ser encontrada, validada e chamada.</h2>
          <p>
            Nao e um site solto. E uma pagina pensada para a realidade de negocios locais que hoje
            dependem de perfil do Google, Instagram ou boca a boca para vender.
          </p>
        </div>
        <div className="guarantee-card">
          {deliverySteps.map((step, index) => (
            <div key={step.title} className="agent-mini-block">
              <span className="step-index">0{index + 1}</span>
              <strong>{step.title}</strong>
              <p>{step.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section-shell" id="checkout">
        <CheckoutForm />
      </section>

      <section className="section-shell faq-shell">
        <div className="section-head">
          <span className="eyebrow">FAQ</span>
          <h2>Perguntas de quem sabe que precisa parecer mais profissional no Google.</h2>
        </div>
        <div className="faq-grid faq-grid-2">
          {faqs.map((item) => (
            <div key={item.question}>
              <strong>{item.question}</strong>
              <p>{item.answer}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
