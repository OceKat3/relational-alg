from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

type Terminal = Callable[[Token], bool]
type grammartype = dict[str, list[list[str | Terminal]]]

from typing import Callable

START_SYMBOL = "^"

from functools import wraps

def hook_str_of_function(func:Terminal, display_text:str):
    setattr(func, "__str__", lambda : display_text)
    return func

def string_literal(token:Token) -> bool:
    return token[0] == 'string_literal'
hook_str_of_function(string_literal, 'string_literal')

def decimal(token:Token) -> bool:
    return token[0] == 'number'
hook_str_of_function(decimal, 'decimal')

protected_identifiers = set()

def literal_identifier(s:str):
    protected_identifiers.add(s.casefold())

    def predicate(token:Token) -> bool:
        return token[0] == 'identifier' and token[1] == s
    return hook_str_of_function(predicate, s)

def identifier(token:Token):
    return token[0] == 'identifier' and token[1].casefold() not in protected_identifiers
hook_str_of_function(identifier, 'identifier')

def special_char(s:str):
    def predicate(token:Token) -> bool:
        return token[0] == 'char' and token[1] in s
    return hook_str_of_function(predicate, s)

literal = special_char

arithmetic_grammar = {
    START_SYMBOL: [["sum"]],
    "sum": [["product"], ["sum", special_char("+"), "sum"]],
    "product": [["factor"], ["product", special_char("*"), "product"]],
    "factor": [[decimal], [special_char("("), "sum", special_char(")")]],
}


# earley parser somehow works for all three of these? 
# i thought that ambiguous grammars would break the parser, but clearly some ambiguous grammars work just fine
left_recursive_test_grammar = {
    START_SYMBOL: [["list"]],
    "list": [
        [decimal],
        ["list", special_char(','), decimal]
    ]
}
right_recursive_test_grammar = {
    START_SYMBOL: [["list"]],
    "list": [
        [decimal],
        [decimal, special_char(','), "list"]
    ]
}
ambiguous_recursive_test_grammar = {
    START_SYMBOL: [["list"]],
    "list": [
        [decimal],
        ["list", special_char(','), "list"]
    ]
}

def sql_keyword(keyword:str):
    assert ' ' not in keyword, f'sql keyword cannot contain a space: {keyword}'
    
    protected_identifiers.add(keyword.casefold())

    def predicate(token:Token) -> bool:
        return token[0] == 'identifier' and token[1].casefold() == keyword.casefold()
    return hook_str_of_function(predicate, keyword.upper())

import itertools
# https://stackoverflow.com/questions/1482308/how-to-get-all-subsets-of-a-set-powerset
def powerset(iterable):
    "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
    s = list(iterable)
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s)+1))

# i don't like this but it makes it easier to write SELECT
def expand_optionals(production: list[str | Terminal | list[str | Terminal]]) -> Generator[list[str | Terminal]]:
    num_optionals = sum(1 for x in production if isinstance(x, list))

    for chosen_optionals in powerset(range(num_optionals)) :
        optional_idx = 0
        out_production: list[str | Terminal] = []
        for x in production :
            if isinstance(x, list):
                if optional_idx in chosen_optionals :
                    out_production += x
                optional_idx += 1
            else:
                out_production.append(x)
        yield out_production

def listify_nonterminal(
        element: str, 
        separator:str | Terminal = special_char(','), 
        separator_optional:bool = True, 
        allow_separator_at_end:bool = False,
        recursion="right"
    ) -> grammartype:
    productions:list[list[str | Terminal]] = [
        [element], 
        [element + "_list", separator, element], 
        [element + "_list", element]
    ]
    if recursion == "left":
        print("warning, left recursion is really bad lol")
    if recursion == "right":
        productions = [x[::-1] for x in productions]
    if not separator_optional :
        productions.pop()
    if allow_separator_at_end :
        productions.append([element, separator])
    return {(element + "_list"): productions}

assert list(expand_optionals(["a", ["b", "c"], "d", ["e"]])) == [["a", "d"], ["a", "b", "c", "d"], ["a", "d", "e"], ["a", "b", "c", "d", "e"]]


# scalar: literal number or string
# scalar_expression: string or equation or attribute
# condition: boolean that might depend on identifiers
# numeric_expression: equation
# number: an int or float
# attribute: table.column or column
# attribute_list
# scalar_expression_list
sql_expression_grammar:grammartype = {
    "boolean_expression": [
        ["disjunct"]
    ],
    "disjunct":[
        ["conjunct", sql_keyword('or'), "disjunct"],
        ["conjunct"]
    ],
    "conjunct":[
        ["not", sql_keyword('and'), "conjunct"],
        ["not"]
    ],
    "not": [
        ["boolean_factor"],
        [sql_keyword('not'), "boolean_factor",]
    ],
    "boolean_factor": [
        [special_char('('), "boolean_expression", special_char(')')],
        ["condition"],
    ],

    "condition":[
        ["boolean_literal"],
        ["scalar_expression", special_char('<>'), "scalar_expression"],
        ["scalar_expression", special_char('='), "scalar_expression"],
        ["scalar_expression", special_char('<>'), special_char('='), "scalar_expression"],
        ["scalar_expression", special_char('='), special_char('='), "scalar_expression"],
    ],

    "boolean_literal": [
        [sql_keyword("true")],
        [sql_keyword("false")]
    ],

    "scalar": [
        ["number"],
        [string_literal]
    ],

    "scalar_expression": [
        ["numeric_expression"],
        [string_literal],
    ],

    "aggregate": [
        [sql_keyword("COUNT"), special_char('('), special_char('*'), special_char(')')],
        [sql_keyword("COUNT"), special_char('('), "boolean_expression", special_char(')')],
        [sql_keyword("COUNT"), special_char('('), "scalar_expression", special_char(')')],
        [sql_keyword("AVG"), special_char('('), "numeric_expression", special_char(')')],
        [sql_keyword("MIN"), special_char('('), "scalar_expression", special_char(')')],
        [sql_keyword("MAX"), special_char('('), "scalar_expression", special_char(')')],
    ],

    "numeric_expression": [
        ["additive"]
    ],

    "additive": [
        ["multiplicative", special_char('+-'), "additive"],
        ["multiplicative"],
    ],
    "multiplicative": [
        ["unm", special_char('*/'), "multiplicative"],
        ["unm"],
    ],
    "unm": [
        ["factor"],
        [special_char('-'), "factor"],
    ],
    "factor": [
        [special_char('('), "additive", special_char(')')],
        ["number"],
        ["attribute"],
        ["aggregate"]
    ],
    "number":[
        [decimal],
        [decimal, special_char('.'), decimal],
        [special_char('.'), decimal],
    ],
    "attribute": [
        [identifier],
        [identifier, special_char('.'), identifier],
    ],

    **listify_nonterminal("attribute"),
    **listify_nonterminal("scalar_expression"),
    "identifier_list": [
        [identifier],
        [identifier, "identifier_list"],
        [identifier, special_char(','), "identifier_list"]
    ]
}

sql_grammar:grammartype = {
    **sql_expression_grammar,

    START_SYMBOL: [["statement_list"]],

    # "input": [
    #     ["statement"],
    #     ["statement", special_char(';')],
    #     ["statement", special_char(';'), "input"]
    # ],
    **listify_nonterminal("statement", separator=special_char(';'), separator_optional=False, allow_separator_at_end=True),

    "statement": [
        ["create_table"],
        ["insert"],
        ["query"],
        # ["delete"]
    ],

    "query": [
        ["select"],
        ["select", "binary_relational_operator", "query"]
    ],

    "create_table": [
        [sql_keyword('CREATE'), sql_keyword('TABLE'), identifier, special_char('('), "column_def_list", special_char(')')]
    ],
    "type": [
        [sql_keyword('NUM')],
        [sql_keyword('VARCHAR')],
        [sql_keyword('VARCHAR'), special_char('('), decimal, special_char(')')]
    ],
    "column_def": [
        [identifier, "type"]
    ],
    **listify_nonterminal("column_def"),



    "insert": [
        [
            sql_keyword('INSERT'), sql_keyword('INTO'), identifier, 
            sql_keyword('VALUES'), "tuple_literal_list"
        ],
        [
            sql_keyword('INSERT'), sql_keyword('INTO'), identifier,
            special_char('('), "identifier_list", special_char(')'),
            sql_keyword('VALUES'), "tuple_literal_list"
        ]
    ],
    "tuple_literal": [
        [special_char('('), "scalar_expression_list", special_char(')')]
    ],
    **listify_nonterminal("tuple_literal"),


    "select": [
        *expand_optionals([
            sql_keyword('SELECT'),
            [sql_keyword('DISTINCT')],
            "select_result",
            ["from"],
            ["where"],
            ["groupby"],
            ["having"],
            ["orderby"],
            ["limit"]
        ]),
        *expand_optionals([
            sql_keyword('SELECT'),
            [sql_keyword('DISTINCT')],
            "select_result",
            [sql_keyword('AGGREGATE')],
            ["from"],
            ["where"],
        ])
    ],

    "select_item": [
        ["attribute"],
        ["scalar_expression", sql_keyword('AS'), identifier],
    ],
    **listify_nonterminal("select_item"),
    "select_result": [
        ["select_item_list"],
        [special_char('*')]
    ],

    "from": [
        [sql_keyword('FROM'), "table_or_subquery"],
        [sql_keyword('FROM'), "table_or_subquery", "join_clause"],
    ],
    "join_clause": [
        ["join_operator", "table_or_subquery", "join_condition"],
        ["join_operator", "table_or_subquery", "join_condition", "join_clause"],
        [special_char(','), "table_or_subquery"],
        [special_char(','), "table_or_subquery", "join_clause"]
    ],
    "table_or_subquery": [
        [identifier],
        [identifier, sql_keyword("AS"), identifier],
        [special_char('('), "query", special_char(')'), sql_keyword("AS"), identifier]
    ],
    "join_operator": [
        [sql_keyword('JOIN')],
        [sql_keyword('INNER'), sql_keyword('JOIN')],
        [sql_keyword('LEFT'), sql_keyword('JOIN')],
        [sql_keyword('CROSS'), sql_keyword('JOIN')]
    ],
    "join_condition": [
        [sql_keyword('ON'), "boolean_expression"],
    ],

    "where": [[sql_keyword('WHERE'), "boolean_expression"]],
    "groupby": [
        [sql_keyword('GROUP'), sql_keyword('BY'), "attribute_list"]
    ],

    "having": [[sql_keyword('HAVING'), "boolean_expression"]],

    "orderby": [[sql_keyword('ORDER'), sql_keyword('BY'), "scalar_expression_list"]],
    "limit": [[sql_keyword('LIMIT'), "number"]],

    "binary_relational_operator": [
        [sql_keyword("UNION")], 
        [sql_keyword("UNION"), sql_keyword("ALL")], 
        [sql_keyword("INTERSECT")],
        [sql_keyword("EXCEPT")],
    ],

}

