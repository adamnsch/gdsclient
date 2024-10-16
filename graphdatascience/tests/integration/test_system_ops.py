import pytest

from graphdatascience.graph_data_science import GraphDataScience


def test_listProgress(gds: GraphDataScience) -> None:
    result = gds.beta.listProgress()

    assert len(result) >= 0


@pytest.mark.enterprise
def test_systemMonitor(gds: GraphDataScience) -> None:
    result = gds.alpha.systemMonitor()

    assert result["freeHeap"] >= 0
    assert len(result["ongoingGdsProcedures"]) >= 0


@pytest.mark.skip_on_aura
def test_sysInfo(gds: GraphDataScience) -> None:
    result = gds.debug.sysInfo()

    assert "gdsVersion" in (list(result["key"]))


@pytest.mark.enterprise
def test_is_licensed(gds: GraphDataScience) -> None:
    assert gds.is_licensed()
