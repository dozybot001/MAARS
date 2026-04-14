"""Runtime NVIDIA GPU discovery for prompts (model / VRAM / compute capability / driver)."""

from __future__ import annotations

import csv
import functools
import io
import shutil
import subprocess

from backend.config import settings


def _run_smi_args(args: list[str], timeout: float) -> str | None:
    try:
        r = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


@functools.lru_cache(maxsize=1)
def _nvidia_smi_csv() -> str | None:
    """First successful nvidia-smi CSV probe (host or Docker). Cached per process."""
    q = [
        "--query-gpu=gpu_name,memory.total,memory.free,compute_cap,driver_version",
        "--format=csv,noheader,nounits",
    ]
    smi = shutil.which("nvidia-smi")
    if smi:
        out = _run_smi_args([smi, *q], timeout=10.0)
        if out:
            return out
    # Same image as start.sh / README — requires Docker + NVIDIA Container Toolkit.
    return _run_smi_args(
        [
            "docker",
            "run",
            "--rm",
            "--gpus",
            "all",
            "nvidia/cuda:12.8.0-runtime-ubuntu24.04",
            "nvidia-smi",
            *q,
        ],
        timeout=90.0,
    )


def _format_csv_body(csv_text: str) -> tuple[list[str], str | None]:
    """Return per-device English lines and a single driver version if present."""
    rows = list(csv.reader(io.StringIO(csv_text.strip())))
    if not rows:
        return [], None
    dev_lines: list[str] = []
    driver: str | None = None
    for i, row in enumerate(rows):
        if len(row) < 4:
            continue
        name, total_mib, free_mib, cc = (x.strip() for x in row[:4])
        extra = row[4].strip() if len(row) > 4 else ""
        if extra and (driver is None or extra != "[N/A]"):
            driver = extra
        try:
            total_i = int(float(total_mib))
            mib_note = f"{total_i} MiB VRAM total"
            if free_mib and free_mib != "[N/A]":
                free_i = int(float(free_mib))
                mib_note += f", {free_i} MiB free"
            gib = total_i / 1024.0
            mib_note += f" (~{gib:.1f} GiB)"
        except (ValueError, TypeError):
            mib_note = f"VRAM {total_mib} MiB (raw)"
        cc_note = f"compute capability {cc}" if cc and cc != "[N/A]" else ""
        parts = [f"GPU {i}: **{name}**", mib_note]
        if cc_note:
            parts.append(cc_note)
        dev_lines.append(" — ".join(parts))
    return dev_lines, driver


def gpu_disclosure_markdown() -> str:
    """
    English markdown fragment for Calibrate / Strategy / Execute / Evaluate context.
    When GPU is disabled in config, returns the CPU-only line only.
    """
    if not settings.docker_sandbox_gpu:
        return (
            "- **GPU:** not enabled (sandbox is CPU-only; set `MAARS_DOCKER_SANDBOX_GPU=true` for GPU)"
        )
    csv_body = _nvidia_smi_csv()
    if not csv_body:
        return (
            "- **GPU:** passthrough enabled in MAARS (`--gpus` on code_execute), but **could not probe** "
            "devices (no host `nvidia-smi` and/or `docker run --gpus all … nvidia-smi` failed). "
            "Treat as CUDA-capable NVIDIA hardware only if your Container Toolkit is working."
        )
    devices, driver = _format_csv_body(csv_body)
    if not devices:
        return (
            "- **GPU:** passthrough enabled, but **nvidia-smi output was empty or unparsable**"
        )
    lines = [
        "- **GPU:** NVIDIA device(s) visible to the host (same class of GPU is requested for each "
        "`code_execute` container via Docker `device_requests`):",
        *[f"  - {d}" for d in devices],
    ]
    if driver and driver != "[N/A]":
        lines.append(f"  - Driver version (reported): **{driver}**")
    lines.append(
        "  - *Use this for planning: pick batch sizes / model sizes that fit **free VRAM**, "
        "and CUDA/PyTorch builds matching the visible compute capability.*"
    )
    return "\n".join(lines)
