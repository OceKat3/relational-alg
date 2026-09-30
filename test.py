from parser import tokenizer

# tests from the assignment in brightspace

from pprint import pformat, pprint

def assert_equal(actual, expected):
    assert actual == expected, f'{pformat(actual)} \nwas not equal to \n{pformat(expected)}'

def test_tokenizer_1():

    document = "select[x1=3](R)"

    tokens = list(tokenizer(document))

    assert_equal(tokens, [
        ('identifier', 'select', 5),
        ('char', '[', 6),
        ('identifier', 'x1', 8),
        ('char', '=', 9),
        ('number', 3, 10),
        ('char', ']', 11),
        ('char', '(', 12),
        ('identifier', 'R', 13),
        ('char', ')', 14),
    ])

def test_tokenizer_2():

    document = "select[x1=3](R)"
    document_with_spaces = "  select  [   x1 =   3 ]  ( R  )  "

    tokens = list(tokenizer(document))
    tokens2 = list(tokenizer(document_with_spaces))

    assert len(tokens) == len(tokens2), f'parse lengths differ'

    for a, b in zip(tokens, tokens2) :
        assert_equal(a[:2], b[:2])

# tests 3 and 4 don't do much since my tokenizer reads each special character individually

def test_tokenizer_3():

    # my parser explicitly reads >= as two tokens, so this test doesn't do much
    
    document = "select[Age>=30](R)"

    assert_equal(list(tokenizer(document)), [
        ('identifier', 'select', 5),
        ('char', '[', 6),
        ('identifier', 'Age', 9),
        ('char', '>', 10),  ###
        ('char', '=', 11),  ###
        ('number', 30, 13),
        ('char', ']', 14),
        ('char', '(', 15),
        ('identifier', 'R', 16),
        ('char', ')', 17)
    ])

def test_tokenizer_4():

    document = "select[Age>-30](R)"

    tokens = list(tokenizer(document))

    assert any(x[:2] == ('char', '>') for x in tokens)
    assert any(x[:2] == ('char', '-') for x in tokens)
    assert any(x[:2] == ('number', 30) for x in tokens)

def test_tokenizer_5():

    document="select[Name=\"Bob)\"](R)"

    tokens = list(tokenizer(document))

    assert any(x[:2] == ('string_literal', 'Bob)') for x in tokens)

def test_tokenizer_6():

    document="select[Name=\"a,b\"](R)"
    
    tokens = list(tokenizer(document))

    assert any(x[:2] == ('string_literal', 'a,b') for x in tokens)

def test_tokenizer_7():

    document="select[Name=\"this is a \\\"string\\\" inside of a string\"](R)"
        
    tokens = list(tokenizer(document))

    assert any(x[:2] == ('string_literal', 'this is a "string" inside of a string') for x in tokens)

#this test doesn't do much, since the tokenizer cannot tell between keywords and identifiers
#this would fail in the grammar
def test_tokenizer_8():

    document="select[union=3](R)"
            
    tokens = list(tokenizer(document))

    assert any(x[:2] == ('identifier', 'union') for x in tokens)

def test_tokenizer_9():

    document="select[Name=\"Bob](R)"

    try :            
        tokens = list(tokenizer(document))
        
    except SyntaxError :
        pass
    except BaseException as e :
        raise e
    else :
        raise AssertionError('expected tokenizer to throw an error for the unclosed string')

def test_tokenizer_emptystring():

    document="select[Name=\"\"](R)"
        
    tokens = list(tokenizer(document))

    assert any(x[:2] == ('string_literal', '') for x in tokens)


from parser import Recognizer, Parser, RelationalTreeReducer

recognize = lambda document : Recognizer(
    document=list(tokenizer(document)),
    real_string_input=document,
).earley_recognize()

def parse_to_ast(document):

    tokens = list(tokenizer(document))

    recognizer = Recognizer(document=tokens, real_string_input=document)
    recognizer.earley_recognize()

    parser = Parser(items = recognizer.state_sets, document=recognizer.document)
    parse_tree = parser.create_tree()

    ast = RelationalTreeReducer().ast(parse_tree)

    return ast

# i don't do associativity for binary relational operators because I think it's not obvious
# these tests are still useful to make sure stuff works as expected

