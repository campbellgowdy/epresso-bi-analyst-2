"""Fixed analytical tool dispatcher. No model-written code or SQL is executed."""
import json
import re
import urllib.request
import analytics
import business_tools as bt

TOOLS={
 'revenue_summary':{'fn':bt.revenue_summary,'params':{'filters'}},
 'revenue_breakdown':{'fn':bt.revenue_breakdown,'params':{'group','filters'}},
 'compare_years':{'fn':bt.compare_years,'params':{'earlier','later','filters'}},
 'quality':{'fn':bt.quality,'params':{'filters'}},
 # Kept for the original hand-checkable test suite.
 'get_total':{'fn':analytics.get_total,'params':{'value_col','filters'}},
 'group_total':{'fn':analytics.group_total,'params':{'value_col','group_col','filters'}},
 'data_quality_report':{'fn':analytics.data_quality_report,'params':set()},
}
PUBLIC_TOOLS=['revenue_summary','revenue_breakdown','compare_years','quality']
UNSUPPORTED='I cannot answer that from the available data. I can calculate revenue totals, revenue by year/month/channel/store/category/product, store changes between years, and data quality. Costs are needed for profit; causal evidence is needed to explain why a change happened.'

def run_tool(name,args,df,log):
    try:
        if name not in TOOLS: result=analytics._error(name,f'Unknown tool: {name}')
        elif set(args)-TOOLS[name]['params']: result=analytics._error(name,'Unexpected argument(s).')
        else: result=TOOLS[name]['fn'](df,**args)
    except (TypeError,ValueError,KeyError) as exc:
        result=analytics._error(name,f'Invalid analytical request: {exc}')
    log.append({'tool':name,'arguments':args,'result':result.to_dict()})
    return result

def scope_text(filters):
    if not filters:return 'All stores, all years, all channels, all categories and products'
    return '; '.join(f'{k}: {v}' for k,v in filters.items())+'; other dimensions: all'

def rules_router(question,df,filters=None):
    q=question.lower(); scope=dict(filters or {})
    if not {'Revenue','Year','Category','Product'}.issubset(df.columns): return None
    if any(w in q for w in ['profit','margin','why','cause','caused','should we','recommend','forecast','predict','weather']):return None
    years=sorted(set(int(y) for y in re.findall(r'\b(?:19|20)\d{2}\b',q)))
    for y in years:
        if y not in set(df.Year.dropna().astype(int)):return 'revenue_summary',{'filters':{**scope,'Year':y}}
    stores=re.findall(r'\bsh\d+\b',q)
    if stores:scope['Store ID']=[s.upper() for s in stores]
    elif re.search(r'\bstore\s+(?:named\s+)?[a-z0-9]+',q) and not any(w in q for w in ['by store','store revenue','store type','store declined','store had','store has','store changes']):
        # Do not silently ignore a requested, unrecognized store.
        return 'revenue_summary',{'filters':{**scope,'Store ID':re.search(r'\bstore\s+(?:named\s+)?([a-z0-9]+)',q).group(1)}}
    city_matches=[str(v) for v in df['City'].dropna().unique() if re.search(r'(?<!\w)'+re.escape(str(v).lower())+r'(?!\w)',q)] if 'City' in df else []
    if city_matches:scope['Store ID']=df.loc[df.City.isin(city_matches),'Store ID'].unique().tolist()
    if 'website' in q and not any(w in q for w in ['by channel','compare','versus',' vs ','both']):scope['Channel']='Website'
    if any(w in q for w in ['brick','physical']) and not any(w in q for w in ['by channel','compare','versus',' vs ','both']):scope['Channel']='Brick & Mortar'
    for col in ['Category','Product']:
        matches=[str(v) for v in df[col].dropna().unique() if re.search(r'(?<!\w)'+re.escape(str(v).lower())+r'(?!\w)',q)]
        if matches:scope[col]=matches
    # Data-quality questions must not be mistaken for an unknown city (e.g. 'in the sales data').
    if any(w in q for w in ['missing','duplicate','quality','blank','null']):return 'quality',{'filters':scope}
    if re.search(r'\bin\s+[a-z]',q) and not city_matches and not any(w in q for w in ['all','website','brick']) and not any(str(v).lower() in q for c in ['Category','Product'] for v in df[c].dropna().unique()): return None
    if re.search(r'for (?:category|product) ',q) and not any(c in scope for c in ['Category','Product']): return None
    if any(w in q for w in ['declin','growth','grew','change','compare years','year over year','year-over-year']):
        available=sorted(df.Year.dropna().astype(int).unique())
        pair=years if len(years)==2 else available[-2:] if len(years)==0 else []
        if len(pair)!=2:return None
        return 'compare_years',{'earlier':int(pair[0]),'later':int(pair[1]),'filters':scope}
    if years:scope['Year']=years if len(years)>1 else years[0]
    if any(w in q for w in ['missing','duplicate','quality','blank']):return 'quality',{'filters':scope}
    if any(w in q for w in ['revenue','sales','earning']):
        for words,group in [(['monthly','by month','trend'],'Month'),(['by year','annual'],'Year'),
             (['by category','top category','categories'],'Category'),(['by product','top product'],'Product'),
             (['channel','store type','website versus','website vs'],'Channel'),(['by store','top store','which store','stores'],'Store')]:
            if any(w in q for w in words):return 'revenue_breakdown',{'group':group,'filters':scope}
        return 'revenue_summary',{'filters':scope}
    return None

