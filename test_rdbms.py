from rdbms import Recognizer, Parser, tokenizer, sql_grammar, SqlTreeReducer
from pprint import pformat, pprint
from contextlib import contextmanager
# testing utils
def assert_equal(actual, expected):
    assert actual == expected, f'{pformat(actual)} \nwas not equal to \n{pformat(expected)}'

@contextmanager
def expect_failure(*errors: type[BaseException]):
    
    try :
        yield
    except errors :
        pass
    except BaseException as e :
        raise AssertionError(f"block raised an unexpected error: ", e)
    else:
        raise AssertionError(f"block did not raise any of these errors: {errors}")

##

def test_parse_select_1():
    test_cases = [
        "SELECT 1",
        "SELECT 1;",
        "SELECT 1; SELECT 1",
        "SELECT 1; SELECT 1;",

        "SELECT * FROM Emp as e, Dept as d WHERE e.did = d.did;"
        "SELECT did, COUNT(*) AS n, AVG(salary) AS avg_sal FROM Emp WHERE age > 25 GROUP BY did HAVING COUNT(*) > 5 ORDER BY n DESC LIMIT 10;",
        "SELECT city FROM Emp UNION SELECT city FROM Dept",
        "SELECT t.did, t.n FROM (SELECT did, COUNT(*) AS n FROM Emp GROUP BY did) AS t WHERE t.n > 3;",
        "SELECT a e.d a.b+c.d-(-e.f) g AS f h FROM sometable JOIN someothertable USING d LEFT JOIN (select a,b FROM c WHERE d=e) AS asdasd ON a=d GROUP BY a b HAVING c=d",

        "SELECT COUNT(A) AS count_a FROM B;",
        "SELECT a+b FROM B GROUP BY a;",
        "SELECT COUNT(a) AS count_a FROM B",
        "SELECT COUNT(a) AS count_a FROM B GROUP BY a;",
        "SELECT COUNT(a) AS count_a FROM B GROUP BY a;",
        "SELECT a FROM B;",
        "SELECT COUNT(a) AS count_a FROM B GROUP BY b;",
        "SELECT b FROM B GROUP BY b;",
        "SELECT a FROM B GROUP BY b;",
    ]

    for document in test_cases:
        print(document)
        tokens = list(tokenizer(document))

        r = Recognizer(document=tokens, real_string_input=document, grammar=sql_grammar)
        r.earley_recognize()

        p = Parser(items=r.state_sets, document=tokens)
        parsetree = p.create_tree()

        assert SqlTreeReducer.ast(parsetree) is not None

def test_parse_create_table_1():
    return
    test_cases = [
        "CREATE TABLE employees (id NUM name VARCHAR password VARCHAR(64))",
        "CREATE TABLE employees (id NUM, name VARCHAR, password VARCHAR(64))",
        ]

    for document in test_cases:

        tokens = list(tokenizer(document))

        r = Recognizer(document=tokens, real_string_input=document, grammar=sql_grammar)
        r.earley_recognize()

        p = Parser(items=r.state_sets, document=tokens)
        parsetree = p.create_tree()

        assert SqlTreeReducer.ast(parsetree) is not None

def test_parse_insert_1():
    return
    test_cases = [   
        'INSERT INTO employees VALUES (1, 2, 3), ("A", "B", "asdasdasdasdasd"), (1,2,3,4,5,6,7,8,9)'
    ]

    for document in test_cases:

        tokens = list(tokenizer(document))

        r = Recognizer(document=tokens, real_string_input=document, grammar=sql_grammar)
        r.earley_recognize()

        p = Parser(items=r.state_sets, document=tokens)
        parsetree = p.create_tree()

        assert SqlTreeReducer.ast(parsetree) is not None


"SELECT COUNT(a) FROM B" # this should fail because a is not aggregated
"SELECT COUNT(a) FROM B GROUP BY a;" # this should fail because expressions values need to be renamed
"SELECT COUNT(a) AS count_a FROM B GROUP BY a;" # this should fail because a is aggregated twice
"SELECT a FROM B;" # this should work just fine
"SELECT COUNT(a) FROM B GROUP BY b;" # this should work just fine
"SELECT b FROM B GROUP BY b;" # this should work just fine
"SELECT a FROM B GROUP BY b;" # this should fail because a is not aggregated


"SELECT a FROM B JOIN B ON b1=b2" #should fail typecheck due to an ambiguous self join






# test runner

all_tests = [(key, value) for key, value in locals().items() if key.startswith('test')]

for name, t in all_tests :
    try:
        t()
        print(f'test passed: {name}')
    except BaseException as e:
        print(f'(!) test failed: {name}')
        print(type(e), e)
        raise e