from pprint import pformat
def check_grammar(grammar:grammartype):
    used = set()
    for key in grammar:
        for rule in grammar[key]:
            for symbol in rule:
                if type(symbol) == str :
                    used.add(symbol)
                    assert symbol in grammar, f"{key} -> ...{symbol}...,   {symbol} not found in grammar"
                elif isinstance(symbol, Callable):
                    assert isinstance(symbol(('identifier','aasdasd',5)), bool), f"{key} -> ...{symbol}..., {symbol} is not a function from tokens to bools"

    def production_to_str(production:list[str | Terminal]) -> str :
        return ' '.join([x.__str__() for x in production])
    def rule_to_str(rule:list[list[str | Terminal]]) -> str :
        return ' & '.join(production_to_str(x) for x in rule)

    for key1, key2 in itertools.combinations(grammar.keys(), 2) :
        if rule_to_str(grammar[key1]) == rule_to_str(grammar[key2]) :
            print(f"possibly duplicate rules {key1} and {key2}")

    for key1, key2 in itertools.combinations(grammar.keys(), 2) :
        productions1 = set(production_to_str(p) for p in grammar[key1])
        productions2 = set(production_to_str(p) for p in grammar[key2])

        intersection = productions1.intersection(productions2)
        if len(intersection) > 0 :
            print(f"possibly duplicate productions in {key1} and {key2} : {intersection}")
        
    
    unused = set(grammar.keys()).difference(used).difference({START_SYMBOL})
    if len(unused) > 0 :
        print(f"note, grammar did not use the following nonterminals: {unused}")

    def check_for_left_recursion(nonterminal:str, path:list[str]=[]):
        path = path + [nonterminal]
        left_productions = [x[0] for x in grammar[nonterminal]]
        for l in left_productions :
            if not isinstance(l, str) : continue
            if l in path :
                print('left recursive path: ', ' -> '.join(path + [l]))
            else:
                check_for_left_recursion(l, path)
    check_for_left_recursion(START_SYMBOL)

if __name__ == "__main__" :
    check_grammar(sql_grammar)





from typing import Any
from contextlib import contextmanager
from contextvars import ContextVar

type t_varchar = tuple[Literal["varchar"], int]

type t_type = type[int]|type[float]|type[bool]|type[str]|t_varchar

def is_any(inst, *types) -> bool :
    return any(isinstance(inst, t) for t in types)

def stringy_t(x): return x == str or isinstance(x, tuple)

def are_types_compatible(a:t_type, b:t_type) -> t_type | None:
    if a == b == int : return int
    if a in [int, float] and b in [int, float] : return float
    if isinstance(a, tuple) and isinstance(b, tuple) : return ("varchar", a[1]+b[1])
    if stringy_t(a) and stringy_t(b) : return str
    if a == b == bool : return bool
    return None

def sql_isinstance(x, t:t_type):
    if isinstance(t, tuple):
        return isinstance(x, str) and len(x) <= t[1]
    return isinstance(x, t)

@dataclass
class Table:

    name: str
    schema: list[ColDef]

    @dataclass
    class ColDef:
        name: str
        type: t_type
        hidden: bool = False

        def __repr__(self) -> str:
            return (self.name, getattr(self.type, '__name__', self.type)).__repr__()
        def __hash__(self) -> int:
            return self.__repr__().__hash__()
        def __eq__(self, other: object) -> bool:
            if isinstance(other, Table.ColDef) :
                return self.__repr__() == other.__repr__()
            else :
                return False

class SQLContext:

    tables:ContextVar[list[Table]] = ContextVar('sql_context_tables', default=[])
    
    aggregated_attributes:ContextVar[list[SQL.Attribute]] = ContextVar('sql_aggregate_attributes', default=[])
    in_aggregate_query:ContextVar[bool] = ContextVar('sql_in_aggregate_function', default=False)
    in_aggregate_function:ContextVar[bool] = ContextVar('sql_in_aggregate_function', default=False)

    @contextmanager
    @staticmethod
    def tables_in_scope(*tables: Table):
        with SQLContext.tables.set(SQLContext.tables.get() + list(tables)) :
            yield
        
class Database:

    def get_table_by_name(self, name:str) -> Table | None:
        raise NotImplementedError()


@dataclass
class MockDatabaseSchemaOnly(Database):
    mock_schema: list[Table]

    @staticmethod
    def from_tables(**schema: list[tuple[str, t_type]]) -> MockDatabaseSchemaOnly:

        for tablename, coldefs in schema.items() :
            for name, type in coldefs: 
                assert type == int or (isinstance(type, tuple) and type[0] == "varchar"), "bad types in mock database"

        return MockDatabaseSchemaOnly([
            Table(
                tablename,
                [Table.ColDef(*t) for t in coldefs]
            )
            for tablename, coldefs in schema.items()
        ])

    def get_table_by_name(self, name:str) -> Table | None:        
        return next((x for x in self.mock_schema if x.name == name), None)

class ExecutionContext:
    cur_database: ContextVar[Database | None] = ContextVar('current_database', default=None)

    @staticmethod
    def database() -> Database:
        db = ExecutionContext.cur_database.get()
        if db: return db
        raise ValueError("no database in context")
    
