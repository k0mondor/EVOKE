"""
LK-M1299 EEG 数据实时接收 + 三分类示例
======================================
用法:
  1. 先在上位机电脑上打开 LK-M1299 上位机软件，连接设备并开始采集
  2. 将 TCP_IP 改为上位机电脑的局域网 IP
  3. 运行本脚本

TCP 协议格式 (每帧 328 字节):
  [0:4]   int32        采样点数 (固定 10)
  [4:8]   int32        采样率 (如 500)
  [8:328] float32[80]  10 samples * 8 channels (CH1..CH8 交替排列)

数据单位: uV (微伏)
"""

import socket
import struct
import time

# ==================== 配置 ====================
TCP_IP = "192.168.1.100"   # 改成上位机电脑的局域网 IP
TCP_PORT = 12345
SAVE_TO_CSV = False         # 是否保存原始数据到 CSV
# ===============================================

# 协议常量
HEADER_BYTES = 8
NUM_CHANNELS = 8
SAMPLES_PER_FRAME = 10
EXPECTED_FRAME_SIZE = HEADER_BYTES + SAMPLES_PER_FRAME * NUM_CHANNELS * 4  # = 328


def connect():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10.0)
    print(f"[EEG] 正在连接 {TCP_IP}:{TCP_PORT} ...")
    sock.connect((TCP_IP, TCP_PORT))
    sock.settimeout(None)
    print("[EEG] 连接成功! 等待数据...")
    return sock


def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("连接断开")
        buf += chunk
    return buf


def parse_frame(data):
    """解析一帧，返回 (sampling_rate, 通道数据列表)

    通道数据: list of 10 samples, 每个 sample 是 8 个 float 的列表
    """
    num_samples, sampling_rate = struct.unpack("<ii", data[:8])
    raw_floats = struct.unpack(f"<{num_samples * NUM_CHANNELS}f", data[8:])

    frames = []
    for s in range(num_samples):
        ch_values = list(raw_floats[s * NUM_CHANNELS : (s + 1) * NUM_CHANNELS])
        frames.append(ch_values)

    return sampling_rate, frames


def your_classifier(frame):
    """三分类算法占位函数

    Args:
        frame: list of 10 samples, 每个 sample 为 8 通道 float 列表
               shape = [10, 8]

    Returns:
        分类结果: 0, 1, 2 分别代表三个类别
    """
    # ==========================================
    # 在这里实现你的三分类算法
    # 示例: 返回 0
    # ==========================================
    return 0


def main():
    csv_file = None
    csv_writer = None
    frame_count = 0

    sock = connect()

    if SAVE_TO_CSV:
        import csv
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        csv_file = open(f"eeg_raw_{timestamp}.csv", "w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([f"CH{i+1}" for i in range(NUM_CHANNELS)])

    try:
        while True:
            data = recv_exact(sock, EXPECTED_FRAME_SIZE)

            sampling_rate, frames = parse_frame(data)

            if csv_writer is not None:
                for sample in frames:
                    csv_writer.writerow([f"{v:.3f}" for v in sample])

            result = your_classifier(frames)

            frame_count += 1
            if frame_count % 10 == 0:
                print(f"[EEG] 已接收 {frame_count} 帧 | "
                      f"采样率={sampling_rate}Hz | "
                      f"分类结果={result}")

    except KeyboardInterrupt:
        print("\n[EEG] 用户中断")
    except ConnectionError as e:
        print(f"[EEG] 连接错误: {e}")
    except Exception as e:
        print(f"[EEG] 异常: {e}")
    finally:
        sock.close()
        if csv_file:
            csv_file.close()
        print(f"[EEG] 已断开, 共接收 {frame_count} 帧")


if __name__ == "__main__":
    main()
