"""
=============================================================================
Proiect: Sistem Ciber-Fizic (CPS) pentru Monitorizare AMR Pharma
Modul:   Aplicație Web / HMI Dashboard cu Login Screen și RBAC
=============================================================================
"""

import dash
from dash import dcc, html, ctx, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sqlite3
import paho.mqtt.publish as publish
import ssl
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = "pharma_data.db"

USERS = {
    'manager': {'password': 'dafi2026', 'role': 'Manager Depozit'},
    'auditor': {'password': 'pharma123', 'role': 'Auditor GxP'}
}

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "AMR Pharma - Control Panel"

COLORS = {
    'bg_page': '#f1f5f9', 'bg_card': '#ffffff', 'nav_bg': '#1e293b',
    'text_main': '#334155', 'text_sub': '#64748b', 'accent': '#3b82f6',
    'success': '#10b981', 'danger': '#ef4444', 'border': '#e2e8f0',
    'disabled': '#cbd5e1'
}

MQTT_BROKER = "a66111aa5df847cba675dddc5d9ecc65.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
AUTH = {'username': "test-dafi", 'password': "Test_Dafi_Ana_Miu1"}

# ==========================================
# STRUCTURA PRINCIPALĂ (SHELL) CU CEASUL INCLUS
# ==========================================
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='session-store', storage_type='session'), 
    html.Div(id='page-content'),
    dcc.Interval(id='timer', interval=2000, n_intervals=0) # ⏳ CEASUL A FOST RESTAURAT AICI!
], style={'backgroundColor': COLORS['bg_page'], 'minHeight': '100vh', 'fontFamily': '"Segoe UI", Arial'})

def get_navbar(username, role):
    return html.Div([
        html.Div([
            html.H2("⚕️ AMR Pharma - Sistem CPS GxP", style={'margin': '0', 'color': 'white', 'fontWeight': '600'}),
            html.Span("Panou de Control Automatizat și Audit Trail", style={'color': '#cbd5e1', 'fontSize': '14px'})
        ]),
        html.Div([
            dcc.Link("🕹️ Misiune Live", href="/", style={'color': 'white', 'textDecoration': 'none', 'marginRight': '20px', 'fontWeight': 'bold'}),
            dcc.Link("🗄️ Data Logging", href="/logging", style={'color': '#cbd5e1', 'textDecoration': 'none', 'marginRight': '30px', 'fontWeight': 'bold'}),
            html.Div([
                html.Span(f"👤 {username.upper()} ({role})", style={'color': '#cbd5e1', 'marginRight': '15px', 'fontSize': '14px'}),
                html.Button("🚪 Deconectare", id="btn-logout", n_clicks=0, style={'padding': '8px 15px', 'backgroundColor': COLORS['danger'], 'color': 'white', 'border': 'none', 'borderRadius': '5px', 'cursor': 'pointer', 'fontWeight': 'bold'})
            ], style={'borderLeft': '1px solid #334155', 'paddingLeft': '20px', 'display': 'flex', 'alignItems': 'center'}),
            html.Div([
                html.Button(id='btn-login'), dcc.Input(id='login-user'), dcc.Input(id='login-pass'), html.Div(id='login-error')
            ], style={'display': 'none'})
        ], style={'display': 'flex', 'alignItems': 'center'})
    ], style={'backgroundColor': COLORS['nav_bg'], 'padding': '15px 40px', 'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'})