class Expr:

    class ScalarExpression:
        def eval(self, *a, **kwa) -> int | float | str:
            raise NotImplementedError()
        def typecheck(self) -> type[int]|type[float]|type[str]|t_varchar:
            raise NotImplementedError()

    class BooleanExpression:
        def eval(self, *a, **kwa) -> bool:
            raise NotImplementedError()
        def typecheck(self) -> type[bool]:
            raise NotImplementedError()

    @dataclass
    class BinaryScalarExpression(ScalarExpression):
        left:Expr.ScalarExpression
        right:Expr.ScalarExpression

        verb:str = ''
        def operation(self, x, y) -> int | float | str : raise NotImplementedError()

        def eval(self, *a, **kwa) -> int | float | str:
            left = self.left.eval(*a, **kwa)
            right = self.right.eval(*a, **kwa)
                        
            return self.operation(
                self.left.eval(*a, **kwa),
                self.right.eval(*a, **kwa)
            )

        def typecheck(self) -> type[int]|type[float]|type[str]|t_varchar:
            left = self.left.typecheck()
            right = self.right.typecheck()

            if left in [int, float] and right in [int, float] :
                return float
            if left == int and right == int :
                return int
            raise TypeError(f"cannot {self.verb} {left} and {right}")

    class Add(BinaryScalarExpression):
        operation = lambda self, x, y : x+y
        verb = 'add'
        def typecheck(self):
            left = self.left.typecheck()
            right = self.right.typecheck()

            if left in [int, float] and right in [int, float] :
                return float
            if left == int and right == int :
                return int
            if isinstance(left, tuple) and isinstance(right, tuple) :
                return ("varchar", left[1] + right[1])
            if stringy_t(left) and stringy_t(right) :
                return str

            raise TypeError(f"cannot {self.verb} {left} and {right}")
    class Subtract(BinaryScalarExpression):
        operation = lambda self, x, y : x-y
        verb = 'subtract'
    class Multiply(BinaryScalarExpression):
        operation = lambda self, x, y : x*y
        verb = 'multiply'
    class Divide(BinaryScalarExpression):
        operation = lambda self, x, y : x/y
        verb = 'divide'

    @dataclass
    class Unm(ScalarExpression):
        arg:Expr.ScalarExpression
        def eval(self, *a, **kwa) -> int | float:
            arg = self.arg.eval(*a, **kwa)
            return -arg #type: ignore
        
        def typecheck(self):
            t = self.arg.typecheck()
            assert t in [int, float], f"cannot negate {t} (unary minus)"
            return t

    @dataclass
    class BinaryCondition(BooleanExpression):
        left: Expr.ScalarExpression
        right: Expr.ScalarExpression

        def operation(self, x, y) -> bool: raise NotImplementedError()

        def eval(self, *a, **kwa) -> bool:
            left = self.left.eval(*a, **kwa)
            right = self.right.eval(*a, **kwa)
            self.counter += 1
            return self.operation(
                left, right 
            )

        def typecheck(self):
            left = self.left.typecheck()
            right = self.right.typecheck()
            if left in [int, float] and right in [int, float] : return bool
            if stringy_t(left) and stringy_t(right) : return bool
            raise TypeError(f"cannot compare ({self.__class__.__name__}) {left} and {right}")
            
    class Eq(BinaryCondition):
        operation = lambda self, x, y : x == y
    class Less(BinaryCondition):
        operation = lambda self, x, y : x < y
    class Leq(BinaryCondition):
        operation = lambda self, x, y : x <= y

    @dataclass
    class BinaryBooleanExpression(BooleanExpression):
        left: Expr.BooleanExpression
        right: Expr.BooleanExpression

        def operation(self, x, y) -> bool: raise NotImplementedError()

        def eval(self, *a, **kwa) -> bool:
            return self.operation(
                self.left.eval(*a, **kwa), self.right.eval(*a, **kwa)
            )
        def typecheck(self):
            left = self.left.typecheck()
            right = self.right.typecheck()
            assert left == right == bool, "how did this happen gerbert"
            return bool

    class And(BinaryBooleanExpression):
        operation = lambda self, x, y : x and y
    class Or(BinaryBooleanExpression):
        operation = lambda self, x, y : x or y

    @dataclass
    class Not(BooleanExpression):
        operand: Expr.BooleanExpression

        def eval(self, *a, **kwa) -> bool:
            return not self.operand.eval(*a, **kwa)
        def typecheck(self):
            t = self.operand.typecheck()
            assert t == bool, "how did this happen gerbert"
            return bool
    
    @dataclass
    class ScalarLiteral(ScalarExpression):
        val: str | float | int
        sqltype: type[int] | type[float] | type[str] | t_varchar
        def eval(self, *a, **kwa) -> int | float | str:
            return self.val
        
        def typecheck(self):
            if not sql_isinstance(self.val, self.sqltype) : 
                raise TypeError(f"could not be converted to {self.sqltype.__class__.__name__}: {self.val}")
            return self.sqltype

    @dataclass
    class BooleanLiteral(BooleanExpression):
        val: bool
        def eval(self, *a, **kwa) -> bool:
            return self.val
        
        def typecheck(self):
            assert isinstance(self.val, bool)
            return bool

    @dataclass
    class AggregateFunction():
        operand: Any
        def send(self, tuple) -> None:
            raise NotImplementedError()
        def flush(self) -> str | int:
            raise NotImplementedError()
        def typecheck(self) -> Any:
            if SQLContext.in_aggregate_function.get() :
                raise TypeError(f"cannot use nested aggregation ({self.__class__.__name__.upper()})")
             
    class Max(AggregateFunction):
        operand: Expr.ScalarExpression
        def typecheck(self):
            super().typecheck()
            with SQLContext.in_aggregate_function.set(True):
                t = self.operand.typecheck()
                assert t in [int, float] or stringy_t(t)
                return t
        
        
    class Min(AggregateFunction):
        operand: Expr.ScalarExpression
        def typecheck(self):
            super().typecheck()
            with SQLContext.in_aggregate_function.set(True):
                t = self.operand.typecheck()
                assert t in [int, float] or stringy_t(t)
                return t

    class Avg(AggregateFunction):
        operand: Expr.ScalarExpression
        def typecheck(self):
            super().typecheck()
            with SQLContext.in_aggregate_function.set(True):
                t = self.operand.typecheck()
                assert t in [int, float]
                return float

    @dataclass
    class Count(AggregateFunction):
        operand: Expr.BooleanExpression | Expr.ScalarExpression | Literal['*']
        def typecheck(self):
            super().typecheck()
            with SQLContext.in_aggregate_function.set(True):
                if self.operand == '*' : return int
                self.operand.typecheck()
                return int

class SQL:

    @dataclass
    class SQLNode:
        def typecheck(self) -> Any:
            raise NotImplementedError()

    @dataclass
    class ChainStatements(SQLNode):

        statements: list[SQL.Select | SQL.CreateTable | SQL.Insert]

        def typecheck(self):
            for statement in self.statements[:-1] :
                statement.typecheck()
            return self.statements[-1].typecheck()

    class Query(SQLNode):
        def typecheck(self) -> list[Table.ColDef]:
            raise NotImplementedError()
        
    @dataclass
    class Select(Query):
        items: list[Item | SQL.Attribute] | Literal['*']
        distinct: bool = False
        from_table: SQL.TableName | SQL.Subquery | None = None
        from_joins: list[SQL.Join | SQL.CommaJoin] | None = None
        where: Expr.BooleanExpression | None = None
        group_attributes: list[SQL.Attribute] | None = None
        having: Expr.BooleanExpression | None = None
        order_by: list[Expr.ScalarExpression] | None = None
        limit: int | None = None


        aggregated: bool = False
        out_cols: list[Table.ColDef] | None = None
        tables_in_context: list[Table] |None = None
        
        @dataclass
        class Item:
            value: Expr.ScalarExpression
            rename: str | None
            def typecheck(self) -> Table.ColDef:
                if isinstance(self.value, SQL.Attribute) :
                    return Table.ColDef(self.rename or self.value.col, self.value.typecheck())
                if self.rename is None :
                    raise TypeError("complex expressions in SELECT must be given a name")
                return Table.ColDef(self.rename, self.value.typecheck())

        def typecheck(self) -> list[Table.ColDef]:

            self.aggregated = self.aggregated or self.group_attributes is not None
            if not self.aggregated :
                assert self.having is None, f"cannot use HAVING without a GROUP BY"

            if self.from_joins :
                assert self.from_table, "how...."

            tables_in_context: list[Table] = []
            if self.from_table :
                tables_in_context.append(self.from_table.typecheck())
            for join in self.from_joins or [] :
                if isinstance(join, SQL.CommaJoin):
                    joinee_table = join.compute_table(tables_in_context[-1])    
                elif isinstance(join, SQL.Join):
                    joinee_table = join.compute_table()
                else:
                    raise TypeError("")
                
                if any(t for t in tables_in_context if t.name == joinee_table.name) :
                    raise TypeError(f"table name not unique: {joinee_table.name}")
                tables_in_context.append(joinee_table)


            with SQLContext.tables_in_scope(*tables_in_context) :
                if self.where : self.where.typecheck()

                for a in self.group_attributes or [] :
                    a.typecheck()

                for join in self.from_joins or [] :
                    join.typecheck()
                
                with SQLContext.aggregated_attributes.set(self.group_attributes or []) :
                    with SQLContext.in_aggregate_query.set(self.aggregated) :
                        out_cols:list[Table.ColDef] = []
                        def add_select_item(new_col:Table.ColDef):
                            if any(c for c in out_cols if c.name == new_col.name) :
                                raise TypeError(f"SELECT output contains ambiguous columns: {new_col.name}. Use AS to disambiguate")
                            out_cols.append(new_col)
                        
                        if self.items == '*' :
                            for table in tables_in_context :
                                for col in table.schema :
                                    add_select_item(col) 
                        else:                
                            for item in self.items :
                                if isinstance(item, self.Item) :
                                    add_select_item(item.typecheck())
                                elif isinstance(item, SQL.Attribute) :
                                    add_select_item(Table.ColDef(item.col, item.typecheck()))
                                else:
                                    raise TypeError("not a valid select item??", item)
                        
                        if self.having: 
                            self.having.typecheck()
                    

            self.out_cols = out_cols
            self.tables_in_context = tables_in_context
            return out_cols
                    
    @dataclass
    class Subquery(SQLNode):
        query: SQL.Query
        rename: str

        def typecheck(self) -> Table:
            assert self.rename is not None
            #no correlated subqueries
            with SQLContext.tables.set([]) :
                return Table(
                    self.rename,
                    self.query.typecheck()
                )
        @property
        def name(self) : 
            return self.rename
    
    @dataclass
    class Join(SQLNode):
        joinee: SQL.Subquery | SQL.TableName
        opname: Literal["INNER"] | Literal["LEFT"] | Literal["CROSS"]
        on: Expr.BooleanExpression

        def compute_table(self):
            return self.joinee.typecheck()

        def typecheck(self) -> None:
            assert self.on.typecheck() == bool
            assert self.opname in ["INNER", "LEFT", "CROSS"], f"invalid join, {self.opname}"

    # natural inner join
    @dataclass
    class CommaJoin(SQLNode):
        joinee: SQL.Subquery | SQL.TableName
        cols_in_common: list[Table.ColDef] | None = None
        left_table_name:str | None = None

        # mutates state of columns in the left table
        def compute_table(self, left_table: Table):
            self.left_table_name = left_table.name
            self.cols_in_common = []

            right_table = self.joinee.typecheck()
            left = dict((c.name, c) for c in left_table.schema)
            right = dict((c.name, c) for c in right_table.schema)

            key_overlap = set(left.keys()).intersection(right.keys())

            if len(key_overlap) == 0 :
                raise TypeError(f"comma join failed on {self.joinee.name}, no shared column names")

            for shared_colname in key_overlap :
                resultant_type = are_types_compatible(left[shared_colname].type, right[shared_colname].type)
                if not resultant_type:
                    # TODO give the user a warning?
                    continue
                self.cols_in_common.append(Table.ColDef(shared_colname, resultant_type))
                left[shared_colname].hidden = True
                right[shared_colname].type = resultant_type
            
            return right_table

        def typecheck(self) -> None:
            pass

    @dataclass
    class Insert(SQLNode):
        into: str
        data: list[list[Expr.ScalarExpression]]

        cols: list[str] | None = None
        
        into_table: Table | None = None

        # table.schema index -> given data index
        permutation: list[int] | None = None
        
        def typecheck(self) -> None:
            db = ExecutionContext.database()
            table = db.get_table_by_name(self.into)
            self.into_table = table
            if not table :
                raise TypeError(f"table does not exist: {self.into}")

            if self.cols :
                self.permutation = [None] * len(table.schema) #type: ignore
                assert self.permutation is not None
                
                seen_names = set()
                for input_idx, col in enumerate(self.cols) :
                    if col in seen_names :
                        raise TypeError(f"duplicate name in INSERT clause: {col}")
                    seen_names.add(col)

                    schema_idx, matching_col = next(((i, c) for i, c in enumerate(table.schema) if c.name == col), (None, None))
                    if matching_col is None or schema_idx is None :
                        raise TypeError(f"inserted column {col} does not exist in {self.into}")
                    self.permutation[schema_idx] = input_idx

                if len(self.cols) < len(table.schema) :
                    raise TypeError(f"inserting into {self.into}, missing some columns: {set(c.name for c in table.schema).difference(set(self.cols))}")
            
            for row in self.data:
                if len(row) != len(table.schema) : 
                    raise TypeError(f"wrong number of elements in tuple {row}, got {len(row)} elements but was expecting {len(table.schema)} elements in {self.into}")
                
                for i, coldef in enumerate(table.schema):
                    item = row[self.permutation[i]] if self.permutation is not None else row[i]
                    item_type = item.typecheck()
                    
                    if not are_types_compatible(item_type, coldef.type) :
                        # TODO pretty print coldef.type
                        raise TypeError(f"type mismatch, {item} is not {coldef.type}")
                    
                    if isinstance(item, Expr.ScalarLiteral) and isinstance(item_type, tuple) and isinstance(coldef.type, tuple) :
                        if item_type[1] > coldef.type[1] :
                            raise TypeError(f'string exceeds the size limit of VARCHAR({coldef.type[1]}): "{item.val}" ')
            
                
            
    @dataclass
    class CreateTable(SQLNode):
        tablename: str
        coldefs: list[Table.ColDef]

        def typecheck(self) -> Any:
            db = ExecutionContext.database()
            existing_table = db.get_table_by_name(self.tablename)
            if existing_table :
                raise TypeError(f"table already exists: {self.tablename}")

            seen_names = set()
            for col in self.coldefs :
                if col.name in seen_names :
                    raise TypeError(f"duplicate name in table definition: {self.tablename}.{col.name}")
                seen_names.add(col.name)

            return None
        
    @dataclass
    class Attribute(Expr.ScalarExpression):
        col: str
        table: str | None = None

        def is_in_groupby(self):
            if self.table :
                return any(x for x in SQLContext.aggregated_attributes.get() if x.table == self.table and x.col == self.col)
            else:
                return any(x for x in SQLContext.aggregated_attributes.get() if x.col == self.col)
    

        def is_aggregation_valid(self:SQL.Attribute):
            return SQLContext.in_aggregate_function.get() ^ SQLContext.in_aggregate_query.get() ^ self.is_in_groupby()
            
        def resolve_all(self:SQL.Attribute, check_hidden=False) -> Generator[tuple[Table, Table.ColDef]]:
            for table in SQLContext.tables.get() :
                if self.table and table.name != self.table : continue
                for col in table.schema :
                    if col.hidden and not check_hidden : continue
                    if col.name == self.col :
                        yield (table, col)

        def resolve(self:SQL.Attribute) -> tuple[Table, Table.ColDef]:
            resolutions = list(self.resolve_all())

            if len(resolutions) == 0 :
                resolutions = list(self.resolve_all(check_hidden=True))

            if len(resolutions) == 1 : return resolutions[0]
            if len(resolutions) == 0 : 
                available_attributes: list[str] = [
                    f"{table.name}.{col.name}"
                    for table in SQLContext.tables.get()
                    for col in table.schema
                ]
                raise TypeError(f"{self.col} could not be found in this context (available: {available_attributes})")
            raise TypeError(f"{self.col} is ambiguous in this context ({', '.join(f"{table.name}.{col.name}" for table,col in resolutions)})")
            
        def typecheck(self):

            table, col = self.resolve()
            self.table = table.name

            if self.is_aggregation_valid() :
                print(self)

                if not SQLContext.in_aggregate_query.get() :
                    raise TypeError(f"cannot aggregate {self.col} when not in an aggregate query. use SELECT ... AGGREGATE FROM, or SELECT ... GROUP BY")

                if SQLContext.in_aggregate_function.get() :
                    raise TypeError(f"cannot access aggregated field {self.col} inside an aggregate function")
                else:
                    raise TypeError(f"cannot access field {self.col} outside an aggregate function, did you mean to put {self.col} in GROUP BY?")

            return col.type

    
    @dataclass
    class TableName(SQLNode):
        original_name: str
        rename: str | None = None
        def typecheck(self) -> Table:

            db = ExecutionContext.database()
            table = db.get_table_by_name(self.original_name)
            if not table:
                raise TypeError(f"table {self.original_name} does not exist")
            return Table(self.rename or table.name, table.schema)
            
        @property
        def name(self) -> str: return self.rename or self.original_name 

    @dataclass
    class SetOperator(SQLNode):
        left: SQL.Query
        right: SQL.Query
        operator: Literal['UNION'] | Literal['UNION ALL'] | Literal['INTERSECT'] | Literal['EXCEPT']

        shared_cols: list[Table.ColDef] | None = None

        def check_schemas_compatible(self, left:list[Table.ColDef], right:list[Table.ColDef]):
            left_nameset = set(c.name for c in left)
            right_nameset = set(c.name for c in left)

            shared_names = left_nameset.intersection(right_nameset)

            if len(shared_names) == 0 :
                raise TypeError(f"cannot {self.operator}, no column names in common")

            shared_cols:list[Table.ColDef] = []

            for n in shared_names :
                left_col = next(c for c in left if c.name == n)
                right_col = next(c for c in right if c.name == n)

                resultant_type = are_types_compatible(left_col.type, right_col.type)
                if resultant_type :
                    shared_cols.append(Table.ColDef(n, resultant_type))

            if len(shared_cols) == 0 :
                raise TypeError(f"cannot {self.operator}, columns do not have compatible types: f{shared_names}")

            self.shared_cols = shared_cols
            return shared_cols

        def typecheck(self) -> list[Table.ColDef]:
            left = self.left.typecheck()
            right = self.right.typecheck()
            assert self.operator in ['UNION', 'UNION ALL', 'INTERSECT', 'EXCEPT']

            return self.check_schemas_compatible(left, right)
            


            


