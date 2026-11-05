"""Approved analytical tools: explicit filters in, a common ToolResult out."""
import pandas as pd
import analytics
from analytics import ToolResult
FILTERS={'Year','Channel','Store ID','Category','Product'}
GROUPS={'Channel','Store','Category','Product','Year','Month'}

def scoped(df,filters):
    bad=set(filters or {})-FILTERS
    if bad: return df,f'Unsupported filter(s): {sorted(bad)}'
    return analytics._apply_filters(df,filters)

def result(name,value,definition,filters,rows,caveats=None):
    return ToolResult(name,value,definition,{'filters':filters or 'All data'},rows,
                      ['Revenue is not profit.']+(caveats or []))

def revenue_summary(df,filters=None):
    work,err=scoped(df,filters)
    if err:return analytics._error('revenue_summary',err,{'filters':filters})
    good=work['Revenue'].notna()
    total=float(work.loc[good,'Revenue'].sum()); n=int(good.sum())
    return result('revenue_summary',{'revenue':total,'sales_records':len(work),
        'valid_revenue_records':n,'average_revenue_per_record':total/n if n else None,
        'stores':int(work['Store ID'].nunique())},'Sum of Revenue; average per valid sales record, not per customer order',
        filters,n,[f'{int((~good).sum())} missing/invalid revenue records excluded.'])

def revenue_breakdown(df,group='Channel',filters=None):
    if group not in GROUPS:return analytics._error('revenue_breakdown',f'Unsupported grouping: {group}')
    work,err=scoped(df,filters)
    if err:return analytics._error('revenue_breakdown',err,{'filters':filters})
    valid=work['Revenue'].notna() & work[group].notna()
    grouped=work.loc[valid].groupby(group)['Revenue'].sum()
    return result('revenue_breakdown',{'group':group,'revenue':{str(k):float(v) for k,v in grouped.items()}},
        f'Sum of Revenue by {group}',filters,int(valid.sum()),[f'{int((~valid).sum())} rows missing revenue or grouping value excluded.'])

def compare_years(df,earlier,later,filters=None):
    filters=dict(filters or {}); filters.pop('Year',None)
    work,err=scoped(df,filters)
    if err:return analytics._error('compare_years',err,{'filters':filters})
    valid_years=set(df['Year'].dropna().astype(int))
    if earlier not in valid_years or later not in valid_years or earlier>=later:
        return analytics._error('compare_years','Choose two existing years in increasing order.')
    work=work[work.Year.isin([earlier,later])]
    pivot=work.pivot_table(index='Store',columns='Year',values='Revenue',aggfunc='sum')
    records=[]
    for store,row in pivot.iterrows():
        a=row.get(earlier); b=row.get(later)
        comparable=pd.notna(a) and pd.notna(b)
        records.append({'store':store,'earlier_revenue':float(a) if pd.notna(a) else None,
           'later_revenue':float(b) if pd.notna(b) else None,
           'change':float(b-a) if comparable else None,
           'change_pct':float((b-a)/a*100) if comparable and a!=0 else None,
           'status':'Comparable' if comparable else 'Missing period; no decline inferred'})
    scope={**filters,'Year':[int(earlier),int(later)]}
    return result('compare_years',{'earlier':int(earlier),'later':int(later),'stores':records},
        'Revenue change by store; only stores with both periods are comparable',scope,int(work.Revenue.notna().sum()),
        ['Recorded revenue differences do not establish their cause.'])

def quality(df,filters=None):
    work,err=scoped(df,filters)
    if err:return analytics._error('quality',err,{'filters':filters})
    return result('quality',{'rows':len(work),'duplicate_sales_ids':int(work['Sales ID'].duplicated().sum()),
        'missing':{c:int(n) for c,n in work.isna().sum().items() if n},
        'negative_revenue_records':int((work.Revenue<0).sum())},'Missing/invalid values and duplicate keys in the prepared sales model',filters,len(work))
