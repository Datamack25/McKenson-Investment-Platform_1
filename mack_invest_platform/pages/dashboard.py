# pages/dashboard.py  —  MAM v7.1  SYNTAX FIXED
"""
FIXES v7.1:
  - SyntaxError ligne 333 corrigé : f-string imbriquée remplacée par variable intermédiaire
  - pct_cell / pnl_cell déjà dans ui.py
  - Wizard + contraintes + comparaison conservés intégralement
"""
from __future__ import annotations
import uuid
import streamlit as st

from components.ui import section_title
from utils.data import get_or_init_state, get_multi_prices, persist

_TAPE_SYMBOLS = [
    ("^GSPC","S&P500"),("^IXIC","NASDAQ"),("^DJI","DOW"),("^FCHI","CAC40"),
    ("^GDAXI","DAX"),("^FTSE","FTSE"),("GC=F","GOLD"),("CL=F","WTI"),
    ("BTC-USD","BTC"),("ETH-USD","ETH"),("EURUSD=X","EUR/USD"),("^VIX","VIX"),
    ("AAPL","AAPL"),("NVDA","NVDA"),("MSFT","MSFT"),("TSLA","TSLA"),
    ("AMZN","AMZN"),("META","META"),
]
_FIXED_COUNT = 2
_EMOJIS = ["📁","🦅","🐂","🎯","🌊","🔥","💼","🏆","⚡","🎲","🦁","🐉","🌙","☀️","💫","🧠","🔮","🏔️","🌿","🎪"]
_TEAM_EMOJIS = ["🏢","🦅","🐂","🎯","🌊","🔥","🏆","⚡","🎲","🌍","🦁","🐉","💡","🚀","🔬","🏛️","🌐","💎","🔱","🎓"]

_STRATEGIES = [
    {"id":"growth",    "emoji":"📈","name":"Growth",        "desc":"Actions à forte croissance, tech & momentum"},
    {"id":"value",     "emoji":"💎","name":"Value",          "desc":"Actifs décotés — approche Graham/Buffett"},
    {"id":"momentum",  "emoji":"🚀","name":"Momentum",       "desc":"Suivi de tendance multi-classes d'actifs"},
    {"id":"income",    "emoji":"💰","name":"Income",         "desc":"Dividendes & actifs à rendement"},
    {"id":"macro",     "emoji":"🌍","name":"Global Macro",   "desc":"Thèmes macro multi-actifs"},
    {"id":"hedging",   "emoji":"🛡️","name":"Hedging",        "desc":"Options & positions inverses"},
    {"id":"balanced",  "emoji":"⚖️","name":"Balanced 60/40", "desc":"Allocation classique actions/obligations"},
    {"id":"commodity", "emoji":"🛢️","name":"Commodities",    "desc":"Matières premières & énergie"},
    {"id":"crypto",    "emoji":"₿", "name":"Crypto Alpha",   "desc":"Panier d'actifs digitaux"},
    {"id":"arbitrage", "emoji":"🔁","name":"Arbitrage",      "desc":"Long/short market-neutral"},
]

_ASSET_CONSTRAINTS: dict[str, dict] = {
    "equity":    {"emoji":"📊","name":"Actions",           "max_alloc":100,"max_single":30,  "allowed_suffix":[],"forbidden_suffix":["-USD","=F","=X"],"rules":["Max 30% par titre","Pas de crypto/forex/futures"]},
    "etf":       {"emoji":"🗂️","name":"ETFs / Indices",    "max_alloc":100,"max_single":50,  "allowed_suffix":[],"forbidden_suffix":["-USD","=F","=X"],"rules":["Max 50% par ETF","Diversification recommandée"]},
    "crypto":    {"emoji":"₿", "name":"Crypto",            "max_alloc":30, "max_single":15,  "allowed_suffix":["-USD"],"forbidden_suffix":[],"rules":["Max 30% du portf.","Max 15% par crypto","Uniquement *-USD"]},
    "commodity": {"emoji":"🛢️","name":"Matières premières","max_alloc":40, "max_single":20,  "allowed_suffix":["=F"],"forbidden_suffix":[],"rules":["Max 40% en commodities","Max 20% par contrat *=F"]},
    "forex":     {"emoji":"💱","name":"Forex",              "max_alloc":30, "max_single":15,  "allowed_suffix":["=X"],"forbidden_suffix":[],"rules":["Max 30% en forex","Uniquement *=X","Max 15% par paire"]},
    "bond":      {"emoji":"📜","name":"Obligations",        "max_alloc":60, "max_single":25,  "allowed_suffix":[],"forbidden_suffix":["-USD","=F","=X"],"rules":["Max 60% en obligations","TLT, IEF, LQD recommandés"]},
    "mixed":     {"emoji":"🌐","name":"Multi-actifs",       "max_alloc":100,"max_single":25,  "allowed_suffix":[],"forbidden_suffix":[],"rules":["Max 25% par position","Toutes classes autorisées"]},
}

