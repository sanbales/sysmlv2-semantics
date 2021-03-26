from collections import defaultdict
import networkx as NX


class ModelingSession:
    """
    A class to contain a live, in-memory version of the model and support rapid execution of commands
    """

    def __init__(self, ele_list=None):
        self.lookup = ModelLookup()
        self.ele_list = ele_list
        self.graph_manager = GraphManager(session_handle=self)

    def thaw_json_data(self, jsons=()):
        self.lookup.memoize_many(ele_list=jsons)
        self.graph_manager.build_graphs_from_data(ele_list=jsons)

    def get_data_by_id(self, ele_id=''):
        trial = self.lookup.get_element_by_id(ele_id=ele_id)
        if trial is None:
            for ele in self.ele_list:
                if ele['@id'] == ele_id:
                    self.lookup.memoize_one(ele=ele)
                    return ele
        else:
            return trial

        raise ValueError("No element found with ID = " + str(ele_id))

    def get_name_by_id(self, ele_id=''):
        trial = self.get_data_by_id(ele_id=ele_id)
        if trial is not None and 'name' in trial:
            return trial['name']
        else:
            return None

    def get_metaclass_by_id(self, ele_id=''):
        trial = self.get_data_by_id(ele_id=ele_id)
        if trial is not None and '@type' in trial:
            return trial['@type']
        else:
            return None

    def get_all_of_metaclass(self, metaclass_name=''):
        if metaclass_name in self.lookup.metaclass_lookup:
            return [self.get_data_by_id(this_id) for this_id in self.lookup.metaclass_lookup[metaclass_name]]
        else:
            return []

    def feature_lower_multiplicity(self, feature_id=''):
        feature = self.get_data_by_id(feature_id)
        if feature['multiplicity'] is not None:
            if '@id' in feature['multiplicity']:
                mult = self.get_data_by_id(feature['multiplicity']['@id'])
                if '@id' in mult['lowerBound']:
                    return self.get_data_by_id(mult['lowerBound']['@id'])['value']

        return 1

    def feature_upper_multiplicity(self, feature_id=''):
        feature = self.get_data_by_id(feature_id)
        if feature['multiplicity'] is not None:
            if '@id' in feature['multiplicity']:
                mult = self.get_data_by_id(feature['multiplicity']['@id'])
                if '@id' in mult['upperBound']:
                    return self.get_data_by_id(mult['upperBound']['@id'])['value']

        return 1


class ModelLookup:
    """
    Support rapid return of commonly queried attributes such as name, id, and metatype
    """

    def __init__(self):
        self.id_memo_dict = {}
        self.metaclass_lookup = defaultdict(list)

    def memoize(self, *elements: dict):
        self.id_memo_dict.update({
            element['@id']: element
            for element in elements
        })
        types_mapping = defaultdict(list)
        _ = {
            types_mapping[element["@type"]].append(element["@id"])
            for element in elements
        }
        self.metaclass_lookup.update(types_mapping)

    def get_element_by_id(self, element_id: str = ""):
        return self.id_memo_dict.get(element_id, None)


class KernelReference:
    """
    Utility class to hold key information about the SysML v2 language
    """


class GraphManager:
    """
    Class to handle multiple syntactic graphs to support rapid analysis of the current model
    and also semantic interpretations
    """

    _TYPE_MAPPINGS = dict(
        Superclassing=dict(source="general", target="specific"),
        FeatureTyping=dict(source="type", target="typedFeature"),
        FeatureMembership=dict(source="owningType", target="memberFeature"),
    )

    def __init__(self, session_handle=None):
        self.graph = NX.MultiDiGraph()
        self.banded_featuring_graph = NX.DiGraph()
        self.session = session_handle

    def build_graphs_from_data(self, *elements):
        """
        Packs elements into utility syntax graphs for later processing
        :param ele_list: list of element JSONs to pack
        :return: nothing
        """

        for element in elements:
            element_type = element["@type"]
            mapping = self._TYPE_MAPPINGS.get(element_type, None)
            if mapping is None:
                continue
            source = element[mapping["source"]["@id"]]
            target = element[mapping["target"]["@id"]]



            if element['@type'] == 'Superclassing':
                general = element['general']['@id']
                specific = element['specific']['@id']
                self.superclassing_graph.add_node(general, name=self.session.get_name_by_id(ele_id=general))
                self.superclassing_graph.add_node(specific, name=self.session.get_name_by_id(ele_id=specific))
                self.superclassing_graph.add_edge(general, specific)

                self.banded_featuring_graph.add_node(general, name=self.session.get_name_by_id(ele_id=general))
                self.banded_featuring_graph.add_node(specific, name=self.session.get_name_by_id(ele_id=specific))
                self.banded_featuring_graph.add_edge(general, specific, kind='Superclassing')

            elif element['@type'] == 'FeatureTyping':
                typ = element['type']['@id']
                feature = element['typedFeature']['@id']

                # limit to part usages for now

                if self.session.get_metaclass_by_id(feature) == 'PartUsage':

                    self.feature_typing_graph.add_node(feature, name=self.session.get_name_by_id(ele_id=feature))
                    self.feature_typing_graph.add_node(typ, name=self.session.get_name_by_id(ele_id=typ))
                    self.feature_typing_graph.add_edge(feature, typ)

                    self.banded_featuring_graph.add_node(feature, name=self.session.get_name_by_id(ele_id=feature))
                    self.banded_featuring_graph.add_node(typ, name=self.session.get_name_by_id(ele_id=typ))
                    self.banded_featuring_graph.add_edge(feature, typ, kind='FeatureTyping')

            elif element['@type'] == 'FeatureMembership':
                owner = element['owningType']['@id']
                feature = element['memberFeature']['@id']

                # limit to part usages for now

                if self.session.get_metaclass_by_id(feature) == 'PartUsage':
                    self.part_featuring_graph.add_node(owner, name=self.session.get_name_by_id(ele_id=owner))
                    self.part_featuring_graph.add_node(feature, name=self.session.get_name_by_id(ele_id=feature))
                    self.part_featuring_graph.add_edge(owner, feature)

                    self.banded_featuring_graph.add_node(feature, name=self.session.get_name_by_id(ele_id=feature))
                    self.banded_featuring_graph.add_node(owner, name=self.session.get_name_by_id(ele_id=owner))
                    self.banded_featuring_graph.add_edge(owner, feature, kind='FeatureMembership')

    def get_feature_type_name(self, feature_id=''):
        types = list(self.feature_typing_graph.successors(feature_id))
        if len(types) > 1:
            return 'Multiple Names'
        else:
            return self.session.get_name_by_id(types[0])
