# Neo4j graph-loading contract

The Python pipeline performs reproducible graph analytics with NetworkX and exports `artifacts/results/graph_edges.csv`. The Cypher script demonstrates how the same synthetic network can be loaded into Neo4j for interactive investigation.

Copy `data/demo/customers.csv` and `artifacts/results/graph_edges.csv` into the Neo4j import directory, then execute `load_graph.cypher` with an appropriately restricted account.

This is an optional extension. It does not require or imply a hosted Neo4j instance, and graph relationships remain synthetic supporting evidence—not findings of wrongdoing.