@dataclass
class Relation:
    cols: list[str]
    data: list[list[str | int | float]]

    _column_lookup: dict[str, int]

    def __init__(self, cols:list[str], data:list[list[str|int|float]]) -> None:
        self.cols = cols
        self.data = data

        self._column_lookup = dict(
            (col, i) for i, col in enumerate(cols)
        )

    def index(self, i:int) -> BoundTuple:
        return BoundTuple(self.data[i], self)

    def bound_tuples(self) -> Generator[BoundTuple]:
        for tup in self.data :
            yield BoundTuple(tup, self) # TODO performance: malloc will slow things down here

    def prettyprint(self):

        column_widths = [len(col) + 4 for col in self.cols]

        def print_aligned(objs:list):
            for o, w in zip(objs, column_widths):
                print(str(o).ljust(w), end='')
            print()

        print_aligned(self.cols)
        
        for t in self.data :
            print_aligned(t)

@dataclass
class BoundTuple:
    data: list[str | int | float]
    table: Relation
    
class AlgebraNode:
    allowed_types:list[type] = [object]
    counter:int = 0

    def is_allowed_type(self, arg:Any) -> bool:
        return any(isinstance(arg, T) for T in self.allowed_types)

    def eval(self, bound_tuples:list[BoundTuple], known_relations:dict[str, Relation]) -> Any:
        raise NotImplementedError()

class RelationExpression(AlgebraNode):
    def eval(self, *a, **kwa) -> Relation:
        raise NotImplementedError()


from itertools import chain

def match_attribute_name_to_tuples(attribute_name:str, bound_tuples:list[BoundTuple]) -> list[tuple[int,int]]:

    def match_one_tuple(bound_tuple:BoundTuple) :
        for colname in bound_tuple.table.cols :
            if colname == attribute_name or colname.split('.')[-1] == attribute_name :
                yield bound_tuple.table._column_lookup[colname]

    if len(bound_tuples) == 2 :
        if attribute_name.startswith('left.') :
            return [(0, j) for _, j in match_attribute_name_to_tuples(attribute_name.split('.')[-1], [bound_tuples[0]])]
        if attribute_name.startswith('right.') :
            return [(1, j) for _, j in match_attribute_name_to_tuples(attribute_name.split('.')[-1], [bound_tuples[1]])]

    def iter_matches():
        for i, t in enumerate(bound_tuples) :
            yield from map(lambda j : (i,j), match_one_tuple(t))

    return list(iter_matches())

# @dataclass
# class NamedAttribute(ScalarExpression):
#     attribute_name: str

#     _index_cache: tuple[int, int] | None = None

#     def use_cache(self, bound_tuples:list[BoundTuple]):
#         assert self._index_cache

#         i, j = self._index_cache

#         assert i < len(bound_tuples)
#         assert j < len(bound_tuples[i].data)

#         assert bound_tuples[i].table.cols[i].split('.')[-1] == self.attribute_name
#         return bound_tuples[i].data[j]

    
#     def eval(self, bound_tuples:list[BoundTuple], *a, **kwa):

#         if len(bound_tuples) == 0 :
#             raise NameError(f'attribute used in empty context: {self.attribute_name}')

#         try :
#             return self.use_cache(bound_tuples)
#         except :
#             self._index_cache = None

