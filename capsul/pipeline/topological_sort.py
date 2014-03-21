#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
import logging


class GraphNode(object):
    """ Simple Graph Node Structure

    Attributes
    ----------
    name : str
        the node name
    meta : object
        a python object stored in the node
    links_to : list
         object to store the graph edges: sucessor
    links_from : list
        object to store the graph edges: predecessor
    links_to_degree : int
        degree of the node regarding the successors
    links_from_degree : int
        degree of the node regarding the predecessors

    Methods
    --------
    add_link_to
    remove_link_to
    add_link_from
    remove_link_from
    """

    def __init__(self, name, meta):
        """ Create a Graph Node

        Parameters
        ----------
        name: str (mandatory)
        the name of the node

        meta: object
        an python object to store in the node
        """
        self.name = name
        self.meta = meta
        # variables to store the graph edges
        self.links_to = []
        self.links_from = []
        # the degree of the node
        self.links_to_degree = 0
        self.links_from_degree = 0

    def add_link_to(self, node):
        """ Method to add a Successor

        Parameters
        ----------
        node: GraphNode (mandatory)
        the successor node
        """
        if node not in self.links_to:
            self.links_to.append(node)
            self.links_to_degree += 1

    def remove_link_to(self, node):
        """ Method to remove a Successor

        Parameters
        ----------
        node: GraphNode (mandatory)
        the successor node
        """
        if node in self.links_to:
            self.links_to.remove(node)
            self.links_to_degree -= 1

    def add_link_from(self, node):
        """ Method to add a Predecessor

        Parameters
        ----------
        node: GraphNode (mandatory)
        the predecessor node
        """
        if node not in self.links_from:
            self.links_from.append(node)
            self.links_from_degree += 1

    def remove_link_from(self, node):
        """ Method to remove a Predecessor

        Parameters
        ----------
        node: GraphNode (mandatory)
        the predecessor node
        """
        if node in self.links_from:
            self.links_from.remove(node)
            self.links_from_degree -= 1


class Graph(object):
    """ Simple Graph Structure on which we want to perform a
    topological tree (no cycle).

    The algorithm is based on the R.E. Tarjanlinear linear
    optimization (O(N+A)).

    Attributes
    ----------
    _nodes : dict
        the graph nodes {node.name: node}
    _links : list
        graph edges (from_node, to_node)

    Methods
    --------
    add_node
    find_node
    add_link
    topological_sort
    """

    def __init__(self):
        """ Create a Graph
        """
        self._nodes = {}
        self._links = []

    def add_node(self, node):
        """ Method to add a GraphNode in the Graph

        Parameters
        ----------
        node: GraphNode (mandatory)
        the node to insert
        """
        logging.debug("node: {0}".format(node.name))
        if not isinstance(node, GraphNode):
            raise Exception("Expect a GraphNode, got {0}".format(node))
        if node.name in self._nodes:
            raise Exception("Expect a GraphNode with a unique name, "
                            "got {0}".format(node))
        self._nodes[node.name] = node

    def find_node(self, node_name):
        """ Method to find a GraphNode in the Graph

        Parameters
        ----------
        node_name: str (mandatory)
        the name of the desired node
        """
        if node_name in self._nodes:
            return self._nodes[node_name]
        return None

    def add_link(self, from_node, to_node):
        """ Method to add an edge between two GraphNodes of the Graph

        Parameters
        ----------
        from_node: GraphNode (mandatory)
        a node in the graph
        to_node: GraphNode (mandatory)
        the successor node
        """
        logging.debug("link: {0}->{1}".format(from_node, to_node))
        if from_node not in self._nodes:
            raise Exception("Node {0} is not defined in the Graph."
                   "Use add_node() method".format(from_node))
        if to_node not in self._nodes:
            raise Exception("Node {0} is not defined in the Graph."
                   "Use add_node() method".format(to_node))
        if (from_node, to_node) not in self._links:
            self._nodes[to_node].add_link_from(self._nodes[from_node])
            self._nodes[from_node].add_link_to(self._nodes[to_node])
            self._links.append((from_node, to_node))

    def topological_sort(self):
        """ Perform the topological sort: find an order in which all the
        nodes can be taken.
        Step 1: Identify nodes that have no incoming link (nnil).
        Step 2: Loop until there are nnil
        a) Delete the current nodes c_nnil of in-degree 0.
        b) Place it in the output.
        c) Remove all its outgoing links from the graph.
        d) If the node has in-degree 0, add the node to nnil.
        Step 3: Assert that there is no loop in the graph.

        Returns
        -------
        output: list of tuple
        a list of ordered nodes with a tuple element containing the node
        name and the node meta element.
        """
        ordered_nodes = []

        # Step 1
        nnil = []
        for name, node in self._nodes.iteritems():
            if node.links_from_degree == 0:
                nnil.append(node)

        # Step 2
        while len(nnil):
        #-- a
            c_nnil = nnil.pop()
        #-- b
            ordered_nodes.append(c_nnil)
        #-- c
            for node in c_nnil.links_to:
                node.remove_link_from(c_nnil)
        #-- d
                if node.links_from_degree == 0:
                    nnil.append(node)

        # Step 3
        if len(ordered_nodes) == len(self._nodes):
            return [(node.name, node.meta) for node in ordered_nodes]
        else:
            raise Exception("There is loop in the Graph."
                            "Please inverstigate")


if __name__ == '__main__':

    """ A toy example:
    slip -> chaussettes -> chemise -> veste -> pantalon -> ceinture ->
    chaussures -> cravate
    """

    objects = ["chaussures", "chaussettes", "slip", "pantalon", "ceinture",
        "chemise", "veste", "cravate"]

    dependancies = [
        ("slip", "pantalon"),
        ("chemise", "cravate"),
        ("chemise", "pantalon"),
        ("pantalon", "ceinture"),
        ("chaussettes", "chaussures"),
        ("pantalon", "chaussures"),
        ("ceinture", "chaussures"),
        ("chemise", "veste"),
        ]

    g = Graph()

    for o in objects:
        g.add_node(GraphNode(o, None))

    for d in dependancies:
        g.add_link(d[0], d[1])

    r = g.topological_sort()
    r = [x[0] for x in r]
    print(" -> ".join(r))
