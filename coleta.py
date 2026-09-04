# -*- coding: utf-8 -*-
"""Etapa 1: aplica a trava de qualidade às observações transcritas e grava o estado.

Uso:
    python coleta.py hoje                        # data de hoje (Brasília), se é pregão e se já foi coletado
    python coleta.py observacoes.json            # só avalia e imprime o relatório
    python coleta.py observacoes.json --gravar   # avalia e, se passar, grava no estado

Formato de observacoes.json (o agente só transcreve; quem decide é este script):
{
 "data_referencia": "2026-09-04",
 "observacoes": {
   "LFTB11": [{"fonte": "MoneyTimes", "preco": 126.14, "carimbo": "2026-09-04"},
              {"fonte": "B3", "preco": 126.07, "carimbo": "2026-09-04"}],
   ...
   "GOVT":  [{"fonte": "stockanalysis", "preco": 22.35, "carimbo": "2026-09-04"}],
   "IBOV":  [{"fonte": "statusinvest", "preco": 185188, "carimbo": null}],
   "PTAX":  [{"fonte": "BCB-1", "preco": 5.0962, "carimbo": "2026-09-04"}],
   "CDI":   [{"fonte": "BCB-4389", "preco": 13.90, "carimbo": "2026-09-03"}]
 },
 "proventos": {"GOVT": 0.076}      # opcional: só ETFs EUA com data ex na data de referência
}
"carimbo" é a data (AAAA-MM-DD) que a fonte informa para o preço; null quando a fonte não informa.
Data com hora ("2026-09-04 17:42:04") é aceita: o script usa só os dez primeiros caracteres.
Preço que a fonte não devolveu: não incluir a observação (não inventar). Chave ausente e lista
vazia são equivalentes.

Regras (na ordem):
 1. Carimbo. Todo ativo precisa de ao menos uma observação com carimbo igual à data de referência.
    Observação sem carimbo só corrobora. Duas exceções explícitas: IBOV (aceita sem carimbo,
    só entra em texto comparativo, não na cota) e CDI (aceita o último ponto publicado, marcado
    como provisório; o BCB publica com atraso e a taxa move a cota abaixo da terceira casa).
 2. Concordância. Entre as observações com carimbo válido, máximo/mínimo − 1 > 0,5% barra o ativo.
 3. Sanidade. Variação contra o pregão anterior acima de 15% barra o ativo.
Preço escolhido: a observação válida da fonte de maior prioridade (ordem em PRIORIDADE).
Sai com código 0 se passou, 1 se barrou. O relatório impresso é o corpo do e-mail de falha.
"""
import sys, json
from datetime import date
import estado as E

ATIVOS_B3 = ["LFTB11","B5P211","B5MB11","WRLD11","SPXR11","GOLD11","SMAL11"]
ATIVOS_EUA = ["GOVT","TLT","KMLM","SMH","URA"]
PRIORIDADE = ["MoneyTimes","B3","stockanalysis","BCB-1","BCB-4389","statusinvest"]
TOL_CONCORDANCIA = 0.005
TOL_SANIDADE = 0.15
SEM_CARIMBO_OK = {"IBOV"}

def _prio(o):
    f = o.get("fonte", "")
    return PRIORIDADE.index(f) if f in PRIORIDADE else len(PRIORIDADE)