def test_grammar_10():

    from parser import Union, RelationSubtract, NamedRelation

    document1 = "(A union B) minus C"

    ast = parse_to_ast(document1)

    match ast :
        case RelationSubtract(
                left=Union(
                    left=NamedRelation(relation_name="A"), 
                    right=NamedRelation(relation_name="B")), 
                right=NamedRelation(relation_name="C")
            ) :
            return
        
    raise AssertionError(pformat(ast))

def test_grammar_11():

    from parser import Union, RelationSubtract, NamedRelation
    
    document1 = "A minus (B minus C)"

    ast = parse_to_ast(document1)

    match ast :
        case RelationSubtract(
                left=NamedRelation(relation_name="A"),
                right=RelationSubtract(
                    left=NamedRelation(relation_name="B"), 
                    right=NamedRelation(relation_name="C")
                ), 
            ) :
            return
        
    raise AssertionError(pformat(ast))

def test_grammar_12():

    from parser import Select, Not, And, Or, Less, Eq
    
    document1 = "select[not (a=1 and b=2) or c>3](R)"

    ast = parse_to_ast(document1)

    match ast :
        case Select(
                predicate=Or(
                    left=Not(And(Eq(), Eq())),
                    right=Less(),
                )
            ) :
            return
        
    raise AssertionError(pformat(ast))

# boolean operator precedence
def test_grammar_13():

    from parser import Select, Not, And, Or, Less, Eq
    
    document1 = "select[a=1 and b<2 or c=3](R)"

    ast = parse_to_ast(document1)

    match ast :
        case Select(
                predicate=Or(
                    left=And(Eq(), Less()),
                    right=Eq(),
                )
            ) :
            return
        
    raise AssertionError(pformat(ast))

def test_grammar_14():

    from parser import Project, Select, Eq, Less, ScalarLiteral, NamedRelation
    
    document1 = 'project[name](select[age>30](select[department="asd"](R)))'

    ast = parse_to_ast(document1)

    match ast :
        case Project(
                relation=Select(
                    predicate=Less(),
                    relation=Select(
                        predicate=Eq(right=ScalarLiteral()),
                        relation=NamedRelation()
                    )
                )
            ) :
            return
        
    raise AssertionError(pformat(ast))

def test_grammar_15():

    from parser import RelationSubtract, Union, Intersection
    
    document1 = '(A union B) minus (C intersect D)'

    ast = parse_to_ast(document1)

    match ast :
        case RelationSubtract(
            left=Union(),
            right=Intersection()
        ) :
            return
        
    raise AssertionError(pformat(ast))

def test_grammar_16():
    
    document1 = 'select[Age>30](R'

    try :
        ast = parse_to_ast(document1)
    except SyntaxError as e :
        assert 'did you mean' in str(e)
        assert ')' in str(e)
    else :
        raise AssertionError('expected syntaxerror')

def test_grammar_17():

    document1 = 'select[](R)'

    try :
        ast = parse_to_ast(document1)
    except SyntaxError as e :
        assert 'did you mean' in str(e)
        assert 'identifier' in str(e)
    else :
        raise AssertionError('expected syntaxerror')

def test_grammar_thetajoin():

    from parser import GenericJoin, Eq
    
    document1 = 'A join[cola=colb] B'

    ast = parse_to_ast(document1)
    
    match ast :
        case GenericJoin(
            jointype=('join', Eq, 'inner')
        ) :
            return
        
    raise AssertionError(pformat(ast))

def test_grammar_naturaljoin():

    from parser import GenericJoin, Eq
    
    document1 = 'A left join B'

    ast = parse_to_ast(document1)
    
    match ast :
        case GenericJoin(
            jointype=('join', 'natural', 'left')
        ) :
            return
        
    raise AssertionError(pformat(ast))

def test_grammar_invalid_join():

    document1 = 'A left outer join B'

    try :
        ast = parse_to_ast(document1)
    except SyntaxError as e :
        assert 'did you mean' in str(e)
        assert 'join' in str(e)
    else :
        raise AssertionError('expected syntaxerror')

# numeric and boolean evaluation tests

def test_expression_bedmas():

    document = "eval 1+2*3+4"

    ast = parse_to_ast(document)

    assert_equal(
        11, ast.eval([], {})
    )