#         possible_matches = match_attribute_name_to_tuples(self.attribute_name, bound_tuples)
#         if len(possible_matches) == 0 :
#             raise NameError(f'Could not find attribute {self.attribute_name}')
#         if len(possible_matches) > 1 :
#             if len(bound_tuples) == 2 :
#                 raise NameError(f'{self.attribute_name} is ambiguous in this context. Use the left. and right. prefixes to disambiguate')
#             else :
#                 raise NameError(f'{self.attribute_name} is ambiguous in this context')

#         self._index_cache = possible_matches[0]
#         i, j = possible_matches[0]

#         return bound_tuples[i].data[j]

# @dataclass
# class NamedRelation(RelationExpression):
#     relation_name: str
#     def eval(self, bound_tuples, known_relations:dict[str, Relation]) -> Relation:
#         try :
#             relation = known_relations[self.relation_name]

#             return Relation(
#                 cols = [
#                     '.'.join(([self.relation_name] + c.split('.'))[-2:])
#                     for c in relation.cols
#                 ],
#                 data=relation.data
#             )
#         except KeyError as e :
#             raise NameError(f'Not a known relation: {self.relation_name}')



# @dataclass
# class UnaryRelational(RelationExpression):
#     relation: RelationExpression

#     def eval(self, *a, **kwa) -> Relation:
#         return self.operation(self.relation.eval(*a, **kwa))

#     def operation(self, r:Relation) -> Relation:
#         raise NotImplementedError()

# def project(self:Project, r:Relation) -> Relation:

#     projected_indices = []
#     used_cols = []
#     for i, col in enumerate(r.cols) :
#         projected_col = next((x for x in self.columns if col in x or col.split('.')[-1] in x), None)
#         if projected_col :
#             projected_indices.append(i)
#             used_cols.append(projected_col)

#     missed_cols = [x for x in self.columns if x not in used_cols]

#     if len(missed_cols) > 0 :
#         raise NameError(f"Projection failed, some colmmns not found: {', '.join(missed_cols)}")

#     return Relation(
#         cols=[r.cols[i] for i in projected_indices],
#         data=[
#             [d[i] for i in projected_indices]
#             for d in r.data
#         ]
#     )

# def select(self:Select, r:Relation) -> Relation:
#     return Relation(
#         cols=r.cols,
#         data=[
#             d.data
#             for d in r.bound_tuples()
#             if self.predicate.eval([d], {})
#         ]
#     )

# def rename(self:Rename, r:Relation) -> Relation:
#     def rename_col(col:str):
#         if col in self.renames : return self.renames[col]
        
#         split = col.split('.')
#         if len(split) == 2 and split[1] in self.renames : return f'{split[0]}.{self.renames[split[1]]}'
#         return col
    
#     return Relation(
#         cols = [rename_col(col) for col in r.cols],
#         data = r.data
#     )
    
# def compute(self:Compute, r:Relation) -> Relation:
#     return Relation(
#         cols = r.cols + [c[1] for c in self.computes],
#         data=[
#             d.data + [computation.eval([d], {}) for computation, _ in self.computes]
#             for d in r.bound_tuples()
#         ]
#     )

# @dataclass
# class Project(UnaryRelational):
#     columns: list[str]
#     operation = project

# @dataclass
# class Select(UnaryRelational):
#     predicate: BooleanExpression
#     operation = select
# @dataclass
# class Rename(UnaryRelational):
#     renames: dict[str, str]
#     operation = rename
# @dataclass
# class Compute(UnaryRelational):
#     computes: list[tuple[AlgebraNode, str]]
#     operation = compute


@dataclass
class BinaryRelationalExpression(RelationExpression):
    left:RelationExpression
    right:RelationExpression

    def operation(self, r1:Relation, r2:Relation) -> Relation:
        raise NotImplementedError()

    def eval(self, *a, **kwa) -> Relation:
        return self.operation(
            self.left.eval(*a, **kwa),
            self.right.eval(*a, **kwa)
        )

def strip_table_prefixes(relation:Relation) -> Relation :
    stripped = Relation(
        cols = [col.split('.')[-1] for col in relation.cols],
        data = relation.data
    )
    if len(set(stripped.cols)) < len(stripped.cols) :
        raise NameError(f'Schema ambiguity after removing relation prefixes: {', '.join(relation.cols)}')
    return stripped

def check_shared_columns(r1:Relation, r2:Relation, verb:str):
    colset1 = set(r1.cols)
    colset2 = set(r2.cols)

    if colset1 != colset2 :
        raise TypeError(f'Cannot perform {verb}: schemas do not match. left: {colset1}, right: {colset2}')

def union(self, r1:Relation, r2:Relation) -> Relation:

    r1 = strip_table_prefixes(r1)
    r2 = strip_table_prefixes(r2)

    check_shared_columns(r1, r2, 'union')

    return Relation(
        cols=r1.cols,
        data=r1.data + [
            [t[r2._column_lookup[r1col]] for r1col in r1.cols]
            for t in r2.data
        ]
    )
    
def intersection(self, r1:Relation, r2:Relation) -> Relation:

    r1 = strip_table_prefixes(r1)
    r2 = strip_table_prefixes(r2)

    check_shared_columns(r1, r2, 'intersection')

    return Relation(
        cols=r1.cols,
        data=[
            t
            for t in (
                [t[r2._column_lookup[r1col]] for r1col in r1.cols]
                for t in r2.data
            )
            if t in r1.data
        ]
    )

def subtract(self, r1:Relation, r2:Relation) -> Relation:

    r1 = strip_table_prefixes(r1)
    r2 = strip_table_prefixes(r2)

    check_shared_columns(r1, r2, 'subtraction')
    
    return Relation(
        cols=r1.cols,
        data=[
            t
            for t in (
                [t[r1._column_lookup[r2col]] for r2col in r2.cols]
                for t in r1.data
            )
            if t not in r2.data
        ]
    )

def divide(self, r1:Relation, r2:Relation) -> Relation:

    r1 = strip_table_prefixes(r1)
    r2 = strip_table_prefixes(r2)

    if not set(r2.cols).issubset(set(r1.cols)) :
        raise TypeError('Relation division failed: right side schema must be a subset of left side schema')

    cols_not_in_r2 = list(set(r1.cols).difference(set(r2.cols)))

    equivalence_classes:dict[tuple, set] = dict()

    for t in r1.data :
        equivalence_key = tuple(t[r1._column_lookup[c]] for c in cols_not_in_r2)
        residual = tuple(t[r1._column_lookup[c]] for c in r2.cols)

        if equivalence_key not in equivalence_classes :
            equivalence_classes[equivalence_key]= set()
        
        equivalence_classes[equivalence_key].add(residual)

    valid_equivalence_classes = [
        list(eq)
        for eq, residuals in equivalence_classes.items()
        if residuals == set(r2.data)
    ]

    return Relation(
        cols = cols_not_in_r2,
        data=valid_equivalence_classes
    )

def disambiguate_columns_for_join(r1:Relation, r2:Relation) -> tuple[Relation, Relation] :

    shared_columns = set(r1.cols).intersection(set(r2.cols))

    new_r1_cols = [*r1.cols]
    new_r2_cols = [*r2.cols]

    for s in shared_columns :
        i = r1._column_lookup[s]
        new_r1_cols[i] = f"left.{new_r1_cols[i].split('.')[-1]}"
        i = r2._column_lookup[s]
        new_r2_cols[i] = f"right.{new_r2_cols[i].split('.')[-1]}"

    return (
        Relation(
            cols=new_r1_cols,
            data=r1.data
        ),
        Relation(
            cols=new_r2_cols,
            data=r2.data
        )
    )

def join(self:GenericJoin, r1:Relation, r2:Relation) -> Relation:

    _, joiner, jointype = self.jointype

    if joiner != 'natural' :
        r1, r2 = disambiguate_columns_for_join(r1, r2)
    elif joiner == 'natural' :
        r1 = strip_table_prefixes(r1)
        r2 = strip_table_prefixes(r2)

    _join_condition: Callable[[BoundTuple, BoundTuple], bool] = lambda a, b : NotImplemented

    shared_columns = set(r1.cols).intersection(set(r2.cols))
    if joiner == 'natural' :
        _join_condition = lambda t1, t2 : all(
            t1.data[t1.table._column_lookup[col]]
            == t2.data[t2.table._column_lookup[col]]
            for col in shared_columns       
        )
    else :
        _join_condition = lambda t1, t2 : joiner.eval([t1,t2], {})

    def wrapper(*a):
        self.counter += 1
        return _join_condition(*a)
    join_condition = wrapper
    
    def get_fully_joined_relation():
        if jointype == 'inner' :
            return Relation(
                cols = r1.cols + r2.cols,
                data = [
                    t1.data + t2.data
                    for t1 in r1.bound_tuples()
                    for t2 in r2.bound_tuples()
                    if join_condition(t1, t2)
                ]
            )
        if jointype == 'left' :
            data = []
            for t1 in r1.bound_tuples() :
                any_matches = False
                for t2 in r2.bound_tuples() :
                    if not join_condition(t1, t2) : continue
                    any_matches = True
                    data.append(t1.data + t2.data)
                if not any_matches :
                    data.append(t1.data + ([None] * len(r2.cols)))
            return Relation(
                cols = r1.cols + r2.cols,
                data = data
            )
        if jointype == 'outer' :
            #maybe there is a symmetric algorithm for computing outer joins? i don't know it

            data = []
            r2_matches = [False] * len(r2.data)

            for t1 in r1.bound_tuples() :
                any_matches = False
                for i, t2 in enumerate(r2.bound_tuples()) :
                    if not join_condition(t1, t2) : continue
                    any_matches = True
                    r2_matches[i] = True
                    data.append(t1.data + t2.data)
                if not any_matches :
                    data.append(t1.data + ([None] * len(r2.cols)))

            for i, r2_match in enumerate(r2_matches) :
                if not r2_match :
                    data.append(([None] * len(r2.cols)) + r2.data[i])
            
            return Relation(
                cols = r1.cols + r2.cols,
                data = data
            )
        raise SyntaxError(f'invalid join type: "{jointype}"')

    r = get_fully_joined_relation()

    def remove_duplicate_columns(relation:Relation) -> Relation :
        nonduplicate_indices = []
        seen_set = set()
        for i, col in enumerate(relation.cols) :
            if col in seen_set : continue
            seen_set.add(col)
            nonduplicate_indices.append(i)
        return Relation(
            cols=[relation.cols[i] for i in nonduplicate_indices],
            data = [
                [t[i] for i in nonduplicate_indices]
                for t in relation.data
            ]
        )

    if joiner == 'natural' :
        return remove_duplicate_columns(r)
    return r

