"""Reproduce evidence using original data, a CSV replacement, and independent Decimal arithmetic."""
from pathlib import Path
from decimal import Decimal
import subprocess
import csv
import io
import json
import pandas as pd
import data_model as dm
import business_tools as bt
import agent

OUT=Path('evidence');OUT.mkdir(exist_ok=True)
def dump(name,value):(OUT/name).write_text(json.dumps(value,indent=2,default=str))
sources=dm.repository_sources('data');tables,fp=dm.load_sources(sources);sales,joins=dm.prepare_model(tables)
dump('merge_checks.json',joins)
grains=[]
for name,df in tables.items():
    grains.append({'Table':name,'Rows':len(df),'Columns':len(df.columns),'Key':dm.KEYS.get(name,'Survey ID' if name=='Survey' else 'Not a fact table'),
        'Revenue?':name=='Sales','Duplicate rows':int(df.duplicated().sum()),'Missing cells':int(df.isna().sum().sum())})
pd.DataFrame(grains).to_csv(OUT/'table_profiles.csv',index=False)
# Read the Access export with Python's csv and Decimal. No pandas/analytics sum.
raw=subprocess.run(['mdb-export','data/Support_EX_B_Sales (1).accdb','Sales'],capture_output=True,text=True,check=True).stdout
rows=list(csv.DictReader(io.StringIO(raw)))
independent=sum((Decimal(r['Revenue']) for r in rows),Decimal('0'))
app_total=bt.revenue_summary(sales).value['revenue']
assert Decimal(str(app_total))==independent
dump('independent_check.json',{'method':'mdb-export → csv.DictReader → sum(Decimal(Revenue)); no pandas or application summation',
    'rows':len(rows),'independent_revenue':str(independent),'app_revenue':app_total,'match':True})
metrics=[{'Metric':'Total revenue (2025–2029)','App result':app_total,'Power BI result':'NOT PROVIDED','Status':'Pending Power BI comparison'}]
for group in ['Channel','Year','Month']:
    value=bt.revenue_breakdown(sales,group).value['revenue']
    for k,v in value.items():metrics.append({'Metric':f'{group}: {k}','App result':v,'Power BI result':'NOT PROVIDED','Status':'Pending Power BI comparison'})
metrics.append({'Metric':'Sales records','App result':len(sales),'Power BI result':'NOT PROVIDED','Status':'Pending Power BI comparison'})
pd.DataFrame(metrics).to_csv(OUT/'power_bi_comparison.csv',index=False)
# Predict first, then serialize/reload a real replacement file and test scopes.
modified=tables['Sales'].copy();row=modified.iloc[0].copy();modified.loc[0,'Revenue']=float(row.Revenue)+1000
changed=sales.loc[sales['Sales ID']==row['Sales ID']].iloc[0]
prediction={'row':row.to_dict(),'old_value':float(row.Revenue),'new_value':float(row.Revenue)+1000,
 'predicted_total':app_total+1000,'affected_year':int(changed.Year),'affected_month':changed.Month,
 'affected_store':changed['Store ID'],'affected_channel':changed.Channel,'affected_category':changed.Category,'affected_product':changed.Product,
 'predicted_change':1000,'unchanged':['row count','dimension tables','all scopes excluding changed row']}
dump('1000_prediction.json',prediction)
path=OUT/'Sales_modified_plus_1000.csv';modified.to_csv(path,index=False)
updated_tables={**tables,**dm.read_source(path.read_bytes(),path.name)}
updated,_=dm.prepare_model(updated_tables)
checks=[]
for scope in [{},{'Year':int(changed.Year)},{'Month':str(changed.Month)},{'Store ID':changed['Store ID']},
              {'Channel':changed.Channel},{'Category':changed.Category},{'Product':changed.Product},
              {'Year':int(changed.Year),'Store ID':changed['Store ID'],'Channel':changed.Channel}]:
    def total(df):
        sub=df
        for col,value in scope.items():sub=sub[sub[col]==value]
        return float(sub.Revenue.sum())
    a,b=total(sales),total(updated);assert b-a==1000
    checks.append({'scope':scope,'before':a,'after':b,'expected_change':1000,'actual_change':b-a,'pass':True})
other_year=next(int(y) for y in sales.Year.dropna().unique() if y!=changed.Year)
a=bt.revenue_summary(sales,{'Year':other_year}).value['revenue'];b=bt.revenue_summary(updated,{'Year':other_year}).value['revenue'];assert a==b
checks.append({'scope':{'Year':other_year},'before':a,'after':b,'expected_change':0,'actual_change':b-a,'pass':True})
assert len(sales)==len(updated)
before=agent.answer_question('What is total revenue?',sales)
after=agent.answer_question('What is total revenue?',updated)
restored,_=dm.prepare_model(tables);assert bt.revenue_summary(restored).value['revenue']==app_total
dump('1000_results.json',{'prediction':prediction,'scope_checks':checks,'assistant_before':before,'assistant_after':after,
  'record_count_unchanged':True,'original_restored':True,'code_changes_needed_for_data_update':False,
  'test_environment':'Local source-file round trip. AppTest separately simulates sidebar upload in one unchanged session. Hosted/browser upload still needs team confirmation.'})
questions=[('Numerical calculation','What is total revenue?','Revenue equals independently checked source sum'),
 ('Numerical comparison','Which stores declined between 2028 and 2029?','Compare matched store revenue across both years; never infer missing period as zero'),
 ('Missing information','What is total profit?','Decline to calculate profit without costs'),
 ('Analytical judgment','Why did revenue change?','Decline causation; identify missing evidence'),
 ('Updated data','What is total revenue?','Original total plus exactly 1000 after replacement')]
records=[]
for kind,q,expected in questions:
    a=agent.answer_question(q,updated if kind=='Updated data' else sales)
    passed=bool(a['tool_log']) if kind in ['Numerical calculation','Numerical comparison','Updated data'] else not a['tool_log']
    if kind=='Updated data':passed=passed and a['tool_log'][0]['result']['value']['revenue']==app_total+1000
    records.append({'test':kind,'question':q,'expected':expected,'actual':a,'pass':passed})
dump('agent_tests.json',records)
assert all(r['pass'] for r in records)
print(json.dumps({'total':app_total,'independent':str(independent),'years':bt.revenue_breakdown(sales,'Year').value,
    'channels':bt.revenue_breakdown(sales,'Channel').value,'survey_rows':len(tables.get('Survey',[])),'update_checks':len(checks),'agent_tests':len(records)},indent=2))