def layout_login():
    return html.Div([
        html.Div([
            html.H2("⚕️ AMR Pharma", style={'textAlign': 'center', 'color': COLORS['text_main'], 'marginBottom': '5px'}),
            html.P("Autentificare Securizată GxP", style={'textAlign': 'center', 'color': COLORS['text_sub'], 'marginBottom': '30px'}),
            
            # CĂSUȚE FOARTE MARI ȘI FONT VIZIBIL (18px)
            dcc.Input(id='login-user', type='text', placeholder='👤 Nume utilizator (ex: manager)', 
                      style={'width': '100%', 'padding': '15px', 'marginBottom': '15px', 'borderRadius': '6px', 
                             'border': f"1px solid {COLORS['border']}", 'boxSizing': 'border-box', 
                             'fontSize': '18px', 'height': '55px'}),
                             
            dcc.Input(id='login-pass', type='password', placeholder='🔑 Parola', 
                      style={'width': '100%', 'padding': '15px', 'marginBottom': '20px', 'borderRadius': '6px', 
                             'border': f"1px solid {COLORS['border']}", 'boxSizing': 'border-box', 
                             'fontSize': '18px', 'height': '55px'}),
            
            html.Button('Intrare în Sistem', id='btn-login', n_clicks=0, 
                        style={'width': '100%', 'padding': '14px', 'backgroundColor': COLORS['accent'], 'color': 'white', 
                               'fontWeight': 'bold', 'border': 'none', 'borderRadius': '6px', 'cursor': 'pointer', 'fontSize': '18px'}),
                               
            html.Div(id='login-error', style={'color': COLORS['danger'], 'textAlign': 'center', 'marginTop': '15px', 'fontWeight': 'bold', 'fontSize': '15px'}),

            # Truc Dash invizibil
            html.Button(id='btn-logout', style={'display': 'none'})
            
        ], style={'backgroundColor': COLORS['bg_card'], 'padding': '40px', 'borderRadius': '12px', 'boxShadow': '0 10px 25px rgba(0,0,0,0.1)', 'width': '380px'})
    ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'minHeight': '100vh', 'backgroundColor': COLORS['nav_bg']})

def layout_monitorizare(username, role):
    este_manager = (username == 'manager')
    btn_start_color = COLORS['success'] if este_manager else COLORS['disabled']
    btn_stop_color = COLORS['danger'] if este_manager else COLORS['disabled']
    cursor_style = 'pointer' if este_manager else 'not-allowed'

    return html.Div([
        get_navbar(username, role),
        html.Div([
            html.Div([
                html.H4("🕹️ 1. Control Misiune AMR", style={'margin': '0 0 15px 0', 'color': COLORS['text_main'], 'borderBottom': f"2px solid {COLORS['border']}", 'paddingBottom': '10px'}),
                html.Div([
                    html.Span("Lungime X (m): ", style={'fontWeight': 'bold'}),
                    dcc.Input(id='input-x', type='number', value=10, min=2, disabled=not este_manager, style={'margin': '0 20px 0 10px', 'padding': '8px', 'borderRadius': '5px', 'border': f"1px solid {COLORS['border']}", 'width': '80px'}),
                    html.Span("Lățime Y (m): ", style={'fontWeight': 'bold'}),
                    dcc.Input(id='input-y', type='number', value=10, min=2, disabled=not este_manager, style={'margin': '0 20px 0 10px', 'padding': '8px', 'borderRadius': '5px', 'border': f"1px solid {COLORS['border']}", 'width': '80px'}),
                    html.Button("▶️ START MISSION", id="btn-start", n_clicks=0, disabled=not este_manager, style={'padding': '10px 20px', 'backgroundColor': btn_start_color, 'color': 'white', 'fontWeight': 'bold', 'cursor': cursor_style, 'border': 'none', 'borderRadius': '6px'}),
                    html.Button("🛑 OPRIRE URGENȚĂ", id="btn-stop", n_clicks=0, disabled=not este_manager, style={'padding': '10px 20px', 'backgroundColor': btn_stop_color, 'color': 'white', 'fontWeight': 'bold', 'cursor': cursor_style, 'border': 'none', 'borderRadius': '6px', 'marginLeft': '15px'}),
                ], style={'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap', 'backgroundColor': '#f8fafc', 'padding': '15px', 'borderRadius': '8px'}),
                html.Div("🔒 Mod Read-Only: Nu aveți permisiunea de a controla robotul." if not este_manager else "", style={'color': COLORS['danger'], 'marginTop': '10px', 'fontWeight': 'bold', 'fontSize': '13px'}),
                html.Div(id='status-comanda', style={'marginTop': '15px', 'fontWeight': 'bold', 'color': COLORS['accent'], 'fontSize': '15px'})
            ], style={'backgroundColor': COLORS['bg_card'], 'padding': '25px', 'borderRadius': '12px', 'marginBottom': '20px'}),
            html.Div([
                html.H4("📡 2. Starea Mașinii & Telemetrie Live", style={'margin': '0 0 15px 0', 'color': COLORS['text_main']}),
                html.Div(id='live-telemetry-widget', style={'minHeight': '120px'})
            ], style={'backgroundColor': COLORS['bg_card'], 'padding': '25px', 'borderRadius': '12px', 'borderLeft': f"6px solid {COLORS['accent']}", 'marginBottom': '20px'}),
            html.Div([
                html.H3("📍 3. Mapare Termică Volumetrică 3D", style={'margin': '0 0 5px 0', 'color': COLORS['text_main']}),
                dcc.Graph(id='live-3d-graph', style={'height': '55vh'})
            ], style={'backgroundColor': COLORS['bg_card'], 'padding': '25px', 'borderRadius': '12px'})
        ], style={'maxWidth': '1400px', 'margin': '0 auto', 'padding': '30px'})
    ])