_STRATEGY_CONSTRAINTS: dict[str, dict] = {
    "growth":    {"recommended":["equity","etf"],         "max_crypto":10,"max_bond":10},
    "value":     {"recommended":["equity","bond"],         "max_crypto":5, "max_bond":30},
    "momentum":  {"recommended":["equity","etf","crypto"], "max_crypto":20,"max_bond":5},
    "income":    {"recommended":["bond","etf","equity"],   "max_crypto":5, "max_bond":60},
    "macro":     {"recommended":["mixed"],                 "max_crypto":15,"max_bond":30},
    "hedging":   {"recommended":["etf","bond","forex"],    "max_crypto":10,"max_bond":40},
    "balanced":  {"recommended":["equity","bond","etf"],   "max_crypto":5, "max_bond":40},
    "commodity": {"recommended":["commodity","etf"],       "max_crypto":10,"max_bond":10},
    "crypto":    {"recommended":["crypto"],                "max_crypto":80,"max_bond":0},
    "arbitrage": {"recommended":["equity","etf","forex"],  "max_crypto":10,"max_bond":20},
}


def _build_tape(prices: dict) -> str:
    def item_html(sym, label, animated):
        if sym not in prices: return ""
        px, pct = prices[sym]
        arr  = "▲" if pct >= 0 else "▼"
        cls  = "tape-up" if pct >= 0 else "tape-dn"
        sign = "+" if pct >= 0 else ""
        px_str = f"${px:,.0f}" if px >= 1000 else (f"${px:,.2f}" if px >= 1 else f"${px:,.5f}")
        bc = "#00d4ff" if animated else "#7c3aed"
        return (
            f'<span class="tape-item">'
            f'<span class="tape-badge" style="border-color:{bc};color:{bc};">{label}</span>'
            f'<span class="tape-px">{px_str}</span>'
            f'<span class="{cls}">{arr}{sign}{abs(pct):.2f}%</span>'
            f'</span>'
        )
    anim  = "".join(item_html(s, l, True)  for s, l in _TAPE_SYMBOLS[:-_FIXED_COUNT])
    fixed = "".join(item_html(s, l, False) for s, l in _TAPE_SYMBOLS[-_FIXED_COUNT:])
    return f"""<style>
.tape-wrap{{display:flex;align-items:center;width:100%;height:28px;
  background:rgba(0,8,18,.96);border:1px solid rgba(0,212,255,.16);
  border-radius:5px;overflow:hidden;margin-bottom:6px;}}
.tape-scroll-zone{{flex:1;overflow:hidden;height:100%;display:flex;align-items:center;}}
.tape-track{{display:flex;white-space:nowrap;animation:tape-anim 80s linear infinite;
  height:100%;align-items:center;}}
.tape-track:hover{{animation-play-state:paused;}}
@keyframes tape-anim{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}
.tape-fixed{{display:flex;align-items:center;height:100%;padding:0 4px;flex-shrink:0;
  border-left:1px solid rgba(124,58,237,.3);background:rgba(124,58,237,.06);}}
.tape-item{{display:inline-flex;align-items:center;gap:4px;padding:0 10px;
  border-right:1px solid rgba(255,255,255,.05);font-family:'Share Tech Mono',monospace;font-size:.63rem;}}
.tape-badge{{display:inline-flex;align-items:center;justify-content:center;
  width:42px;height:16px;border:1px solid;border-radius:2px;
  font-family:'Rajdhani',sans-serif;font-weight:700;font-size:.58rem;letter-spacing:.04em;}}
.tape-px{{color:#e2e8f0;font-size:.63rem;}}
.tape-up{{color:#00ff88;font-size:.60rem;}}
.tape-dn{{color:#ff3b6b;font-size:.60rem;}}
</style>
<div class="tape-wrap">
  <div class="tape-scroll-zone"><div class="tape-track">{anim}{anim}</div></div>
  <div class="tape-fixed">{fixed}</div>
</div>"""


