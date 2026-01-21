import matplotlib
# GUIバックエンドを強制的に指定 (Pyplotをインポートする前に記述)
matplotlib.use('TkAgg')

import ctypes
from sys import platform
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, TextBox, Button # Buttonを追加
from collections import deque

# --- 1. 初期設定 ---
INITIAL_THRESHOLD_MV = 20.0 
AVERAGE_WINDOW = 5.0
hzAcq = 20000000.0   
nSamples = 4096      

history_duration = 10.0
max_history_len = 2000

freqGen = 1000000.0
ampGen = 5.0

# --- 2. デバイス接続 ---
if platform.startswith("linux"):
    dwf = ctypes.cdll.LoadLibrary("libdwf.so")
else:
    print("This script is for Linux (Raspberry Pi).")
    exit()

hdwf = ctypes.c_int()
print("Opening device...")
dwf.FDwfDeviceOpen(ctypes.c_int(-1), ctypes.byref(hdwf))

if hdwf.value == 0:
    print("failed to open device")
    quit()

# --- 3. Wavegen 設定 ---
channel_gen = ctypes.c_int(0) 
node_carrier = ctypes.c_int(0)
dwf.FDwfAnalogOutNodeEnableSet(hdwf, channel_gen, node_carrier, ctypes.c_bool(True))
dwf.FDwfAnalogOutNodeFunctionSet(hdwf, channel_gen, node_carrier, ctypes.c_ubyte(1)) 
dwf.FDwfAnalogOutNodeFrequencySet(hdwf, channel_gen, node_carrier, ctypes.c_double(freqGen))
dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, channel_gen, node_carrier, ctypes.c_double(ampGen))
dwf.FDwfAnalogOutConfigure(hdwf, channel_gen, ctypes.c_bool(True))

# --- 4. Scope 設定 ---
dwf.FDwfAnalogInChannelEnableSet(hdwf, ctypes.c_int(0), ctypes.c_bool(True))
dwf.FDwfAnalogInChannelRangeSet(hdwf, ctypes.c_int(0), ctypes.c_double(5.0))
dwf.FDwfAnalogInFrequencySet(hdwf, ctypes.c_double(hzAcq))
dwf.FDwfAnalogInBufferSizeSet(hdwf, ctypes.c_int(nSamples))
dwf.FDwfAnalogInConfigure(hdwf, ctypes.c_int(1), ctypes.c_int(1))

# --- 5. データバッファ ---
time_history = deque(maxlen=max_history_len)
val_history = deque(maxlen=max_history_len)
avg_history = deque(maxlen=max_history_len)
calc_buffer_t = deque()
calc_buffer_v = deque()

# --- 6. GUI初期化 ---
plt.ion()

fig, ax = plt.subplots(figsize=(10, 7))
plt.subplots_adjust(bottom=0.30) 

# プロット線の初期化
line_curr, = ax.plot([], [], 'g-', linewidth=1.5, label='Voltage')
line_avg, = ax.plot([], [], color='orange', linestyle='--', linewidth=1.5, label='5s Average')
alert_text = ax.text(0.05, 0.9, '', transform=ax.transAxes, fontsize=14, fontweight='bold', color='red',
                     bbox=dict(facecolor='white', alpha=0.8, edgecolor='red'))

ax.set_xlim(0, history_duration)
ax.set_xlabel("Time (s)")
ax.set_ylabel("Voltage (V)")
ax.grid(True)
ax.legend(loc='upper right')

# === GUI部品配置 ===

# 1. スライダー
ax_slider = plt.axes([0.15, 0.1, 0.50, 0.03], facecolor='lightgoldenrodyellow')
slider = Slider(ax_slider, 'Thresh (mV)', 1.0, 100.0, valinit=INITIAL_THRESHOLD_MV)

# 2. テキストボックス
ax_box = plt.axes([0.75, 0.1, 0.15, 0.05])
text_box = TextBox(ax_box, 'Set mV: ', initial=str(INITIAL_THRESHOLD_MV))

# 3. ダークモード切り替えボタン (追加箇所)
ax_button = plt.axes([0.05, 0.02, 0.15, 0.05]) # 左下に配置
btn_dark = Button(ax_button, 'Dark Mode', color='lightgray', hovercolor='0.9')

# === イベント処理関数 ===

def update_title(val_mv):
    ax.set_title(f"Voltage Change Detector")

def submit_text(text):
    try:
        val_mv = float(text)
        slider.set_val(val_mv)
    except ValueError:
        pass

def update_slider(val):
    text_box.set_val(f"{val:.1f}")
    update_title(val)

# ダークモード状態管理変数
is_dark_mode = False

