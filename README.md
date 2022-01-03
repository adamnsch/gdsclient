# gdsclient

**NOTE:** This is a work in progress and many GDS features are known to be missing or not working properly.

This repo hosts the sources for `gdsclient`, a Python wrapper API for operating and working with the [Neo4j Graph Data Science (GDS) library](https://github.com/neo4j/graph-data-science).
gdsclient enables users to write pure Python code to project graphs, run algorithms, and define and use machine learning pipelines in GDS.
The API is designed to mimic the GDS Cypher procedure API, but in Python code.
It abstracts the necessary operation of the Neo4j Python Driver to offer a simpler surface.

Please leave any feedback as issues on this repository.
Happy coding!


## Installation

To build and install `gdsclient` from this repository, simply run the following command:

```bash
pip install .
```


## Documentation

A minimal example of using `gdsclient` to connect to a Neo4j database and run GDS algorithms:

```python
from neo4j import GraphDatabase
from gdsclient import Neo4jQueryRunner, GraphDataScience

# Set up driver and gds module
URI = "bolt://localhost:7687"  # Override according to your setup
driver = GraphDatabase.driver(URI)  # You might also have auth set up in your db
gds = GraphDataScience(Neo4jQueryRunner(driver))
gds.set_database("my-db")  # Not using the default database

# Project your graph
G = gds.graph.project("graph", "*", "*")

# Run the PageRank algorithm with custom configuration
gds.pageRank.write(G, tolerance=0.5, writeProperty="pagerank")
```

For extensive documentation of all operations supported by GDS, please refer to the [GDS Manual](https://neo4j.com/docs/graph-data-science/current/).

Extensive end-to-end examples in Jupyter ready-to-run notebooks can be found in the `examples` directory:

* [Computing similarities with KNN based on FastRP embeddings](examples/fastrp-and-knn.ipynb)


## License

`gdsclient` is licensed under the Apache Software License version 2.0.
All content is copyright © Neo4j Sweden AB.


## Acknowledgements

This work has been inspired by the great work done in the following libraries:

* [pygds](https://github.com/stellasia/pygds) by stellasia
* [gds-python](https://github.com/moxious/gds-python) by moxious