def _wizard(state: dict):
    step = st.session_state.get("wizard_step", 1)
    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(0,212,255,.08),rgba(124,58,237,.08));
    border:1px solid rgba(0,212,255,.25);border-radius:12px;padding:22px 26px;margin-bottom:18px;">
    <div style="font-family:Rajdhani,sans-serif;font-size:1.3rem;font-weight:700;
    color:#00d4ff;letter-spacing:.12em;">🚀 NOUVEAU PORTEFEUILLE</div>
    <div style="font-family:Share Tech Mono,monospace;font-size:.73rem;color:#7a93b0;margin-top:4px;">
    Configurez votre portefeuille en 4 étapes</div></div>
    """, unsafe_allow_html=True)

    labels = ["Identité", "Stratégie", "Actifs", "Équipe"]
    bar_html = '<div style="display:flex;gap:6px;margin-bottom:20px;">'
    for i, lbl in enumerate(labels, 1):
        done   = i < step
        active = i == step
        col  = "#00ff88" if done else ("#00d4ff" if active else "rgba(255,255,255,.1)")
        tcol = "#00ff88" if done else ("#00d4ff" if active else "#334155")
        prefix = "✓ " if done else ""
        bar_html += (
            f'<div style="flex:1;text-align:center;">'
            f'<div style="height:3px;background:{col};border-radius:2px;margin-bottom:4px;"></div>'
            f'<div style="font-family:Rajdhani;font-size:.6rem;color:{tcol};'
            f'letter-spacing:.1em;text-transform:uppercase;">{prefix}{lbl}</div>'
            f'</div>'
        )
    st.markdown(bar_html + "</div>", unsafe_allow_html=True)

    if step == 1:
        st.markdown('<div style="font-family:Rajdhani;font-size:1rem;font-weight:700;color:#e2e8f0;margin-bottom:14px;">📝 Identité du portefeuille</div>', unsafe_allow_html=True)
        c1, c2 = st.columns([3, 1])
        with c1:
            name = st.text_input("Nom", placeholder="ex: Alpha Growth Fund", key="wiz_name")
        with c2:
            emoji = st.selectbox("Icône", _EMOJIS, key="wiz_emoji")
        capital = st.number_input("Capital initial ($)", min_value=10_000, max_value=100_000_000, value=1_000_000, step=100_000, key="wiz_capital")
        if st.button("Suivant →", key="wiz_s1", use_container_width=True):
            if not name or len(name.strip()) < 2:
                st.error("Nom trop court (min 2 caractères).")
            else:
                st.session_state.update({"wizard_step":2,"wiz_name_ok":name.strip(),"wiz_emoji_ok":emoji,"wiz_capital_ok":capital})
                st.rerun()

    elif step == 2:
        st.markdown('<div style="font-family:Rajdhani;font-size:1rem;font-weight:700;color:#e2e8f0;margin-bottom:14px;">🎯 Stratégie d\'investissement</div>', unsafe_allow_html=True)
        sel = st.session_state.get("wiz_strat", "")
        cols = st.columns(2)
        for i, s in enumerate(_STRATEGIES):
            with cols[i % 2]:
                is_sel = sel == s["id"]
                sc  = _STRATEGY_CONSTRAINTS.get(s["id"], {})
                rec = ", ".join(sc.get("recommended", []))
                border = "rgba(0,212,255,.7)" if is_sel else "rgba(0,212,255,.12)"
                bg     = "rgba(0,212,255,.1)"  if is_sel else "rgba(0,10,25,.4)"
                st.markdown(
                    f'<div style="background:{bg};border:1px solid {border};border-radius:8px;padding:10px 14px;margin-bottom:4px;">'
                    f'<span style="font-size:1.1rem;">{s["emoji"]}</span> '
                    f'<b style="font-family:Rajdhani;color:#e2e8f0;">{s["name"]}</b><br>'
                    f'<span style="font-family:Share Tech Mono;font-size:.66rem;color:#7a93b0;">{s["desc"]}</span><br>'
                    f'<span style="font-family:Rajdhani;font-size:.6rem;color:#00d4ff;">Actifs : {rec} · crypto max {sc.get("max_crypto",0)}%</span>'
                    f'</div>', unsafe_allow_html=True)
                # FIX: pas de f-string imbriquée — variable intermédiaire
                btn_label = "✓ Sélectionné" if is_sel else s["name"]
                if st.button(btn_label, key=f'wiz_strat_{s["id"]}', use_container_width=True):
                    st.session_state["wiz_strat"] = s["id"]
                    st.rerun()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Retour", key="wiz_b2", use_container_width=True):
                st.session_state["wizard_step"] = 1; st.rerun()
        with c2:
            if st.button("Suivant →", key="wiz_f2", use_container_width=True):
                if not st.session_state.get("wiz_strat"):
                    st.error("Choisissez une stratégie.")
                else:
                    st.session_state["wizard_step"] = 3; st.rerun()

    elif step == 3:
        strat_id  = st.session_state.get("wiz_strat", "growth")
        sc        = _STRATEGY_CONSTRAINTS.get(strat_id, {})
        rec_types = sc.get("recommended", [])
        st.markdown('<div style="font-family:Rajdhani;font-size:1rem;font-weight:700;color:#e2e8f0;margin-bottom:6px;">📦 Classes d\'actifs autorisées</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-family:Share Tech Mono;font-size:.7rem;color:#7a93b0;margin-bottom:14px;">'
            f'Stratégie <b style="color:#00d4ff;">{strat_id}</b> — '
            f'recommandé : <b style="color:#00ff88;">{", ".join(rec_types) or "libre"}</b> · '
            f'crypto max <b style="color:#ffd700;">{sc.get("max_crypto",0)}%</b></div>',
            unsafe_allow_html=True)
        sel_types = list(st.session_state.get("wiz_types", []))
        cols = st.columns(2)
        for i, (at_id, at) in enumerate(_ASSET_CONSTRAINTS.items()):
            with cols[i % 2]:
                is_rec = at_id in rec_types
                is_sel = at_id in sel_types
                border = "rgba(0,255,136,.6)" if is_sel else ("rgba(0,212,255,.3)" if is_rec else "rgba(255,255,255,.08)")
                bg     = "rgba(0,255,136,.07)" if is_sel else ("rgba(0,212,255,.05)" if is_rec else "rgba(0,10,25,.4)")
                rec_badge = ('<span style="font-family:Rajdhani;font-size:.58rem;color:#00ff88;background:rgba(0,255,136,.12);border:1px solid rgba(0,255,136,.3);border-radius:3px;padding:1px 5px;margin-left:6px;">RECOMMANDÉ</span>' if is_rec else "")
                rules_html = "".join(f'<div style="font-size:.62rem;color:#475569;">• {r}</div>' for r in at.get("rules",[]))
                st.markdown(
                    f'<div style="background:{bg};border:1px solid {border};border-radius:8px;padding:10px 14px;margin-bottom:4px;">'
                    f'<span style="font-size:1.1rem;">{at["emoji"]}</span> '
                    f'<b style="font-family:Rajdhani;color:#e2e8f0;">{at["name"]}</b>{rec_badge}<br>'
                    f'<div style="margin-top:4px;font-family:Share Tech Mono;">{rules_html}</div>'
                    f'</div>', unsafe_allow_html=True)
                # FIX: variable intermédiaire pour éviter la f-string imbriquée
                btn_lbl = "✓ Activé" if is_sel else ("Activer " + at["name"])
                if st.button(btn_lbl, key=f'wiz_at_{at_id}', use_container_width=True):
                    if at_id in sel_types:
                        sel_types.remove(at_id)
                    else:
                        sel_types.append(at_id)
                    st.session_state["wiz_types"] = sel_types
                    st.rerun()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Retour", key="wiz_b3", use_container_width=True):
                st.session_state["wizard_step"] = 2; st.rerun()
        with c2:
            if st.button("Suivant →", key="wiz_f3", use_container_width=True):
                if not sel_types:
                    st.error("Activez au moins un type d'actif.")
                else:
                    st.session_state["wizard_step"] = 4; st.rerun()

    elif step == 4:
        st.markdown('<div style="font-family:Rajdhani;font-size:1rem;font-weight:700;color:#e2e8f0;margin-bottom:6px;">🏢 Équipe — <span style="color:#7a93b0;font-size:.8rem;font-weight:400;">optionnel</span></div>', unsafe_allow_html=True)
        teams = state.get("teams", {})
        team_mode = st.radio("Équipe", ["Sans équipe","Rejoindre une équipe existante","Créer une nouvelle équipe"], key="wiz_team_mode")
        chosen_team_id = None
        if team_mode == "Rejoindre une équipe existante":
            if not teams:
                st.info("Aucune équipe existante.")
            else:
                opts = {tid: f'{t["emoji"]} {t["name"]}' for tid, t in teams.items()}
                chosen_team_id = st.selectbox("Choisir l'équipe", list(opts.keys()), format_func=lambda x: opts[x], key="wiz_join_team")
        elif team_mode == "Créer une nouvelle équipe":
            c1, c2 = st.columns([3, 1])
            with c1:
                st.text_input("Nom de l'équipe", placeholder="ex: Hedge Fund Alpha", key="wiz_new_team_name")
            with c2:
                st.selectbox("Icône", _TEAM_EMOJIS, key="wiz_new_team_emoji")

        strat_obj = next((s for s in _STRATEGIES if s["id"] == st.session_state.get("wiz_strat","")), _STRATEGIES[0])
        types_sel = st.session_state.get("wiz_types", [])
        types_str = " · ".join(_ASSET_CONSTRAINTS[t]["emoji"]+" "+_ASSET_CONSTRAINTS[t]["name"] for t in types_sel if t in _ASSET_CONSTRAINTS)
        st.markdown(
            f'<div style="background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.2);border-radius:8px;padding:14px;margin:16px 0;">'
            f'<div style="font-family:Rajdhani;font-size:.78rem;color:#00d4ff;letter-spacing:.1em;margin-bottom:8px;">RÉCAPITULATIF</div>'
            f'<div style="font-family:Share Tech Mono;font-size:.74rem;color:#e2e8f0;line-height:2.2;">'
            f'<b>Nom :</b> {st.session_state.get("wiz_emoji_ok","📁")} {st.session_state.get("wiz_name_ok","—")}<br>'
            f'<b>Capital :</b> ${st.session_state.get("wiz_capital_ok",1_000_000):,.0f}<br>'
            f'<b>Stratégie :</b> {strat_obj["emoji"]} {strat_obj["name"]}<br>'
            f'<b>Actifs :</b> {types_str or "—"}'
            f'</div></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Retour", key="wiz_b4", use_container_width=True):
                st.session_state["wizard_step"] = 3; st.rerun()
        with c2:
            if st.button("✅ Créer le portefeuille", key="wiz_create", use_container_width=True):
                _do_create(state, team_mode, chosen_team_id)


def _do_create(state: dict, team_mode: str, chosen_team_id):
    name    = st.session_state.get("wiz_name_ok", "Mon Portefeuille")
    emoji   = st.session_state.get("wiz_emoji_ok", "📁")
    capital = st.session_state.get("wiz_capital_ok", 1_000_000)
    strat   = st.session_state.get("wiz_strat", "growth")
    types   = st.session_state.get("wiz_types", ["equity"])
    teams   = state.setdefault("teams", {})

    if team_mode == "Créer une nouvelle équipe":
        tname  = st.session_state.get("wiz_new_team_name", "").strip() or "Mon Équipe"
        temoji = st.session_state.get("wiz_new_team_emoji", "🏢")
        tid    = "T" + uuid.uuid4().hex[:6].upper()
        teams[tid] = {"id":tid,"name":tname,"emoji":temoji,"portfolios":{}}
        st.session_state["active_team"] = tid
    elif team_mode == "Rejoindre une équipe existante" and chosen_team_id:
        tid = chosen_team_id
        st.session_state["active_team"] = tid
    else:
        solo_key = "__solo__"
        if solo_key not in teams:
            teams[solo_key] = {"id":solo_key,"name":"Solo","emoji":"👤","portfolios":{}}
        tid = solo_key

    pid = "P" + uuid.uuid4().hex[:6].upper()
    teams[tid]["portfolios"][pid] = {
        "id":pid,"name":name,"emoji":emoji,
        "strategy":strat,"asset_types":types,
        "cash":float(capital),"initial_cash":float(capital),
        "holdings":{},"trades":[],"history":[],
    }
    st.session_state["active_portfolio"] = pid
    persist()
    for k in list(st.session_state.keys()):
        if k.startswith("wiz_"):
            del st.session_state[k]
    st.session_state["wizard_step"] = 1
    st.session_state.pop("force_wizard", None)
    st.success(f"✅ **{emoji} {name}** créé avec ${capital:,.0f} de capital !")
    st.balloons()
    st.rerun()


def _check_constraints(port: dict, live: dict) -> list[str]:
    warnings = []
    holdings = port.get("holdings", {})
    types    = port.get("asset_types", [])
    if not holdings or not types:
        return warnings
    total_mkt = sum(pos.get("qty",0) * live.get(tk,(pos.get("avg_price",0),0))[0] for tk, pos in holdings.items())
    cash      = port.get("cash", 0.0)
    total_val = total_mkt + cash
    if total_val <= 0:
        return warnings
    for tk, pos in holdings.items():
        qty  = pos.get("qty", 0)
        curr = live.get(tk, (pos.get("avg_price",0), 0))[0]
        val  = qty * curr
        pct  = val / total_val * 100
        asset_class = "equity"
        if tk.endswith("-USD"): asset_class = "crypto"
        elif tk.endswith("=F"): asset_class = "commodity"
        elif tk.endswith("=X"): asset_class = "forex"
        if asset_class not in types:
            warnings.append(f"⚠️ {tk} ({asset_class}) non autorisé dans ce portefeuille")
            continue
        cst = _ASSET_CONSTRAINTS.get(asset_class, {})
        max_single = cst.get("max_single", 100)
        if pct > max_single:
            warnings.append(f"⚠️ {tk} : {pct:.1f}% > max {max_single}% ({asset_class})")
    return warnings


def _comparison_panel(state: dict, live: dict):
    teams = state.get("teams", {})
    rows  = []
    for tid, team in teams.items():
        tlabel = "Solo" if tid == "__solo__" else f'{team["emoji"]} {team["name"]}'
        for pid, port in team.get("portfolios", {}).items():
            if not port.get("holdings"):
                continue
            cash = port.get("cash", 0.0)
            init = port.get("initial_cash", 1_000_000)
            mkt = cost = pnl = 0.0
            for tk, pos in port["holdings"].items():
                qty = pos.get("qty", 0); avg = pos.get("avg_price", 0.0)
                curr, _ = live.get(tk, (avg, 0.0))
                mkt += qty * curr; cost += qty * avg; pnl += qty * (curr - avg)
            total    = cash + mkt
            pnl_pct  = pnl / cost * 100 if cost > 0 else 0.0
            vs_init  = (total - init) / init * 100 if init > 0 else 0.0
            strat_obj = next((s for s in _STRATEGIES if s["id"] == port.get("strategy","")), None)
            rows.append({
                "team": tlabel,
                "name": port.get("emoji","📁") + " " + port.get("name","—"),
                "strategy": (strat_obj["emoji"]+" "+strat_obj["name"]) if strat_obj else "—",
                "types": " ".join(_ASSET_CONSTRAINTS.get(t,{}).get("emoji","") for t in port.get("asset_types",[])),
                "total":total,"cash":cash,"pnl":pnl,"pnl_pct":pnl_pct,"vs_init":vs_init,
                "n_pos":len(port["holdings"]),
            })
    if len(rows) < 2:
        return
    section_title("COMPARAISON DES PORTEFEUILLES", "📊")
    rows.sort(key=lambda r: r["vs_init"], reverse=True)
    hdr = ["#","Équipe","Portefeuille","Stratégie","Actifs","AUM","P&L $","P&L %","vs Initial","Pos."]
    th  = "".join(f'<th style="font-family:Rajdhani;font-size:.62rem;color:#ffd700;letter-spacing:.08em;text-transform:uppercase;padding:7px 9px;background:rgba(255,215,0,.05);border-bottom:1px solid rgba(255,215,0,.15);">{c}</th>' for c in hdr)
    medals = ["🥇","🥈","🥉"]
    tbody  = ""
    for rank, r in enumerate(rows, 1):
        pc  = "#00ff88" if r["pnl"]>0 else ("#ff3b6b" if r["pnl"]<0 else "#94a3b8")
        vc  = "#00ff88" if r["vs_init"]>0 else ("#ff3b6b" if r["vs_init"]<0 else "#94a3b8")
        sg  = "+" if r["pnl"]>0 else ""; sv = "+" if r["vs_init"]>0 else ""
        med = medals[rank-1] if rank<=3 else str(rank)
        tbody += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,.04);">'
            f'<td style="padding:6px 9px;text-align:center;">{med}</td>'
            f'<td style="padding:6px 9px;font-family:Rajdhani;font-size:.78rem;color:#7a93b0;">{r["team"]}</td>'
            f'<td style="padding:6px 9px;font-family:Rajdhani;font-weight:700;color:#e2e8f0;">{r["name"]}</td>'
            f'<td style="padding:6px 9px;font-family:Share Tech Mono;font-size:.68rem;color:#7a93b0;">{r["strategy"]}</td>'
            f'<td style="padding:6px 9px;font-size:.9rem;">{r["types"]}</td>'
            f'<td style="padding:6px 9px;font-family:Share Tech Mono;color:#e2e8f0;">${r["total"]:,.0f}</td>'
            f'<td style="padding:6px 9px;font-family:Share Tech Mono;color:{pc};font-weight:bold;">{sg}${abs(r["pnl"]):,.0f}</td>'
            f'<td style="padding:6px 9px;font-family:Share Tech Mono;color:{pc};">{sg}{abs(r["pnl_pct"]):.2f}%</td>'
            f'<td style="padding:6px 9px;font-family:Share Tech Mono;color:{vc};font-weight:bold;">{sv}{abs(r["vs_init"]):.2f}%</td>'
            f'<td style="padding:6px 9px;color:#00d4ff;">{r["n_pos"]}</td>'
            f'</tr>'
        )
    st.markdown(
        f'<div style="overflow-x:auto;border:1px solid rgba(255,215,0,.15);border-radius:8px;margin-bottom:16px;">'
        f'<table style="width:100%;border-collapse:collapse;font-family:Share Tech Mono;font-size:.75rem;color:#e2e8f0;">'
        f'<thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)


def render():
    state = get_or_init_state()
    teams = state.get("teams", {})

    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;letter-spacing:.12em;'
        'color:#00ff88;margin:0 0 6px;text-shadow:0 0 30px rgba(0,255,136,.4);">'
        '🏠 DASHBOARD — MAM</h1>', unsafe_allow_html=True)

    tape_prices = get_multi_prices(tuple(s for s, _ in _TAPE_SYMBOLS))
    st.markdown(_build_tape(tape_prices), unsafe_allow_html=True)

    if st.session_state.get("force_wizard"):
        st.session_state.pop("force_wizard", None)
        _wizard(state)
        return

    all_ports = []
    for tid, team in teams.items():
        tlabel = "Solo" if tid == "__solo__" else f'{team["emoji"]} {team["name"]}'
        for pid, port in team.get("portfolios", {}).items():
            if port.get("name"):
                all_ports.append({"port":port,"pid":pid,"tid":tid,"team_label":tlabel})

    if not all_ports:
        _wizard(state)
        return

    _, col_btn = st.columns([6, 1])
    with col_btn:
        if st.button("➕ Nouveau", key="btn_new_top", use_container_width=True):
            st.session_state["force_wizard"] = True; st.rerun()

    all_tickers: set[str] = set()
    for item in all_ports:
        all_tickers.update(item["port"].get("holdings", {}).keys())
    live = get_multi_prices(tuple(all_tickers)) if all_tickers else {}

    _comparison_panel(state, live)

    ports_with_pos = [item for item in all_ports if item["port"].get("holdings")]
    if not ports_with_pos:
        _show_empty_ports(all_ports)
        return

    total_cash = total_mkt = total_pnl = total_cost = 0.0
    for item in ports_with_pos:
        port = item["port"]
        total_cash += port.get("cash", 0.0)
        for tk, pos in port.get("holdings", {}).items():
            qty = pos.get("qty", 0); avg = pos.get("avg_price", 0.0)
            curr = live.get(tk, (avg, 0.0))[0]
            total_mkt  += qty * curr; total_cost += qty * avg; total_pnl += qty * (curr - avg)

    total_aum     = total_cash + total_mkt
    total_pnl_pct = total_pnl / total_cost * 100 if total_cost > 0 else 0.0
    pnl_col       = "#00ff88" if total_pnl >= 0 else "#ff3b6b"
    sg            = "+" if total_pnl >= 0 else ""
    kpi = 'background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.15);border-radius:8px;padding:14px 16px;'
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        st.markdown(f'<div style="{kpi}"><div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;letter-spacing:.12em;text-transform:uppercase;">AUM Total</div><div style="font-family:Share Tech Mono;font-size:1.5rem;color:#e2e8f0;">${total_aum:,.0f}</div><div style="font-size:.7rem;color:#475569;">{len(ports_with_pos)} portf. actif(s)</div></div>', unsafe_allow_html=True)
    with c2:
        cp = f"{total_cash/total_aum*100:.1f}%" if total_aum else "—"
        st.markdown(f'<div style="{kpi}"><div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;letter-spacing:.12em;text-transform:uppercase;">Cash</div><div style="font-family:Share Tech Mono;font-size:1.5rem;color:#00d4ff;">${total_cash:,.0f}</div><div style="font-size:.7rem;color:#475569;">{cp} du total</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div style="{kpi}"><div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;letter-spacing:.12em;text-transform:uppercase;">Marché</div><div style="font-family:Share Tech Mono;font-size:1.5rem;color:#e2e8f0;">${total_mkt:,.0f}</div><div style="font-size:.7rem;color:#475569;">positions ouvertes</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div style="{kpi}"><div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;letter-spacing:.12em;text-transform:uppercase;">P&L Global</div><div style="font-family:Share Tech Mono;font-size:1.5rem;color:{pnl_col};">{sg}${abs(total_pnl):,.2f}</div><div style="font-size:.7rem;color:{pnl_col};">{sg}{abs(total_pnl_pct):.2f}%</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section_title("MES PORTEFEUILLES", "📁")

    for item in ports_with_pos:
        port     = item["port"]; tlabel = item["team_label"]
        holdings = port.get("holdings", {}); cash = port.get("cash", 0.0)
        mkt = cost = pnl = 0.0; positions = []
        for tk, pos in holdings.items():
            qty = pos.get("qty",0); avg = pos.get("avg_price",0.0)
            curr, pd_ = live.get(tk,(avg,0.0))
            pos_mkt = qty*curr; pos_cost = qty*avg; pos_pnl = pos_mkt-pos_cost
            mkt+=pos_mkt; cost+=pos_cost; pnl+=pos_pnl
            positions.append({"ticker":tk,"qty":qty,"avg":avg,"curr":curr,"pct_d":pd_,"mkt":pos_mkt,"cost":pos_cost,"pnl":pos_pnl})
        ppct  = pnl/cost*100 if cost>0 else 0.0
        p_col = "#00ff88" if pnl>=0 else "#ff3b6b"; sg2 = "+" if pnl>=0 else ""
        strat_obj = next((s for s in _STRATEGIES if s["id"]==port.get("strategy","")), None)
        types_str = " ".join(_ASSET_CONSTRAINTS.get(t,{}).get("emoji","") for t in port.get("asset_types",[]))
        warns = _check_constraints(port, live)
        st.markdown(
            f'<div style="background:rgba(0,10,25,.6);border:1px solid rgba(0,212,255,.18);border-radius:10px;padding:16px 20px;margin-bottom:12px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
            f'<div><span style="font-family:Rajdhani;font-size:1.1rem;font-weight:700;color:#e2e8f0;">{port.get("emoji","📁")} {port.get("name","—")}</span>'
            f'<span style="font-family:Rajdhani;font-size:.62rem;color:#475569;letter-spacing:.1em;margin-left:8px;">{tlabel}</span>'
            f'<span style="font-size:.85rem;margin-left:6px;">{types_str}</span></div>'
            f'<div style="text-align:right;"><div style="font-family:Share Tech Mono;font-size:.82rem;color:#e2e8f0;">AUM <b>${cash+mkt:,.0f}</b></div>'
            f'<div style="font-family:Share Tech Mono;font-size:.78rem;color:{p_col};">P&L {sg2}${abs(pnl):,.2f} ({sg2}{abs(ppct):.2f}%)</div></div>'
            f'</div>', unsafe_allow_html=True)
        for w in warns:
            st.warning(w)
        col_hdrs = ["TICKER","QTÉ","PX ENTRÉE","PX ACTUEL","VAR 1J","VALEUR","P&L $","P&L %"]
        th = "".join(f'<th style="font-family:Rajdhani;font-size:.63rem;color:#00d4ff;letter-spacing:.08em;text-transform:uppercase;padding:6px 10px;background:rgba(0,212,255,.06);border-bottom:1px solid rgba(0,212,255,.14);">{c}</th>' for c in col_hdrs)
        tbody = ""
        for pos in positions:
            tk=pos["ticker"]; qty=pos["qty"]; avg=pos["avg"]; curr=pos["curr"]; pct_d=pos["pct_d"]; p_v=pos["mkt"]; p_pnl=pos["pnl"]; p_cost=pos["cost"]
            p_pct = p_pnl/p_cost*100 if p_cost>0 else 0.0
            fmt = lambda v: f"${v:,.0f}" if v>=1000 else (f"${v:,.2f}" if v>=1 else f"${v:,.5f}")
            pc  = "#00ff88" if p_pnl>0 else ("#ff3b6b" if p_pnl<0 else "#94a3b8")
            dc  = "#00ff88" if pct_d>0 else ("#ff3b6b" if pct_d<0 else "#94a3b8")
            sgp = "+" if p_pnl>0 else ""; sgd = "+" if pct_d>0 else ""
            arp = "▲" if p_pnl>0 else ("▼" if p_pnl<0 else "▬")
            ard = "▲" if pct_d>0 else ("▼" if pct_d<0 else "▬")
            tbody += (
                f'<tr style="border-bottom:1px solid rgba(255,255,255,.03);">'
                f'<td style="padding:6px 10px;color:#00d4ff;font-weight:bold;font-family:Rajdhani;font-size:.82rem;">{tk}</td>'
                f'<td style="padding:6px 10px;font-family:Share Tech Mono;font-size:.74rem;">{qty:,.4f}</td>'
                f'<td style="padding:6px 10px;color:#7a93b0;font-family:Share Tech Mono;font-size:.74rem;">{fmt(avg)}</td>'
                f'<td style="padding:6px 10px;font-family:Share Tech Mono;font-size:.74rem;">{fmt(curr)}</td>'
                f'<td style="padding:6px 10px;color:{dc};font-family:Share Tech Mono;font-size:.74rem;">{ard} {sgd}{abs(pct_d):.2f}%</td>'
                f'<td style="padding:6px 10px;font-family:Share Tech Mono;font-size:.74rem;">${p_v:,.2f}</td>'
                f'<td style="padding:6px 10px;color:{pc};font-weight:bold;font-family:Share Tech Mono;font-size:.74rem;">{sgp}${abs(p_pnl):,.2f}</td>'
                f'<td style="padding:6px 10px;color:{pc};font-family:Share Tech Mono;font-size:.74rem;">{arp} {sgp}{abs(p_pct):.2f}%</td>'
                f'</tr>'
            )
        st.markdown(f'<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;color:#e2e8f0;"><thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table></div></div>', unsafe_allow_html=True)


def _show_empty_ports(all_ports: list):
    st.markdown("""
    <div style="background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.2);border-radius:12px;padding:20px;text-align:center;margin:16px 0;">
    <div style="font-size:2rem;margin-bottom:8px;">💼</div>
    <div style="font-family:Rajdhani,sans-serif;font-size:1rem;font-weight:700;color:#e2e8f0;letter-spacing:.1em;">PORTEFEUILLES PRÊTS — EN ATTENTE DE POSITIONS</div>
    <div style="font-family:Share Tech Mono,monospace;font-size:.73rem;color:#7a93b0;margin-top:6px;">Allez dans <b style="color:#00d4ff;">Trading Desk</b> pour passer vos premiers ordres.</div>
    </div>""", unsafe_allow_html=True)
