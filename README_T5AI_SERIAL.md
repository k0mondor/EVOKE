# T5AI 串口输出

EEG 后端通过 T5AI 开发板自身的 USB 下载通道发送三分类结果，不需要外接 USB-TTL。

配置位于 `.env`：

```dotenv
EEG_DEVICE_MODE=serial
EEG_DEVICE_SERIAL_PORT=auto
EEG_DEVICE_SERIAL_BAUDRATE=115200
EEG_DEVICE_SERIAL_TIMEOUT_S=0.5
```

`auto` 会枚举 USB 串口，根据 T5AI 板载 CH342 的 `VID:PID=1A86:55D2` 和 A 通道标识找到命令口，同时排除 CH342-B 日志口。因此换电脑或 USB 插口导致 COM 编号变化时，不需要修改配置，程序中也没有写死具体 COM 编号。

如果同时连接多块 T5AI，程序会拒绝猜测目标板。这种情况下才需要运行 `--list` 查看端口，并把 `.env` 中的 `auto` 改为目标板的具体 COM 口。

串口格式为 `115200 8N1`、无校验、无流控、DTR/RTS 关闭；输出为 ASCII `0\n`、`1\n`、`2\n`，对应 `left`、`right`、`feet`。

自动识别并验证全部场景：

```powershell
python scripts/test_t5_serial.py --list
python scripts/test_t5_serial.py --all
python scripts/test_t5_serial.py --interactive
```

正常情况下脚本会先显示实际解析出的端口，再分别收到 `OK 0`、`OK 1`、`OK 2`。需要手动覆盖时使用 `--port COMx`。烧录工具或串口助手必须先关闭，避免占用同一个下载/命令口。后端断线后会重新枚举并连接 CH342-A，因此重新插拔后 COM 编号变化也可以恢复。
