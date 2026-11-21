import pytest
from tests.continuous_samples import run_continuous_case


@pytest.mark.parametrize('interval',[20,33,50,66])
@pytest.mark.parametrize('noise',[0,1.0])
def test_mixed_continuous_sequence_has_no_open_or_duplicate(interval,noise):
    result=run_continuous_case(interval,noise,7)
    assert result['expected']==10
    assert result['executed']==10,result
    assert result['missed']==result['wrong']==result['duplicates']==0
    assert result['owned_keys']==[]


def test_continuous_replay_is_deterministic():
    assert run_continuous_case(40,1.0,42)==run_continuous_case(40,1.0,42)
