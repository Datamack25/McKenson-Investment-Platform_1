import streamlit as st
from utils.data import load_events, load_assets, get_price

def render():
    # 1. Injection du CSS global (indispensable pour les animations)
    inject_css()

    # 2. Préparation des données du Ticker de prix
    assets_df = load_assets()
    strip_data = []
    for _, asset in assets_df.iterrows():
        symbol = asset["ticker"]
        price = get_price(symbol)
        # On peut calculer ou simuler un pourcentage de variation
        strip_data.append({
            "ticker": symbol,
            "price": price,
            "pct": 0.12 # Exemple : +0.12%
        })
    
    # 3. Rendu du bandeau des prix (tout en haut)
    render_ticker_strip(strip_data)

    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;'
        'letter-spacing:0.1em;color:#ff3b6b;margin:15px 0 5px;">📰 MARKET EVENTS</h1>',
        unsafe_allow_html=True,
    )

    # 4. Chargement et affichage du bandeau de News défilantes
    events_df = load_events()
    active_events = events_df[events_df["active"] == True] if "active" in events_df.columns else events_df
    
    render_news_banner(active_events)

    # 5. Simulateur d'impact (le reste de ton interface)
    st.write("") # Espacement
    section_title("PRICE IMPACT SIMULATOR")
    
    col1, col2 = st.columns(2)
    with col1:
        sim_ticker = st.selectbox("Select Asset", assets_df["ticker"].tolist(), key="sim_t")
        sim_move = st.slider("Hypothetical Shock (%)", -30.0, 30.0, -10.0, 0.5)
    
    with col2:
        spot = get_price(sim_ticker)
        if spot:
            new_price = spot * (1 + sim_move / 100)
            st.metric("Current", f"{spot:,.4f}")
            st.metric("After Shock", f"{new_price:,.4f}", delta=f"{sim_move:+.1f}%")

    # 6. Historique complet
    section_title("ALL EVENTS LOG")
    st.dataframe(events_df, use_container_width=True, hide_index=True)
