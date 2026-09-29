import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from prismforge.agent import run_ai, run_demo, analysis_error_message
from prismforge.charts import KINDS, chart, numeric
from prismforge.data import EXTENSIONS, demo_data, load_file, unique_name
from prismforge.report import export_report
from prismforge.sql import execute, quality, schema

load_dotenv(Path(__file__).resolve().parent / ".env")
st.set_page_config(page_title='PrismForge AI', page_icon='💎', layout='wide')
st.markdown('''<style>
.block-container{padding-top:2rem;max-width:1550px}
[data-testid="stMetric"]{background:linear-gradient(125deg,#252345,#181a35);border:1px solid #393558;border-radius:16px;padding:18px}
[data-testid="stMetricValue"]{color:#c4b5fd}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:18px}
.hero{background:linear-gradient(105deg,#30275b,#172d46);border:1px solid #4d4376;border-radius:22px;padding:26px 32px;margin-bottom:24px}
.hero h1{color:#f5f3ff;margin:4px 0;font-size:36px}.hero p{color:#c8c7e1;margin:4px 0}
.eyebrow{color:#67e8f9;letter-spacing:3px;font-size:11px;font-weight:700}
</style><div class="hero"><div class="eyebrow">YOUR DATA. CLEARER DECISIONS.</div>
<h1>💎 PrismForge AI</h1><p>Conversational analytics & business intelligence studio</p></div>''', unsafe_allow_html=True)

for key, default in [('tables', demo_data()), ('history', []), ('report', []),
                     ('notes', []), ('dataset_label', 'Synthetic retail demo'), ('revision', 0)]:
    if key not in st.session_state:
        st.session_state[key] = default


def replace_workspace(tables, label, notes):
    st.session_state.tables = tables
    st.session_state.dataset_label = label
    st.session_state.notes = notes
    st.session_state.history = []
    st.session_state.report = []
    st.session_state.revision += 1
    st.session_state.pop('result', None)
    st.session_state.pop('sql_result', None)


def show_figure(fig, key):
    if fig is not None:
        st.plotly_chart(fig, width='stretch', key=key)


