"use client";

import { useEffect, useMemo, useState } from "react";
import type { PlanKey } from "@/lib/site-config";
import { sitePlans } from "@/lib/site-config";

type CheckoutState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string };

export function CheckoutForm() {
  const [selectedPlan, setSelectedPlan] = useState<PlanKey>("pro");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [cellphone, setCellphone] = useState("");
  const [taxId, setTaxId] = useState("");
  const [state, setState] = useState<CheckoutState>({ status: "idle" });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const planParam = params.get("plan");
    if (planParam === "start" || planParam === "pro" || planParam === "premium") {
      setSelectedPlan(planParam);
    }
  }, []);

  const activePlan = useMemo(
    () => sitePlans.find((plan) => plan.key === selectedPlan) ?? sitePlans[2],
    [selectedPlan]
  );

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState({ status: "loading" });

    try {
      const response = await fetch("/api/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan: selectedPlan,
          customer: {
            name,
            email,
            cellphone,
            taxId
          }
        })
      });

      const payload = await response.json();
      if (!response.ok || !payload?.checkoutUrl) {
        throw new Error(payload?.error || "Nao foi possivel iniciar o checkout.");
      }

      window.location.href = payload.checkoutUrl;
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Falha inesperada ao iniciar o pagamento."
      });
    }
  }

  return (
    <div className="checkout-shell">
      <div className="checkout-copy">
        <span className="eyebrow">Tire a empresa do improviso</span>
        <h2>Escolha o pacote ideal para o negocio ganhar identidade propria e passar mais confianca no Google.</h2>
        <p>
          Esta entrega foi desenhada para empresas locais que hoje aparecem sem um site profissional,
          dependem demais do WhatsApp e acabam perdendo credibilidade na hora da comparacao.
        </p>
        <div className="checkout-benefits">
          <span>Mais autoridade para quem pesquisa no Google</span>
          <span>Mais clareza para explicar servicos e diferenciais</span>
          <span>Mais seguranca no pagamento com PIX e cartao</span>
        </div>
        <div className="active-plan-card">
          <strong>{activePlan.title}</strong>
          <span>
            {activePlan.originalPriceLabel ? (
              <>
                <small className="price-strike">{activePlan.originalPriceLabel}</small> {activePlan.priceLabel}
              </>
            ) : (
              activePlan.priceLabel
            )}
          </span>
          <small>{activePlan.delivery}</small>
        </div>
      </div>

      <form className="checkout-panel" onSubmit={handleSubmit}>
        <label>
          Pacote
          <select value={selectedPlan} onChange={(e) => setSelectedPlan(e.target.value as PlanKey)}>
            {sitePlans.map((plan) => (
              <option key={plan.key} value={plan.key}>
                {plan.title} - {plan.priceLabel}
              </option>
            ))}
          </select>
        </label>

        <label>
          Nome do cliente
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ex: Maria da Silva"
          />
        </label>

        <label>
          E-mail
          <input
            required
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="cliente@empresa.com"
          />
        </label>

        <label>
          WhatsApp
          <input
            value={cellphone}
            onChange={(e) => setCellphone(e.target.value)}
            placeholder="(83) 99999-9999"
          />
        </label>

        <label>
          CPF ou CNPJ
          <input
            required
            value={taxId}
            onChange={(e) => setTaxId(e.target.value)}
            placeholder="Ex: 11144477735"
          />
        </label>

        <button type="submit" disabled={state.status === "loading"}>
          {state.status === "loading" ? "Gerando checkout..." : "Pagar com PIX ou cartao"}
        </button>

        <p className="checkout-note">
          O pagamento acontece em ambiente hospedado da AbacatePay. Depois da confirmacao, o cliente
          retorna para a pagina de sucesso, mantendo um fluxo comercial mais profissional do inicio ao fim.
        </p>

        {state.status === "error" ? <div className="error-box">{state.message}</div> : null}
      </form>
    </div>
  );
}
