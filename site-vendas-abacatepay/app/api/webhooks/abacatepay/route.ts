import { NextResponse } from "next/server";
import { getWebhookSecret, verifyWebhookSecret } from "@/lib/abacatepay";

export async function POST(request: Request) {
  const { searchParams } = new URL(request.url);
  const secret = searchParams.get("secret");
  const rawBody = await request.text();

  if (!verifyWebhookSecret(secret)) {
    return NextResponse.json({ ok: false, error: "Webhook secret invalido." }, { status: 401 });
  }

  let payload: unknown = null;
  try {
    payload = JSON.parse(rawBody);
  } catch {
    return NextResponse.json({ ok: false, error: "Payload invalido." }, { status: 400 });
  }

  // Neste ponto voce pode salvar em um banco, notificar WhatsApp ou disparar automacoes.
  if (!getWebhookSecret()) {
    console.warn("[abacatepay:webhook] recebido sem secret configurado. Use apenas em ambiente de teste.");
  }
  console.log("[abacatepay:webhook]", JSON.stringify(payload));

  return NextResponse.json({ ok: true });
}
