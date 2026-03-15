const ABACATEPAY_API_BASE = "https://api.abacatepay.com/v2";
const ABACATEPAY_API_V1_BASE = "https://api.abacatepay.com/v1";

type CreateCheckoutInput = {
  productId?: string;
  productName: string;
  productDescription: string;
  amountCents: number;
  customer?: {
    name?: string;
    email?: string;
    cellphone?: string;
    taxId?: string;
  };
  externalId: string;
  completionUrl: string;
  returnUrl: string;
  metadata?: Record<string, string>;
};

function getApiKey() {
  const key = process.env.ABACATEPAY_API_KEY;
  if (!key) throw new Error("ABACATEPAY_API_KEY nao configurada.");
  return key;
}

function getApiVersion() {
  return (process.env.ABACATEPAY_API_VERSION || "v1").trim().toLowerCase();
}

export async function createHostedCheckout(input: CreateCheckoutInput) {
  const apiVersion = getApiVersion();

  const response = await fetch(
    apiVersion === "v2"
      ? `${ABACATEPAY_API_BASE}/checkouts/create`
      : `${ABACATEPAY_API_V1_BASE}/billing/create`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${getApiKey()}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(
        apiVersion === "v2"
          ? {
              items: [{ id: input.productId, quantity: 1 }],
              methods: ["PIX", "CARD"],
              completionUrl: input.completionUrl,
              returnUrl: input.returnUrl,
              externalId: input.externalId,
              metadata: input.metadata ?? {},
              customer: input.customer
            }
          : {
              frequency: "ONE_TIME",
              methods: ["PIX", "CARD"],
              products: [
                {
                  externalId: input.externalId,
                  name: input.productName,
                  description: input.productDescription,
                  quantity: 1,
                  price: input.amountCents
                }
              ],
              returnUrl: input.returnUrl,
              completionUrl: input.completionUrl,
              externalId: input.externalId,
              metadata: input.metadata ?? {},
              customer: {
                name: input.customer?.name,
                email: input.customer?.email,
                cellphone: input.customer?.cellphone,
                taxId: input.customer?.taxId
              }
            }
      )
    }
  );

  const payload = await response.json();
  if (!response.ok || !payload?.success || !payload?.data?.url) {
    throw new Error(payload?.error || "Falha ao criar checkout na AbacatePay.");
  }
  return payload.data;
}

export function getWebhookSecret() {
  return process.env.ABACATEPAY_WEBHOOK_SECRET?.trim() || "";
}

export function verifyWebhookSecret(secret: string | null) {
  const expected = getWebhookSecret();
  if (!expected) return true;
  return secret === expected;
}
