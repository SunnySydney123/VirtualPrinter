#!/usr/bin/env python3
"""
VirtualPrinter.py
    written by Sunil Sharma (Tungsten Automation) provided as-is with no warranty.

A simple RAW print job listener and logger for Windows.
On startup, it prompts the user for the IP address to bind to,
creates a job folder for that IP, and saves all print jobs and logs there.

Example output folder:
    C:\VirtualPrinter\jobs\192.168.50.123\
Usage:
    python printer_catcher.py
to create an exe
    pyinstaller --onefile --console VirtualPrinter.py

Ctrl-C to stop gracefully.
"""

import socket
import threading
import os
import csv
from datetime import datetime, UTC
import itertools
import signal
import sys


# ---------------------------------------------
# BASE CONFIG — actual OUT_DIR is set dynamically
# ---------------------------------------------
PORT = 9100
BASE_OUT_DIR = r"C:\VirtualPrinter\jobs"

OUT_DIR = None       # Will be set after IP selection
LOG_CSV = None       # Will also be set after IP selection

SOCKET_TIMEOUT = 5.0
RECV_SIZE = 65536
MAX_WORKERS = 50

_seq_counter = itertools.count(1)
_active_workers = 0
_active_workers_lock = threading.Lock()
_shutdown_event = threading.Event()


# =====================================================
#              IP SELECTION & FOLDER SETUP
# =====================================================

def get_local_ips():
    """Return a list of local IPv4 addresses."""
    ips = set()
    hostname = socket.gethostname()

    # Direct host lookup
    try:
        host_ips = socket.gethostbyname_ex(hostname)[2]
        for ip in host_ips:
            if "." in ip:
                ips.add(ip)
    except:
        pass

    # Interface enumeration
    try:
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if "." in ip:
                ips.add(ip)
    except:
        pass

    return sorted(ips)


def prompt_for_bind_ip():
    print("==========================================")
    print(" VirtualPrinter - Network Binding Setup")
    print("==========================================\n")

    ips = get_local_ips()

    print("Available local IP addresses:")
    for ip in ips:
        print(f"  - {ip}")
    print()

    while True:
        user_ip = input("Enter the IP to bind to (or press Enter for 0.0.0.0): ").strip()

        if user_ip == "":
            return "0.0.0.0"

        try:
            socket.inet_aton(user_ip)
            return user_ip
        except socket.error:
            print("\nInvalid IPv4 address. Try again.\n")


def set_output_dirs(selected_ip):
    """
    Creates:
        C:\VirtualPrinter\jobs\<selected-ip>\
    And updates OUT_DIR and LOG_CSV.
    """
    global OUT_DIR, LOG_CSV

    OUT_DIR = os.path.join(BASE_OUT_DIR, selected_ip)
    LOG_CSV = os.path.join(OUT_DIR, "log.csv")

    # Ensure directory exists
    os.makedirs(OUT_DIR, exist_ok=True)


# =====================================================
#                     CSV / FS HELPERS
# =====================================================

def init_csv():
    new_file = not os.path.exists(LOG_CSV)
    if new_file:
        with open(LOG_CSV, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["timestamp", "filename", "client_ip", "client_port", "bytes", "duration_seconds"])


def append_log_row(row):
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(row)


# =====================================================
#                 CLIENT HANDLER THREAD
# =====================================================

def handle_client(conn, addr):
    global _active_workers
    start = datetime.now(UTC)
    client_ip, client_port = addr
    seq = next(_seq_counter)
    bytes_received = 0
    filename = None

    try:
        conn.settimeout(SOCKET_TIMEOUT)
        parts = []

        while True:
            try:
                chunk = conn.recv(RECV_SIZE)
            except socket.timeout:
                break

            if not chunk:
                break

            parts.append(chunk)
            bytes_received += len(chunk)

        if parts:
            ts = datetime.now(UTC).strftime("%d%m%Y-%H%M%S")
            filename = f"{ts}-{seq:05d}.raw"
            outpath = os.path.join(OUT_DIR, filename)

            with open(outpath, "wb") as fh:
                for p in parts:
                    fh.write(p)

            duration = (datetime.now(UTC) - start).total_seconds()
            print(f"[{datetime.now(UTC).isoformat()}] {client_ip}:{client_port} "
                  f"-> {filename} ({bytes_received} bytes, {duration:.2f}s)")

            append_log_row([
                datetime.now(UTC).isoformat(),
                filename,
                client_ip,
                client_port,
                bytes_received,
                f"{duration:.2f}"
            ])

        else:
            print(f"[{datetime.now(UTC).isoformat()}] {client_ip}:{client_port} -> (empty job)")
            append_log_row([
                datetime.now(UTC).isoformat(),
                "",
                client_ip,
                client_port,
                0,
                "0.00"
            ])

    except Exception as e:
        print(f"[ERROR] handling {addr}: {e}")

    finally:
        try:
            conn.close()
        except:
            pass

        with _active_workers_lock:
            _active_workers -= 1


# =====================================================
#                  MAIN SERVER LOOP
# =====================================================

def serve_forever(bind_addr):
    global _active_workers

    # Ensure folder + log file exist
    os.makedirs(OUT_DIR, exist_ok=True)
    init_csv()

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        listener.bind((bind_addr, PORT))
    except Exception as e:
        print(f"\nERROR: Cannot bind to {bind_addr}:{PORT}")
        print(f"Reason: {e}")
        sys.exit(1)

    listener.listen(128)
    listener.settimeout(1.0)

    print(f"\n==========================================")
    print(f" Listening on {bind_addr}:{PORT}")
    print(f" Saving jobs to: {OUT_DIR}")
    print(" Press Ctrl-C to stop.")
    print("==========================================\n")

    try:
        while not _shutdown_event.is_set():
            try:
                conn, addr = listener.accept()
            except socket.timeout:
                continue

            with _active_workers_lock:
                if _active_workers >= MAX_WORKERS:
                    print(f"[WARN] Too many workers ({MAX_WORKERS}). Dropping {addr}")
                    conn.close()
                    continue
                _active_workers += 1

            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        _shutdown_event.set()
        listener.close()

        while True:
            with _active_workers_lock:
                active = _active_workers
            if active == 0:
                break

            print(f"Waiting for {active} worker threads...")
            threading.Event().wait(0.5)

        print("Stopped.")


# =====================================================
#                     MAIN ENTRY
# =====================================================

def handle_signals():
    def _sig_handler(signum, frame):
        print(f"\nSignal {signum} received. Shutting down...")
        _shutdown_event.set()
    signal.signal(signal.SIGINT, _sig_handler)


if __name__ == "__main__":
    handle_signals()

    bind_ip = prompt_for_bind_ip()
    set_output_dirs(bind_ip)

    serve_forever(bind_ip)
