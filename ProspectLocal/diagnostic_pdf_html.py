import base64
import io
import json
import os
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from jinja2 import Environment, FileSystemLoader, select_autoescape


BROWSER_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def _truncate(text, limit):
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit - 3].rstrip()}..."


def _score_color(score):
    if score >= 70:
        return "good"
    if score >= 40:
        return "warn"
    return "bad"


def _score_label(score):
    if score >= 70:
        return "Bom"
    if score >= 40:
        return "Regular"
    return "Critico"


def _score_phrase(score):
    if score >= 75:
        return "A empresa ja tem uma base digital consistente e pode focar em conversao."
    if score >= 55:
        return "Existe uma base relevante, mas ainda ha ajustes claros para captar mais contatos."
    if score >= 35:
        return "A presenca atual funciona, porem ainda esta abaixo do potencial comercial do negocio."
    return "A presenca digital esta fragil e ha espaco imediato para elevar confianca e visibilidade."


def _normalize_url(url):
    url = str(url or "").strip()
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    return f"https://{url}"


def _safe_json_loads(value, default):
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _extract_named_items(items, limit=6):
    out = []
    for item in items or []:
        value = ""
        if isinstance(item, str):
            value = item.strip()
        elif isinstance(item, dict):
            value = str(
                item.get("title")
                or item.get("name")
                or item.get("label")
                or item.get("value")
                or ""
            ).strip()
        if value and value not in out:
            out.append(value)
        if len(out) >= limit:
            break
    return out


def _flatten_additional_info(additional_info, limit=8):
    labels = []
    groups = []
    if isinstance(additional_info, dict):
        for group_name, group_items in additional_info.items():
            if group_name:
                groups.append(str(group_name).strip())
            if isinstance(group_items, list):
                for entry in group_items:
                    if isinstance(entry, dict):
                        for key, value in entry.items():
                            truthy = value not in (False, None, "", [], {})
                            if truthy and key and key not in labels:
                                labels.append(str(key).strip())
                    elif isinstance(entry, str) and entry.strip() and entry.strip() not in labels:
                        labels.append(entry.strip())
            elif isinstance(group_items, dict):
                for key, value in group_items.items():
                    truthy = value not in (False, None, "", [], {})
                    if truthy and key and key not in labels:
                        labels.append(str(key).strip())
        return groups[:4], labels[:limit]
    return [], []


def _find_browser():
    for name in ("chrome", "msedge"):
        resolved = shutil.which(name)
        if resolved:
            return resolved
    for candidate in BROWSER_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    raise RuntimeError("Nao foi possivel localizar Chrome ou Edge para gerar o PDF.")


