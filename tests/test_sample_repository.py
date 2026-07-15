import pytest

from model.sample import Sample
from storage.sample_repository import SampleRepository, ConflictError


def test_저장한_시료_목록을_그대로_불러온다(tmp_path):
    repo = SampleRepository(tmp_path / "samples.json")
    repo.save([Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480)])

    loaded = repo.load()

    assert len(loaded) == 1
    assert loaded[0].sample_id == "S-001"


def test_파일이_없으면_빈_목록을_반환한다(tmp_path):
    repo = SampleRepository(tmp_path / "samples.json")
    assert repo.load() == []


def test_쓰기_도중_실패해도_기존_파일이_손상되지_않는다(tmp_path, mocker):
    path = tmp_path / "samples.json"
    repo = SampleRepository(path)
    repo.save([Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480)])

    mocker.patch("storage.sample_repository.os.replace", side_effect=OSError("disk full"))
    with pytest.raises(OSError):
        repo.save([Sample("S-002", "GaN 에피택셜-4인치", 0.3, 0.78, 220)])

    # 실패 이전 저장 내용이 그대로 남아 있어야 한다
    assert repo.load()[0].sample_id == "S-001"


def test_로드_이후_외부에서_파일이_변경되면_저장시_충돌을_감지한다(tmp_path):
    path = tmp_path / "samples.json"
    repo = SampleRepository(path)
    repo.save([Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480)])

    loaded_repo = SampleRepository(path)
    loaded_repo.load()

    # 다른 프로세스가 파일을 직접 수정한 상황을 재현
    other_repo = SampleRepository(path)
    other_repo.save([Sample("S-999", "외부에서 추가된 시료", 0.1, 0.5, 10)])

    with pytest.raises(ConflictError):
        loaded_repo.save([Sample("S-002", "GaN 에피택셜-4인치", 0.3, 0.78, 220)])
