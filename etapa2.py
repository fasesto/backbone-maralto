# -*- coding: utf-8 -*-
"""Etapa 2: decide se a nota do dia sai, gera os .docx e marca o envio.

Uso:
    python etapa2.py decidir [AAAA-MM-DD]    # imprime JSON: {"acao": ..., "ref": ..., "motivo": ...}
    python etapa2.py cdi AAAA-MM-DD TAXA     # substitui CDI provisório pela taxa definitiva do BCB
    python etapa2.py gerar [AAAA-MM-DD]      # gera os dois .docx da referência e imprime os caminhos
    python etapa2.py enviada [AAAA-MM-DD]    # marca a referência como enviada (só depois do e-mail sair)
    python etapa2.py serie                   # imprime as séries publicadas (markdown)

Referência = a data passada; sem data, o último pregão B3 anterior a hoje (Brasília).
 - "enviar": referência está no estado e ainda não tem nota enviada.
 - "pular": referência já tem nota enviada (feriado ontem, ou execução repetida). Não avisar ninguém.
 - "falha": referência não está no estado. A coleta da véspera barrou. Avisar só o Bruno.
"""
import sys, json
from datetime import date, datetime, timedelta, timezone
import estado as E

BRT = timezone(timedelta(hours=-3))

def hoje_brt():
    return datetime.now(BRT).date()

def referencia(est, arg=None):
    return date.fromisoformat(arg) if arg else E.pregao_anterior(est, hoje_brt())

def decidir(est, arg=None):
    ref = referencia(est, arg)
    if not E.tem_data(est, ref):
        return {"acao": "falha", "ref": ref.isoformat(),
                "motivo": f"o fechamento de {ref.strftime('%d/%m/%Y')} não foi coletado; a coleta da véspera barrou"}
    if E.nota_ja_enviada(est, ref):
        return {"acao": "pular", "ref": ref.isoformat(), "motivo": "nota desta referência já foi enviada"}
    return {"acao": "enviar", "ref": ref.isoformat(),
            "cdi_provisorio": ref.isoformat() in est.get("cdi_provisorio", []),
            "motivo": "referência coletada e sem nota enviada"}

def serie_md(est):
    import nota
    ref = E.ultima_data(est)
    out = [f"## Fechamentos ({min(est['precos'])} a {max(est['precos'])})", "",
           "| Data | " + " | ".join(E.CAMPOS) + " |", "|" + "---|"*(len(E.CAMPOS)+1)]
    for d, v in sorted(est["precos"].items()):
        out.append(f"| {d} | " + " | ".join(str(v[c]) for c in E.CAMPOS) + " |")
    cc, _ = nota.serie_completa(ref)
    ce, _ = nota.serie_essencial(ref)
    da = E.ANCORA_COMPLETA[0]
    out += ["", f"## Completa publicada (âncora {da.strftime('%d/%m/%Y')} = {E.ANCORA_COMPLETA[1]:.3f})", "",
            "| Data | Cota | Var. dia |", "|---|---|---|"]
    ds = [d for d in sorted(cc) if d >= da]
    for i, d in enumerate(ds):
        var = "" if i == 0 else f"{(cc[d]/cc[ds[i-1]]-1)*100:+.2f}%"
        out.append(f"| {d.strftime('%d/%m/%Y')} | {cc[d]:.3f} | {var} |")
    out += ["", f"## Essencial publicada (base 100,000 em {E.BASE_ESSENCIAL.strftime('%d/%m/%Y')})", "",
            "| Data | Cota | Var. dia |", "|---|---|---|"]
    ds = sorted(ce)
    for i, d in enumerate(ds):
        var = "" if i == 0 else f"{(ce[d]/ce[ds[i-1]]-1)*100:+.2f}%"
        out.append(f"| {d.strftime('%d/%m/%Y')} | {ce[d]:.3f} | {var} |")
    out += ["", "## Procedência", ""]
    for d, p in sorted(est.get("procedencia", {}).items()):
        out.append(f"- {d}: {p}")
    if est.get("cdi_provisorio"):
        out += ["", "CDI provisório em: " + ", ".join(est["cdi_provisorio"])]
    out += ["", "Notas enviadas: " + ", ".join(est["notas_enviadas"])]
    return "\n".join(out) + "\n"

def main():
    cmd = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 and cmd in ("decidir", "gerar", "enviada") else None
    est = E.carregar()
    if cmd == "decidir":
        print(json.dumps(decidir(est, arg), ensure_ascii=False)); return 0
    if cmd == "cdi":
        d, taxa = date.fromisoformat(sys.argv[2]), float(sys.argv[3])
        E.corrigir_cdi(est, d, taxa); E.gravar(est)
        print(f"CDI de {d} = {taxa} gravado como definitivo"); return 0
    if cmd == "gerar":
        dec = decidir(est, arg)
        if dec["acao"] != "enviar":
            print(json.dumps(dec, ensure_ascii=False)); return 1
        import nota
        for s in nota.gerar(date.fromisoformat(dec["ref"])):
            print(s)
        return 0
    if cmd == "enviada":
        ref = referencia(est, arg)
        if not E.tem_data(est, ref):
            print(f"{ref} não está no estado; nada marcado"); return 1
        E.marcar_nota_enviada(est, ref); E.gravar(est)
        print(f"{ref} marcada como enviada"); return 0
    if cmd == "serie":
        sys.stdout.write(serie_md(est)); return 0
    print(__doc__); return 2

if __name__ == "__main__":
    sys.exit(main())
