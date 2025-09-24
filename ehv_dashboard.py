import streamlit as st
import random
from collections import deque
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- Page Config ---
st.set_page_config(page_title="4-Bus EHV SCADA Simulator", layout="wide")
st.title("⚡ 4-Bus EHV Substation SCADA Simulator (Digital Twin)")

# Auto-refresh every second
st_autorefresh(interval=1000, key="refresh_sim")

# --- Session State Setup ---
components = [
    "breaker1","breaker2","breaker3","breaker4","breaker5","breaker6",
    "cap1","cap2","cap3","cap4",
    "tap1","tap2","tap3","tap4",
    "alarm","breaker_flash1","breaker_flash2","breaker_flash3",
    "breaker_flash4","breaker_flash5","breaker_flash6",
    "transformer_flash1","transformer_flash2","transformer_flash3",
    "fault_bus1","fault_bus2","fault_bus3","fault_bus4"
]

for comp in components:
    if comp not in st.session_state:
        if "breaker" in comp and "flash" not in comp:
            st.session_state[comp] = "Closed ✅"
        elif "cap" in comp:
            st.session_state[comp] = "Off ⚡"
        elif "tap" in comp:
            st.session_state[comp] = "0"
        elif "alarm" in comp:
            st.session_state[comp] = "None"
        elif "flash" in comp:
            st.session_state[comp] = False
        elif "fault" in comp:
            st.session_state[comp] = False

if "history" not in st.session_state:
    st.session_state.history = {f"voltage_bus{i+1}":deque(maxlen=50) for i in range(4)}
    st.session_state.history.update({f"current_bus{i+1}":deque(maxlen=50) for i in range(4)})
    st.session_state.history.update({f"load_bus{i+1}":deque(maxlen=50) for i in range(4)})
    st.session_state.history.update({"temp":deque(maxlen=50),"sf6":deque(maxlen=50)})

# --- Layout: Side by Side ---
col_scada, col_controls = st.columns([2,1])  # SCADA wider than controls

# --- Controls Section ---
with col_controls:
    st.subheader("🔧 Bus Load Control (MW)")
    load_bus = []
    for i in range(4):
        load = st.slider(f"Bus{i+1} Load", 50, 200, 100, key=f"load_slider{i+1}")
        load_bus.append(load)
        st.session_state.history[f"load_bus{i+1}"].append(load)

    st.subheader("⚠️ Fault Injection")
    for i in range(4):
        st.session_state[f"fault_bus{i+1}"] = st.checkbox(f"Inject Fault Bus{i+1}", value=st.session_state[f"fault_bus{i+1}"])

    # Breakers
    st.markdown("### Breakers")
    breaker_list=["breaker1","breaker2","breaker3","breaker4","breaker5","breaker6"]
    for i, b in enumerate(breaker_list):
        if st.button(f"Toggle {b}"):
            st.session_state[b]="Open ❌" if st.session_state[b]=="Closed ✅" else "Closed ✅"
            st.session_state[f"breaker_flash{i+1}"]=True

    # Capacitors
    st.markdown("### Capacitor Banks")
    cap_list=["cap1","cap2","cap3","cap4"]
    for c in cap_list:
        if st.button(f"Toggle {c}"):
            st.session_state[c]="On ⚡" if st.session_state[c]=="Off ⚡" else "Off ⚡"

    # Tap changers
    st.markdown("### Tap Changers")
    tap_list=["tap1","tap2","tap3","tap4"]
    for t in tap_list:
        st.slider(f"{t} Position",0,10,int(st.session_state[t]),key=t)

# --- Simulate Live Data ---
voltage_bus = []
current_bus = []
for i in range(4):
    base_v = 400 + random.uniform(-5,5)
    base_i = 120 + (load_bus[i]-100)*0.3 + random.uniform(-5,5)
    # Fault logic
    if st.session_state[f"fault_bus{i+1}"]:
        base_i += 30
        st.session_state[f"breaker{i+1}"]="Open ❌"
        st.session_state[f"breaker_flash{i+1}"]=True
        st.session_state.alarm="⚠️ Fault Detected!"
    voltage_bus.append(round(base_v,2))
    current_bus.append(round(base_i,2))

temp = round(60 + random.uniform(-5,5),2)
sf6 = round(101325 + random.uniform(-200,200),2)

for i in range(4):
    st.session_state.history[f"voltage_bus{i+1}"].append(voltage_bus[i])
    st.session_state.history[f"current_bus{i+1}"].append(current_bus[i])
st.session_state.history["temp"].append(temp)
st.session_state.history["sf6"].append(sf6)

# --- Helper Functions ---
def flow_style(current):
    if current < 110: return "green",2
    elif current < 125: return "orange",4
    else: return "red",6

def check_transformer_overload(current, limit=130):
    return current > limit

