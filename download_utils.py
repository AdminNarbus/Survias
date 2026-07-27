import os
import time


def find_completed_excel(download_dir):
    candidates = []

    for filename in os.listdir(download_dir):
        if not filename.lower().endswith(".xlsx"):
            continue

        file_path = os.path.join(download_dir, filename)
        if os.path.isfile(file_path):
            candidates.append(file_path)

    if not candidates:
        return None

    return max(candidates, key=os.path.getmtime)


def wait_for_download(download_dir, timeout=30, poll_interval=1):
    start_time = time.time()
    previous_candidate = None
    previous_size = None

    while time.time() - start_time < timeout:
        candidate = find_completed_excel(download_dir)

        if candidate:
            try:
                current_size = os.path.getsize(candidate)
            except FileNotFoundError:
                candidate = None
            else:
                if (
                    candidate == previous_candidate
                    and current_size == previous_size
                    and current_size > 0
                ):
                    return candidate

                previous_candidate = candidate
                previous_size = current_size

        time.sleep(poll_interval)

    return None