def llm_router(question,df,filters,api_key,model='gpt-4.1-mini'):
    """Optional live tool selection. Only schema-enumerated loaded values are allowed."""
    filter_props={col:{'type':'array','items':{'enum':[int(x) if col=='Year' else str(x) for x in df[col].dropna().unique()]}} for col in bt.FILTERS}
    tools=[]
    for name in PUBLIC_TOOLS:
        props={'filters':{'type':'object','properties':filter_props,'additionalProperties':False}}
        required=[]
        if name=='revenue_breakdown':props['group']={'type':'string','enum':sorted(bt.GROUPS)};required=['group']
        if name=='compare_years':
            for col in ['earlier','later']:props[col]={'type':'integer','enum':sorted(df.Year.dropna().astype(int).unique().tolist())}
            required=['earlier','later']
        tools.append({'type':'function','function':{'name':name,'description':bt.__dict__[name if name!='quality' else 'quality'].__doc__ or name,
            'parameters':{'type':'object','properties':props,'required':required,'additionalProperties':False}}})
    payload={'model':model,'temperature':0,'tools':tools,'tool_choice':'auto','messages':[
       {'role':'system','content':'Select only an approved tool. Use these explicit sidebar filters unless the user names another scope: '+json.dumps(filters)+'. Refuse profit, causation, forecasts and unsupported requests. Do not infer missing costs. Never invent a store/year. Do not write code. For store decline compare the two requested years, or the latest two available.'},
       {'role':'user','content':question}]}
    req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=25) as response:data=json.load(response)
    calls=data['choices'][0]['message'].get('tool_calls',[])
    if not calls:return None
    if len(calls)!=1:raise ValueError('Exactly one tool must be selected.')
    call=calls[0]['function'];args=json.loads(call['arguments'])
    if call['name'] not in PUBLIC_TOOLS:raise ValueError('Tool is not approved.')
    args['filters']={**filters,**args.get('filters',{})}
    return call['name'],args

def format_findings(result,question=""):
    if result.error:return 'The request could not be completed: '+result.error
    if result.rows_used==0:return 'No usable records match this scope. A zero or empty result does not establish that business activity was zero.'
    if result.tool=='revenue_summary':
        v=result.value
        average='Unavailable' if v['average_revenue_per_record'] is None else f"${v['average_revenue_per_record']:,.2f}"
        return f"Revenue: ${v['revenue']:,.2f}. Sales records: {v['sales_records']:,}. Average revenue per valid sales record: {average}. Stores represented: {v['stores']}."
    if result.tool=='revenue_breakdown':return '\n'.join(f'- {k}: ${v:,.2f}' for k,v in sorted(result.value['revenue'].items(),key=lambda x:x[1],reverse=True))
    if result.tool=='compare_years':
        rows=result.value['stores']; q=question.lower()
        if any(w in q for w in ['declin','fall','fell','decreas']):
            selected=[r for r in rows if r['change'] is not None and r['change']<0]
            lines=['Stores with a recorded revenue decline:' if selected else 'No comparable store declined in the selected periods.']
        elif any(w in q for w in ['growth','grew','increas']):
            selected=[r for r in rows if r['change'] is not None and r['change']>0]
            lines=['Stores with recorded revenue growth:' if selected else 'No comparable store grew in the selected periods.']
        else:
            selected=[r for r in rows if r['change'] is not None]
            lines=['Recorded revenue changes by comparable store:']
        for r in selected:lines.append(f"- {r['store']}: ${r['earlier_revenue']:,.2f} → ${r['later_revenue']:,.2f}; change ${r['change']:,.2f}.")
        if any(r['change'] is None for r in rows):lines.append('Some stores lack a period and cannot be classified as declining or growing.')
        return '\n'.join(lines)
    return json.dumps(result.value,indent=2)

def answer_question(question,df,mode='rules',filters=None,api_key=None,model='gpt-4.1-mini'):
    filters=filters or {};log=[];notice='';used='rules-based'
    # Always guard unsupported judgments before any provider call.
    guarded=any(w in question.lower() for w in ['profit','margin','why','cause','forecast','predict','should we'])
    if guarded:routed=None
    elif mode=='llm' and api_key:
        try:routed=llm_router(question,df,filters,api_key,model);used='live model tool selection'
        except Exception:
            routed=rules_router(question,df,filters);notice='The model service was unavailable. Switched to the rules-based assistant.'
    else:routed=rules_router(question,df,filters)
    if routed is None:return {'scope':scope_text(filters),'findings':UNSUPPORTED,'interpretation':'The available data does not support the requested conclusion.',
        'next_steps':'Provide the missing evidence or ask one of the supported revenue/data-quality questions.','tool_log':log,'mode':used,'notice':notice}
    name,args=routed;result=run_tool(name,args,df,log)
    return {'scope':scope_text(result.scope.get('filters') if isinstance(result.scope.get('filters'),dict) else filters),
        'findings':format_findings(result,question),'interpretation':' '.join(result.caveats) if not result.error else 'No numerical conclusion is supported by this request.',
        'next_steps':'Review the data-quality and source records before acting; no recommendation is supported by revenue alone.',
        'tool_log':log,'mode':used,'notice':notice}