def cartesian_product(self, r1:Relation, r2:Relation) -> Relation:

    if not set(r1.cols).isdisjoint(set(r2.cols)) :
        raise TypeError(f'Cartesian product must be performed on disjoint schemas. Shared columns: {set(r1.cols).intersection(set(r2.cols))}')

    return Relation(
        cols = r1.cols + r2.cols,
        data = [
            t1 + t2
            for t2 in r2.data
            for t1 in r1.data
        ]
    )

    

class Union(BinaryRelationalExpression):
    operation = union
class Intersection(BinaryRelationalExpression):
    operation = intersection
class RelationSubtract(BinaryRelationalExpression):
    operation = subtract
class RelationDivide(BinaryRelationalExpression):
    operation = divide
class CartesianProduct(BinaryRelationalExpression):
    operation = cartesian_product

# type JoinSpecification = tuple[
#     Literal['join'],
#     Literal['natural'] | BooleanExpression,
#     Literal['inner'] | Literal['left'] | Literal['outer']
# ]

# @dataclass
# class GenericJoin(BinaryRelationalExpression):
#     jointype:JoinSpecification
#     operation = join




from typing import Literal, Generator, Iterable

type Token = tuple[Literal['string_literal'] | Literal['identifier'] | Literal['char'], str, int] \
    | tuple[Literal['number'], int, int]

def tokenizer(document: str) -> Generator[Token]:

    current_token = ""
    document_index = 0
    current_state = None # type: ignore

    WHITESPACE = lambda c : c in ' \t\n'

    ALLOWED_SPECIAL_CHARS = lambda c : c in '()[]{}<>=+*/-.,;'

    IDENTIFIER_BEGIN = lambda c : "a" <= c <= "z" or "A" <= c <= "Z" or c == '_'
    NUMBER = lambda c : "0" <= c <= "9"
    IDENTIFIER_BODY = lambda c : IDENTIFIER_BEGIN(c) or NUMBER(c)

    STRING_BEGIN = lambda c : c == "\""
    STRING_END = lambda c : c == "\""
    STRING_ESCAPE = lambda c : c == "\\"

    def escaped_string(next_char) -> Generator[Token]:
        nonlocal current_state, current_token
        current_token += next_char
        current_state = string
        yield from []

    def string(next_char) -> Generator[Token]:
        nonlocal current_state, current_token

        if STRING_END(next_char) :
            yield ('string_literal', current_token, document_index)
            current_state = document_begin
        elif STRING_ESCAPE(next_char) :
            current_state = escaped_string
        else :
            current_token += next_char
            current_state = string

    def identifier(next_char) -> Generator[Token]:
        nonlocal current_state, current_token

        if IDENTIFIER_BODY(next_char):
            current_token += next_char
        else:
            current_state = document_begin
            yield ('identifier', current_token, document_index-1)
            yield from document_begin(next_char)
        yield from []

    def number(next_char) -> Generator[Token]:
        nonlocal current_state, current_token
        if NUMBER(next_char) :
            current_token += next_char
        else :
            yield ('number', int(current_token), document_index-1)
            current_state = document_begin
            yield from document_begin(next_char)
        yield from []

    def document_begin(next_char: str) -> Generator[Token]:
        nonlocal current_state

        if IDENTIFIER_BEGIN(next_char) :
            current_state = identifier
            yield from identifier(next_char)
        elif STRING_BEGIN(next_char):
            current_state = string
        elif NUMBER(next_char) :
            current_state = number
            yield from number(next_char)
        elif WHITESPACE(next_char):
            pass
        elif ALLOWED_SPECIAL_CHARS(next_char):
            yield ('char', next_char, document_index)
        else:
            raise SyntaxError(f'unexpected character: "{next_char}"')
        yield from []
    current_state:Callable[..., Generator[Token]] = document_begin

    def document_loop() -> Generator[Token]:
        nonlocal document_index
        for character in document :
            yield from current_state(character)
            document_index += 1

        if len(current_token) > 0 :
            if current_state in [identifier, number] :
                yield from current_state(' ')
            elif current_state in [string, escaped_string] :
                raise SyntaxError('expected string to terminate at end of input')
            

    for token in document_loop():
        yield token
        current_token = ""


def is_token_terminal(token: str | Terminal | None):
    return type(token) != str

@dataclass
class ParsingItem:
    start:int
    rule: list[str | Terminal]
    goal: str
    progress:int = 0

    @property
    def next_token(self):
        return self.rule[self.progress] if self.progress < len(self.rule) else None

    @property
    def is_completed(self) -> bool:
        return self.progress == len(self.rule)

    @property
    def action_needed(self):
        if self.is_completed : return 'complete'
        
        waiting_on_terminal = is_token_terminal(self.next_token)

        return 'scan' if waiting_on_terminal else 'predict'

    @staticmethod
    def token_to_str(token: str | Terminal):
        return token.__str__()

    def __str__(self) -> str:
        return f"{self.goal} -> {' '.join(map(self.token_to_str, self.rule[:self.progress]))} . {' '.join(map(self.token_to_str, self.rule[self.progress:]))}  ({self.start})"

@dataclass
class Recognizer:

    document: list[Token]
    real_string_input: str
    grammar: grammartype = field(default_factory=lambda : relational_algebra_grammar)
    state_sets: list[list[ParsingItem]] = field(default_factory=lambda : [])

    def item_already_exists(self, i, new_item:ParsingItem):
        return any(
            other.rule == new_item.rule and 
            other.progress == new_item.progress and 
            other.start == new_item.start and 
            other.goal == new_item.goal
            for other in self.state_sets[i]
        )

    @staticmethod
    def repr_state_sets(state_sets) -> str :
        return "\n".join(
            f"=== {i} ===\n{'\n'.join(map(str, state_set))}"
            for i, state_set in enumerate(state_sets)
        )

    def complete(self, i, j):

        item:ParsingItem = self.state_sets[i][j]
        assert item.is_completed

        for other_item in self.state_sets[item.start] :

            if other_item.next_token != item.goal : continue

            next_item = ParsingItem(
                start = other_item.start,
                progress = other_item.progress + 1,
                rule = other_item.rule,
                goal = other_item.goal,
            )

            if self.item_already_exists(i, next_item) : continue

            self.state_sets[i].append(next_item)

    def predict(self, i, j):

        item:ParsingItem = self.state_sets[i][j]
        next_token = item.next_token
        assert isinstance(next_token, str)

        child_rules = self.grammar[next_token]

        for child_rule in child_rules :

            new_item = ParsingItem(rule=child_rule, goal=next_token, start=i)
            if self.item_already_exists(i, new_item) : continue

            self.state_sets[i].append(new_item)

    def scan(self, i, j):
        item:ParsingItem = self.state_sets[i][j]
        terminal_predicate = item.next_token
        assert isinstance(terminal_predicate, Callable)

        if i + 1 >= len(self.state_sets) or i >= len(self.document) : return

        next_symbol_in_stream = self.document[i]

        if terminal_predicate(next_symbol_in_stream) :
            next_item = ParsingItem(
                start = item.start,
                progress = item.progress + 1,
                rule = item.rule,
                goal = item.goal
            )

            if self.item_already_exists(i+1, next_item) : return
            self.state_sets[i+1].append(next_item)

    def diagnose_problem(self):

        if len(self.document) == 0 : 
            raise SyntaxError('recognizer got empty document, or no tokens were read')

        """
        1. invert the state sets, complete and incomplete
        2. find the maximum k for which there is a ((0) ^ -> alpha (end=k)) (there may be multiple items)
        3. since the parse failed, that item(s) still has a next_token. it is not complete
        4. recurse through next_token until they are all terminals. Then output, "expected one of (terminal1, terminal2) at k" 
        """

        inverted_state_sets = Parser.invert_items(self.state_sets, unsafe=True)

        def find_partially_completed_items(i:int, goal:str) -> list[InvertedItem]:

            candidates = [item for item in inverted_state_sets[i] if item.goal == goal]

            candidates = sorted(candidates, key=lambda item : item.end, reverse=False)
            
            if len(candidates) == 0 :
                # print('no candidates', i, goal)
                return []
            
            farthest_end = max(candidates, key=lambda c : c.end).end
            # print(goal, farthest_end)
            return [item for item in candidates]
            
            # print(candidates)
            # quit()
        seen_set:set[InvertedItem] = set()
        def diagnose_recursively(item:InvertedItem) -> set[InvertedItem]:
            if item in seen_set : return set()
            seen_set.add(item)

            
            # assert item.progress < len(item.rule)
            if item.progress == len(item.rule) : return set()

            if is_token_terminal(item.next_token) :
                assert is_token_terminal(item.next_token)
                return set([item]) #type: ignore
            else :
                next_goal = item.next_token
                assert isinstance(next_goal, str)

                items_which_would_have_completed_this_one = find_partially_completed_items(item.end, next_goal)

                out:set[InvertedItem] = set()
                for item in items_which_would_have_completed_this_one :
                    out.update(diagnose_recursively(item))

                return out
        
        items_waiting_for_terminal = diagnose_recursively(
            find_partially_completed_items(0, START_SYMBOL)[0]
        )
        
        farthest_parse_distance = max(items_waiting_for_terminal, key=lambda c : c.end).end
        farthest_parsed_items = [x for x in items_waiting_for_terminal if x.end == farthest_parse_distance and x.end > 0]

        def get_error_message(problem_items: list[InvertedItem]) -> str:

            problem_items = sorted(problem_items,key=lambda item : len(item.goal))

            previous_token_document_pos = self.document[max(problem_items[0].end - 1, 0)][2]

            preview_slice = slice(max(0,previous_token_document_pos-40), min(previous_token_document_pos+5, len(self.real_string_input)))

            document_neighbourhood = self.real_string_input[preview_slice]
            marker = ''.join([('^' if i == previous_token_document_pos else ' ') for i in range(len(self.real_string_input))][preview_slice])

            def terminal_to_str(item:InvertedItem):
                t:Terminal = item.next_token #type: ignore
                if t == identifier : return 'an identifier'
                if t == decimal : return 'a number'
                return f"'{t.__str__()}'"

            recommendations = []
            for item in problem_items :
                recommendation = terminal_to_str(item)
                if recommendation not in recommendations :
                    recommendations.append(recommendation)

            return f"did you mean:\n{', or '.join(recommendations)} \nat '{document_neighbourhood}' ?" \
                 f"\n     {marker}"

        # TODO this is a bit of a hack
        if len(farthest_parsed_items) == 0 :
            raise SyntaxError('Failed to parse beginning of string')

        raise SyntaxError(get_error_message(farthest_parsed_items))

    def earley_recognize(self):

        self.state_sets = [
            [] for x in self.document
        ] + [[]]

        self.state_sets[0] = [
            ParsingItem(rule=x, start=0, goal=START_SYMBOL)
            for x in self.grammar[START_SYMBOL]
        ]

        for i in range(len(self.document) + 1) :
            j = 0
            while j < len(self.state_sets[i]):

                match self.state_sets[i][j].action_needed:
                    case 'predict' :
                        self.predict(i, j)
                    case 'scan' :
                        self.scan(i, j)
                    case 'complete' :
                        self.complete(i, j)
                j += 1

        was_parse_successful = any(
            item.start == 0 and item.is_completed and item.goal==START_SYMBOL for item in self.state_sets[-1]
        )

        if not was_parse_successful :
            # print(
            #     self.repr_state_sets(self.state_sets)
            # )
            self.diagnose_problem()

        def remove_all_incomplete_items():

            for i, state_set in enumerate(self.state_sets) :
                self.state_sets[i] = [
                    item
                    for item in state_set
                    if item.is_completed
                ]

        # print([len(x) for x in self.state_sets])

        # print(
        #     self.repr_state_sets(self.state_sets)
        # )

        remove_all_incomplete_items()

        return was_parse_successful

