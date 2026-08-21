// Aurelia AML synthetic graph import for Neo4j 5.x.
// Run only against a non-production demonstration database.

CREATE CONSTRAINT synthetic_customer_id IF NOT EXISTS
FOR (customer:SyntheticCustomer)
REQUIRE customer.customer_id IS UNIQUE;

LOAD CSV WITH HEADERS FROM 'file:///customers.csv' AS row
MERGE (customer:SyntheticCustomer {customer_id: row.customer_id})
SET customer.customer_type = row.customer_type,
    customer.segment = row.segment,
    customer.residence_country = row.residence_country,
    customer.data_class = row.data_class;

LOAD CSV WITH HEADERS FROM 'file:///graph_edges.csv' AS row
MATCH (source:SyntheticCustomer {customer_id: row.source_customer_id})
MATCH (target:SyntheticCustomer {customer_id: row.target_customer_id})
MERGE (source)-[relationship:TRANSFERRED_TO]->(target)
SET relationship.transaction_count = toInteger(row.transaction_count),
    relationship.amount_try = toFloat(row.amount_try),
    relationship.first_seen = datetime(row.first_seen),
    relationship.last_seen = datetime(row.last_seen),
    relationship.data_class = 'CONTROLLED_SYNTHETIC';

// Investigator view: short directed cycles. Results require human contextual review.
MATCH path = (a:SyntheticCustomer)-[:TRANSFERRED_TO]->(b:SyntheticCustomer)
             -[:TRANSFERRED_TO]->(c:SyntheticCustomer)-[:TRANSFERRED_TO]->(a)
WHERE a <> b AND b <> c AND c <> a
RETURN path
LIMIT 100;
