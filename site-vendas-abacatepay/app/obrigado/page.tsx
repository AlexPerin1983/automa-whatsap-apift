export default function ObrigadoPage() {
  return (
    <main className="success-shell">
      <div className="success-card">
        <span className="eyebrow">Pagamento iniciado</span>
        <h1>Pedido recebido.</h1>
        <p>
          Se o pagamento ja foi confirmado, agora voce pode seguir com o atendimento e o onboarding.
          Se ainda estiver pendente, acompanhe pelo recibo ou pelo painel da AbacatePay.
        </p>
        <a href="/" className="primary-link">Voltar para a oferta</a>
      </div>
    </main>
  );
}
