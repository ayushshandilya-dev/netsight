"""
live_sniffer.py
---------------
Real-time packet capture + live attack forecasting for SIH26153.

Sniffs packets directly from a live network interface with Scapy and reuses the
exact same 500-packet window accumulator as the offline PCAP path
(packet_features.ingest_packet / finalize_window), so a "live" window is
bit-identical to a file-driven one. Completed windows stream through the
deployed RandomForest / LSTM forecasters in a background thread and produce the
same JSON timeline shape as infer.run_inference.

Two sources:
  * mode="sniff"   — live interface capture (Scapy). On macOS/Linux this needs
    root (BPF). Failures (e.g. PermissionError) are surfaced to the UI instead
    of crashing the app.
  * mode="replay"  — streams the committed Friday-DDoS windows at a configurable
    cadence, so the entire live-forecasting experience can be demonstrated on
    any machine with no root and no network traffic. Feature-identical to the
    demo pipeline.

Designed to be driven from the Streamlit dashboard: a LiveSession is started in
daemon threads and read through session.snapshot() on every rerun — Streamlit's
st.fragment(run_every=...) powers the auto-refreshing live panel.
"""

import queue
import threading
import time
from collections import deque

import pandas as pd

from packet_features import ingest_packet, finalize_window, new_tweets
from infer import (
    RAW_FEATURE_COLS,
    RollingFeatureBuilder,
    WINDOW_SIZE,
    correlate_incidents,
)

DEFAULT_SOURCE = "dataset/demo_friday_ddos_windows.csv"
DEFAULT_LIVE_SOURCE = DEFAULT_SOURCE
BATCH_LIMIT = 16
RECOMPUTE_INC_EVERY = 40


def list_interfaces():
    """[(name, ip)] for interface sniffing; safe to call without root."""
    out = []
    try:
        from scapy.all import get_if_addr, get_if_list
        for name in get_if_list():
            try:
                addr = get_if_addr(name)
            except Exception:
                addr = ""
            if addr and not addr.startswith("0.0.0.0"):
                out.append((name, addr))
    except Exception:
        pass
    return out or [("en0", "unknown")]


class LiveState:
    """Thread-safe snapshot of a running live session."""

    def __init__(self, mode, iface=None, source=None):
        self.lock = threading.RLock()
        self.mode = mode
        self.iface = iface
        self.source = source
        self.running = False
        self.error = None
        self.packets = 0
        self.bytes = 0
        self.windows_total = 0
        self.alerts = 0
        self.peak_risk = 0.0
        self.current_window = 0
        self.pps_override = None
        self.started_at = time.time()
        self.last_update = None
        self.timeline = []
        self.incidents = []
        self._pkt_times = deque(maxlen=96)
        self._inc_since = 0

    def set_running(self, v):
        with self.lock:
            self.running = bool(v)

    def fail(self, msg):
        with self.lock:
            self.error = str(msg)
            self.running = False

    def bump_packets(self, count=1, abytes=0):
        with self.lock:
            self.packets += int(count)
            self.bytes += int(abytes)
            now = time.monotonic()
            for _ in range(min(int(count), 512)):
                self._pkt_times.append(now)
            self.last_update = time.time()

    def set_current_window(self, n):
        with self.lock:
            self.current_window = int(n)

    def set_pps(self, pps):
        with self.lock:
            self.pps_override = float(pps)

    def mark_window(self):
        with self.lock:
            self.windows_total += 1

    def append_timeline(self, entries):
        with self.lock:
            self.timeline.extend(entries)
            new_alerts = sum(1 for e in entries if e.get("predicted_alert"))
            self.alerts += new_alerts
            for e in entries:
                if float(e.get("risk_score", 0.0)) > self.peak_risk:
                    self.peak_risk = float(e.get("risk_score", 0.0))
            self.last_update = time.time()
            self._inc_since += len(entries)
            if self._inc_since >= RECOMPUTE_INC_EVERY:
                self._inc_since = 0
                try:
                    self.incidents = correlate_incidents(list(self.timeline))
                except Exception:
                    pass

    def snapshot(self):
        with self.lock:
            ptt = self._pkt_times
            pps = self.pps_override
            if pps is None and len(ptt) > 1:
                el = ptt[-1] - ptt[0]
                pps = (len(ptt) - 1) / el if el > 1e-9 else 0.0
            return {
                "mode": self.mode,
                "iface": self.iface,
                "source": self.source,
                "running": self.running,
                "error": self.error,
                "packets": self.packets,
                "bytes_mb": round(self.bytes / (1024 * 1024), 3),
                "windows_total": self.windows_total,
                "alerts": self.alerts,
                "peak_risk": round(self.peak_risk, 4),
                "current_window": self.current_window,
                "pps": round(max(pps or 0.0, 0.0), 1),
                "elapsed": round(time.time() - self.started_at, 1),
                "timeline": list(self.timeline),
                "incidents": list(self.incidents),
                "last_alert": next(
                    (e for e in reversed(self.timeline) if e.get("predicted_alert")),
                    None,
                ),
            }


