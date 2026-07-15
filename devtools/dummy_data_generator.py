import random
import re

from model.sample import Sample

_NAME_PREFIXES = ["실리콘 웨이퍼", "GaN 에피택셜", "SiC 파워소자", "GaAs RF소자"]
_NAME_SUFFIXES = ["4인치", "6인치", "8인치", "12인치"]

_CUSTOMER_NAME_CANDIDATES = ["삼성전자 파운드리", "SK하이닉스", "TSMC코리아", "DB하이텍"]

_SAMPLE_ID_PATTERN = re.compile(r"^S-(\d+)$")


def _next_sample_id(existing_samples: list) -> str:
    max_number = 0
    existing_ids = {sample.sample_id for sample in existing_samples}
    for sample in existing_samples:
        match = _SAMPLE_ID_PATTERN.match(sample.sample_id)
        if match:
            max_number = max(max_number, int(match.group(1)))

    candidate_number = max_number + 1
    candidate_id = f"S-{candidate_number:03d}"
    while candidate_id in existing_ids:
        candidate_number += 1
        candidate_id = f"S-{candidate_number:03d}"
    return candidate_id


def generate_dummy_sample(sample_id: str, rng: random.Random) -> Sample:
    name = f"{rng.choice(_NAME_PREFIXES)}-{rng.choice(_NAME_SUFFIXES)}"
    avg_production_time_min = round(rng.uniform(0.1, 5.0), 2)
    yield_rate = round(rng.uniform(0.7, 1.0), 2)
    stock_qty = rng.randint(0, 1000)
    return Sample(sample_id, name, avg_production_time_min, yield_rate, stock_qty)


def generate_dummy_samples(count: int, existing_samples: list, rng: random.Random | None = None) -> list:
    if count < 0:
        raise ValueError("count는 0 이상이어야 합니다.")

    if rng is None:
        rng = random.Random()

    all_samples = list(existing_samples)
    generated = []
    for _ in range(count):
        sample_id = _next_sample_id(all_samples)
        sample = generate_dummy_sample(sample_id, rng)
        all_samples.append(sample)
        generated.append(sample)
    return generated


def generate_dummy_order_input(existing_samples: list, rng: random.Random | None = None) -> dict:
    if not existing_samples:
        raise ValueError("existing_samples는 비어 있을 수 없습니다.")

    if rng is None:
        rng = random.Random()

    sample = rng.choice(existing_samples)
    customer_name = rng.choice(_CUSTOMER_NAME_CANDIDATES)
    quantity = rng.randint(1, 500)
    return {
        "sample_id": sample.sample_id,
        "customer_name": customer_name,
        "quantity": quantity,
    }
