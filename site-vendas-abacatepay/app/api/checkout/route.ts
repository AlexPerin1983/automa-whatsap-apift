import { NextResponse } from "next/server";
import { createHostedCheckout } from "@/lib/abacatepay";
import { getPlanByKey } from "@/lib/site-config";

type CheckoutRequestBody = {
  plan?: string;
  customer?: {
    name?: string;
    email?: string;
    cellphone?: string;
    taxId?: string;
  };
};

function getBaseUrl() {
  return (
    process.env.NEXT_PUBLIC_SITE_URL ||
    (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "http://localhost:3000")
  );
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as CheckoutRequestBody;
    const plan = getPlanByKey(body.plan);
    if (!plan) {
      return NextResponse.json({ error: "Plano invalido." }, { status: 400 });
    }

    const apiVersion = (process.env.ABACATEPAY_API_VERSION || "v1").trim().toLowerCase();
    const productId = process.env[plan.productEnv];
    if (apiVersion === "v2" && !productId) {
      return NextResponse.json(
        { error: `Produto do plano ${plan.key} nao configurado no ambiente.` },
        { status: 500 }
      );
    }
    if (apiVersion === "v1" && !body.customer?.taxId?.trim()) {
      return NextResponse.json(
        { error: "CPF ou CNPJ e obrigatorio para gerar checkout na API v1 da AbacatePay." },
        { status: 400 }
      );
    }

    const baseUrl = getBaseUrl();
    const emailBase = body.customer?.email?.trim() || "lead@placeholder.local";
    const externalId = `site-${plan.key}-${Date.now()}`;

    const checkout = await createHostedCheckout({
      productId,
      productName: plan.title,
      productDescription: `Pagamento de ${plan.title} - ${plan.delivery}`,
      amountCents: plan.priceCents,
      externalId,
      completionUrl: `${baseUrl}/obrigado?checkout=${externalId}`,
      returnUrl: `${baseUrl}/#checkout`,
      customer: {
        name: body.customer?.name?.trim(),
        email: emailBase,
        cellphone: body.customer?.cellphone?.trim(),
        taxId: body.customer?.taxId?.trim()
      },
      metadata: {
        source: "site-vendas-abacatepay",
        plan: plan.key
      }
    });

    return NextResponse.json({
      checkoutId: checkout.id,
      checkoutUrl: checkout.url
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Falha ao criar checkout." },
      { status: 500 }
    );
  }
}