def _file_to_data_uri(path):
    if not path or not os.path.exists(path):
        return ""
    ext = Path(path).suffix.lower().lstrip(".") or "png"
    mime = "image/png" if ext == "png" else f"image/{ext}"
    encoded = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _build_view_model(data):
    nome = str(data.get("nome") or "Empresa")
    categoria = str(data.get("categoria") or "Categoria nao informada")
    telefone = str(data.get("telefone") or "Nao informado")
    endereco = str(data.get("endereco") or "Endereco nao informado")
    cidade = str(data.get("cidade") or "Cidade nao informada")
    tem_web = bool(data.get("tem_website"))
    website_url = str(data.get("website_url") or "").strip()
    website_link = _normalize_url(website_url)
    avaliacao = float(data.get("avaliacao") or 0)
    total_avaliacoes = int(data.get("total_avaliacoes") or 0)
    total_fotos = int(data.get("total_fotos") or 0)
    dist = {}
    for k, v in (data.get("distribuicao_estrelas", {}) or {}).items():
        try:
            dist[int(k)] = int(v)
        except Exception:
            continue

    sc_pres = min(
        100,
        (40 if tem_web else 0)
        + round(min(total_fotos / 20.0, 1) * 30)
        + (10 if categoria != "Categoria nao informada" else 0)
        + (10 if endereco != "Endereco nao informado" else 0)
        + (5 if telefone != "Nao informado" else 0),
    )
    sc_rep = min(
        100,
        (round((avaliacao / 5.0) * 60) if avaliacao > 0 else 0)
        + round(min(total_avaliacoes / 100.0, 1) * 40),
    )
    sc_eng = min(
        100,
        round(min(total_fotos / 30.0, 1) * 50) + round(min(total_avaliacoes / 50.0, 1) * 50),
    )
    sc_total = round(sc_pres * 0.40 + sc_rep * 0.35 + sc_eng * 0.25)
    pot_pres = min(100, sc_pres + (40 if not tem_web else 0) + (15 if total_fotos < 20 else 0))
    pot_rep = min(100, sc_rep + (10 if avaliacao < 4.5 else 0) + (15 if total_avaliacoes < 50 else 0))
    pot_eng = min(100, sc_eng + (20 if total_fotos < 30 else 0) + (15 if total_avaliacoes < 50 else 0))
    potential_total = round(pot_pres * 0.40 + pot_rep * 0.35 + pot_eng * 0.25)
    score_gain = max(0, potential_total - sc_total)

    recs = []
    if not tem_web:
        recs.append(
            {
                "priority": "Alta",
                "title": "Criar um site profissional",
                "body": "Sem um site proprio, a empresa perde autoridade e deixa escapar clientes que pesquisam antes de contratar.",
            }
        )
    if total_fotos < 5:
        recs.append(
            {
                "priority": "Alta",
                "title": f"Ampliar a galeria do perfil ({total_fotos} fotos)",
                "body": "Mais fotos aumentam cliques, melhoram percepcao de qualidade e ajudam o cliente a confiar mais rapido.",
            }
        )
    elif total_fotos < 15:
        recs.append(
            {
                "priority": "Media",
                "title": f"Reforcar o acervo visual ({total_fotos} fotos)",
                "body": "Chegar a 20+ fotos deixa o perfil mais competitivo e mais persuasivo na busca local.",
            }
        )
    if avaliacao > 0 and avaliacao < 4.0:
        recs.append(
            {
                "priority": "Alta",
                "title": f"Elevar a nota media ({avaliacao:.1f})",
                "body": "Uma reputacao abaixo de 4 estrelas reduz conversao e cria inseguranca logo no primeiro contato.",
            }
        )
    if total_avaliacoes < 10:
        recs.append(
            {
                "priority": "Media",
                "title": f"Gerar mais avaliacoes ({total_avaliacoes})",
                "body": "Aumentar a prova social melhora a posicao no Google e fortalece a decisao de compra.",
            }
        )
    elif total_avaliacoes < 30:
        recs.append(
            {
                "priority": "Baixa",
                "title": f"Estruturar rotina de avaliacoes ({total_avaliacoes})",
                "body": "A empresa ja tem base, mas pode crescer mais rapido com um processo simples de pedido de feedback.",
            }
        )
    neg = dist.get(1, 0) + dist.get(2, 0)
    if neg >= 3 and total_avaliacoes > 0 and (neg / total_avaliacoes) > 0.15:
        recs.append(
            {
                "priority": "Alta",
                "title": f"Responder feedbacks negativos ({neg})",
                "body": "Responder comentarios publicamente transmite seriedade e ajuda a reduzir desgaste de reputacao.",
            }
        )
    if not recs:
        recs.append(
            {
                "priority": "Baixa",
                "title": "Consolidar a operacao digital",
                "body": "O perfil esta em bom nivel. O proximo passo e escalar reputacao, visibilidade e conversao de forma previsivel.",
            }
        )

    gaps = []
    if not tem_web:
        gaps.append("ausencia de site profissional")
    if total_fotos < 20:
        gaps.append("acervo visual abaixo do ideal")
    if total_avaliacoes < 30:
        gaps.append("volume de avaliacoes ainda baixo")
    if avaliacao and avaliacao < 4.5:
        gaps.append("nota de reputacao abaixo do ideal")
    main_gap = gaps[0] if gaps else "conversao e recorrencia comercial"

    strengths = []
    if tem_web:
        strengths.append("Ja existe um ponto proprio de conversao para receber demanda.")
    if avaliacao >= 4.5 and total_avaliacoes >= 10:
        strengths.append("A reputacao local passa confianca logo no primeiro contato.")
    if total_fotos >= 20:
        strengths.append("O volume de fotos ajuda a valorizar a percepcao do negocio.")
    if total_avaliacoes >= 30:
        strengths.append("A prova social ja comeca a reduzir objecoes comerciais.")
    if not strengths:
        strengths.append("Existe um bom espaco para evoluir rapido com ajustes simples.")
    if len(strengths) == 1:
        strengths.append("O perfil atual ja oferece sinais suficientes para construir uma apresentacao melhor.")

    opportunities = []
    if not tem_web:
        opportunities.append("Criar um site ou pagina de alta conversao para capturar demanda fora do Google.")
    if total_fotos < 20:
        opportunities.append("Ampliar o acervo visual para reforcar autoridade e cliques no perfil.")
    if total_avaliacoes < 30:
        opportunities.append("Estruturar uma rotina de pedido de avaliacao para ganhar prova social.")
    if avaliacao and avaliacao < 4.5:
        opportunities.append("Tratar reputacao e respostas publicas para proteger a conversao.")
    if not opportunities:
        opportunities.append("Focar o proximo ciclo em conversao, velocidade de resposta e recorrencia.")

    data_str = date.today().strftime("%d/%m/%Y")
    stars_filled = max(0, min(5, int(round(avaliacao))))
    stars_visual = ("★" * stars_filled) + ("☆" * (5 - stars_filled)) if avaliacao else "Sem nota"
    dist_total = max(total_avaliacoes, sum(dist.values()), 1)
    negative_share = round((neg / total_avaliacoes) * 100) if total_avaliacoes else 0
    wa_display = str(data.get("seu_whatsapp") or "").strip()
    wa_num = re.sub(r"\D", "", wa_display)
    if wa_num and not wa_num.startswith("55"):
        wa_num = f"55{wa_num}"
    wa_link = f"https://wa.me/{wa_num}?text=Quero%20ver%20uma%20demonstracao%20do%20meu%20site" if wa_num else ""

    extras = _safe_json_loads(data.get("dados_extras"), {})
    search_rank = extras.get("rank")
    try:
        search_rank = int(search_rank) if search_rank not in (None, "") else None
    except Exception:
        search_rank = None
    search_query = str(extras.get("searchString") or "").strip()
    search_page_url = str(extras.get("searchPageUrl") or "").strip()
    is_ad = bool(extras.get("isAdvertisement"))
    people_also_search = _extract_named_items(extras.get("peopleAlsoSearch"), limit=5)
    reviews_tags = _extract_named_items(extras.get("reviewsTags"), limit=6)
    image_categories = _extract_named_items(extras.get("imageCategories"), limit=5)
    additional_groups, additional_features = _flatten_additional_info(extras.get("additionalInfo") or {}, limit=8)
    owner_updates = extras.get("ownerUpdates") or []
    qna_items = extras.get("questionsAndAnswers") or []
    raw_reviews = extras.get("reviews") or []
    owner_responses = sum(1 for rv in raw_reviews if (rv.get("responseFromOwnerText") or "").strip())
    reviews_with_photos = sum(1 for rv in raw_reviews if rv.get("reviewImageUrls"))
    recent_reviews = 0
    for rv in raw_reviews:
        published = str(rv.get("publishedAtDate") or "").strip()
        if published.startswith(str(date.today().year)) or published.startswith(str(date.today().year - 1)):
            recent_reviews += 1
    opening_hours = _safe_json_loads(data.get("horario"), [])
    has_hours = bool(opening_hours)
    is_claimed = bool(data.get("reivindicado"))
    has_menu = bool(data.get("menu_url"))
    has_description = bool(str(data.get("descricao") or extras.get("description") or "").strip())
    has_extra_categories = bool(_safe_json_loads(data.get("categorias"), []))
    has_attributes = bool(additional_features)

    completeness_checks = [
        ("Perfil reivindicado", is_claimed),
        ("Horario preenchido", has_hours),
        ("Site conectado", tem_web),
        ("Descricao do negocio", has_description),
        ("Categorias complementares", has_extra_categories),
        ("Atributos do perfil", has_attributes),
        ("Galeria relevante", total_fotos >= 10),
        ("CTA adicional", has_menu),
    ]
    completeness_score = round(sum(1 for _, ok in completeness_checks if ok) / max(len(completeness_checks), 1) * 100)
    completeness_ok = [label for label, ok in completeness_checks if ok][:4]
    completeness_missing = [label for label, ok in completeness_checks if not ok][:3]

    priorities = []
    priority_class = {"Alta": "bad", "Media": "warn", "Baixa": "good"}
    for idx, rec in enumerate(recs[:3], start=1):
        priorities.append(
            {
                "index": f"{idx:02d}",
                "priority": rec["priority"].upper(),
                "title": rec["title"],
                "body": rec["body"],
                "class_name": priority_class.get(rec["priority"], "good"),
            }
        )

    categories = [
        {
            "title": "Presenca online",
            "current": sc_pres,
            "potential": pot_pres,
            "delta": max(0, pot_pres - sc_pres),
            "class_name": _score_color(sc_pres),
            "label": _score_label(sc_pres),
        },
        {
            "title": "Reputacao local",
            "current": sc_rep,
            "potential": pot_rep,
            "delta": max(0, pot_rep - sc_rep),
            "class_name": _score_color(sc_rep),
            "label": _score_label(sc_rep),
        },
        {
            "title": "Engajamento",
            "current": sc_eng,
            "potential": pot_eng,
            "delta": max(0, pot_eng - sc_eng),
            "class_name": _score_color(sc_eng),
            "label": _score_label(sc_eng),
        },
    ]

    review_distribution = []
    for stars in range(5, 0, -1):
        count = int(dist.get(stars, 0))
        review_distribution.append(
            {
                "label": f"{stars} estrelas",
                "count": count,
                "percent": round((count / dist_total) * 100),
            }
        )

    return {
        "generated_at": data_str,
        "company_name": nome,
        "category": categoria,
        "phone": telefone,
        "address": endereco,
        "city": cidade,
        "website_url": website_url,
        "website_link": website_link,
        "has_website": tem_web,
        "google_rating": f"{avaliacao:.1f}" if avaliacao else "--",
        "google_rating_value": avaliacao,
        "google_reviews": total_avaliacoes,
        "google_photos": total_fotos,
        "stars_visual": stars_visual,
        "score_total": sc_total,
        "score_total_label": _score_label(sc_total),
        "score_total_class": _score_color(sc_total),
        "score_phrase": _score_phrase(sc_total),
        "score_gain": score_gain,
        "potential_total": potential_total,
        "main_gap": main_gap.capitalize(),
        "strengths": strengths[:2],
        "opportunities": opportunities[:2],
        "categories": categories,
        "priorities": priorities,
        "review_distribution": review_distribution,
        "negative_feedback_text": f"{neg} avaliacoes baixas ({negative_share}%)" if neg else "Sem concentracao relevante de notas baixas",
        "commercial_signal": "Perfil com boa base" if sc_rep >= 70 else "Confianca moderada" if sc_rep >= 40 else "Confianca fragil",
        "search_rank": search_rank,
        "search_query": search_query or "Busca local principal",
        "search_page_url": search_page_url,
        "is_ad": is_ad,
        "people_also_search": people_also_search,
        "reviews_tags": reviews_tags,
        "image_categories": image_categories,
        "additional_groups": additional_groups,
        "additional_features": additional_features,
        "owner_updates_count": len(owner_updates),
        "qna_count": len(qna_items),
        "owner_responses_count": owner_responses,
        "reviews_with_photos": reviews_with_photos,
        "recent_reviews_count": recent_reviews,
        "completeness_score": completeness_score,
        "completeness_ok": completeness_ok,
        "completeness_missing": completeness_missing,
        "has_hours": has_hours,
        "is_claimed": is_claimed,
        "prepared_by": str(data.get("seu_nome") or "OtimizaAI"),
        "whatsapp_display": wa_display or "WhatsApp nao informado",
        "whatsapp_link": wa_link,
        "cover_chips": [
            _truncate(categoria, 18),
            _truncate(cidade, 16),
            data_str,
        ],
        "meta": [
            {"label": "Empresa", "value": _truncate(nome, 24)},
            {"label": "Nicho", "value": _truncate(categoria, 20)},
            {"label": "Local", "value": _truncate(cidade, 20)},
            {"label": "Potencial", "value": f"{sc_total} para {potential_total}"},
        ],
        "roadmap": [
            {
                "step": "01",
                "title": "Base web e conversao",
                "body": "Criar ou refinar uma pagina com proposta clara, prova social e CTA direto para WhatsApp.",
                "result": "Mais clareza comercial e menos perda de interessados",
                "accent": "blue",
            },
            {
                "step": "02",
                "title": "Perfil Google e reputacao",
                "body": "Atualizar fotos, reforcar o perfil e estruturar uma rotina simples para novas avaliacoes.",
                "result": "Mais confianca na busca local e maior taxa de clique",
                "accent": "gold",
            },
            {
                "step": "03",
                "title": "Fluxo comercial",
                "body": "Diminuir atrito no atendimento e transformar pesquisa local em conversa mais qualificada.",
                "result": "Mais respostas e mais oportunidades reais de venda",
                "accent": "green",
            },
        ],
    }