def csv_bytes(frame):
    safe = frame.copy()
    for col in safe:
        safe[col] = safe[col].map(lambda v: "'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@', '\t', '\r')) else v)
    return safe.to_csv(index=False).encode('utf-8-sig')


def builder(frame, prefix, suggested='Auto', default_x='', default_y=''):
    if frame.empty:
        st.info('No matching rows to chart.')
        return None
    columns = list(frame.columns)
    nums = numeric(frame)
    a, b, c = st.columns(3)
    kind = a.selectbox('Chart type', KINDS, index=KINDS.index(suggested) if suggested in KINDS else 0, key=prefix+'kind')
    x = b.selectbox('Dimension / X', columns, index=columns.index(default_x) if default_x in columns else 0, key=prefix+'x')
    y = c.selectbox('Measure / Y', nums or ['No numeric columns'], index=nums.index(default_y) if default_y in nums else 0, key=prefix+'y')
    d, e = st.columns(2)
    color = d.selectbox('Split by colour', ['None'] + columns, key=prefix+'color')
    aggregation = e.selectbox('Aggregation', ['None', 'Sum', 'Mean', 'Count', 'Min', 'Max'], key=prefix+'agg')
    target = st.number_input('Gauge target', min_value=0.01, value=100.0, key=prefix+'target') if kind == 'Gauge' else 100
    if kind in ('Funnel', 'Waterfall'):
        st.caption('Rows define stage order. Waterfall treats each row as a relative change; use signed deltas.')
    if kind == 'Map':
        st.caption('Dimension must contain recognized country names. Missing/unrecognized countries will not be plotted.')
    try:
        fig = chart(frame, kind, x, y, color, aggregation, target=target)
        if fig is None:
            st.dataframe(frame, hide_index=True, width='stretch')
        else:
            show_figure(fig, prefix+'plot')
        return fig
    except (ValueError, TypeError) as exc:
        st.info(str(exc))
        return None


with st.sidebar:
    st.title('💎 Workspace')
    st.caption(st.session_state.dataset_label)
    uploads = st.file_uploader('Upload your data', type=EXTENSIONS, accept_multiple_files=True,
        help='CSV, Excel, JSON, Parquet, SQLite, text PDF, Word and more. 20 MB per file.')
    encoding_note = 'CSV delimiter is detected automatically. Numeric cells should not contain currency symbols.'
    st.caption(encoding_note)
    if st.button('Load uploaded files', type='primary', width='stretch'):
        if not uploads:
            st.warning('Choose one or more files first.')
        elif len(uploads) > 10 or sum(f.size for f in uploads) > 50 * 1024 * 1024:
            st.error('Workspace limit: 10 files and 50 MB total uploaded size.')
        else:
            try:
                tables, notes, used = {}, [], set()
                for f in uploads:
                    imported, messages = load_file(f.name, f.getvalue())
                    for name, frame in imported.items():
                        tables[unique_name(name, used)] = frame
                    notes.extend(messages)
                if not tables or len(tables) > 30 or sum(len(x) for x in tables.values()) > 300_000:
                    raise ValueError('Workspace limit: 30 tables and 300,000 rows total.')
                replace_workspace(tables, f'{len(uploads)} uploaded file(s)', notes)
                st.rerun()
            except Exception as exc:
                st.error(f'Upload not loaded: {exc}')
    if st.button('Reset to demo data', width='stretch'):
        replace_workspace(demo_data(), 'Synthetic retail demo', [])
        st.rerun()
    st.divider()
    mode = st.radio('Query engine', ['Offline demo', 'AI analyst'])
    provider = st.selectbox('AI provider', ['Gemini', 'OpenAI'])
    key_name = 'GEMINI_API_KEY' if provider == 'Gemini' else 'OPENAI_API_KEY'
    model_name = 'GEMINI_MODEL' if provider == 'Gemini' else 'OPENAI_MODEL'
    default_model = 'gemini-3.8-flash' if provider == 'Gemini' else 'gpt-4.1-mini'
    model = st.text_input(f'{provider} model', value=os.getenv(model_name, default_model), key='model_'+provider)
    override_key = st.text_input(f'{provider} API key (session only)', type='password',
        key='api_key_'+provider, help=f'Leave blank to use {key_name} from .env. Paste only the key.') if mode == 'AI analyst' else ''
    api_key = (override_key or os.getenv(key_name, '')).strip()
    if mode == 'AI analyst':
        st.caption('API key configured.' if api_key else f'Enter your {provider} API key above or set {key_name} in .env.')
    consent = st.checkbox(f'Allow {provider} to receive my question, schema and result excerpts', value=False, key='consent_'+provider)
    samples = st.checkbox('Also share 2 sample rows per table', value=False, key='samples_'+provider)
    st.caption(f'Uploads stay in this local session. AI mode sends the listed context to {provider}; its API quotas, billing and data policies apply. No key is bundled.')

tables = st.session_state.tables
rev = str(st.session_state.revision)
for note in st.session_state.notes:
    st.warning(note)

dashboard, analyst, explorer, studio, sqltab, reporttab = st.tabs([
    '◈ Business dashboard', '✦ Ask your data', '▦ Data explorer',
    '◉ Chart studio', '⌘ SQL workbench', '↗ Business report'])

with dashboard:
    st.subheader('Business pulse')
    st.caption('Dashboard filters affect this dashboard only. AI and SQL query all loaded rows; include desired filters in your question.')
    with st.expander('Data source and filters', expanded=False):
        table_name = st.selectbox('Dashboard table', list(tables), key='dashboard_table'+rev)
        data = tables[table_name]
        nums = numeric(data)
        dims = [c for c in data if c not in nums and data[c].nunique() <= 100]
        datecols = [c for c in data if any(t in c.lower() for t in ('date', 'timestamp'))]
        filtered = data.copy()
        if not dims:
            filtered['_all_records'] = 'All records'
            dims = ['_all_records']
        fa, fb = st.columns(2)
        if [c for c in dims if c in data]:
            filter_col = fa.selectbox('Filter dimension', ['None'] + [c for c in dims if c in data], key='filter_col'+rev+table_name)
            if filter_col != 'None':
                values = sorted(data[filter_col].dropna().astype(str).unique())
                selected = fb.multiselect('Include values', values, default=values, key='filter_vals'+rev+table_name+filter_col)
                filtered = filtered[filtered[filter_col].astype(str).isin(selected)]
        if datecols:
            datecol = st.selectbox('Date filter column', ['None'] + datecols, key='datecol'+rev+table_name)
            if datecol != 'None':
                dates = pd.to_datetime(filtered[datecol], errors='coerce')
                if dates.notna().any():
                    bounds = st.date_input('Date range', (dates.min().date(), dates.max().date()), key='range'+rev+table_name+datecol)
                    if len(bounds) == 2:
                        filtered = filtered[(dates.dt.date >= bounds[0]) & (dates.dt.date <= bounds[1])]
    if not nums:
        st.info('This table contains text. Use Ask your data to search documents, or convert a numeric column in Data explorer.')
        st.dataframe(filtered.head(100), width='stretch')
    elif filtered.empty:
        st.warning('No rows match these filters.')
    else:
        ca, cb = st.columns(2)
        measure = ca.selectbox('Business measure', nums, index=nums.index('revenue') if 'revenue' in nums else 0, key='measure'+rev+table_name)
        dimension = cb.selectbox('Break down by', dims, key='dimension'+rev+table_name)
        m1, m2, m3, m4 = st.columns(4)
        total = filtered[measure].sum()
        m1.metric('Visible records', f'{len(filtered):,}')
        m2.metric(f'Total {measure}', f'{total/1000:,.1f}K' if abs(total) >= 10000 else f'{total:,.2f}')
        m3.metric(f'Average {measure}', f'{filtered[measure].mean():,.2f}')
        m4.metric('Missing cells', f'{int(filtered.isna().sum().sum()):,}')
        st.caption('Metrics use the selected measure as stored. Currency is not inferred. Sum is appropriate only for additive measures.')
        dashboard_sections = []
        row1 = st.columns([1.5, 1])
        with row1[0]:
            if datecols:
                trend = filtered.copy()
                trend['_month'] = pd.to_datetime(trend[datecols[0]], errors='coerce').dt.strftime('%Y-%m')
                fig = chart(trend.dropna(subset=['_month']), 'Area', '_month', measure, aggregation='Sum', title='Performance over time')
            else:
                fig = chart(filtered, 'Bar', dimension, measure, aggregation='Sum', title='Category performance')
            show_figure(fig, 'dash_trend')
            dashboard_sections.append({'title': 'Performance', 'figure': fig})
        with row1[1]:
            kind = 'Donut' if (filtered[measure].dropna() >= 0).all() else 'Bar'
            fig = chart(filtered, kind, dimension, measure, aggregation='Sum', title='Contribution by segment')
            show_figure(fig, 'dash_mix')
            dashboard_sections.append({'title': 'Segment contribution', 'figure': fig})
        row2 = st.columns(3)
        with row2[0]:
            fig = chart(filtered, 'Bar', dimension, measure, aggregation='Sum', title='Segment comparison')
            show_figure(fig, 'dash_bars')
            dashboard_sections.append({'title': 'Segments', 'figure': fig})
        with row2[1]:
            fig = chart(filtered, 'Histogram', measure, title='Value distribution')
            show_figure(fig, 'dash_hist')
            dashboard_sections.append({'title': 'Distribution', 'figure': fig})
        with row2[2]:
            gauge_target = st.number_input('Set your business target', min_value=.01, value=float(max(abs(total)*1.2, 1)), key='dash_target'+rev+table_name+measure)
            fig = chart(filtered, 'Gauge', dimension, measure, title=f'{measure} / target', target=gauge_target)
            show_figure(fig, 'dash_gauge')
            dashboard_sections.append({'title': 'User-defined target', 'figure': fig, 'text': f'Target: {gauge_target:,.2f}. Initial target is illustrative; set your actual business target.'})
        summary = f'Table: {table_name}. Visible rows: {len(filtered):,} of {len(data):,}. Measure: {measure}. Total: {total:,.2f}. Mean: {filtered[measure].mean():,.2f}. Missing cells: {int(filtered.isna().sum().sum())}. This is a descriptive dashboard, not a causal explanation.'
        st.info(summary)
        st.download_button('Download dashboard report', export_report('PrismForge business dashboard', [{'title':'Scope', 'text':summary}] + dashboard_sections), 'prismforge-dashboard.html', 'text/html')

with analyst:
    st.subheader('Ask a question. Inspect the evidence.')
    st.caption('AI can aggregate, compare, join, filter and retrieve document excerpts. Follow-up questions include the previous four questions and SQL statements.')
    st.code('Offline: count rows | preview data | revenue by region\nAI: Compare monthly revenue by region.\nAI: Which category has the highest profit margin?\nAI: Create an executive summary of revenue by channel.', language=None)
    with st.form('question_form'):
        question = st.text_area('Your business question', placeholder='Which region generated the most revenue?')
        ask = st.form_submit_button('Analyze my data', type='primary')
    if ask:
        if not question.strip():
            st.warning('Enter a question first.')
        elif mode == 'AI analyst' and (not api_key or not consent):
            st.warning('Add an API key and enable context sharing in the sidebar to use AI.')
        else:
            with st.spinner('Inspecting schema, executing SQL, preparing results...'):
                try:
                    result = run_demo(question, tables) if mode == 'Offline demo' else run_ai(question, tables, api_key, model, st.session_state.history, samples, provider=provider)
                    result['question'] = question
                    st.session_state.result = result
                    st.session_state.history.append({'question': question, 'sql': result['plan'].sql})
                except Exception as exc:
                    st.error(analysis_error_message(exc, provider) if mode == 'AI analyst' else str(exc))
    result = st.session_state.get('result')
    if result:
        st.markdown('**Question:** ' + result['question'])
        st.markdown(result['answer'])
        with st.expander('Query plan and execution steps', expanded=True):
            st.write(result['plan'].explanation)
            st.code(result['plan'].sql, language='sql')
            st.write(' → '.join(result['trace']))
        frame = result['frame']
        if frame is not None:
            if result['truncated']:
                st.warning('Result capped at 2,000 rows. Ask for SQL aggregation for complete totals.')
            st.dataframe(frame, hide_index=True, width='stretch')
            fig = builder(frame, 'result'+rev+str(len(st.session_state.history)), result['plan'].chart, result['plan'].x, result['plan'].y)
            st.download_button('Download query result CSV', csv_bytes(frame), 'query-result.csv', 'text/csv')
            if st.button('Add this analysis to business report'):
                st.session_state.report.append({'title':result['question'], 'text':result['answer'], 'sql':result['plan'].sql, 'frame':frame.copy(), 'figure':fig})
                st.success('Added. Open Business report to download.')
    with st.expander('Recent questions and SQL'):
        st.json(st.session_state.history[-10:])

with explorer:
    st.subheader('Sources & data quality')
    name = st.selectbox('Inspect table', list(tables), key='explorer'+rev)
    frame = tables[name]
    st.caption(f'{len(frame):,} rows · {len(frame.columns)} columns · names normalized for SQL')
    st.dataframe(frame.head(500), hide_index=True, width='stretch')
    st.dataframe(quality(frame), hide_index=True, width='stretch')
    st.caption(f'Exact duplicate rows: {int(frame.duplicated().sum()):,}. Preview shows up to 500 rows.')
    with st.expander('Convert a column type'):
        col = st.selectbox('Column', list(frame.columns), key='convert_col'+rev+name)
        dtype = st.selectbox('Convert to', ['Numeric', 'ISO date', 'Text'])
        st.caption('Numeric conversion removes commas and common currency symbols. Invalid values become missing. Dates use pandas parsing; inspect ambiguous day/month dates before conversion.')
        if st.button('Apply conversion'):
            copy = frame.copy()
            if dtype == 'Numeric':
                copy[col] = pd.to_numeric(copy[col].astype(str).str.replace(r'[$€£₹,]', '', regex=True), errors='coerce')
            elif dtype == 'ISO date':
                copy[col] = pd.to_datetime(copy[col], errors='coerce').dt.strftime('%Y-%m-%d')
            else:
                copy[col] = copy[col].astype('string')
            updated = dict(tables)
            updated[name] = copy
            replace_workspace(updated, st.session_state.dataset_label, [f'Converted {name}.{col} to {dtype}; {int(copy[col].isna().sum())} missing values. Previous query/report results cleared.'])
            st.rerun()
    st.download_button('Download this table', csv_bytes(frame), name+'.csv', 'text/csv')
    with st.expander('Schema used by the analyst'):
        st.json(schema(tables))

with studio:
    st.subheader('Chart studio')
    st.caption('Choose the visual that fits the business question. For categories, use Sum/Mean before plotting raw transactional data. Large plots use the first 5,000 rows; use SQL to aggregate all rows.')
    name = st.selectbox('Chart source', list(tables), key='studio'+rev)
    source = tables[name].head(5000)
    fig = builder(source, 'studio_builder'+rev+name)
    if fig is not None and st.button('Add chart to report'):
        st.session_state.report.append({'title':f'Chart: {name}', 'figure':fig, 'text':f'Source {name}; chart built from first {len(source)} of {len(tables[name])} rows.'})
        st.success('Chart added to report.')

with sqltab:
    st.subheader('Read-only SQL workbench')
    st.caption('One SELECT or WITH query. Writes, schema changes, file access and unapproved functions are blocked.')
    sql = st.text_area('SQL query', value=f'SELECT * FROM "{next(iter(tables))}" LIMIT 20', key='sql_text'+rev)
    if st.button('Run SQL'):
        try:
            frame, truncated = execute(tables, sql)
            st.session_state.sql_result = (frame, truncated)
        except Exception as exc:
            st.error(str(exc))
    if 'sql_result' in st.session_state:
        frame, truncated = st.session_state.sql_result
        st.dataframe(frame, hide_index=True, width='stretch')
        if truncated:
            st.warning('Showing first 2,000 rows.')
        st.download_button('Download SQL result', csv_bytes(frame), 'sql-result.csv', 'text/csv')

with reporttab:
    st.subheader('Your business report')
    st.caption('Add query analyses and chart-studio visuals, then export a standalone interactive HTML report. Open it in a browser; Print > Save as PDF creates a static version.')
    title = st.text_input('Report title', 'PrismForge | Business review')
    sections = st.session_state.report
    if not sections:
        st.info('No sections yet. Add an analysis from Ask your data or a chart from Chart studio. The dashboard also has its own report download.')
    for i, section in enumerate(sections):
        with st.expander(f'{i+1}. {section["title"]}'):
            st.write(section.get('text', ''))
    if sections:
        st.download_button('Download interactive business report', export_report(title, sections), 'prismforge-business-report.html', 'text/html')
        if st.button('Clear report sections'):
            st.session_state.report = []
            st.rerun()

st.caption('PrismForge AI · Local portfolio edition · Results depend on source data and query correctness. Verify business-critical conclusions against the displayed SQL.')
