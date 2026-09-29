"""Chart factory shared by the dashboard, query results, and report export."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PALETTE = ['#A78BFA', '#22D3EE', '#FB7185', '#FBBF24', '#34D399', '#60A5FA', '#F472B6']
KINDS = ['Auto', 'Bar', 'Horizontal bar', 'Stacked bar', 'Line', 'Area', 'Scatter',
         'Bubble', 'Pie', 'Donut', 'Histogram', 'Box', 'Violin', 'Heatmap',
         'Treemap', 'Sunburst', 'Funnel', 'Waterfall', 'Gauge', 'Map', 'Table']


def theme(fig, title=''):
    fig.update_layout(template='plotly_dark', title=title, height=355,
        paper_bgcolor='#181A35', plot_bgcolor='#181A35',
        font={'family': 'Arial', 'color': '#E9EAF7', 'size': 12},
        colorway=PALETTE, margin={'l': 28, 'r': 20, 't': 52, 'b': 30},
        legend={'orientation': 'h', 'y': -0.2}, hovermode='closest')
    fig.update_xaxes(gridcolor='#2B2D4B')
    fig.update_yaxes(gridcolor='#2B2D4B')
    return fig


def numeric(frame):
    return list(frame.select_dtypes(include='number').columns)


def chart(frame, kind='Auto', x=None, y=None, color=None, aggregation='None', title='', target=100):
    if frame.empty or kind == 'Table':
        return None
    nums = numeric(frame)
    x = x if x in frame else frame.columns[0]
    y = y if y in nums else (nums[0] if nums else None)
    color = color if color in frame and color not in (x, y) else None
    if kind == 'Auto':
        if not y:
            return None
        if len(frame) == 1:
            return theme(go.Figure(go.Indicator(mode='number', value=float(frame[y].iloc[0]))), title or y)
        kind = 'Line' if any(t in x.lower() for t in ('date', 'month', 'week', 'year')) else 'Bar'
    if kind == 'Heatmap':
        if len(nums) < 2:
            raise ValueError('Heatmap needs at least two numeric columns.')
        return theme(px.imshow(frame[nums].corr(), color_continuous_scale='RdBu_r', zmin=-1, zmax=1), title or 'Correlation (not causation)')
    if kind == 'Histogram':
        if x not in nums:
            raise ValueError('Select a numeric X column for a histogram.')
        return theme(px.histogram(frame, x=x, color=color, color_discrete_sequence=PALETTE), title or f'Distribution of {x}')
    if not y:
        raise ValueError('This chart requires a numeric measure. Convert columns in Data explorer.')
    data = frame.copy()
    if aggregation != 'None' and kind not in ('Scatter', 'Bubble', 'Box', 'Violin'):
        group = [x] + ([color] if color else [])
        if y in group:
            raise ValueError('Choose a dimension different from the numeric measure.')
        data = data.groupby(group, dropna=False, as_index=False)[y].agg(aggregation.lower())
    args = {'data_frame': data, 'x': x, 'y': y, 'color': color, 'color_discrete_sequence': PALETTE}
    if kind in ('Bar', 'Stacked bar'):
        fig = px.bar(**args, barmode='stack' if kind == 'Stacked bar' else 'group')
    elif kind == 'Horizontal bar':
        fig = px.bar(data, x=y, y=x, color=color, orientation='h', color_discrete_sequence=PALETTE)
    elif kind in ('Line', 'Area'):
        args['data_frame'] = data.sort_values(x)
        fig = px.line(**args, markers=True) if kind == 'Line' else px.area(**args)
    elif kind in ('Scatter', 'Bubble'):
        if kind == 'Bubble' and (data[y] < 0).any():
            raise ValueError('Bubble sizes must be nonnegative.')
        fig = px.scatter(**args, size=y if kind == 'Bubble' else None)
    elif kind in ('Box', 'Violin'):
        fig = px.box(**args) if kind == 'Box' else px.violin(**args, box=True)
    elif kind in ('Pie', 'Donut', 'Treemap', 'Sunburst', 'Funnel', 'Map'):
        if (data[y] < 0).any():
            raise ValueError('This chart needs nonnegative values; use a bar or waterfall for signed values.')
        if kind in ('Pie', 'Donut'):
            fig = px.pie(data, names=x, values=y, hole=.68 if kind == 'Donut' else 0,
                         color_discrete_sequence=PALETTE)
        elif kind in ('Treemap', 'Sunburst'):
            builder = px.treemap if kind == 'Treemap' else px.sunburst
            fig = builder(data.dropna(subset=[x] + ([color] if color else [])),
                          path=[x] + ([color] if color else []), values=y, color_discrete_sequence=PALETTE)
        elif kind == 'Funnel':
            fig = px.funnel(**args)
        else:
            fig = px.choropleth(data, locations=x, locationmode='country names', color=y,
                                 color_continuous_scale=['#312E81', '#A78BFA', '#22D3EE'])
            fig.update_geos(bgcolor='#181A35', showframe=False)
    elif kind == 'Waterfall':
        fig = go.Figure(go.Waterfall(x=data[x], y=data[y], measure=['relative'] * len(data),
            increasing={'marker': {'color': '#34D399'}}, decreasing={'marker': {'color': '#FB7185'}}))
    elif kind == 'Gauge':
        if target <= 0:
            raise ValueError('Gauge target must be positive.')
        value = float(data[y].sum())
        fig = go.Figure(go.Indicator(mode='gauge+number', value=value,
            gauge={'axis': {'range': [0, max(target, value, 1)]}, 'bar': {'color': '#A78BFA'},
                   'threshold': {'line': {'color': '#22D3EE', 'width': 4}, 'value': target}}))
    else:
        raise ValueError('Unsupported chart type.')
    return theme(fig, title or f'{y} by {x}')