def layout_logging(username, role):
    return html.Div([
        get_navbar(username, role),
        html.Div([
            html.Div([
                html.H4("🗄️ Registru Data Logging Imuabil (Edge SQLite)", style={'margin': '0 0 10px 0', 'color': COLORS['text_main']}),
                html.P("Datele stocate local pe Edge sunt mapate în timp real în tabelul de mai jos pentru audit GxP.", style={'color': COLORS['text_sub'], 'fontSize': '14px'}),
                html.Div([
                    html.Button("📥 Export Traseu (.CSV)", id="btn-csv", n_clicks=0, style={'padding': '10px 15px', 'backgroundColor': COLORS['text_sub'], 'color': 'white', 'fontWeight': 'bold', 'cursor': 'pointer', 'border': 'none', 'borderRadius': '6px', 'marginRight': '10px'}),
                    html.Button("🚨 Raport Deviații (.XLSX)", id="btn-excel", n_clicks=0, style={'padding': '10px 15px', 'backgroundColor': COLORS['danger'], 'color': 'white', 'fontWeight': 'bold', 'cursor': 'pointer', 'border': 'none', 'borderRadius': '6px'}),
                    dcc.Download(id="download-handler")
                ], style={'marginBottom': '25px', 'marginTop': '15px'}),
                dash_table.DataTable(
                    id='tabel-audit-records',
                    columns=[
                        {"name": "ID", "id": "id"}, {"name": "Data/Ora", "id": "timestamp"},
                        {"name": "X (m)", "id": "pos_x"}, {"name": "Y (m)", "id": "pos_y"},
                        {"name": "Z (m)", "id": "pos_z"}, {"name": "Temp (°C)", "id": "temperature"},
                        {"name": "Umiditate (%)", "id": "humidity"}, {"name": "Baterie (%)", "id": "battery"},
                        {"name": "Stare FSM", "id": "current_state"}, {"name": "Evaluare", "id": "status"}
                    ],
                    page_size=12,
                    style_header={'backgroundColor': COLORS['nav_bg'], 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'},
                    style_cell={'textAlign': 'center', 'padding': '10px', 'border': '1px solid #e2e8f0'},
                    style_data_conditional=[{'if': {'column_id': 'status', 'filter_query': '{status} eq "ALARM"'}, 'backgroundColor': '#fee2e2', 'color': COLORS['danger'], 'fontWeight': 'bold'}]
                )
            ], style={'backgroundColor': COLORS['bg_card'], 'padding': '30px', 'borderRadius': '12px'})
        ], style={'maxWidth': '1400px', 'margin': '0 auto', 'padding': '30px'})
    ])

@app.callback(
    [Output('session-store', 'data'), Output('login-error', 'children')],
    [Input('btn-login', 'n_clicks'), Input('btn-logout', 'n_clicks')],
    [State('login-user', 'value'), State('login-pass', 'value')],
    prevent_initial_call=True
)
def manage_auth(n_login, n_logout, user, pwd):
    trigger = ctx.triggered_id
    if trigger == 'btn-logout':
        if n_logout is None or n_logout == 0: return dash.no_update, dash.no_update
        return None, "" 
    if trigger == 'btn-login':
        if n_login is None or n_login == 0: return dash.no_update, dash.no_update
        if user in USERS and USERS[user]['password'] == pwd:
            return {'user': user, 'role': USERS[user]['role']}, "" 
        return dash.no_update, "❌ Utilizator sau parolă incorectă!"
    return dash.no_update, dash.no_update

@app.callback(Output('page-content', 'children'), [Input('url', 'pathname'), Input('session-store', 'data')])
def router(pathname, session_data):
    if not session_data: return layout_login()
    if pathname == "/logging": return layout_logging(session_data['user'], session_data['role'])
    return layout_monitorizare(session_data['user'], session_data['role'])

@app.callback(
    Output('status-comanda', 'children'),
    [Input('btn-start', 'n_clicks'), Input('btn-stop', 'n_clicks')],
    [State('input-x', 'value'), State('input-y', 'value'), State('session-store', 'data')],
    prevent_initial_call=True
)
def trimite_comanda(btn_start, btn_stop, x_val, y_val, session_data):
    if not btn_start and not btn_stop: return dash.no_update
    if not session_data or session_data['user'] != 'manager': return "🔒 EROARE DE SECURITATE."
    trigger = ctx.triggered_id
    tls_config = {'cert_reqs': ssl.CERT_REQUIRED, 'tls_version': ssl.PROTOCOL_TLSv1_2}
    try:
        if trigger == "btn-start":
            publish.single("amr_pharma/commands", f"START,{x_val},{y_val}", hostname=MQTT_BROKER, port=MQTT_PORT, auth=AUTH, tls=tls_config)
            return f"✅ Misiune transmisă! Aria setată: {x_val}m x {y_val}m."
        elif trigger == "btn-stop":
            publish.single("amr_pharma/commands", "STOP", hostname=MQTT_BROKER, port=MQTT_PORT, auth=AUTH, tls=tls_config)
            return "🛑 Comandă STOP trimisă către robot."
    except Exception as e: return f"❌ Eroare MQTT: {e}"
    return ""

@app.callback(
    [Output('live-3d-graph', 'figure'), Output('live-telemetry-widget', 'children')],
    [Input('timer', 'n_intervals')],
    [State('input-x', 'value'), State('input-y', 'value')],
    prevent_initial_call=False
)
def update_pagina_monitorizare(n, x_max, y_max):
    try:
        if not dash.callback_context.outputs_list: return dash.no_update, dash.no_update
        if 'live-3d-graph' not in str(dash.callback_context.outputs_list): return dash.no_update, dash.no_update
    except: pass

    limit_x = x_max if x_max and x_max > 0 else 10
    limit_y = y_max if y_max and y_max > 0 else 10

    def get_scene():
        return dict(
            xaxis=dict(title="Axă X (m)", range=[0, limit_x], backgroundcolor="white", gridcolor="lightgrey"),
            yaxis=dict(title="Axă Y (m)", range=[0, limit_y], backgroundcolor="white", gridcolor="lightgrey"),
            zaxis=dict(title="Înălțime Z (m)", range=[0, 4.0], backgroundcolor="white", gridcolor="lightgrey")
        )

    fig = go.Figure()
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, b=0, t=0), scene=get_scene())

    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM telemetry ORDER BY id DESC LIMIT 300", conn)
        conn.close()
    except Exception: return fig, html.Div("Sistem în așteptare...")

    if df.empty: return fig, html.Div("Așteptăm date de la senzorul Edge...")

    last_scan = df.iloc[0]
    fsm_state = last_scan['current_state'] if 'current_state' in df.columns else "NECUNOSCUT"
    
    if fsm_state in ["IDLE", "INIT"]: fsm_color = COLORS['text_sub']
    elif fsm_state in ["SAFE_STOP", "ALARM"]: fsm_color = COLORS['danger']
    else: fsm_color = COLORS['success']

    bat_val = last_scan['battery'] if 'battery' in df.columns else 100.0
    bat_color = COLORS['success'] if bat_val > 15.0 else COLORS['danger']
    temp_color = COLORS['danger'] if last_scan['temperature'] > 25.0 else COLORS['success']

    telemetry_ui = html.Div([
        html.Div([
            html.Div([
                html.P("⚙️ STAREA MAȘINII (FSM):", style={'margin': '0', 'fontSize': '12px', 'fontWeight': 'bold', 'color': COLORS['text_sub']}),
                html.P(f"● {fsm_state}", style={'margin': '5px 0 15px 0', 'fontSize': '24px', 'fontWeight': 'bold', 'color': fsm_color}),
            ], style={'flex': '1.5'}),
            html.Div([
                html.P("📍 POZIȚIE (X, Y, Z):", style={'margin': '0', 'fontSize': '12px', 'fontWeight': 'bold', 'color': COLORS['text_sub']}),
                html.P(f"{last_scan['pos_x']}m, {last_scan['pos_y']}m, {last_scan['pos_z']}m", style={'margin': '5px 0 15px 0', 'fontSize': '18px', 'fontWeight': 'bold'}),
            ], style={'flex': '1.5'}),
            html.Div([
                html.P("🔋 ACUMULATOR:", style={'margin': '0', 'fontSize': '12px', 'fontWeight': 'bold', 'color': COLORS['text_sub']}),
                html.P(f"{int(bat_val)}%", style={'margin': '5px 0 15px 0', 'fontSize': '18px', 'fontWeight': 'bold', 'color': bat_color}),
            ], style={'flex': '1'}),
        ], style={'display': 'flex'}),
        html.Div([
            html.P(f"🌡️ Temp: {last_scan['temperature']} °C", style={'margin': '0 30px 0 0', 'fontSize': '18px', 'fontWeight': 'bold', 'color': temp_color}),
            html.P(f"💧 Umiditate: {last_scan['humidity']}%" if fsm_state != "SAFE_STOP" else "💧 Umiditate: N/A - La stație", style={'margin': '0', 'fontSize': '18px', 'fontWeight': 'bold'})
        ], style={'display': 'flex', 'backgroundColor': '#f8fafc', 'padding': '15px', 'borderRadius': '8px', 'border': f"1px solid {COLORS['border']}"})
    ])

    if 'current_state' in df.columns:
        df_map = df[df['current_state'] == 'EDGE_SAVE_AND_SYNC']
    else:
        df_map = df

    if not df_map.empty:
        df_map['Umid_Afisat'] = df_map.apply(lambda r: f"{r['humidity']}%" if r['pos_z'] <= 0.2 else "N/A (Senzor la sol)", axis=1)
        fig = px.scatter_3d(
            df_map, x='pos_x', y='pos_y', z='pos_z', color='temperature',
            color_continuous_scale='Turbo', range_color=[18, 27],
            custom_data=['Umid_Afisat', 'battery', 'current_state']
        )
        fig.update_traces(
            marker=dict(size=8, opacity=0.8, line=dict(width=0.5, color='DarkSlateGrey')),
            hovertemplate="<b>Poziție:</b> (%{x}m, %{y}m, %{z}m)<br><b>Temp:</b> %{marker.color:.1f} °C<br><b>Stare FSM:</b> %{customdata[2]}<extra></extra>"
        )
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, b=0, t=0), scene=get_scene())

    return fig, telemetry_ui