def test_expression_comparison():

    document = "eval 1+5=2*3"

    ast = parse_to_ast(document)

    assert_equal(
        True, ast.eval([], {})
    )

def test_expression_double_minus():

    document = "eval 1--1"

    ast = parse_to_ast(document)

    assert_equal(
        2, ast.eval([], {})
    )

# this test specifically tests for a regression in a grammar bug i fixed
def test_expression_negation_in_multiplication():

    document = "eval -2*-3"

    ast = parse_to_ast(document)

    assert_equal(
        6, ast.eval([], {})
    )

def test_expression_inequality():

    document = "eval 1<2 and 2>1"

    ast = parse_to_ast(document)

    assert_equal(
        True, ast.eval([], {})
    )

def test_expression_bound_variable():
    document = "eval a+b"

    ast = parse_to_ast(document)

    from parser import BoundTuple, Relation

    r = Relation(
        cols = ['a', 'b'],
        data=[[1, 2]]
    )
    
    assert_equal(
        3, ast.eval(
            [r.index(0)], {}
        )
    )

def test_relation_compute():
    document = "compute[a+R.b as c](R)"

    ast = parse_to_ast(document)

    from parser import BoundTuple, Relation

    r = Relation(
        cols = ['a', 'b'],
        data=[[1, 2]]
    )

    result = ast.eval(
            [], {"R": r}
        )
    
    assert_equal(
        [[1,2,3]], result.data
    )
    assert_equal(
        ['R.a', 'R.b', 'c'], result.cols
    )

def test_relation_project():
    document = "project[a](R)"

    ast = parse_to_ast(document)

    from parser import BoundTuple, Relation

    r = Relation(
        cols=['a', 'b'],
        data=[[1, 2]]
    )

    result = ast.eval(
            [], {"R": r}
        )
    
    assert_equal(
        [[1]], result.data
    )
    assert_equal(
        ['R.a'], result.cols
    )

def test_relation_select():
    document = "select[a>2](R)"

    ast = parse_to_ast(document)

    from parser import BoundTuple, Relation

    r = Relation(
        cols=['a', 'b'],
        data=[[1, 2], [2,3], [3,4]]
    )

    result = ast.eval(
            [], {"R": r}
        )
    
    assert_equal(
        [[3,4]], result.data
    )
    assert_equal(
        ['R.a','R.b'], result.cols
    )

def test_relation_rename():
    document = "rename[a->x, b->y](R)"

    ast = parse_to_ast(document)

    from parser import BoundTuple, Relation

    r = Relation(
        cols=['a', 'b'],
        data=[[1, 2]]
    )

    result = ast.eval(
            [], {"R": r}
        )
    
    assert_equal(
        [[1,2]], result.data
    )
    assert_equal(
        ['R.x','R.y'], result.cols
    )

def test_relation_union():
    document = "A union B"

    ast = parse_to_ast(document)

    from parser import BoundTuple, Relation

    a = Relation(
        cols=['a', 'b'],
        data=[[1, 2], [1,3]]
    )
    b = Relation(
        cols=['a', 'b'],
        data=[[1, 2], [1,6]]
    )

    result = ast.eval(
        [], {"A": a, "B": b}
    )
    
    assert_equal(
        [[1,2], [1,3], [1,2], [1,6]], result.data
    )
    assert_equal(
        ['a','b'], result.cols
    )

def test_semantic_18():
    document = "select[a=b](R)"
    
    ast = parse_to_ast(document)

    from parser import BoundTuple, Relation

    r = Relation(
        cols=['a', 'b'],
        data=[[1, 2], [3,3]]
    )

    result = ast.eval(
            [], {"R": r}
        )
    
    assert_equal(
        [[3,3]], result.data
    )
    assert_equal(
        ['R.a','R.b'], result.cols
    )

def test_semantic_19():
    document = "employees join[employees.departmentid=departments.id] departments"
    
    ast = parse_to_ast(document)

    from parser import BoundTuple, Relation

    employees = Relation(
        cols=['id', 'departmentid'],
        data=[[1, 2], [3,3]]
    )
    departments = Relation(
        cols=['id'],
        data=[[3]]
    )

    result = ast.eval(
        [], {"employees": employees, "departments": departments}
    )
    
    assert_equal(
        [[3,3,3]], result.data
    )
    assert_equal(
        ['employees.id', 'employees.departmentid', 'departments.id'], result.cols
    )

