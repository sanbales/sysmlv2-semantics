from ..fixtures.data_loader import kerbal_model_loaded_client
from pymbe.graph.lpg import SysML2LabeledPropertyGraph
from pymbe.client import SysML2Client
import pytest
import networkx as nx

# there must be a way to reuse from other modules ..
@pytest.fixture
def kerbal_client() -> SysML2Client:

    return kerbal_model_loaded_client()


@pytest.fixture()
def kerbal_ids_by_type(kerbal_client) -> dict:

    ids_dict = {}

    all_elements = kerbal_client.elements_by_id

    for ele_id, ele in all_elements.items():
        if ele["@type"] in ids_dict:
            ids_dict[ele["@type"]].append(ele_id)
        else:
            ids_dict.update({ele['@type']: [ele_id]})

    return ids_dict

@pytest.fixture
def kerbal_lpg() -> SysML2LabeledPropertyGraph:
    new_lpg = SysML2LabeledPropertyGraph()
    client = kerbal_model_loaded_client()

    new_lpg.update(client.elements_by_id, False)

    return new_lpg


def test_graph_load(kerbal_lpg):

    assert len(kerbal_lpg.nodes) == 156
    assert len(kerbal_lpg.edges) == 389 - 156 # nodes + edges should be all elements from the client


def test_graph_projection_part_def_node_filter(kerbal_lpg, kerbal_ids_by_type):
    pdg = kerbal_lpg.get_projection("Part Definition Graph")

    # we actually lose a node on this one ...
    pdg_set = set(pdg.nodes.keys())
    kerbal_set = set(kerbal_ids_by_type['PartDefinition'])

    dropped_nodes = list(kerbal_set - pdg_set)
    test_node = dropped_nodes[0]

    assert kerbal_lpg.nodes[test_node]['name'] == 'Rocket'

    assert len(pdg.nodes) == len(kerbal_ids_by_type['PartDefinition']) - 1


def test_graph_projection_part_def_components(kerbal_lpg):
    pdg = kerbal_lpg.get_projection("Part Definition Graph")

    assert len(list(nx.connected_components(pdg.to_undirected()))) == 2


def test_graph_projection_part_def_components_are_dags(kerbal_lpg):
    pdg = kerbal_lpg.get_projection("Part Definition Graph")

    for comp in nx.connected_components(pdg.to_undirected()):
        connected_sub = nx.subgraph(pdg, list(comp))
        assert nx.is_directed_acyclic_graph(connected_sub)


def test_graph_projection_part_def_edges(kerbal_lpg):
    # check that nothing but Superclassing edges are allowed by the filter
    pdg = kerbal_lpg.get_projection("Part Definition Graph")

    assert all([edge[2] == 'Superclassing^-1' for edge in pdg.edges])