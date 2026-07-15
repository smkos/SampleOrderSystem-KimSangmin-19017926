class Sample:
    """시료 데이터만 보관하는 Model. 검증 로직은 SampleRegistry가 담당한다."""

    def __init__(self, sample_id: str, name: str, avg_production_time_min: float,
                 yield_rate: float, stock_qty: int):
        self.sample_id = sample_id
        self.name = name
        self.avg_production_time_min = avg_production_time_min
        self.yield_rate = yield_rate
        self.stock_qty = stock_qty