def test_natural_join():
    document = "employees join departments"
    
    ast = parse_to_ast(document)

    from parser import GenericJoin, Relation

    employees = Relation(
        cols=['id', 'departmentid'],
        data=[[1, 2], [5,3]]
    )
    departments = Relation(
        cols=['id', 'name'],
        data=[[5, 'department']]
    )

    assert isinstance(ast, GenericJoin)

    result = ast.eval(
        [], {"employees": employees, "departments": departments}
    )
    
    assert_equal(
        [[5,3,'department']], result.data
    )
    assert_equal(
        ['id', 'departmentid', 'name'], result.cols
    )


# "Explain in your README why this query is unanswerable without rename"
# actually this query is totally answerable. use left and right
def test_semantic_20():
    document = "employees left join[left.managerid=right.id] employees"
    
    ast = parse_to_ast(document)

    from parser import BoundTuple, Relation

    employees = Relation(
        cols=['id', 'managerid'],
        data=[[1, 3], [2,3], [3,0]]
    )

    result = ast.eval(
        [], {"employees": employees}
    )
    
    assert_equal(
        [[1,3,3,0], [2,3,3,0], [3,0,None,None]], result.data
    )
    assert_equal(
        ['left.id', 'left.managerid', 'right.id', 'right.managerid'], result.cols
    )

def test_semantic_21():

    document = "R union S"
    
    ast = parse_to_ast(document)

    from parser import BoundTuple, Relation

    R = Relation(
        cols=['a', 'b'],
        data=[[1, 3], [2,3], [3,0]]
    )
    S = Relation(
        cols=['a', 'c'],
        data=[[1,7]]
    )

    try :
        result = ast.eval(
            [], {"R": R, "S":S}
        )
    except TypeError :
        pass
    else:
        raise AssertionError('bad union should raise an error')

def test_semantic_22():

    document = 'select[age<"30"](people)'
    
    ast = parse_to_ast(document)

    from parser import BoundTuple, Relation

    people = Relation(
        cols=['age'],
        data=[[20], [30], [40]]
    )

    try :
        result = ast.eval(
            [], {"people": people}
        )
    except TypeError :
        pass
    else:
        raise AssertionError('bad union should raise an error')

# my system explicitly does not remove duplicates to make it closer to SQL, for later in the project
def test_semantic_23():

    document = 'project[age](people)'
    
    ast = parse_to_ast(document)

    from parser import BoundTuple, Relation

    people = Relation(
        cols=['age', 'name'],
        data=[[20, 'a'], [30, 'b'], [40, 'c'], [30, 'd']]
    )

    result = ast.eval(
        [], {"people": people}
    )

    assert_equal(
        [[20], [30], [40], [30]],
        result.data
    )

# duplicates have no effect
def test_semantic_24():

    document = 'project[age age](people)'
    
    ast = parse_to_ast(document)

    from parser import BoundTuple, Relation

    people = Relation(
        cols=['age', 'name'],
        data=[[20, 'a'], [30, 'b'], [40, 'c'], [30, 'd']]
    )

    result = ast.eval(
        [], {"people": people}
    )

    assert_equal(
        [[20], [30], [40], [30]],
        result.data
    )
    assert_equal(
        ['people.age'],
        result.cols
    )

def test_semantic_24():

    document = 'select[false](people)'
    
    ast = parse_to_ast(document)

    from parser import BoundTuple, Relation

    people = Relation(
        cols=['age', 'name'],
        data=[[20, 'a'], [30, 'b'], [40, 'c'], [30, 'd']]
    )

    result = ast.eval(
        [], {"people": people}
    )

    assert result is not None

    assert_equal(
        ['people.age', 'people.name'],
        result.cols
    )


all_tests = [(key, value) for key, value in locals().items() if key.startswith('test')]

for name, t in all_tests :
    try:
        t()
        print(f'test passed: {name}')
    except BaseException as e:
        print(f'(!) test failed: {name}')
        print(type(e), e)
        raise e