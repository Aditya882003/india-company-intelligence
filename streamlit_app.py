from __future__ import annotations

import sqlite3
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / 'data' / 'processed' / 'company_intelligence.db'

st.set_page_config(page_title='India Company Intelligence', page_icon='🇮🇳', layout='wide', initial_sidebar_state='expanded')

CSS = """
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
.metric-card {background: white; border: 1px solid #E2E8F0; border-radius: 14px; padding: 14px 16px;}
.small-muted {color:#64748B; font-size:0.86rem;}
.signal-high {color:#B91C1C; font-weight:700;}
.signal-medium {color:#B45309; font-weight:700;}
.signal-low {color:#047857; font-weight:700;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def q(sql: str, params=()) -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql_query(sql, conn, params=params)


@st.cache_data(ttl=900)
def load_all() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    companies = q('SELECT * FROM company_master')
    prices = q('SELECT * FROM price_daily ORDER BY trade_date')
    financials = q('SELECT * FROM financial_snapshot ORDER BY as_of_date DESC')
    news = q('SELECT * FROM news_articles ORDER BY published_at DESC')
    logs = q('SELECT * FROM etl_run_log ORDER BY run_ts_utc DESC')
    return companies, prices, financials, news, logs


def attention_score(companies: pd.DataFrame, prices: pd.DataFrame, financials: pd.DataFrame, news: pd.DataFrame) -> pd.DataFrame:
    latest = prices.sort_values('trade_date').groupby('ticker').tail(1).copy()
    f = financials.sort_values('as_of_date').groupby('ticker').tail(1).copy()
    out = latest.merge(companies[['ticker','company_name','sector','industry']], on='ticker', how='left')
    out = out.merge(f[['ticker','revenue_growth_pct','profit_growth_pct','net_margin_pct','debt_equity','roe_pct']], on='ticker', how='left')
    out['financial_pressure_score'] = (
        (out['revenue_growth_pct'] < 0).astype(int)
        + (out['profit_growth_pct'] < 0).astype(int)
        + ((out['debt_equity'] > 2).fillna(False)).astype(int)
    )
    now = pd.Timestamp.now(tz='UTC')
    news2 = news.copy()
    if not news2.empty:
        news2['published_at_dt'] = pd.to_datetime(news2['published_at'], errors='coerce', utc=True)
        recent = news2[news2['published_at_dt'] >= now - pd.Timedelta(days=7)].groupby('ticker').size().rename('news_7d')
        prior = news2[(news2['published_at_dt'] >= now - pd.Timedelta(days=14)) & (news2['published_at_dt'] < now - pd.Timedelta(days=7))].groupby('ticker').size().rename('news_prev_7d')
        n = pd.concat([recent, prior], axis=1).fillna(0).reset_index()
    else:
        n = pd.DataFrame(columns=['ticker','news_7d','news_prev_7d'])
    out = out.merge(n, on='ticker', how='left').fillna({'news_7d':0,'news_prev_7d':0})
    out['news_spike_score'] = ((out['news_7d'] >= 3) & (out['news_7d'] >= out['news_prev_7d'].replace(0, 1) * 1.5)).astype(int)
    out['attention_score'] = out['market_score'].fillna(0) + out['financial_pressure_score'] + out['news_spike_score']
    out['attention_flag'] = np.select([out['attention_score'] >= 5, out['attention_score'] >= 3], ['HIGH','MEDIUM'], default='LOW')
    out['constructive_signal'] = ((out['return_30d'] > 5) & (out['profit_growth_pct'] > 0)).fillna(False)
    return out.sort_values(['attention_score','return_30d'], ascending=[False, True])


def pct(x):
    return '—' if pd.isna(x) else f'{x:.1f}%'


def money_ind(x):
    if pd.isna(x): return '—'
    x = float(x)
    if abs(x) >= 1e12: return f'₹{x/1e12:.2f}T'
    if abs(x) >= 1e9: return f'₹{x/1e9:.1f}B'
    if abs(x) >= 1e6: return f'₹{x/1e6:.1f}M'
    return f'₹{x:,.0f}'


def main():
    if not DB_PATH.exists():
        st.error('The data package has not been initialized yet.')
        st.code('python etl/make_demo_data.py\npython etl/run_pipeline.py --period 1y')
        st.stop()
    companies, prices, financials, news, logs = load_all()
    scored = attention_score(companies, prices, financials, news)

    latest_date = prices['trade_date'].max() if not prices.empty else '—'
    last_run = logs.iloc[0] if not logs.empty else None
    demo = (not financials.empty and financials['source'].fillna('').str.contains('DEMO').all())

    st.title('🇮🇳 India Company Intelligence')
    st.caption('Daily research monitor for Indian listed companies — market signals + financial context + secondary research + news attention.')

    if demo:
        st.warning('The dashboard is currently using seed/demo data. Deploy the repository and run the GitHub Actions refresh to replace it with live public-source data.')
    if last_run is not None:
        st.caption(f"Latest ETL: {last_run['status']} • {last_run['run_ts_utc']} • Market date: {latest_date}")

    st.sidebar.header('Universe filters')
    sectors = sorted(companies['sector'].unique())
    sector_pick = st.sidebar.multiselect('Sector', sectors, default=sectors)
    names = companies.loc[companies['sector'].isin(sector_pick), 'company_name'].sort_values().tolist()
    company_pick = st.sidebar.multiselect('Companies', names)
    min_score = st.sidebar.slider('Minimum attention score', 0, 8, 0)

    universe = scored[scored['sector'].isin(sector_pick)].copy()
    if company_pick:
        universe = universe[universe['company_name'].isin(company_pick)]
    universe = universe[universe['attention_score'] >= min_score]
    if universe.empty:
        st.info('No companies match the selected filters.')
        st.stop()

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric('Companies', len(universe))
    k2.metric('High attention', int((universe.attention_flag == 'HIGH').sum()))
    k3.metric('Median 30D return', pct(universe.return_30d.median()))
    k4.metric('Avg. volatility', pct(universe.volatility_30d.mean()))
    k5.metric('News headlines / 7D', int(universe.news_7d.sum()))

    tab1, tab2, tab3, tab4, tab5 = st.tabs(['Executive Pulse','Company Explorer','Sector View','Research & News','Data & SQL'])

    with tab1:
        st.subheader('Where should an analyst look first?')
        st.caption('Attention score is a triage mechanism, not an investment rating.')
        left, right = st.columns([1.1, 1])
        with left:
            plot = universe.sort_values('attention_score', ascending=True)
            fig = px.bar(plot, x='attention_score', y='company_name', orientation='h', color='attention_flag', text='attention_score', title='Company attention score')
            fig.update_layout(height=620, xaxis_title='Score', yaxis_title=None, legend_title='Flag')
            st.plotly_chart(fig, use_container_width=True)
        with right:
            fig2 = px.scatter(universe, x='volatility_30d', y='return_30d', size='attention_score', color='sector', hover_name='company_name', title='Risk / momentum map')
            fig2.add_vline(x=25, line_dash='dot')
            fig2.add_hline(y=0, line_dash='dot')
            fig2.update_layout(height=620, xaxis_title='30D annualised volatility (%)', yaxis_title='30D return (%)')
            st.plotly_chart(fig2, use_container_width=True)
        table = universe[['company_name','sector','return_30d','volatility_30d','max_drawdown_90d','revenue_growth_pct','profit_growth_pct','news_7d','attention_score','attention_flag']].copy()
        table.columns = ['Company','Sector','30D Return %','30D Volatility %','90D Drawdown %','Revenue Growth %','Profit Growth %','News / 7D','Attention','Flag']
        st.dataframe(table, use_container_width=True, hide_index=True)
        st.download_button('Download company watchlist CSV', table.to_csv(index=False).encode('utf-8'), 'india_company_watchlist.csv', 'text/csv')

    with tab2:
        company = st.selectbox('Company', universe['company_name'].tolist())
        c = universe[universe['company_name'] == company].iloc[0]
        r = companies[companies['ticker'] == c.ticker].iloc[0]
        p = prices[prices.ticker == c.ticker].sort_values('trade_date').copy()
        f = financials[financials.ticker == c.ticker].sort_values('as_of_date', ascending=False)
        nw = news[news.ticker == c.ticker].head(12).copy()
        a,b,c1,d = st.columns(4)
        a.metric('Latest price', f"₹{p.iloc[-1].close:,.2f}")
        b.metric('30D return', pct(c.return_30d))
        c1.metric('Attention', f"{int(c.attention_score)} / {c.attention_flag}")
        d.metric('Profit growth', pct(c.profit_growth_pct))
        st.markdown(f"**{company}** · {r['sector']} · {r['industry']}")
        st.write(r['business_summary'])
        st.info(f"Monitor: {r['monitoring_theme']}")
        fig = px.line(p, x='trade_date', y='close', title='Price history')
        fig.update_layout(yaxis_title='Price (₹)', xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
        x,y,z,w = st.columns(4)
        x.metric('Revenue', money_ind(f.iloc[0]['revenue']) if not f.empty else '—')
        y.metric('Revenue growth', pct(f.iloc[0]['revenue_growth_pct']) if not f.empty else '—')
        z.metric('Net margin', pct(f.iloc[0]['net_margin_pct']) if not f.empty else '—')
        w.metric('ROE', pct(f.iloc[0]['roe_pct']) if not f.empty else '—')
        if not nw.empty:
            st.subheader('Latest research/news headlines')
            for _, nr in nw.iterrows():
                title = nr['title']
                link = nr.get('link') or '#'
                st.markdown(f"- [{title}]({link})")
        st.markdown(f"**Primary research page:** [{r['source_url']}]({r['source_url']})")

    with tab3:
        sector = universe.groupby('sector', as_index=False).agg(
            companies=('ticker','count'), avg_return_30d=('return_30d','mean'), median_return_30d=('return_30d','median'),
            avg_volatility_30d=('volatility_30d','mean'), high_attention=('attention_flag', lambda s: (s=='HIGH').sum()),
            total_news_7d=('news_7d','sum')
        ).sort_values('avg_return_30d', ascending=False)
        st.dataframe(sector.round(2), use_container_width=True, hide_index=True)
        col1,col2 = st.columns(2)
        with col1:
            fig = px.bar(sector.sort_values('avg_return_30d'), x='avg_return_30d', y='sector', orientation='h', title='Average 30D return by sector')
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.scatter(sector, x='avg_volatility_30d', y='avg_return_30d', size='companies', text='sector', title='Sector risk / return')
            fig.update_traces(textposition='top center')
            st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.subheader('Secondary research layer')
        st.caption('Company descriptions and monitoring themes are structured from company/IR materials; the dashboard links to primary sources for verification.')
        research = companies[companies.sector.isin(sector_pick)][['company_name','sector','industry','peer_group','monitoring_theme','source_url']].copy()
        st.dataframe(research, use_container_width=True, hide_index=True)
        st.download_button('Download research universe CSV', research.to_csv(index=False).encode('utf-8'), 'india_company_research.csv', 'text/csv')
        st.subheader('Recent headlines across the universe')
        nw = news[news.ticker.isin(universe.ticker)].copy()
        if nw.empty:
            st.info('No headlines are stored yet. Run the ETL with news enabled.')
        else:
            nw = nw.merge(companies[['ticker','company_name','sector']], on='ticker', how='left').head(40)
            st.dataframe(nw[['published_at','company_name','sector','publisher','title','link']], use_container_width=True, hide_index=True, column_config={'link': st.column_config.LinkColumn('Source')})

    with tab5:
        st.subheader('Operational data & SQL layer')
        log = logs.head(10).copy()
        st.dataframe(log, use_container_width=True, hide_index=True)
        st.markdown('**Tables:** `company_master`, `price_daily`, `financial_snapshot`, `news_articles`, `etl_run_log`')
        st.markdown('The repository includes reusable SQL in `sql/analysis_queries.sql` for company screening, sector comparison, negative-momentum/weak-growth screening and news activity.')
        st.download_button('Download latest price data', prices.to_csv(index=False).encode('utf-8'), 'price_daily.csv', 'text/csv')
        st.download_button('Download latest financial data', financials.to_csv(index=False).encode('utf-8'), 'financial_snapshot.csv', 'text/csv')

    st.markdown('---')
    st.caption('For research and education. Market/financial fields are public-source analytics and may lag or differ from exchange/issuer filings. Headline metadata is not independently verified. Not investment advice.')


if __name__ == '__main__':
    main()
