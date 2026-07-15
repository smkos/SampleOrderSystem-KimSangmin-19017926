from model.sample import Sample


class SampleRegistry:
    """등록된 시료를 인메모리로 보관하고, 등록 시 검증을 수행한다."""

    def __init__(self):
        self._samples: list[Sample] = []

    def register(self, sample: Sample):
        if any(existing.sample_id == sample.sample_id for existing in self._samples):
            raise ValueError(f"이미 등록된 시료 ID입니다: {sample.sample_id}")
        if not sample.name.strip():
            raise ValueError("시료명은 공백일 수 없습니다.")
        if not (0 < sample.yield_rate <= 1):
            raise ValueError(f"수율은 0보다 크고 1 이하여야 합니다: {sample.yield_rate}")
        self._samples.append(sample)

    def list_all(self) -> list[Sample]:
        return list(self._samples)

    def increase_stock(self, sample_id: str, qty: int) -> Sample:
        target = next((sample for sample in self._samples if sample.sample_id == sample_id), None)
        if target is None:
            raise ValueError(f"존재하지 않는 시료 ID입니다: {sample_id}")
        if qty < 0:
            raise ValueError(f"증가시킬 재고 수량은 0 이상이어야 합니다: {qty}")
        target.stock_qty += qty
        return target

    def decrease_stock(self, sample_id: str, qty: int) -> Sample:
        target = next((sample for sample in self._samples if sample.sample_id == sample_id), None)
        if target is None:
            raise ValueError(f"존재하지 않는 시료 ID입니다: {sample_id}")
        if qty < 0:
            raise ValueError(f"감소시킬 재고 수량은 0 이상이어야 합니다: {qty}")
        if target.stock_qty - qty < 0:
            raise ValueError(f"재고가 부족합니다: {sample_id}")
        target.stock_qty -= qty
        return target

    def search(self, keyword: str) -> list[Sample]:
        if not keyword.strip():
            return []
        keyword_lower = keyword.lower()
        return [
            sample
            for sample in self._samples
            if keyword_lower in sample.name.lower() or keyword_lower in sample.sample_id.lower()
        ]