@app.callback(
    Output('tabel-audit-records', 'data'),
    [Input('timer', 'n_intervals')],
    prevent_initial_call=False
)
def update_pagina_logging(n):
    try:
        if not dash.callback_context.outputs_list: return dash.no_update
        if 'tabel-audit-records' not in str(dash.callback_context.outputs_list): return dash.no_update
    except: pass
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT id, timestamp, pos_x, pos_y, pos_z, temperature, humidity, battery, current_state, status FROM telemetry ORDER BY id DESC LIMIT 300", conn)
        conn.close()
        return df.to_dict('records')
    except Exception: return []

@app.callback(Output("download-handler", "data"), [Input("btn-csv", "n_clicks"), Input("btn-excel", "n_clicks")], prevent_initial_call=True)
def descarca_rapoarte(btn_csv, btn_excel):
    if not btn_csv and not btn_excel: return dash.no_update
    conn = sqlite3.connect(DB_PATH)
    trigger = ctx.triggered_id
    if trigger == "btn-csv":
        df = pd.read_sql_query("SELECT * FROM telemetry", conn)
        conn.close()
        return dcc.send_data_frame(df.to_csv, "Raport_Audit_Tehnic_AMR.csv", index=False)
    else:
        df = pd.read_sql_query("SELECT timestamp, pos_x, pos_y, pos_z, temperature FROM telemetry WHERE temperature > 25.0", conn)
        conn.close()
        if df.empty: df = pd.DataFrame({"Rezultat Audit": ["Depozit conform normelor GDP. Nu există deviații termice."] })
        return dcc.send_data_frame(df.to_excel, "Raport_Deviatii_GxP_Pharma.xlsx", index=False)

if __name__ == "__main__":
    app.run(debug=True, port=8050)