@dataclass
class InvertedItem(ParsingItem):
    end: int = 0

    @staticmethod
    def from_item(item:ParsingItem, i:int, unsafe=False):
        if not unsafe:
            assert item.progress == len(item.rule)
        return InvertedItem(
            start=item.start,
            end=i,
            goal=item.goal,
            rule=item.rule,
            progress=item.progress
        )

    def __hash__(self) -> int:
        return str(self).__hash__()

    def __str__(self) -> str:
        return f"{self.start} {self.goal} -> {' '.join(map(self.token_to_str, self.rule[:self.progress]))} . {' '.join(map(self.token_to_str, self.rule[self.progress:]))}  ({self.end})"
    

class Parser:

    inverted_items: list[list[InvertedItem]]
    document: list[Token]
    seen_set:list[InvertedItem]

    def __init__(self, items: list[list[ParsingItem]], document: list[Token]):
        
        assert len(items) > 0
        
        self.inverted_items = Parser.invert_items(items)
        self.document = document

        self.seen_set = list()

        # print(Recognizer.repr_state_sets(self.inverted_items))

    @dataclass
    class Node:
        children: list[Parser.Node | Token]
        item:InvertedItem

        @property
        def symbol(self) -> str:
            return self.item.goal

        def to_printable_graph(self):
            return (self.symbol, [
                child if isinstance(child, tuple) else child.to_printable_graph() for child in self.children
            ])

        def prettyprint(self, indentation_level:int=0, simple=False):
            SPACE = '  '
            if (len(self.children) > 1) or not simple :                
                print(SPACE * indentation_level + self.item.goal)
            for child in self.children :
                if isinstance(child, Parser.Node) :
                    child.prettyprint(indentation_level+1, simple=simple)
                else :
                    print(SPACE * (indentation_level+1) + str(child))

    @staticmethod
    def invert_items(items: list[list[ParsingItem]], unsafe=False) -> list[list[InvertedItem]]:
        out = [[] for x in items]

        for i, state_set in enumerate(items):
            for item in state_set :
                out[item.start].append(InvertedItem.from_item(item, i, unsafe))

        return out

    def get_max_length_item(self, i:int, symbol:str, end:int) -> InvertedItem:

        state_set = self.inverted_items[i]

        try :
            return max(
                [item for item in state_set if item.goal == symbol and item not in self.seen_set and item.end <= end],
                key = lambda item : item.end,
            )
        except ValueError :
            raise RuntimeError(f"is the grammar ambiguous? ", i, symbol, end)

    def create_tree(self, i=0, symbol=START_SYMBOL, end=-1, recursive_depth:int = 0) -> Node :
        if end == -1 : end = len(self.document)

        # print(
        #     Recognizer.repr_state_sets(self.inverted_items)
        # )

        # print('    ' * recursive_depth, end=" ")
        # print(i, symbol, end)
        item = self.get_max_length_item(i, symbol, end)
       
        # print(str(item))
        self.seen_set.append(item)

        # print(f"={i}= {item.__str__()}")

        if symbol == START_SYMBOL and item.end != len(self.document) :
            print(i, symbol, item)
            raise SyntaxError(f'Failed to fully parse input')

        children:list[Parser.Node | Token] = []

        document_position = i
        
        for child_symbol in item.rule :

            if is_token_terminal(child_symbol) :
                children.append(self.document[document_position])
                document_position += 1
            else:
                assert isinstance(child_symbol, str)
                try :
                    child_node = self.create_tree(document_position, child_symbol, end=item.end, recursive_depth=recursive_depth+1)
                except BaseException as e :
                    print('asdasdasdasdasasdsd')
                    Parser.Node(item=item, children=children).prettyprint(simple=False)
                    exit()

                children.append(child_node)
                document_position = child_node.item.end

        return Parser.Node(
            item=item,
            children=children
        )

from itertools import chain
def dict_union(d1:dict, d2:dict):
    return dict(
        chain(d1.items(), d2.items())
    )


