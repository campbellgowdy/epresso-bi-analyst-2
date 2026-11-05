"""Read content, validate source schemas and join dimensions without changing revenue."""
from pathlib import Path
import hashlib
import tempfile
import pandas as pd
import analytics

REQUIRED = {
 'Sales': ['Sales ID','Date','Store ID','StoreYear','Category ID','Product ID','Revenue'],
 'Products': ['Product ID','Product'], 'Categories':['Category ID','Category'],
 'Stores':['ID','StoreType','City'],
}
KEYS = {'Sales':'Sales ID','Products':'Product ID','Categories':'Category ID','Stores':'ID'}

def read_source(content, filename):
    suffix = Path(filename).suffix.lower()
    if suffix in {'.accdb','.mdb'}:
        with tempfile.NamedTemporaryFile(suffix=suffix) as f:
            f.write(content); f.flush()
            return {name: analytics.load_access_table(f.name, name)
                    for name in analytics.access_table_names(f.name) if name in REQUIRED}
    if suffix in analytics.EXCEL_EXT:
        sheets = analytics.excel_sheet_names(content)
        matched = {s: analytics.load_table(content,filename,s) for s in sheets if s in REQUIRED}
        if matched:
            return matched
        # The workbook has title rows above its true survey header.
        raw={f'Survey / {s}':analytics.load_table(content,filename,s) for s in sheets}
        for sheet in sheets:
            frame=pd.read_excel(__import__('io').BytesIO(content),sheet_name=sheet,header=None)
            for i,row in frame.iterrows():
                if {'Survey ID','Store ID','Year','Satisfaction','Interest'}.issubset(set(row.dropna().astype(str))):
                    survey=pd.read_excel(__import__('io').BytesIO(content),sheet_name=sheet,header=i)
                    survey=survey.dropna(how='all')
                    raw['Survey']=survey
                    raw.pop(f'Survey / {sheet}',None)
                    break
        return raw
    frame = analytics.load_table(content,filename)
    for name in ('Sales','Products','Categories','Stores'):
        if set(REQUIRED[name]).issubset(frame.columns):
            return {name:frame}
    raise ValueError('CSV columns must identify Sales, Products, Categories or Stores. Required columns: '+str(REQUIRED))

def load_sources(sources):
    tables={}; fingerprint=hashlib.sha256()
    for filename,content in sources:
        fingerprint.update(filename.encode()); fingerprint.update(content)
        tables.update(read_source(content,filename))
    return tables,fingerprint.hexdigest()

def repository_sources(directory):
    directory=Path(directory)
    return [(p.name,p.read_bytes()) for p in sorted(directory.iterdir())
            if p.suffix.lower() in {'.accdb','.mdb','.csv','.xlsx'}]

def prepare_model(tables):
    for table,columns in REQUIRED.items():
        if table not in tables: raise ValueError(f'Missing required table: {table}')
        missing=set(columns)-set(tables[table].columns)
        if missing: raise ValueError(f'{table}: missing required column(s): {", ".join(sorted(missing))}')
        key=KEYS[table]
        if not analytics.check_unique_ids(tables[table],key)['is_unique']:
            raise ValueError(f'{table}.{key} must be unique and nonblank. Fix duplicate/missing keys before analysis.')
    sales=tables['Sales'].copy()
    sales['Revenue']=pd.to_numeric(sales['Revenue'],errors='coerce')
    sales['Date']=pd.to_datetime(sales['Date'],errors='coerce',format='mixed')
    sales['Year']=sales['Date'].dt.year.astype('Int64')
    sales['Month']=sales['Date'].dt.to_period('M').astype('string').mask(sales['Date'].isna())
    reports=[]
    for name,key in [('Products','Product ID'),('Categories','Category ID'),('Stores','Store ID')]:
        right=tables[name].copy()
        if name=='Stores': right=right.rename(columns={'ID':'Store ID'})
        # Only dimension attributes; no second measure or duplicated join keys.
        before=len(sales); revenue=float(sales['Revenue'].sum())
        unmatched=int((~sales[key].isin(right[key])).sum())
        sales=sales.merge(right,on=key,how='left',validate='many_to_one')
        after=float(sales['Revenue'].sum())
        reports.append({'dimension':name,'rows_before':before,'rows_after':len(sales),
                        'revenue_before':revenue,'revenue_after':after,'unmatched_rows':unmatched})
        if len(sales)!=before or abs(revenue-after)>0.005:
            raise ValueError(f'{name}: join changed row count or revenue; analysis stopped.')
    sales['Channel']=sales['StoreType'].fillna('Unknown')
    sales['Store']=sales['Store ID'].astype('string')+' · '+sales['City'].fillna(sales['StoreType']).fillna('Unknown')
    for col in ['Product','Category','Store']:
        sales[col]=sales[col].fillna('Unknown')
    return sales,reports