def avaliar(obs_doc, est):
    ref = date.fromisoformat(obs_doc["data_referencia"])
    obs = obs_doc["observacoes"]
    ant = E.pregao_anterior(est, ref)
    p_ant = est["precos"].get(ant.strftime("%Y-%m-%d"))
    linhas, falhas, escolhidos, procedencia = [], [], {}, []
    cdi_provisorio = False

    for ativo in E.CAMPOS:
        lista = [dict(o) for o in obs.get(ativo, []) if o.get("preco") is not None]
        for o in lista:
            o["carimbo"] = str(o["carimbo"])[:10] if o.get("carimbo") else None
            if ativo == "IBOV": o["preco"] = round(float(o["preco"]))
        if not lista:
            falhas.append(f"{ativo}: nenhuma fonte devolveu preço")
            linhas.append(f"{ativo}: SEM OBSERVAÇÃO"); continue
        desc = "; ".join(f"{o['fonte']} {o['preco']} @ {o.get('carimbo') or 'sem carimbo'}" for o in lista)

        if ativo == "CDI":
            com = [o for o in lista if o.get("carimbo")]
            if not com:
                falhas.append("CDI: fonte sem data"); linhas.append(f"CDI: {desc} -> BARRADO (sem data)"); continue
            o = max(com, key=lambda o: o["carimbo"])
            if o["carimbo"] > ref.isoformat():
                falhas.append("CDI: data posterior à referência"); linhas.append(f"CDI: {desc} -> BARRADO"); continue
            cdi_provisorio = o["carimbo"] < ref.isoformat()
            escolhidos["CDI"] = float(o["preco"])
            tag = "provisório, última taxa publicada" if cdi_provisorio else "definitivo"
            linhas.append(f"CDI: {desc} -> {o['preco']} ({tag})")
            procedencia.append(f"CDI {o['preco']} {o['fonte']} @ {o['carimbo']} ({tag})")
            continue

        validas = [o for o in lista if o.get("carimbo") == ref.isoformat()]
        if not validas and ativo in SEM_CARIMBO_OK:
            validas = [o for o in lista if not o.get("carimbo") or o.get("carimbo") == ref.isoformat()]
            aviso = " (aceito sem carimbo, exceção explícita)"
        else:
            aviso = ""
        if not validas:
            falhas.append(f"{ativo}: nenhuma fonte com carimbo {ref.strftime('%d/%m/%Y')}")
            linhas.append(f"{ativo}: {desc} -> BARRADO (carimbo)"); continue

        precos = [float(o["preco"]) for o in validas]
        if len(precos) > 1 and (max(precos)/min(precos) - 1) > TOL_CONCORDANCIA:
            falhas.append(f"{ativo}: fontes com carimbo válido divergem mais de 0,5% ({min(precos)} a {max(precos)})")
            linhas.append(f"{ativo}: {desc} -> BARRADO (concordância)"); continue

        o = sorted(validas, key=_prio)[0]
        px = float(o["preco"])
        if p_ant and ativo in p_ant and p_ant[ativo]:
            var = px/float(p_ant[ativo]) - 1
            if abs(var) > TOL_SANIDADE:
                falhas.append(f"{ativo}: variação de {var*100:+.1f}% contra {ant.strftime('%d/%m')} ({p_ant[ativo]} -> {px})")
                linhas.append(f"{ativo}: {desc} -> BARRADO (sanidade {var*100:+.1f}%)"); continue
            var_txt = f", {var*100:+.2f}% vs {ant.strftime('%d/%m')}"
        else:
            var_txt = ""
        escolhidos[ativo] = px
        unica = "fonte única" if len(validas) == 1 else f"{len(validas)} fontes com carimbo"
        linhas.append(f"{ativo}: {desc} -> {px} de {o['fonte']}{aviso} ({unica}{var_txt})")
        procedencia.append(f"{ativo} {px} {o['fonte']} @ {o.get('carimbo') or 'sem carimbo'} ({unica})")

    rel = [f"Coleta Backbone — pregão de {ref.strftime('%d/%m/%Y')} (anterior em estado: {ant.strftime('%d/%m/%Y')})", ""]
    rel += linhas
    rel.append("")
    if falhas:
        rel.append("RESULTADO: BARRADO. Estado não alterado. Condições que falharam:")
        rel += [f" - {f}" for f in falhas]
    else:
        rel.append("RESULTADO: PASSOU. Linha pronta para gravar.")
    return {"ref": ref, "passou": not falhas, "relatorio": "\n".join(rel), "precos": escolhidos,
            "procedencia": "; ".join(procedencia), "cdi_provisorio": cdi_provisorio,
            "proventos": obs_doc.get("proventos") or None}

def main():
    est = E.carregar()
    if sys.argv[1] == "hoje":
        from datetime import datetime, timedelta, timezone
        hoje = datetime.now(timezone(timedelta(hours=-3))).date()
        print(json.dumps({"hoje": hoje.isoformat(), "pregao_b3": E.dia_util_b3(est, hoje),
                          "ja_coletado": E.tem_data(est, hoje),
                          "ultimo_no_estado": E.ultima_data(est).isoformat()})); return 0
    arq = sys.argv[1]
    gravar = "--gravar" in sys.argv
    doc = json.load(open(arq, encoding="utf-8"))
    ref = date.fromisoformat(doc["data_referencia"])
    if not E.dia_util_b3(est, ref):
        print(f"{ref.strftime('%d/%m/%Y')} não é pregão B3 (fim de semana ou feriado). Nada a fazer."); return 0
    if E.tem_data(est, ref):
        print(f"{ref.strftime('%d/%m/%Y')} já está no estado. Coleta já feita. Nada a fazer."); return 0
    from datetime import datetime, timedelta, timezone
    agora = datetime.now(timezone(timedelta(hours=-3)))
    if gravar and ref == agora.date() and agora.hour < 18:
        print(f"São {agora.strftime('%H:%M')} de Brasília: o pregão de {ref.strftime('%d/%m')} ainda não fechou. "
              "Preço intradiário não é fechamento. Não gravado."); return 1
    if gravar and ref > agora.date():
        print("Data de referência no futuro. Não gravado."); return 1
    r = avaliar(doc, est)
    print(r["relatorio"])
    if not r["passou"]:
        return 1
    if gravar:
        E.adicionar_pregao(est, ref, r["precos"], r["procedencia"], r["cdi_provisorio"], r["proventos"])
        E.gravar(est)
        print(f"\nGravado em {E.ARQ}: {ref.isoformat()}")
    else:
        print("\n(não gravado: rode com --gravar)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
