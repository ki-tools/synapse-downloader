from .synapse_proxy import SynapseProxy
import synapseclient as syn


class SynapseParentIter:
    """Iterator for traversing Synapse parents."""

    def __init__(self, syn_entity):
        """Instantiates a new instance.

        Args:
            syn_entity: The Synapse entity to start with.
        """
        self._current_entity = syn_entity

    def __iter__(self):
        return self

    def __next__(self):
        """Gets the next parent entity until the Project entity is found.

        NOTE: There is a parent above a Synapse Project but it is not accessible.

        Returns:
            The next Synapse parent.
        """
        if isinstance(self._current_entity, syn.Project):
            raise StopIteration()

        self._current_entity = SynapseProxy.get(self._current_entity.get('parentId', None))

        return self._current_entity

    def project(self):
        syn_parents = [self._current_entity] if isinstance(self._current_entity, syn.Project) else list(self)

        # The last item will always be a Synapse Project.
        return syn_parents[-1]