def build_diagnostic_pdf_html(data, output, ensure_logo_assets=None, draw_text_logo=None):
    if ensure_logo_assets:
        ensure_logo_assets()

    base_dir = Path(__file__).resolve().parent
    env = Environment(
        loader=FileSystemLoader(str(base_dir / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("diagnostic_pdf.html")

    vm = _build_view_model(data)
    logo_path = base_dir / "assets" / "Logo.png"
    logo_data = _file_to_data_uri(logo_path)
    vm["logo_main"] = logo_data
    vm["logo_header"] = logo_data
    vm["logo_cta"] = logo_data

    html = template.render(**vm)
    browser = _find_browser()

    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        html_path = tmp_path / "diagnostic.html"
        pdf_path = tmp_path / "diagnostic.pdf"
        html_path.write_text(html, encoding="utf-8")

        commands = [
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--allow-file-access-from-files",
                "--print-to-pdf-no-header",
                f"--print-to-pdf={pdf_path}",
                html_path.as_uri(),
            ],
            [
                browser,
                "--headless",
                "--disable-gpu",
                "--allow-file-access-from-files",
                "--print-to-pdf-no-header",
                f"--print-to-pdf={pdf_path}",
                html_path.as_uri(),
            ],
        ]

        last_error = None
        for cmd in commands:
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=90)
                if pdf_path.exists() and pdf_path.stat().st_size > 0:
                    break
            except Exception as exc:
                last_error = exc

        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
            raise RuntimeError("Falha ao gerar PDF via HTML/Chrome headless.") from last_error

        pdf_bytes = pdf_path.read_bytes()

    if hasattr(output, "write"):
        output.write(pdf_bytes)
        if hasattr(output, "seek"):
            output.seek(0)
        return output

    Path(output).write_bytes(pdf_bytes)
    return output
