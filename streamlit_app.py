"""E-Presso: current-data dashboard, audited joins, and constrained analytical assistant."""
from pathlib import Path
import hashlib
import json
import io
import zipfile
import pandas as pd
import plotly.express as px
import streamlit as st
import analytics
import data_model as dm
import business_tools as bt
import agent

st.set_page_config(page_title='E-Presso · Coffee & clarity',page_icon='☕',layout='wide')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Dancing+Script:wght@600;700&display=swap');

.stApp {
    background: #F7F2E7;
    color: #293D30;
    font-family: 'DM Sans', sans-serif;
}

[data-testid=stSidebar] {
    background-color: #E8EDDF;
    background-image:
        linear-gradient(#49644855 50%, transparent 50%),
        linear-gradient(90deg, #49644855 50%, transparent 50%);
    background-size: 28px 28px;
}

h1, h2, h3 {
    color: #294334 !important;
    font-family: 'Dancing Script', cursive !important;
}

[data-testid=stMetric] {
    background: #FFFCF4;
    border: 1px solid #C5D0B9;
    border-radius: 16px;
    padding: 20px;
}

[data-testid=stMetricValue] {
    color: #294334;
}

.stButton>button {
    background: #496448;
    color: white;
    border: 0;
    border-radius: 10px;
}

.hero {
    background: linear-gradient(120deg, #294334, #526B4D);
    border: 4px solid #D5B875;
    padding: 28px 32px;
    border-radius: 18px;
    margin-bottom: 22px;
    text-align: center;
    color: #FFF9E9;
    box-shadow: 0 4px 10px #263D3220;
}

.hero h1 {
    color: #FFF4D9 !important;
    font-size: 48px;
    margin: 8px 0;
}

.hero p {
    color: #F1E5C9;
    margin: 6px 0;
    font-size: 16px;
}

.hero .eyebrow {
    color: #E5C995;
    letter-spacing: .15em;
    font-size: 12px;
    font-weight: 700;
}
</style>
''', unsafe_allow_html=True)

st.image(
    Path(__file__).parent / "assets" / "e-presso camp.png",
    use_container_width=True
)

@st.cache_data(show_spinner=False)
def cached_sources(sources):
    # The content bytes, not just filenames, are included in Streamlit's cache key.
    return dm.load_sources(sources)

with st.sidebar:
    st.header('Your coffee, your data')
    st.caption('Starts with the supplied E-Presso data. Uploads replace matching tables immediately.')
    uploads=st.file_uploader('Update data',type=['csv','tsv','txt','xlsx','xlsm','accdb','mdb'],accept_multiple_files=True,
        help='Access: Sales, Products, Categories tables. CSV: one recognized table. Excel: named table sheets, or survey sheets.')
    st.caption('Remove uploaded files to restore the repository data.')
try:
    original=dm.repository_sources(Path(__file__).parent/'data')
    sources=original+[(f.name,f.getvalue()) for f in uploads]
    tables,fingerprint=cached_sources(sources)
    sales,merge_reports=dm.prepare_model(tables)
except Exception as exc:
    st.error(f'Could not prepare the data: {exc}')
    st.info('Check the required table names and columns. Access files require mdbtools on the host (packages.txt).')
    st.stop()

st.session_state.setdefault('n_questions',0)
st.session_state.setdefault('history',[])
if st.session_state.get('dataset')!=fingerprint:
    st.session_state.history=[]
    st.session_state.dataset=fingerprint

filters={}
with st.sidebar:
    st.subheader('Analysis filters')
    for label,col in [('Year','Year'),('Sales channel','Channel'),('Store','Store ID'),('Category','Category'),('Product','Product')]:
        options=sorted(sales[col].dropna().unique().tolist(),key=str)
        selected=st.multiselect(label,options,key=col+'_'+fingerprint[:10])
        if selected:filters[col]=selected
    st.caption('Empty selection = all values. Every dashboard result and default assistant answer uses these filters.')
filtered,filter_error=bt.scoped(sales,filters)
if filter_error:st.error(filter_error);st.stop()
scope=agent.scope_text(filters)
st.caption('Scope: '+scope)
st.caption('Active data: '+('uploaded updates' if uploads else 'repository originals')+' · snapshot '+fingerprint[:10])

def styled(fig):
    fig.update_layout(
        paper_bgcolor='#F7F2E7',
        plot_bgcolor='#FFFCF4',
        font={
            'family': 'DM Sans',
            'color': '#293D30'
        },
        colorway=[
            '#496448',
            '#A6B28A',
            '#C47745',
            '#D5B875',
            '#263D32'
        ],
        margin=dict(t=28, b=40, l=10, r=10),
        height=370
    )

    st.plotly_chart(fig, width='stretch')

def breakdown(group):
    r=bt.revenue_breakdown(sales,group,filters)
    return pd.DataFrame(list(r.value['revenue'].items()),columns=[group,'Revenue'])

dashboard,assistant,profile,validation=st.tabs(['Dashboard','Analytical assistant','Data & quality','Validation lab'])
with dashboard:
    summary=bt.revenue_summary(sales,filters).value
    cols=st.columns(4)
    cols[0].metric('Revenue',f"${summary['revenue']:,.2f}")
    cols[1].metric('Sales records',f"{summary['sales_records']:,}")
    avg=summary['average_revenue_per_record']
    cols[2].metric('Average / sales record','—' if avg is None else f'${avg:,.2f}')
    cols[3].metric('Stores represented',summary['stores'])
    st.caption('Revenue is the sum of the source Revenue column. A sales record is not necessarily a customer order. Revenue is not profit.')
    if filtered.empty:st.info('No records match this filter combination.')
    else:
        st.subheader('How revenue is brewing')
        monthly=breakdown('Month').sort_values('Month')
        styled(px.line(monthly,x='Month',y='Revenue',markers=True,labels={'Revenue':'Revenue ($)'},title='Monthly revenue'))
        left,right=st.columns(2)
        with left:
            cat=breakdown('Category').sort_values('Revenue')
            styled(px.bar(cat,x='Revenue',y='Category',orientation='h',labels={'Revenue':'Revenue ($)'},title='Revenue by category'))
        with right:
            channel=breakdown('Channel')
            styled(px.bar(channel,x='Channel',y='Revenue',labels={'Revenue':'Revenue ($)'},title='Revenue by sales channel'))
        store=breakdown('Store').sort_values('Revenue',ascending=False)
        styled(px.bar(store,x='Store',y='Revenue',labels={'Revenue':'Revenue ($)'},title='Revenue by store'))
        if not cat.empty:
            top=cat.iloc[-1]
            st.info(f"Highest revenue category in this scope: {top.Category} (${top.Revenue:,.2f}). This does not establish profitability or explain the cause of performance.")
    st.download_button('Download filtered sales',filtered.to_csv(index=False).encode(),'epresso_filtered_sales.csv','text/csv')

with assistant:
    try:key=st.secrets.get('OPENAI_API_KEY','');model=st.secrets.get('OPENAI_MODEL','gpt-4.1-mini')
    except (FileNotFoundError,st.errors.StreamlitSecretNotFoundError):key='';model='gpt-4.1-mini'
    mode='rules'
    if key:
        mode='llm' if st.toggle('Use live language-model tool selection',value=True) else 'rules'
    st.caption('Mode: '+('live model tool selection with rules-based fallback' if mode=='llm' else 'rules-based assistant (Option B; no API key needed)'))
    st.write('Try: “What is total revenue?”, “Revenue by channel”, “Monthly revenue”, “Which stores declined?”, or “Are there missing values?” Name a year or store ID to override that filter.')
    st.caption(f'{st.session_state.n_questions} of 15 questions used this session. Responses retain their original scope and snapshot; data updates clear old answers.')
    for item in st.session_state.history:
        with st.chat_message('user'):st.write(item['question'])
        with st.chat_message('assistant'):
            a=item['answer'];st.markdown('**Scope:** '+a['scope'])
            st.caption('Snapshot '+item['snapshot']+' · '+a['mode'])
            if a['notice']:st.info(a['notice'])
            st.markdown('**Findings**\n\n'+a['findings'])
            st.markdown('**Interpretation**\n\n'+a['interpretation'])
            st.markdown('**Next steps**\n\n'+a['next_steps'])
            with st.expander('Tool-call log: function, arguments and raw result'):st.json(a['tool_log'])
    if st.session_state.n_questions>=15:st.warning('Session question limit reached. Start a new browser session for more questions.')
    question=st.chat_input('Ask about the current E-Presso data',disabled=st.session_state.n_questions>=15)
    if question:
        with st.spinner('Brewing your answer…'):
            answer=agent.answer_question(question,sales,mode,filters,key,model)
        st.session_state.n_questions+=1
        st.session_state.history.append({'question':question,'answer':answer,'snapshot':fingerprint[:10]})
        st.rerun()
    if st.session_state.history:
        st.download_button('Download assistant evidence',json.dumps(st.session_state.history,indent=2,default=str),'assistant_evidence.json','application/json')

with profile:
    st.subheader('Table grain & source profile')
    grains={'Sales':'One monthly store/product/category revenue record per Sales ID in the supplied file; not a customer transaction.',
        'Products':'One product per Product ID.','Categories':'One category per Category ID.',
        'Stores':'One location/channel per ID. Website is a nonphysical store.',
        'Survey':'One store-year survey result per Survey ID. Satisfaction: 0–5; Interest: 0–100. Not joined to sales records.',}
    for name,table in tables.items():
        with st.expander(f'{name} · {len(table):,} rows'):
            st.write(grains.get(name,'Survey source sheet; inspect its headers and units before interpretation. Kept separate from sales to prevent fan-out.'))
            st.dataframe(table.head(50).astype('string'),width='stretch')
            p=analytics.profile_table(table)
            st.write({'rows':p['rows'],'columns':p['columns'],'duplicate_rows':p['duplicate_rows']})
            st.dataframe(p['missing'],width='stretch')
            st.dataframe(p['dtypes'],width='stretch')
            if name in dm.KEYS:st.json(analytics.check_unique_ids(table,dm.KEYS[name]))
    st.subheader('Audited many-to-one joins')
    st.dataframe(pd.DataFrame(merge_reports),width='stretch')
    st.caption('All sales rows are retained. Duplicate or blank dimension keys stop analysis. Unmatched keys remain visible as Unknown; their revenue is retained.')
    st.subheader('Current model quality')

    quality = bt.quality(sales, filters).to_dict()
    quality_values = quality.get('value', {})

    missing = quality_values.get('missing', {})

    if missing:
        st.markdown('**Missing values in the prepared sales model**')

        missing_df = pd.DataFrame([
            {'Field': field, 'Missing records': count}
            for field, count in missing.items()
        ])

        st.dataframe(
            missing_df,
            hide_index=True,
            width='stretch'
        )

        st.caption(
            'Missing City, State, and PostalCode values are expected '
            'for website sales, which do not have a physical store location.'
        )
    else:
        st.success('No missing values detected in the reported fields.')

    st.caption(
        f"Scope: {quality.get('scope', {}).get('filters', 'All data')} "
        f"· Records analyzed: {quality.get('rows_used', 0):,}"
    )

    st.info(
        'Missing dates are excluded from time charts but remain in total revenue. '
        'Missing or nonnumeric revenue is excluded and reported. '
        'Negative revenue is retained and flagged; confirm whether it represents a return. '
        'Revenue is not profit.'
    )

with validation:
    st.subheader('Reconciliation export')
    st.write('These values are calculated from the current data and filters. Compare them with the same scope in Power BI. Power BI results are not available in this repository.')
    metrics=[{'Metric':'Total revenue','App result':bt.revenue_summary(sales,filters).value['revenue'],'Power BI result':'Not supplied'}]
    for group in ['Channel','Year','Month']:
        r=bt.revenue_breakdown(sales,group,filters)
        metrics += [{'Metric':f'{group}: {k}','App result':v,'Power BI result':'Not supplied'} for k,v in r.value['revenue'].items()]
    metrics.append({'Metric':'Sales records','App result':len(filtered),'Power BI result':'Not supplied'})
    validation_df=pd.DataFrame(metrics)
    st.dataframe(validation_df,width='stretch')
    st.download_button('Download comparison table',validation_df.to_csv(index=False).encode(),'power_bi_comparison.csv','text/csv')
    st.subheader('The $1,000 update test')
    st.write('Download a modified Sales CSV, predict the result, then upload it using Update data in the sidebar. This button only generates a copy. It does not modify the active data.')
    valid=tables['Sales'].copy()
    eligible=valid[pd.to_numeric(valid.Revenue,errors='coerce').notna()]
    if not eligible.empty:
        chosen = st.selectbox('Sales ID to change', eligible['Sales ID'].tolist())
        idx = valid.index[valid['Sales ID'] == chosen][0]
        old = float(valid.at[idx, 'Revenue'])
        original_total = float(pd.to_numeric(valid['Revenue'], errors='coerce').sum())

        valid.at[idx, 'Revenue'] = old + 1000

        test_details = pd.DataFrame([
            {'Test detail': 'Sales ID', 'Value': str(chosen)},
            {'Test detail': 'Date', 'Value': pd.to_datetime(valid.at[idx, 'Date']).strftime('%B %d, %Y')},
            {'Test detail': 'Store ID', 'Value': str(valid.at[idx, 'Store ID'])},
            {'Test detail': 'Original revenue', 'Value': f'${old:,.2f}'},
            {'Test detail': 'Modified revenue', 'Value': f'${old + 1000:,.2f}'},
            {'Test detail': 'Expected increase', 'Value': '+$1,000.00'},
            {'Test detail': 'Predicted unfiltered total', 'Value': f'${original_total + 1000:,.2f}'}
        ])

        st.dataframe(test_details, hide_index=True, width='stretch')

        st.write(
            'Prediction: the row’s store, year, month, category, product and channel '
            'totals rise by $1,000. Scopes excluding the row remain unchanged; '
            'record count and dimension tables remain unchanged. After upload, '
            'ask the same total-revenue question and inspect the chart points. '
            'Remove the upload to restore originals.'
        )

        st.download_button(
            'Download modified Sales CSV',
            valid.to_csv(index=False).encode(),
            'Sales_modified_plus_1000.csv',
            'text/csv'
        )
    st.subheader('Submission status')
    st.write('Automated evidence and defense notes are included in the project evidence folder. Still required from the team: actual Power BI comparisons, screenshots from the deployed app, confirmation of contributions and reflection, and commits by each teammate. A local test is not proof that the hosted app has been redeployed.')