# --- SCADA Diagram Section ---
with col_scada:
    st.subheader("Interactive 4-Bus Substation Diagram")
    fig = go.Figure()

    # Busbars
    bus_y = [3,2,1,0.5]
    for y in bus_y:
        fig.add_shape(type="line", x0=1, y0=y, x1=5, y1=y, line=dict(color="black", width=8))

    # Breakers
    breakers = ["breaker1","breaker2","breaker3","breaker4","breaker5","breaker6"]
    breaker_pos = [(0,3),(0,2),(0,1),(0,0.5),(2,2.5),(4,1.5)]
    for idx,(b,(x,y)) in enumerate(zip(breakers, breaker_pos), start=1):
        fig.add_shape(type="line", x0=x, y0=y, x1=x+1, y1=y, line=dict(color="blue", width=4))
        color = "green" if st.session_state[b]=="Closed ✅" else "red"
        if st.session_state[f"breaker_flash{idx}"]:
            color="yellow"
            st.session_state[f"breaker_flash{idx}"]=False
        fig.add_trace(go.Scatter(x=[x+1], y=[y], mode='markers+text',
                                 marker=dict(size=20,color=color),
                                 text=[b], textposition="top center"))

    # Transformers
    transformers = [(2.5,2.5,"T1",current_bus[0]),(4.5,1.5,"T2",current_bus[1]),(3,0.75,"T3",current_bus[2])]
    for i,(x,y,name,curr) in enumerate(transformers):
        overload = check_transformer_overload(curr)
        color = "red" if overload else "lightgray"
        if overload:
            st.session_state[f"transformer_flash{i+1}"] = True
        fig.add_shape(type="rect", x0=x-0.3,y0=y-0.3,x1=x+0.3,y1=y+0.3,
                      line=dict(color="black"), fillcolor=color)
        fig.add_trace(go.Scatter(x=[x],y=[y],mode='text',text=[name],textposition="middle center"))

    # Capacitors
    cap_banks=["cap1","cap2","cap3","cap4"]
    cap_pos=[(3,3),(4,2),(3.5,1),(4.5,0.5)]
    for c,(x,y) in zip(cap_banks,cap_pos):
        color="green" if st.session_state[c]=="On ⚡" else "gray"
        fig.add_trace(go.Scatter(x=[x],y=[y],mode='markers+text',
                                 marker=dict(size=25,color=color,symbol="square"),
                                 text=[c],textposition="top center"))

    # Line Flows
    line_pairs=[((2,2.5),(3,3)),((4,1.5),(5,2)),((3.5,0.75),(4.5,0.5))]
    for (start,end),cur in zip(line_pairs,current_bus[:3]):
        c,w=flow_style(cur)
        fig.add_annotation(x=end[0],y=end[1],ax=start[0],ay=start[1],
                           xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=3, arrowsize=1.5,
                           arrowwidth=w, arrowcolor=c)

    # Volt/Current annotations
    bus_positions=[(3,3.3),(4,1.7),(3.5,0.9),(4.5,0.6)]
    for i,(x,y) in enumerate(bus_positions):
        fig.add_annotation(x=x,y=y,text=f"Bus{i+1} V: {voltage_bus[i]} kV",showarrow=False,font=dict(color="blue"))
        fig.add_annotation(x=x,y=y-0.2,text=f"Bus{i+1} I: {current_bus[i]} A",showarrow=False,font=dict(color="orange"))

    # Alarm
    if st.session_state.alarm!="None":
        fig.add_annotation(x=3,y=0.2,text=f"ALARM: {st.session_state.alarm}",
                           showarrow=False,font=dict(color="red",size=18))

    fig.update_layout(xaxis=dict(range=[0,6],visible=False),
                      yaxis=dict(range=[0,4],visible=False),
                      plot_bgcolor='white',height=600)
    st.plotly_chart(fig,use_container_width=True)

# --- Gauge & Metrics Section (Toggle) ---
st.subheader("📊 Live Metrics & Gauges")
show_gauges = st.checkbox("Show Bus Gauges & Metrics", value=True)

if show_gauges:
    col_metrics1, col_metrics2 = st.columns(2)

    with col_metrics1:
        st.subheader("Bus Voltages (kV)")
        for i in range(4):
            fig_v = go.Figure(go.Indicator(
                mode="gauge+number",
                value=st.session_state.history[f"voltage_bus{i+1}"][-1] if st.session_state.history[f"voltage_bus{i+1}"] else 400,
                gauge={'axis':{'range':[380,420]},'bar':{'color':'green'}},
                title={'text':f"Bus{i+1}"}
            ))
            st.plotly_chart(fig_v,use_container_width=True)

        # Temperature & SF6
        temp_val = st.session_state.history["temp"][-1] if st.session_state.history["temp"] else 60
        sf6_val = st.session_state.history["sf6"][-1] if st.session_state.history["sf6"] else 101325
        st.metric("Temperature (°C)", temp_val)
        st.metric("SF6 Pressure (Pa)", sf6_val)

    with col_metrics2:
        st.subheader("Bus Currents (A)")
        for i in range(4):
            fig_i = go.Figure(go.Indicator(
                mode="gauge+number",
                value=st.session_state.history[f"current_bus{i+1}"][-1] if st.session_state.history[f"current_bus{i+1}"] else 120,
                gauge={'axis':{'range':[100,150]},'bar':{'color':'orange'}},
                title={'text':f"Bus{i+1}"}
            ))
            st.plotly_chart(fig_i,use_container_width=True)

    # --- Trend Plot ---
    st.subheader("📈 Trends")
    trend_fig = go.Figure()
    for i in range(1,5):
        trend_fig.add_trace(go.Scatter(y=list(st.session_state.history[f"voltage_bus{i}"]),
                                       mode='lines+markers',name=f"Bus{i} V"))
        trend_fig.add_trace(go.Scatter(y=list(st.session_state.history[f"current_bus{i}"]),
                                       mode='lines+markers',name=f"Bus{i} I"))
        trend_fig.add_trace(go.Scatter(y=list(st.session_state.history[f"load_bus{i}"]),
                                       mode='lines',name=f"Bus{i} Load"))
    trend_fig.add_trace(go.Scatter(y=list(st.session_state.history["temp"]),
                                   mode='lines+markers',name="Temp"))
    trend_fig.add_trace(go.Scatter(y=list(st.session_state.history["sf6"]),
                                   mode='lines+markers',name="SF6"))
    trend_fig.update_layout(plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            xaxis_title="Time →",
                            yaxis_title="Value")
    st.plotly_chart(trend_fig,use_container_width=True)