def toggle_theme(event):
    """ダークモードとライトモードを切り替える関数"""
    global is_dark_mode
    is_dark_mode = not is_dark_mode
    
    if is_dark_mode:
        # ダークモード設定
        bg_color = '#2b2b2b'     # 全体の背景（濃いグレー）
        plot_bg = '#1e1e1e'      # グラフエリアの背景（さらに濃いグレー）
        fg_color = '#dcdcdc'     # 文字色（白っぽいグレー）
        grid_color = '#444444'   # グリッド
        
        # ボタンの見た目変更
        btn_dark.label.set_text("Light Mode")
        btn_dark.color = '#555555'
        btn_dark.label.set_color('white')
        
    else:
        # ライトモード設定
        bg_color = 'white'
        plot_bg = 'white'
        fg_color = 'black'
        grid_color = '#b0b0b0'
        
        # ボタンの見た目変更
        btn_dark.label.set_text("Dark Mode")
        btn_dark.color = 'lightgray'
        btn_dark.label.set_color('black')

    # --- 各要素の色を適用 ---
    fig.patch.set_facecolor(bg_color)   # ウィンドウ背景
    ax.set_facecolor(plot_bg)           # グラフ内背景
    
    # 軸・ラベル・タイトル
    ax.title.set_color(fg_color)
    ax.xaxis.label.set_color(fg_color)
    ax.yaxis.label.set_color(fg_color)
    ax.tick_params(axis='x', colors=fg_color)
    ax.tick_params(axis='y', colors=fg_color)
    
    # スパイン（枠線）
    for spine in ax.spines.values():
        spine.set_edgecolor(fg_color)
        
    # グリッド
    ax.grid(True, color=grid_color)
    
    # 凡例 (Legend)
    legend = ax.get_legend()
    if legend:
        frame = legend.get_frame()
        frame.set_facecolor(plot_bg)
        frame.set_edgecolor(fg_color)
        for text in legend.get_texts():
            text.set_color(fg_color)

    # 再描画
    fig.canvas.draw_idle()


# イベント紐付け
slider.on_changed(update_slider)
text_box.on_submit(submit_text)
btn_dark.on_clicked(toggle_theme) # ボタンクリック時の処理

update_title(INITIAL_THRESHOLD_MV)

# --- 7. メインループ ---
rgdSamples = (ctypes.c_double * nSamples)()
sts = ctypes.c_byte()
start_time = time.time()

print("Monitoring started... (Ctrl+C to stop)")

try:
    while True:
        dwf.FDwfAnalogInStatus(hdwf, ctypes.c_int(1), ctypes.byref(sts))

        if sts.value == 2:
            dwf.FDwfAnalogInStatusData(hdwf, ctypes.c_int(0), rgdSamples, nSamples)
            data_chunk = np.frombuffer(rgdSamples, dtype=np.float64)
            
            current_val = np.max(data_chunk)
            current_t = time.time() - start_time
            
            # 平均計算
            calc_buffer_t.append(current_t)
            calc_buffer_v.append(current_val)
            while len(calc_buffer_t) > 0 and (calc_buffer_t[0] < current_t - AVERAGE_WINDOW):
                calc_buffer_t.popleft()
                calc_buffer_v.popleft()
            
            current_avg = sum(calc_buffer_v) / len(calc_buffer_v) if len(calc_buffer_v) > 0 else current_val
            
            time_history.append(current_t)
            val_history.append(current_val)
            avg_history.append(current_avg)

            # 判定
            threshold_mv = slider.val 
            threshold_v = threshold_mv / 1000.0 
            diff = current_val - current_avg
            
            if current_t > 5.0:
                if diff > threshold_v:
                    alert_msg = f"UP DETECTED! (+{diff*1000:.0f} mV)"
                    alert_text.set_text(alert_msg)
                    alert_text.set_color('red')
                    alert_text.set_visible(True)
                elif diff < -threshold_v:
                    alert_msg = f"DOWN DETECTED! ({diff*1000:.0f} mV)"
                    alert_text.set_text(alert_msg)
                    # ダークモードでも見やすいように青(blue)からシアン(cyan)寄りに変更しても良いが
                    # ひとまず標準の青のままにしています
                    alert_text.set_color('blue') 
                    alert_text.set_visible(True)
                else:
                    alert_text.set_visible(False)
            else:
                alert_text.set_text("Calibrating...")
                alert_text.set_visible(True)

            # グラフ更新
            if current_t > history_duration:
                ax.set_xlim(current_t - history_duration, current_t)
            else:
                ax.set_xlim(0, history_duration)

            if len(val_history) > 1:
                vals = list(val_history) + list(avg_history)
                y_min, y_max = min(vals), max(vals)
                margin = (y_max - y_min) * 0.1 if y_max != y_min else 0.1
                ax.set_ylim(y_min - margin, y_max + margin)

            line_curr.set_data(time_history, val_history)
            line_avg.set_data(time_history, avg_history)
            
            plt.pause(0.01)

except KeyboardInterrupt:
    pass

print("Closing device...")
dwf.FDwfAnalogOutConfigure(hdwf, channel_gen, ctypes.c_bool(False))
dwf.FDwfDeviceCloseAll()