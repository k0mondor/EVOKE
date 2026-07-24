# EEG 实时数据通路开发计划

## 1. 文档目标

本文档专门描述项目从上位机 EEG 数据采集到实时推理、硬件联动和前端可视化的完整数据通路开发计划。

它与仓库根目录的 `README.md` 分工不同：

- `README.md` 负责项目总览；
- `docs/PIPELINE.md` 负责训练/推理主流程概念说明；
- `docs/REALTIME_DATAFLOW_DEVELOPMENT_PLAN.md` 负责实时系统的工程落地方案。

## 2. 目标场景

系统目标是实现以下闭环：

1. 上位机电脑通过 `TCP` 持续发送 EEG 原始数据；
2. Python 实时服务接收并解析数据帧；
3. 数据经过在线预处理、重采样、滑窗和质量控制；
4. 将窗口输入训练好的 `CNN` 模型完成三分类推理；
5. 将推理结果同时发送到：
   - 前端网页，用于实时波形、脑地形图、概率条渲染；
   - 外部硬件控制接口，用于执行动作或反馈；
6. 预留统一扩展接口，支持后续替换模型、增加硬件、扩展消息类型。

最终分类标签保持为：

- `left`
- `right`
- `feet`

## 3. 当前仓库基础

当前仓库中已经存在可复用的模块：

