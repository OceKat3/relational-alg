from rdbms import Recognizer, Parser, tokenizer, sql_grammar


test_cases = [
    "SELECT * FROM Emp as e, Dept as d WHERE e.did = d.did;"
    "SELECT did, COUNT(*) AS n, AVG(salary) AS avg_sal FROM Emp WHERE age > 25 GROUP BY did HAVING COUNT(*) > 5 ORDER BY n DESC LIMIT 10;",
    "SELECT city FROM Emp UNION SELECT city FROM Dept",
    "SELECT t.did, t.n FROM (SELECT did, COUNT(*) AS n FROM Emp GROUP BY did) AS t WHERE t.n > 3;",
    "SELECT a e.d a.b+c.d-(-e.f) g AS f h FROM sometable JOIN someothertable USING d LEFT JOIN (select a,b FROM c WHERE d=e) AS asdasd ON a=d GROUP BY a b HAVING c=d"
]

for document in test_cases:

    tokens = list(tokenizer(document))

    r = Recognizer(document=tokens, real_string_input=document, grammar=sql_grammar)
    r.earley_recognize()

    p = Parser(items=r.state_sets, document=tokens)
    parsetree = p.create_tree()


"SELECT COUNT(A) FROM B;" # this should fail because aggregate values need to be renamed