class LiveSession:
    """Owns the capture + predict daemon threads for one live stream."""

    def __init__(self, engine, mode="replay", iface=None,
                 source=DEFAULT_SOURCE, rate=1.0, max_windows=0):
        self.engine = engine
        self.mode = mode
        self.iface = iface
        self.source = source
        self.rate = max(0.2, float(rate))
        self.max_windows = int(max_windows)
        self.state = LiveState(mode=mode, iface=iface, source=source)
        self._stop = threading.Event()
        self._q = queue.Queue()
        self._wid = 0
        self._tweets = new_tweets()
        self._builder = RollingFeatureBuilder()
        self._threads = []
        self._started = False

    # ----- lifecycle -----

    def start(self):
        if self._started:
            return
        self._started = True
        target = self._capture_loop if self.mode == "sniff" else self._replay_loop
        self._threads = [
            threading.Thread(target=target, daemon=True, name="capture"),
            threading.Thread(target=self._predict_loop, daemon=True, name="predict"),
        ]
        self.state.set_running(True)
        for t in self._threads:
            t.start()

    def stop(self):
        self._stop.set()
        self.state.set_running(False)

    # ----- capture loops -----

    def _capture_loop(self):
        try:
            from scapy.all import sniff

            def on_pkt(pkt):
                if self._stop.is_set():
                    return
                if not (pkt and pkt.haslayer("IP")):
                    # still count non-IP frames like the offline path does
                    self.state.bump_packets()
                    if self._tweets["n"] >= WINDOW_SIZE:
                        self._emit()
                    return
                self.state.bump_packets(abytes=int(pkt[0].len) if pkt[0].len else 0)
                ingest_packet(self._tweets, pkt)
                self.state.set_current_window(self._tweets["n"])
                if self._tweets["n"] >= WINDOW_SIZE:
                    self._emit()

            sniff(iface=self.iface, prn=on_pkt, store=False,
                  stop_filter=lambda p: self._stop.is_set())
        except PermissionError:
            self.state.fail(
                "Permission denied — live capture needs root/BPF. Run the app "
                "with sudo, or switch to Replay mode for a no-privilege demo.")
        except Exception as e:  # noqa: BLE001 — surface any capture failure to the UI
            self.state.fail(f"{type(e).__name__}: {e}")
        finally:
            self.state.set_running(False)

    def _replay_loop(self):
        try:
            df = pd.read_csv(self.source)
        except Exception as e:  # noqa: BLE001
            self.state.fail(f"Replay source unreadable: {e}")
            return
        cols = [c for c in RAW_FEATURE_COLS if c in df.columns]
        n = 0
        for _, r in df.iterrows():
            if self._stop.is_set():
                break
            if self.max_windows and n >= self.max_windows:
                break
            raw = {c: float(r[c]) for c in cols}
            self.state.bump_packets(count=WINDOW_SIZE,
                                    abytes=raw.get("byte_rate", 0.0) * 5.0)
            self.state.set_pps(raw.get("packet_rate", 0.0))
            self._q.put((self._wid, raw, str(r.get("attack_family", "none"))))
            self._wid += 1
            self.state.mark_window()
            self.state.set_current_window(0)
            time.sleep(1.0 / self.rate)
        self._stop.set()
        self.state.set_running(False)

    def _emit(self):
        n_actual = self._tweets["n"]
        if n_actual == 0:
            return
        w = finalize_window(self._tweets)
        if w is None:
            return
        self._q.put((self._wid, w, str(w.get("attack_family", "none"))))
        self._wid += 1
        self.state.mark_window()
        self.state.set_current_window(0)

    # ----- prediction loop -----

    def _predict_loop(self):
        pending = []
        while True:
            while len(pending) < BATCH_LIMIT:
                try:
                    pending.append(self._q.get(timeout=0.25))
                except queue.Empty:
                    break
            if not pending:
                if self._stop.is_set():
                    break
                continue
            self._flush(pending)
            pending = []

    def _flush(self, batch):
        raws, rows, gts = [], [], []
        for _wid, raw, gt in batch:
            self._builder.add(raw)
            rows.append(self._builder.row())
            raws.append(raw)
            gts.append(gt)
        preds = self.engine.predict_batch(rows, raws)
        entries = []
        for (wid, raw, gt), pred, row in zip(batch, preds, rows):
            if pred is None:
                entries.append(self._entry(wid, raw, gt, row, warming=True))
                continue
            risk, alert, family, stage, attr, zero_day = pred
            entries.append(self._entry(
                wid, raw, gt, row,
                risk=risk, alert=alert, family=family, stage=stage,
                attr=attr, zero_day=zero_day))
        self.state.append_timeline(entries)

    def _entry(self, wid, raw, gt, row, warming=False, risk=0.0, alert=False,
               family="none", stage="-", attr=None, zero_day=None):
        e = {
            "window_id": int(wid),
            "flows_in_window": WINDOW_SIZE,
            "gt_family": str(gt or "none"),
            "risk_score": round(float(risk), 4),
            "predicted_alert": bool(alert),
            "attack_family": family,
            "mitre_stage": stage,
            "attribution": attr,
            "zero_day": zero_day,
            "features": {k: round(float(raw.get(k, 0.0)), 3)
                         for k in RAW_FEATURE_COLS},
            "live": True,
            "mode": self.mode,
        }
        if warming:
            e["warming_up"] = True
            e["risk_score"] = 0.0
            e["predicted_alert"] = False
        elif alert:
            e["row76"] = {k: round(float(v), 6) for k, v in row.items()}
        return e