- TCP 原型脚本：[eeg_client(1).py](file:///c:/Users/32349/eeg-model/eeg_client(1).py)
- 预处理模块：
  - [models/preprocessing/filters.py](file:///c:/Users/32349/eeg-model/models/preprocessing/filters.py)
  - [models/preprocessing/windowing.py](file:///c:/Users/32349/eeg-model/models/preprocessing/windowing.py)
  - [models/preprocessing/pipeline.py](file:///c:/Users/32349/eeg-model/models/preprocessing/pipeline.py)
- 实时骨架：
  - [models/realtime/buffer.py](file:///c:/Users/32349/eeg-model/models/realtime/buffer.py)
  - [models/realtime/inference.py](file:///c:/Users/32349/eeg-model/models/realtime/inference.py)
  - [backend/app/services/realtime_session.py](file:///c:/Users/32349/eeg-model/backend/app/services/realtime_session.py)
- 前端监控组件：
  - [frontend/src/components/EegWaveformPanel.tsx](file:///c:/Users/32349/eeg-model/frontend/src/components/EegWaveformPanel.tsx)
  - [frontend/src/components/TopomapPanel.tsx](file:///c:/Users/32349/eeg-model/frontend/src/components/TopomapPanel.tsx)
  - [frontend/src/components/ProbabilityBarsPanel.tsx](file:///c:/Users/32349/eeg-model/frontend/src/components/ProbabilityBarsPanel.tsx)
- 当前最佳模型 checkpoint：
  - `checkpoints/best_long_t_new4_excl133728_plain_cnn.pt`

## 4. 训练协议与在线协议对齐要求

实时推理必须尽量贴合当前最佳离线训练协议，否则线上分布会偏移。

当前 checkpoint 元信息表明，在线链路第一版应严格对齐以下配置：

- 目标采样率：`250 Hz`
- 窗长：`4.0 s`
- 步长：`2.0 s`
- 预处理带通：`4-30 Hz`
- 陷波：`50 Hz`
- 重参考：`none`
- ICA：`关闭`
- 输入形状：`(batch, channels, time)`

注意：

- 当前 TCP 原型脚本中帧头采样率示例为 `500 Hz`；
- 当前最佳模型训练协议为 `250 Hz`；
- 因此实时链路必须在进入模型前显式完成 `500 -> 250` 的在线重采样。

## 5. 目标数据通路

```text
上位机 EEG TCP 流
  -> TCP 接收器
  -> 协议解析
  -> 原始帧缓存
  -> 在线重采样 (500 -> 250)
  -> 在线滤波 (4-30Hz + 50Hz notch)
  -> 滚动窗口构建 (4s, stride 2s)
  -> 窗口质量评估 (PTP / RMS)
  -> CNN 推理
  -> 结果平滑 / 门控
  -> WebSocket 广播给前端
  -> Device Adapter 输出给外部硬件
```

## 6. 总体架构设计

建议采用五段式架构：

### 6.1 采集层

职责：

- 与上位机建立 TCP 连接；
- 接收固定帧长数据；
- 处理断连、重连、超时；
- 输出统一的原始 EEG 帧对象。

输入：

- `328 bytes / frame` 原始二进制数据

输出：

- `sampling_rate`
- `num_samples`
- `channels`
- `timestamp`
- `frame_index`

### 6.2 在线信号处理层

职责：

- 将原始数据转为 `samples x channels` 数组；
- 在线重采样；
- 维持滚动缓存；
- 执行滤波和滑窗；
- 产出可进入模型的窗口张量。

输入：

- 原始帧序列

输出：

- `window_data`
- `window_start_ms`
- `window_end_ms`
- `quality metrics`

### 6.3 推理层

职责：

- 加载 checkpoint；
- 根据模型配置构造网络；
- 将窗口数据喂给 CNN；
- 输出类别概率与置信度；
- 提供后处理与平滑接口。

输出：

- `label`
- `probabilities`
- `confidence`
- `low_confidence / usable`

### 6.4 分发层

职责：

- 将实时结果广播给前端；
- 将动作指令发送给硬件适配器；
- 统一管理消息格式和 session 生命周期。

### 6.5 表现层

职责：

- 前端网页实时展示 EEG 波形；
- 绘制脑地形图；
- 用动态条形图展示分类概率；
- 显示当前类别、置信度和信号质量；
- 保持后续可扩展到更多视图。

## 7. 模块拆分建议

建议新增或扩展如下模块：

### 7.1 `models/realtime/`

- `tcp_receiver.py`
  - 建立 TCP 连接
  - 接收固定长度帧
  - 解析为结构化数据
- `resampler.py`
  - 负责 `500Hz -> 250Hz`
- `online_preprocessor.py`
  - 负责 bandpass / notch
  - 负责窗口准备
- `window_buffer.py`
  - 维护滚动样本缓存
  - 提供 `4s / 2s` 滑窗输出
- `quality.py`
  - 计算 `PTP / RMS / usable`
- `checkpoint_runner.py`
  - 加载训练好的 plain CNN checkpoint
- `postprocess.py`
  - 平滑概率
  - 抑制抖动
  - 产生 `hold` 状态
- `device_adapter.py`
  - 定义统一外设接口

### 7.2 `backend/app/`

- `services/realtime_hub.py`
  - 统一调度 TCP 接收、推理、广播、硬件输出
- `api/ws.py`
  - 暴露 WebSocket 路由
- `schemas/messages.py`
  - 维护消息协议

### 7.3 `frontend/src/`

- `services/realtime.ts`
  - 从 demo socket 切换为真实 WebSocket
- `stores/realtimeStore.ts`
  - 存储实时 EEG、topomap、probabilities、connection 状态
- `components/EegWaveformPanel.tsx`
  - 对接真实数据
- `components/TopomapPanel.tsx`
  - 对接真实 topomap
- `components/ProbabilityBarsPanel.tsx`
  - 对接真实推理结果

## 8. 消息协议设计

建议统一使用 envelope 包装消息：

```json
{
  "version": "1.0",
  "type": "mi_probs",
  "session_id": "rt-001",
  "timestamp_ms": 1784771007000,
  "payload": {}
}
```

建议至少定义以下消息类型。

### 8.1 EEG 原始帧消息

```json
{
  "type": "eeg_frame",
  "payload": {
    "sampling_rate": 250,
    "channels": {
      "CH1": [0.1, 0.2, 0.3],
      "CH2": [0.2, 0.1, 0.0]
    }
  }
}
```

### 8.2 推理概率消息

```json
{
  "type": "mi_probs",
  "payload": {
    "label": "left",
    "probabilities": {
      "left": 0.72,
      "right": 0.18,
      "feet": 0.10
    },
    "confidence": 0.72,
    "usable": true
  }
}
```

### 8.3 脑地形图消息

```json
{
  "type": "topomap",
  "payload": [
    {
      "id": "instant",
      "values": [0.1, -0.2, 0.05, 0.3],
      "timestamp": "2026-07-24T12:00:00Z"
    }
  ]
}
```

### 8.4 外设动作消息

```json
{
  "type": "device_action",
  "payload": {
    "device_id": "motor-01",
    "action": "emit_left",
    "accepted": true
  }
}
```

## 9. 外部硬件扩展接口设计

硬件接口不要直接写死在分类器中，而应抽象成适配器层。

建议统一接口：

```python
class DeviceAdapter:
    def connect(self) -> None: ...
    def send_action(self, action: str, payload: dict) -> None: ...
    def close(self) -> None: ...
```

首版兼容以下输出方式：

- TCP
- 串口
- HTTP
- WebSocket
- MQTT

同时增加动作门控机制：

- 置信度阈值
- 最小触发间隔 `cooldown`
- 连续窗口投票
- `hold` 状态

目标是先保证控制稳定，再逐步提高灵敏度。

## 10. 前端可视化设计

### 10.1 波形图

显示内容：

- 8 通道滚动 EEG 波形；
- 最近若干秒的数据；
- 在线状态与采样率提示。

### 10.2 脑地形图

第一版策略：

- 基于 8 通道瞬时值、RMS 或 bandpower 构造 topomap 输入；
- 采用简化插值，先把监控链路跑通；
- 等确认通道实际电极位置后，再做更真实的头皮插值渲染。

需要尽快确认：

- `CH1 ~ CH8` 对应的真实电极位置；
- 是否存在固定 montage；
- 是否需要左右半球可解释显示。

### 10.3 动态概率条

显示内容：

- `left / right / feet` 三类概率；
- 当前 dominant label；
- `confidence` 与 `usable` 状态。

建议：

- 概率先做平滑；
- 低置信度时避免频繁横跳；
- 对 `hold` 或 `low_quality` 状态做单独展示。

## 11. 在线质量控制策略

当前 checkpoint 协议已提供一版伪迹阈值，可直接作为首版在线质量门控：

- `ptp_threshold = 179.4873`
- `rms_threshold = 22.4605`

首版逻辑建议：

1. 对每个推理窗口计算 `PTP` 和 `RMS`；
2. 若超阈值，则标记 `usable = false`；
3. 前端保留显示，但降低结果可信度提示；
4. 硬件控制不触发，仅发送 `hold`；
5. 后端记录异常窗口比例，供后续调试。

## 12. 分阶段开发计划

### 阶段 A：打通原始数据接收

目标：

- 从上位机稳定接入 TCP 数据；
- 正确解析每帧 `328 bytes`；
- 能持续打印采样率、帧计数和通道数据摘要。

验收标准：

- 能持续运行不少于 `10 min`；
- 无明显丢帧或频繁断连；
- 能正确识别 `sampling_rate` 和 `10 x 8` 通道结构。

### 阶段 B：打通在线信号处理

目标：

- 将原始帧拼成滚动时间序列；
- 实现在线重采样到 `250Hz`；
- 实现 `4s` 滑窗和 `2s` 步长；
- 输出与训练协议一致的窗口形状。

验收标准：

- 模型输入形状稳定为 `(1, 8, 1000)`；
- 窗口生成节奏稳定；
- 能输出 `PTP / RMS`。

### 阶段 C：打通 checkpoint 推理

目标：

- 加载 `best_long_t_new4_excl133728_plain_cnn.pt`；
- 执行实时推理；
- 输出三分类概率和置信度。

验收标准：

- 可以对连续窗口稳定输出 `left/right/feet` 概率；
- 前向推理耗时满足实时要求；
- 模型输出格式统一。

### 阶段 D：打通前后端实时可视化

目标：

- FastAPI 暴露 WebSocket；
- 前端替换 demo 数据源；
- 波形图、topomap、概率条接入真实数据。

验收标准：

- 网页可实时看到 EEG 波形更新；
- 概率条能反映实时推理；
- topomap 能随数据刷新。

### 阶段 E：打通硬件控制接口

目标：

- 增加 `DeviceAdapter`；
- 输出受控动作指令；
- 增加门控、冷却和日志。

验收标准：

- 外设可收到动作；
- 低置信度或低质量窗口不会误触发；
- 行为可追踪、可复现。

### 阶段 F：联调整体稳定性

目标：

- 验证长时间运行；
- 统计推理延迟、消息延迟、丢帧率；
- 校正 topomap 映射与动作策略。

验收标准：

- 连续运行稳定；
- 浏览器和硬件都能同步接收结果；
- 整体链路没有明显内存泄漏或阻塞。

## 13. 关键风险与应对

### 13.1 采样率不一致

风险：

- 上位机输出 `500Hz`，模型训练为 `250Hz`。

应对：

- 显式在线重采样；
- 在日志中记录原始采样率和目标采样率；
- 禁止隐式假设输入已经是 `250Hz`。

### 13.2 环境兼容问题

风险：

- 当前全局环境中 `torch==1.11.0` 与 `numpy==2.x` 存在 ABI warning。

应对：

- 已增加兼容导入层，减少导入期噪声；
- 真正联调实时推理前，建议准备独立虚拟环境。

### 13.3 电极映射不明确

风险：

- 若 `CH1~CH8` 与电极位置不明确，脑地形图解释性会偏弱。

应对：

- 先实现“工程可用版 topomap”；
- 后续根据真实 montage 升级。

### 13.4 模型线上抖动

风险：

- 连续窗口结果可能快速跳变。

应对：

- 增加概率平滑；
- 增加低置信度抑制；
- 增加多窗口投票。

### 13.5 外设误触发

风险：

- 推理错误直接传到控制层会带来不稳定动作。

应对：

- 默认 `hold`；
- 引入 `confidence threshold + cooldown + vote`；
- 先做观察模式，再切换执行模式。

## 14. 推荐开发顺序

建议实际实施时按以下顺序推进：

1. 修整 `eeg_client(1).py`，抽离为 `tcp_receiver.py`
2. 完成滚动缓存、重采样和滑窗
3. 接入 checkpoint 推理
4. 增加在线质量门控
5. 增加 FastAPI WebSocket 广播
6. 前端替换 demo 数据源
7. 增加 `DeviceAdapter`
8. 最后统一做长时间稳定性测试

## 15. 首版交付清单

首版建议交付以下成果：

- 可运行的 TCP 实时接收脚本
- 可运行的在线预处理与滑窗模块
- 可加载 checkpoint 的实时推理模块
- 可广播到网页的 WebSocket 后端
- 可展示真实数据的前端 dashboard
- 可发送动作的硬件适配器接口
- 一份联调说明文档

## 16. 当前结论

这条实时数据通路不需要推翻现有工程，而是应在当前仓库基础上分层补齐：

- 采集层补 TCP 稳定接入；
- 推理层从占位分类器切到 checkpoint CNN；
- 后端补实时分发；
- 前端从 demo 切到真实数据；
- 硬件层抽象为统一适配器。

只要在线协议严格贴合当前最佳离线训练协议，这条链路是具备较强落地可行性的。