from math import log10, floor    
class SqlTreeReducer:
    @classmethod
    def ast(cls, node:Parser.Node) -> SQL.SQLNode | None:

        statements = [x for x in cls.reduce(node) if x is not None]
        assert isinstance(statements, list)
        if len(statements) == 0 : return None

        if len(statements) == 1 :
            return statements.pop()
        else:
            root = SQL.ChainStatements(statements)

        return root
    
    @classmethod
    def make_sql_tokens_uppercase(cls, node:Parser.Node):
        for i, (token_or_node, target) in enumerate(zip(node.children, node.item.rule)) :
            if not isinstance(token_or_node, tuple): continue
            kind, data, charpos = token_or_node
            if target.__str__() == target.__str__().upper() and kind != 'number' and isinstance(data, str) :
                node.children[i] = (kind, data.upper(), charpos)
    
    @classmethod
    def reduce(cls, node:Parser.Node) -> Any:
        
        cls.make_sql_tokens_uppercase(node)

        match node.item.goal, *node.children :

            # list
            case nonterminal, Parser.Node() as element if nonterminal.endswith('_list') :
                return [cls.reduce(element)]
            case nonterminal, Parser.Node() as element, Parser.Node() as rest_of_list if nonterminal.endswith('_list') :
                return [cls.reduce(element)] + cls.reduce(rest_of_list)
            case nonterminal, Parser.Node() as element, (_, _, _), Parser.Node() as rest_of_list if nonterminal.endswith('_list') :
                return [cls.reduce(element)] + cls.reduce(rest_of_list)
            case nonterminal, Parser.Node() as element, (_, _, _) if nonterminal.endswith('_list') :
                return [cls.reduce(element)]

            case 'identifier_list', ('identifier', element, _) :
                return [element]
            case 'identifier_list', ('identifier', element, _), Parser.Node() as rest_of_list :
                return [element] + cls.reduce(rest_of_list)
            case 'identifier_list', ('identifier', element, _), (_, _, _), Parser.Node() as rest_of_list :
                return [element] + cls.reduce(rest_of_list)

            # expression grammar

            case 'number', ('number', n, _) :
                return Expr.ScalarLiteral(n, int)
            case 'number', ('number', n, _), ('char', '.', _), ('number', m, _) :
                return Expr.ScalarLiteral( float(n) + float(m) * (10) ** (-(1 + floor(log10(m)))), float )
            case 'number', ('char', '.', _), ('number', m, _) :
                return Expr.ScalarLiteral( float(m) * (10) ** (-(1 + floor(log10(m)))), float )


            case 'additive', Parser.Node() as left, ('char', '+', _), Parser.Node() as right :
                return Expr.Add( cls.reduce(left), cls.reduce(right) )
            case 'additive', Parser.Node() as left, ('char', '-', _), Parser.Node() as right :
                return Expr.Subtract( cls.reduce(left), cls.reduce(right) )
            case 'multiplicative', Parser.Node() as left, ('char', '*', _), Parser.Node() as right :
                return Expr.Multiply( cls.reduce(left), cls.reduce(right) )
            case 'multiplicative', Parser.Node() as left, ('char', '/', _), Parser.Node() as right :
                return Expr.Divide( cls.reduce(left), cls.reduce(right) )
            case 'unm', (_, '-', _), Parser.Node() as operand :
                return Expr.Unm(cls.reduce(operand))

            case 'additive', ('char', '-', _), Parser.Node() as operand :
                return Expr.Unm(cls.reduce(operand))

            case _, ('string_literal', s, _) :
                return Expr.ScalarLiteral(s, ("varchar", len(s)))        

            case 'condition', Parser.Node() as left, ('char', '=', _), Parser.Node() as right :
                return Expr.Eq(cls.reduce(left), cls.reduce(right))
            case 'condition', Parser.Node() as left, ('char', '<', _), Parser.Node() as right :
                return Expr.Less(cls.reduce(left), cls.reduce(right))
            case 'condition', Parser.Node() as left, ('char', '>', _), Parser.Node() as right :
                return Expr.Less(cls.reduce(right), cls.reduce(left))
            case 'condition', Parser.Node() as left, ('char', '=', _), ('char', '=', _), Parser.Node() as right :
                return Expr.Eq(cls.reduce(left), cls.reduce(right))
            case 'condition', Parser.Node() as left, ('char', '<', _), ('char', '=', _), Parser.Node() as right :
                return Expr.Leq(cls.reduce(left), cls.reduce(right))
            case 'condition', Parser.Node() as left, ('char', '>', _), ('char', '=', _), Parser.Node() as right :
                return Expr.Leq(cls.reduce(right), cls.reduce(left))

            case 'disjunct', Parser.Node() as left, (_, 'OR', _), Parser.Node() as right :
                return Expr.Or(cls.reduce(left), cls.reduce(right))
            case 'conjunct', Parser.Node() as left, (_, 'AND', _), Parser.Node() as right :
                return Expr.And(cls.reduce(left), cls.reduce(right))
            case 'not', (_, 'not', _), Parser.Node() as operand :
                return Expr.Not(cls.reduce(operand))

            case 'boolean_literal', ('identifier', 'FALSE', _) :
                return Expr.BooleanLiteral(False)
            case 'boolean_literal', ('identifier', 'TRUE', _) :
                return Expr.BooleanLiteral(True)

            case 'attribute', ('identifier', left, _), _, ('identifier', right, _):
                return SQL.Attribute(table=left, col=right)
            case 'attribute', ('identifier', colname, _):
                return SQL.Attribute(col=colname)

            case "aggregate", (_, "COUNT", _), _, (_, '*', _), _ :
                return Expr.Count('*')
            case "aggregate", (_, "COUNT", _), _, Parser.Node() as operand, _ :
                return Expr.Count(cls.reduce(operand))
            case "aggregate", (_, "MAX", _), _, Parser.Node() as operand, _ :
                return Expr.Max(cls.reduce(operand))
            case "aggregate", (_, "MIN", _), _, Parser.Node() as operand, _ :
                return Expr.Min(cls.reduce(operand))   
            case "aggregate", (_, "MIN", _), _, Parser.Node() as operand, _ :
                return Expr.Avg(cls.reduce(operand))   

            # sql

            case 'query', Parser.Node() as left, Parser.Node() as operator, Parser.Node() as right :
                return SQL.SetOperator(cls.reduce(left), cls.reduce(right), cls.reduce(operator))
            case 'binary_relational_operator', (_, s, _) : 
                return s
            case 'binary_relational_operator', (_, "UNION", _), (_, "ALL", _) : 
                return "UNION ALL"
            
            
            case 'select', _, *children :
                args = {}
                for c in children:
                    match c:
                        case (_, "DISTINCT", _) :
                            args['distinct'] = True
                        case (_, "AGGREGATE", _) :
                            args['aggregated'] = True
                        case Parser.Node() as node :
                            result = cls.reduce(node)
                            if not isinstance(result, dict): print('huh', result)
                            else:
                                args.update(result)
                
                return SQL.Select(**args)
            
            case 'select_result', (_, '*', _) :
                return {"items": '*'}
            case 'select_result', Parser.Node() as item_list :
                return {"items": cls.reduce(item_list)}
            case 'select_item', Parser.Node() as item, (_, 'AS', _), ('identifier', rename, _) :
                return SQL.Select.Item(cls.reduce(item), rename)

            case 'from', _, Parser.Node() as table_or_subquery :
                return {"from_table": cls.reduce(table_or_subquery)}
            case 'from', _, Parser.Node() as table_or_subquery, Parser.Node() as join_clause :
                joins = cls.reduce(join_clause)
                assert isinstance(joins, list)
                return {"from_table": cls.reduce(table_or_subquery), "from_joins": joins}
            # this code for the join clause sucks
            case 'join_clause', Parser.Node() as operator, Parser.Node() as table_or_subquery, Parser.Node() as condition :
                return [SQL.Join(
                    joinee=cls.reduce(table_or_subquery),
                    on=cls.reduce(condition), 
                    opname=cls.reduce(operator)
                    )]
            case 'join_clause', Parser.Node() as operator, Parser.Node() as table_or_subquery, Parser.Node() as condition, Parser.Node() as additional_join:
                return [SQL.Join(
                    joinee=cls.reduce(table_or_subquery),
                    on=cls.reduce(condition), 
                    opname=cls.reduce(operator)
                    )] + cls.reduce(additional_join)
            case 'join_clause', ('char', ',', _), Parser.Node() as table_or_subquery :
                return [SQL.CommaJoin(joinee=cls.reduce(table_or_subquery))]
            case 'join_clause', ('char', ',', _), Parser.Node() as table_or_subquery, Parser.Node() as additional_join :
                return [SQL.CommaJoin(joinee=cls.reduce(table_or_subquery))] + cls.reduce(additional_join)
            case 'join_condition', _, Parser.Node() as condition :
                return cls.reduce(condition)
            
            case 'table_or_subquery', ('identifier', tablename, _) :
                return SQL.TableName(tablename)
            case 'table_or_subquery', ('identifier', tablename, _), ('identifier', 'AS', _), ('identifier', rename, _) :
                return SQL.TableName(tablename, rename=rename)
            case 'table_or_subquery', _, Parser.Node() as subquery, _, (_, "AS", _), ('identifier', rename, _) :
                return SQL.Subquery(cls.reduce(subquery), rename)

            case 'join_operator', (_, 'JOIN', _) :
                return 'INNER'
            case 'join_operator', (_, jointype, _), (_, 'JOIN', _) :
                return jointype

            case 'where', _, Parser.Node() as condition :
                return {"where": cls.reduce(condition)}
            case 'groupby', _, _, Parser.Node() as attribute_list :
                return {"group_attributes": cls.reduce(attribute_list)}
            case 'having', _, Parser.Node() as condition :
                return {"having": cls.reduce(condition)}
            case 'orderby', _, _, Parser.Node() as scalar_expressions :
                return {"order_by": cls.reduce(scalar_expressions)}
            case 'limit', _, Parser.Node() as limit:
                return {"limit": cls.reduce(limit)}

            case 'create_table', _, _, ('identifier', tablename, _), _, Parser.Node() as column_def_list, _ :
                return SQL.CreateTable(tablename, cls.reduce(column_def_list))
            case 'column_def', ('identifier', col_name, _), Parser.Node() as col_type :
                return Table.ColDef(col_name, cls.reduce(col_type))
            case 'type', (_, 'NUM', _) :
                return int
            case 'type', (_, 'VARCHAR', _) :
                return ("varchar", 255)
            case 'type', (_, 'VARCHAR', _), _, ('number', width, _), _ :
                return ("varchar", width)

            case 'insert', _, _, ('identifier', tablename, _), (_, 'VALUES', _), Parser.Node() as tuple_literal_list :
                return SQL.Insert(into=tablename, data=cls.reduce(tuple_literal_list))
            case 'insert', _, _, ('identifier', tablename, _), _, Parser.Node() as identifier_list, _, (_, 'VALUES', _), Parser.Node() as tuple_literal_list :
                return SQL.Insert(into=tablename, data=cls.reduce(tuple_literal_list), cols=cls.reduce(identifier_list))

            case 'tuple_literal', _, Parser.Node() as tuple_elements, _ :
                return cls.reduce(tuple_elements)

            # trivial cases

            case _, ('char', '(', _), Parser.Node() as child, ('char', ')', _) :
                return cls.reduce(child)
            case _, Parser.Node() as child:
                return cls.reduce(child)
            
            case _, token :
                assert not isinstance(token, Parser.Node)

            



from pprint import pprint

if __name__ == "__main__" :

    # document = "SELECT a, count(b) AS num_b FROM c, d INNER JOIN (SELECT h FROM k) AS e ON e.a=c.a WHERE TRUE GROUP BY A, B HAVING MAX(A)>0 LIMIT 5"
    # document = "SELECT * from a,b,c,d"
    document = "SELECT 1;"
    tokens = list(tokenizer(document))

    recognizer = Recognizer(document=tokens, real_string_input=document, grammar=sql_grammar)
    recognizer.earley_recognize()

    parser = Parser(items = recognizer.state_sets, document=recognizer.document)    
    parse_tree = parser.create_tree()

    parse_tree.prettyprint(simple=True)

    sql_ast = SqlTreeReducer.ast(parse_tree)

    pprint(sql_ast)
    sql_ast.typecheck()