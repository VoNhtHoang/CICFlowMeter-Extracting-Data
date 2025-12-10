import zmq
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import threading
import signal
import sys, os
import time # Cần thiết cho việc kiểm tra RCVTIMEO


# ========= 
from FlowFlushTransform import *

# ========= TOÀN CỤC =========
CURR_DIR = Path.cwd()
# Kích thước timeout (miligiây)
TIMEOUT_MS = 500
BATCH_SIZE = 500000


class FlowZmqServer:
    def __init__( self, bind_addr="tcp://*:5555", batch_size=1000, output_dir="flows_parquet"):
        self.bind_addr = bind_addr
        self.batch_size = batch_size
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.ctx = zmq.Context.instance()
        self.sock = self.ctx.socket(zmq.PULL)
        self.sock.bind(self.bind_addr)
        
        # Điều này khiến sock.recv() thoát ra sau 500ms nếu không có tin nhắn
        self.sock.setsockopt(zmq.RCVTIMEO, TIMEOUT_MS) 

        self.flowFlushTransformer = FlowFlushTransformer(
            MINMAX_SCALER_PATH, STANDARD_SCALER_PATH, MINMAX_COLS, STANDARD_COLS, decimal_bin=6
        )
        self.curr_index_parquet = 0
        self.buffer = []
        self.header = None
        self.running = True

        print(f"[PY] ZMQ listening on {self.bind_addr}")

    # =========================
    # Core loop
    # =========================
    def run(self):
        print("[PY] Server running, press Ctrl+C to stop...")
        while self.running:
            try:
                # sock.recv() sẽ chặn tối đa TIMEOUT_MS
                msg = self.sock.recv(flags=0)
                # Nếu nhận được tin nhắn, xử lý nó
                self.handle_message(msg)
                
            except zmq.error.Again:
                # Xảy ra khi timeout (RCVTIMEO) hết hạn và không có tin nhắn. 
                # Đây là cách chúng ta cho phép vòng lặp kiểm tra self.running.
                continue 
                
            except zmq.ZMQError as e:
                # Xảy ra khi socket bị đóng từ bên ngoài (ví dụ: ZContext.term())
                # Hoặc khi có lỗi ZMQ khác
                if self.running: # Nếu lỗi không phải do lệnh tắt, log nó
                     print(f"[ERROR] ZMQ Error: {e}")
                break
                
            except Exception as e:
                print(f"[ERROR] General Error: {e}")
                self.running = False

        self.flush()
        self.close()

    # =========================
    # Message handler
    # =========================
    def handle_message(self, msg: bytes):
        # Giả định dữ liệu là JSON chứa header và flowDump
        data = json.loads(msg.decode("utf-8"))

        # # GỢI Ý: Kiểm tra xem message có phải là tin nhắn control để tắt server không
        # if "command" in data and data["command"] == "shutdown":
        #     self.stop()
        #     return
        
        # Logic trích xuất Flow
        if self.header is None and "header" in data:
            self.header = data["header"].split(",")

        if "flowDump" in data:
            flow_row = data["flowDump"].split(",")
            self.buffer.append(flow_row)

            if len(self.buffer) >= self.batch_size:
                self.flush()

    # =========================
    # Flush to parquet
    # =========================
    def flush_old(self):
        if not self.buffer or self.header is None:
            return

        # Đảm bảo header có số lượng cột khớp với buffer
        try:
            df = pd.DataFrame(self.buffer, columns=self.header)
        except ValueError as e:
            print(f"[ERROR] Column/Data mismatch during DataFrame creation: {e}")
            self.buffer.clear()
            return

        fname =  self.output_dir / f"{datetime.now().date()}" 
        if not os.path.exists(fname):
            os.makedirs(fname)
        fname = fname/ f"flows_{self.curr_index_parquet}.parquet"

        df.to_parquet(
            fname,
            engine="pyarrow",
            compression="snappy"
        )

        print(f"[PY] ✔ Flushed {len(self.buffer)} flows → {fname}")
        
        self.curr_index_parquet +=1;
        self.buffer.clear()
    
    def flush(self):
        if not self.buffer or self.header is None:
            return

        # Đảm bảo header có số lượng cột khớp với buffer
        try:
            df = pd.DataFrame(self.buffer, columns=self.header)
        except ValueError as e:
            print(f"[ERROR] Column/Data mismatch during DataFrame creation: {e}")
            self.buffer.clear()
            return
        
        fname = self.flowFlushTransformer.flush(df)
        
        if fname != None:
            print(f"[PY] ✔ Flushed {len(self.buffer)} flows → {fname}")
        
        self.buffer.clear()
    # =========================
    # Graceful shutdown
    # =========================
    def stop(self, *_):
        if self.running:
            print("\n[PY] Shutdown signal received. Starting graceful termination...")
            self.running = False
            # Nếu ZMQ.term() được gọi, nó sẽ hủy bỏ sock.recv()
            # Tùy thuộc vào phiên bản ZMQ/Python, có thể cần gọi ctx.term()
        
    def close(self):
        if self.sock:
            self.sock.close()
        if self.ctx:
            # ctx.term() sẽ hủy bất kỳ tác vụ chặn nào (như sock.recv())
            self.ctx.term() 
        print("[PY] ZMQ closed")

# =========================
# Entry point
# =========================
if __name__ == "__main__":
    server = FlowZmqServer(
        bind_addr="tcp://*:5555",
        batch_size=10
    )

    # Đăng ký hàm stop cho các tín hiệu
    signal.signal(signal.SIGINT, server.stop)
    signal.signal(signal.SIGTERM, server.stop)

    server.run()