# EVOKE/EEG三分类实时系统

本仓库只保留可部署主链路：8 通道 EEG 接收、实时预处理、左手/右手/脚三分类推理、FastAPI WebSocket 服务、前端展示，以及控制设备的数据输出。

## 当前部署模型

- 权重：`checkpoints/realtime_mi_relative_bandpower_v1.joblib`
- 类别：`left / right / feet`
- 输入：8 通道、250 Hz
- 窗口：4 秒，步长 2 秒
- 一次任务流程：跳过切换后的 1 秒，采集 3 个静息窗；再次跳过 1 秒，采集 3 个想象窗
- 特征：任务窗与静息窗的相对频带功率差，3 个窗聚合后推理
- 离线严格分组验证 balanced accuracy：`0.482456`

训练数据、训练/调参/评估脚本、实验报告和其他 checkpoint 不在远端仓库中。

## 目录

```text
backend/       FastAPI、WebSocket 和实时会话编排
frontend/      React/Vite 展示端，包含 Elms Sans 字体和运行所需素材
models/
  preprocessing/  在线滤波
  realtime/       缓冲、信号质量、推理、后处理和设备适配
checkpoints/   唯一的生产推理权重
scripts/       后端启动脚本和模拟 TCP EEG 数据源
tests/         运行主链路测试
eeg_client(1).py  ADS1299/硬件数据客户端
```

## 安装

后端建议使用 Python 3.10：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

前端：

```powershell
Set-Location frontend
npm install
```

## 运行

启动后端：

```powershell
python scripts/run_realtime_backend.py
```

启动前端：

```powershell
Set-Location frontend
npm run dev
```

默认使用演示 EEG 源。接真实 TCP 数据时，在 `.env` 中设置：

```dotenv
EEG_REALTIME_SOURCE=tcp
EEG_TCP_HOST=127.0.0.1
EEG_TCP_PORT=12345
```

设备输出支持 `serial`、`tcp`、`http` 和 `noop`。真实串口示例：

```dotenv
EEG_DEVICE_MODE=serial
EEG_DEVICE_SERIAL_PORT=auto
EEG_DEVICE_SERIAL_BAUDRATE=115200
```

模拟 TCP EEG 数据源：

```powershell
python scripts/mock_tcp_eeg_server.py
```

## 验证

```powershell
pytest -q
Set-Location frontend
npm run build
npm run lint
```
