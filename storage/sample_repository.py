"""samples.json 로드/저장 (원자적 쓰기 + 동시성 충돌 감지). DataPersistence_PoC 패턴 이식."""
import hashlib
import json
import os
from pathlib import Path

from model.sample import Sample


class ConflictError(Exception):
    """마지막으로 불러온 이후 파일이 외부에서 변경되어 저장을 취소할 때 발생한다."""


def _sample_to_dict(sample: Sample) -> dict:
    return {
        "sample_id": sample.sample_id,
        "name": sample.name,
        "avg_production_time_min": sample.avg_production_time_min,
        "yield_rate": sample.yield_rate,
        "stock_qty": sample.stock_qty,
    }


def _sample_from_dict(data: dict) -> Sample:
    return Sample(
        data["sample_id"],
        data["name"],
        data["avg_production_time_min"],
        data["yield_rate"],
        data["stock_qty"],
    )


class SampleRepository:
    def __init__(self, path: Path):
        self._path = path
        self._last_loaded_hash = None
        self._loaded = False

    def _current_file_hash(self):
        if not self._path.exists():
            return None
        with self._path.open("rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def load(self) -> list[Sample]:
        if not self._path.exists():
            self._last_loaded_hash = None
            self._loaded = True
            return []
        with self._path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self._last_loaded_hash = self._current_file_hash()
        self._loaded = True
        return [_sample_from_dict(item) for item in data]

    def save(self, samples: list[Sample]) -> None:
        if self._loaded and self._current_file_hash() != self._last_loaded_hash:
            raise ConflictError(
                "시료 파일이 마지막으로 불러온 이후 외부에서 변경되었습니다. 저장을 취소합니다."
            )

        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump([_sample_to_dict(s) for s in samples], f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
        self._last_loaded_hash = self._current_file_hash()
